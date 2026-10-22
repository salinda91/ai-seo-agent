import asyncio
import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models import Website, Recommendation, ChangeRecord, AuditLog

logger = logging.getLogger("ai_seo.workflows.codebase.git_fixer")

class LocalCodebaseGitFixer:
    """
    Automates SEO issue fixes for Non-WordPress websites by connecting to
    a local project folder/repository, applying code fixes, and pushing to Git.
    """

    SUPPORTED_EXTENSIONS = [
        ".html", ".htm", ".php", ".blade.php", ".jsx", ".tsx",
        ".vue", ".svelte", ".astro", ".md", ".mdx"
    ]

    async def run_git_command(self, repo_path: Path, args: List[str]) -> Tuple[int, str, str]:
        """Runs a git command in the repository path."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="replace").strip(),
                stderr.decode("utf-8", errors="replace").strip()
            )
        except Exception as e:
            logger.error(f"Failed to execute git {' '.join(args)}: {e}")
            return -1, "", str(e)

    async def validate_repo(self, repo_path_str: str) -> Dict[str, Any]:
        """Validates that path exists and inspects git repository status."""
        p = Path(repo_path_str).resolve()
        if not p.exists() or not p.is_dir():
            return {
                "valid": False,
                "error": f"Directory does not exist: {p}"
            }

        code, out, _ = await self.run_git_command(p, ["rev-parse", "--is-inside-work-tree"])
        is_git = (code == 0 and out == "true")

        current_branch = "main"
        remote_url = ""
        if is_git:
            _, branch_out, _ = await self.run_git_command(p, ["rev-parse", "--abbrev-ref", "HEAD"])
            if branch_out:
                current_branch = branch_out
            _, remote_out, _ = await self.run_git_command(p, ["config", "--get", "remote.origin.url"])
            if remote_out:
                remote_url = remote_out

        return {
            "valid": True,
            "path": str(p),
            "is_git": is_git,
            "current_branch": current_branch,
            "remote_url": remote_url
        }

    def find_file_for_url(self, repo_path: Any, url: str) -> Optional[Path]:
        """
        Maps a crawled URL to a file in the local project repository.
        """
        repo_path = Path(repo_path).resolve()
        parsed = urlparse(url)
        clean_path = parsed.path.strip("/")
        
        # Candidate names
        candidates = []
        if not clean_path or clean_path == "/":
            # Homepage
            candidates = [
                "index.html", "index.htm", "index.php", "resources/views/welcome.blade.php",
                "resources/views/index.blade.php", "app/page.tsx", "app/page.jsx",
                "pages/index.tsx", "pages/index.jsx", "pages/index.js", "src/pages/index.tsx",
                "src/pages/index.astro", "public/index.html"
            ]
        else:
            candidates = [
                f"{clean_path}.html",
                f"{clean_path}/index.html",
                f"{clean_path}.htm",
                f"{clean_path}.php",
                f"resources/views/{clean_path}.blade.php",
                f"resources/views/pages/{clean_path}.blade.php",
                f"app/{clean_path}/page.tsx",
                f"app/{clean_path}/page.jsx",
                f"pages/{clean_path}.tsx",
                f"pages/{clean_path}.jsx",
                f"pages/{clean_path}/index.tsx",
                f"src/pages/{clean_path}.tsx",
                f"public/{clean_path}.html",
                f"content/{clean_path}.md"
            ]

        # 1. Check direct candidates
        for c in candidates:
            target = repo_path / c
            if target.exists() and target.is_file():
                return target

        # 2. Search recursively by filename matching the slug
        slug = clean_path.split("/")[-1] if clean_path else "index"
        for ext in self.SUPPORTED_EXTENSIONS:
            for match in repo_path.rglob(f"*{slug}*{ext}"):
                if "node_modules" not in match.parts and ".git" not in match.parts and "vendor" not in match.parts:
                    return match

        # 3. Fallback: if homepage, look for any index file
        if not clean_path or clean_path == "/":
            for match in repo_path.glob("index.*"):
                if match.is_file():
                    return match

        return None

    def apply_fix_to_content(
        self,
        content: str,
        category: str,
        issue_title: str,
        new_val: str,
        before_val: Optional[str] = None,
        field_hint: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Applies SEO tag insertion or replacement to raw file content.
        Returns: (success: bool, updated_content: str, field_name: str)
        """
        title_lower = (issue_title or "").lower()
        hint_lower = (field_hint or "").lower()
        original_content = content
        field_name = "custom"

        # 1. Title Tag
        if hint_lower == "title" or "title" in title_lower or category == "title":
            field_name = "title"
            if re.search(r"<title[^>]*>.*?</title>", content, re.IGNORECASE | re.DOTALL):
                content = re.sub(
                    r"<title[^>]*>.*?</title>",
                    f"<title>{new_val}</title>",
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f"\\1\n    <title>{new_val}</title>",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "export const metadata" in content:
                # Next.js App Router
                content = re.sub(
                    r"title:\s*['\"][^'\"]*['\"]",
                    f"title: '{new_val}'",
                    content,
                    count=1
                )

        # 2. Meta Description
        elif hint_lower in ("meta_description", "description") or "meta description" in title_lower or "description" in title_lower:
            field_name = "meta_description"
            meta_desc_regex = r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\']\s*\/?>'
            if re.search(meta_desc_regex, content, re.IGNORECASE):
                content = re.sub(
                    meta_desc_regex,
                    f'<meta name="description" content="{new_val}">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <meta name="description" content="{new_val}">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "export const metadata" in content:
                content = re.sub(
                    r"description:\s*['\"][^'\"]*['\"]",
                    f"description: '{new_val}'",
                    content,
                    count=1
                )

        # 3. Canonical Tag
        elif hint_lower == "canonical" or "canonical" in title_lower:
            field_name = "canonical"
            can_regex = r'<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']\s*\/?>'
            if re.search(can_regex, content, re.IGNORECASE):
                content = re.sub(
                    can_regex,
                    f'<link rel="canonical" href="{new_val}" />',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <link rel="canonical" href="{new_val}" />',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 4. Viewport Tag
        elif hint_lower == "viewport" or "viewport" in title_lower:
            field_name = "viewport"
            if "<head>" in content.lower() and "name=\"viewport\"" not in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 5. Image Alt Attributes
        elif hint_lower in ("image_alt", "alt") or "alt" in title_lower or "images" in title_lower:
            field_name = "image_alt"
            # Find img tags without alt or with empty alt
            def alt_replacer(match):
                tag = match.group(0)
                if 'alt=' not in tag.lower():
                    return tag[:-1] + f' alt="{new_val}">'
                elif 'alt=""' in tag or "alt=''" in tag:
                    return tag.replace('alt=""', f'alt="{new_val}"').replace("alt=''", f'alt="{new_val}"')
                return tag

            content = re.sub(r'<img\s+[^>]*>', alt_replacer, content, count=3, flags=re.IGNORECASE)

        # 6. Structured Data (Schema.org JSON-LD)
        elif hint_lower in ("schema", "schema_org") or "structured data" in title_lower or "schema" in title_lower:
            field_name = "schema_org"
            schema_block = f'\n    <script type="application/ld+json">\n{new_val}\n    </script>\n'
            if "</head>" in content.lower():
                content = re.sub(
                    r"(<\/head>)",
                    f'{schema_block}\\1',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 7. H1 Heading Tag
        elif hint_lower in ("h1", "heading") or "h1" in title_lower or "heading" in title_lower or category == "headings":
            field_name = "h1"
            if re.search(r"<h1[^>]*>.*?</h1>", content, re.IGNORECASE | re.DOTALL):
                content = re.sub(
                    r"<h1([^>]*)>.*?</h1>",
                    f"<h1\\1>{new_val}</h1>",
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL
                )
            elif "<body" in content.lower():
                content = re.sub(
                    r"(<body[^>]*>)",
                    f"\\1\n    <h1>{new_val}</h1>",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "<main" in content.lower():
                content = re.sub(
                    r"(<main[^>]*>)",
                    f"\\1\n    <h1>{new_val}</h1>",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        success = (content != original_content)
        return success, content, field_name

    async def fix_and_push_codebase(
        self,
        website_id: int,
        repo_path_str: str,
        db: AsyncSession,
        git_branch: str = "main",
        git_remote: str = "origin",
        auto_push: bool = True
    ) -> Dict[str, Any]:
        """
        Main execution pipeline:
        1. Validates local repository path
        2. Queries all eligible recommendations for the website
        3. Identifies target files and applies code fixes
        4. Stages, commits, and pushes changes to Git
        5. Updates database records with diffs and applied status
        """
        repo_path = Path(repo_path_str).resolve()
        val = await self.validate_repo(str(repo_path))
        if not val["valid"]:
            return {"success": False, "error": val.get("error")}

        branch = git_branch or val.get("current_branch") or "main"
        remote = git_remote or "origin"

        # Initialize git if not already a repo
        if not val.get("is_git"):
            await self.run_git_command(repo_path, ["init"])
            await self.run_git_command(repo_path, ["checkout", "-b", branch])

        # Query suggested recommendations
        stmt = select(Recommendation).where(
            Recommendation.website_id == website_id,
            Recommendation.status == "suggested"
        )
        res = await db.execute(stmt)
        recs = res.scalars().all()

        if not recs:
            return {
                "success": True,
                "message": "No pending SEO recommendations to apply.",
                "fixes_applied": 0,
                "modified_files": []
            }

        fixes_applied = 0
        modified_files = set()
        change_records_saved = []

        for rec in recs:
            target_file = self.find_file_for_url(repo_path, rec.url)
            if not target_file or not target_file.exists():
                logger.debug(f"Could not map URL '{rec.url}' to a file in {repo_path}")
                continue

            try:
                content = target_file.read_text(encoding="utf-8", errors="replace")
                
                # Determine value to inject
                new_value = ""
                change_data = rec.proposed_change_data or {}
                if change_data.get("new_value"):
                    new_value = change_data["new_value"]
                elif change_data.get("proposed_value"):
                    new_value = change_data["proposed_value"]
                elif change_data.get("after", {}).get("meta_description"):
                    new_value = change_data["after"]["meta_description"]
                elif change_data.get("after", {}).get("title"):
                    new_value = change_data["after"]["title"]
                elif "title" in rec.issue_title.lower():
                    new_value = rec.proposed_fix.split(":")[-1].strip(" '\"")
                elif "description" in rec.issue_title.lower():
                    new_value = rec.proposed_fix.split(":")[-1].strip(" '\"")
                else:
                    new_value = rec.proposed_fix

                success, updated_content, field_name = self.apply_fix_to_content(
                    content=content,
                    category=rec.category,
                    issue_title=rec.issue_title,
                    new_val=new_value,
                    before_val=rec.evidence
                )

                if success:
                    target_file.write_text(updated_content, encoding="utf-8")
                    fixes_applied += 1
                    rel_path = str(target_file.relative_to(repo_path))
                    modified_files.add(rel_path)

                    rec.status = "applied"
                    change_rec = ChangeRecord(
                        website_id=website_id,
                        recommendation_id=rec.id,
                        url=rec.url,
                        field_name=f"{rel_path}:{field_name}",
                        before_value=rec.evidence or "empty",
                        after_value=new_value,
                        status="applied"
                    )
                    db.add(change_rec)
                    change_records_saved.append(rel_path)

            except Exception as e:
                logger.warning(f"Error applying fix to {target_file}: {e}")

        await db.commit()

        if fixes_applied == 0:
            return {
                "success": True,
                "message": "Scanned repository, but could not safely match audit issues to file templates.",
                "fixes_applied": 0,
                "modified_files": []
            }

        # Git Stage & Commit
        commit_sha = ""
        commit_msg = f"fix(seo): auto-fix {fixes_applied} technical SEO audit issues\n\nModified files:\n" + "\n".join([f"- {f}" for f in modified_files])
        
        await self.run_git_command(repo_path, ["add", "."])
        c_code, c_out, c_err = await self.run_git_command(repo_path, ["commit", "-m", commit_msg])
        
        if c_code == 0:
            _, sha_out, _ = await self.run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
            commit_sha = sha_out
            logger.info(f"Committed SEO fixes in {repo_path}: {commit_sha}")

        # Git Push
        push_success = False
        push_message = ""
        if auto_push and val.get("remote_url"):
            p_code, p_out, p_err = await self.run_git_command(repo_path, ["push", remote, branch])
            if p_code == 0:
                push_success = True
                push_message = f"Successfully pushed commit {commit_sha} to {remote}/{branch}."
                logger.info(push_message)
            else:
                push_message = f"Committed locally ({commit_sha}), but git push encountered: {p_err or p_out}. Please run 'git push' with authorized credentials."
                logger.warning(push_message)
        else:
            push_message = f"Changes committed locally ({commit_sha}). No git remote configured or auto-push disabled."

        # Audit Log
        audit = AuditLog(
            website_id=website_id,
            action="codebase_seo_autofix_git_push",
            details={
                "repo_path": str(repo_path),
                "fixes_applied": fixes_applied,
                "files_modified": list(modified_files),
                "commit_sha": commit_sha,
                "pushed": push_success,
                "push_message": push_message
            },
            status="success"
        )
        db.add(audit)
        await db.commit()

        return {
            "success": True,
            "fixes_applied": fixes_applied,
            "modified_files": list(modified_files),
            "commit_sha": commit_sha,
            "pushed": push_success,
            "message": f"Successfully applied {fixes_applied} SEO fixes across {len(modified_files)} files. {push_message}"
        }

    async def apply_single_change(
        self,
        website_id: int,
        repo_path_str: str,
        url: str,
        field_name: str,
        new_value: str,
        db: AsyncSession,
        recommendation_id: Optional[int] = None,
        git_branch: str = "main",
        git_remote: str = "origin",
        auto_push: bool = True
    ) -> Dict[str, Any]:
        """
        Applies a single recommendation/change directly to the matching source code file in repo_path_str,
        creates a git commit, optionally pushes to remote, and logs ChangeRecord and AuditLog.
        """
        repo_path = Path(repo_path_str).resolve()
        val = await self.validate_repo(str(repo_path))
        if not val["valid"]:
            return {"success": False, "error": val.get("error", "Invalid repository directory path.")}

        branch = git_branch or val.get("current_branch") or "main"
        remote = git_remote or "origin"

        # Initialize git if not already a repo
        if not val.get("is_git"):
            await self.run_git_command(repo_path, ["init"])
            await self.run_git_command(repo_path, ["checkout", "-b", branch])

        target_file = self.find_file_for_url(repo_path, url)
        if not target_file or not target_file.exists():
            return {
                "success": False,
                "error": f"Could not find matching code template file for URL '{url}' in {repo_path}. Please check your project structure."
            }

        try:
            content = target_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"success": False, "error": f"Could not read {target_file}: {e}"}

        # Look up recommendation if provided
        rec = None
        category = "meta_tags"
        issue_title = field_name
        before_val = None
        if recommendation_id:
            stmt_rec = select(Recommendation).where(Recommendation.id == recommendation_id)
            res_rec = await db.execute(stmt_rec)
            rec = res_rec.scalar_one_or_none()
            if rec:
                category = rec.category or category
                issue_title = rec.issue_title or issue_title
                before_val = rec.evidence

        success, updated_content, actual_field = self.apply_fix_to_content(
            content=content,
            category=category,
            issue_title=issue_title,
            new_val=new_value,
            before_val=before_val,
            field_hint=field_name
        )

        if not success:
            return {
                "success": False,
                "error": f"Could not safely apply {field_name} change to {target_file.name}. Tag pattern not found."
            }

        # Write to file
        target_file.write_text(updated_content, encoding="utf-8")
        rel_path = str(target_file.relative_to(repo_path))

        # Update recommendation status
        if rec:
            rec.status = "applied"

        # ChangeRecord
        change_rec = ChangeRecord(
            website_id=website_id,
            recommendation_id=recommendation_id,
            url=url,
            field_name=f"{rel_path}:{actual_field}",
            before_value=before_val or "empty",
            after_value=new_value,
            status="applied"
        )
        db.add(change_rec)

        # Git Stage & Commit
        commit_sha = ""
        commit_msg = f"fix(seo): update {actual_field} in {rel_path} for {url}"
        await self.run_git_command(repo_path, ["add", str(target_file)])
        c_code, c_out, c_err = await self.run_git_command(repo_path, ["commit", "-m", commit_msg])
        if c_code == 0:
            _, sha_out, _ = await self.run_git_command(repo_path, ["rev-parse", "--short", "HEAD"])
            commit_sha = sha_out.strip()
            logger.info(f"Committed SEO fix {commit_sha} to {rel_path}")

        # Git Push
        pushed = False
        push_message = ""
        if auto_push and val.get("remote_url"):
            p_code, p_out, p_err = await self.run_git_command(repo_path, ["push", remote, branch])
            if p_code == 0:
                pushed = True
                push_message = f"Pushed commit {commit_sha} to {remote}/{branch}."
            else:
                push_message = f"Committed locally ({commit_sha}), but git push encountered: {p_err or p_out}"
        else:
            push_message = f"Committed locally ({commit_sha})."

        # AuditLog
        audit = AuditLog(
            website_id=website_id,
            action="codebase_single_apply_git_push",
            details={
                "file": rel_path,
                "url": url,
                "field": actual_field,
                "commit_sha": commit_sha,
                "pushed": pushed
            },
            status="success"
        )
        db.add(audit)
        await db.commit()

        return {
            "success": True,
            "applied_to": "code",
            "file": rel_path,
            "field": actual_field,
            "commit_sha": commit_sha,
            "pushed": pushed,
            "message": f"Applied {actual_field} fix to {rel_path} and committed to Git ({commit_sha}). {push_message}"
        }

local_codebase_fixer = LocalCodebaseGitFixer()
