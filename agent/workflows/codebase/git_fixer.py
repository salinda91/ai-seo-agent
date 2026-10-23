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

INSTRUCTION_PREFIXES = (
    "fix ", "add ", "update ", "ensure ", "missing ", "todo:", "replace ",
    "remove ", "optimize ", "audit ", "publish ", "resolve "
)

INSTRUCTION_KEYWORDS = (
    "missing_h1", "missing_title", "missing_meta_description", "missing_canonical",
    "missing_structured_data", "thin_content", "long_title", "long_meta_description",
    "images_missing_alt", "120-160 characters", "summarizing page content",
    "primary keyword", "prevent duplicate content indexing", "descriptive alt attributes",
    "on https://", "on http://"
)

def is_instruction_or_defect_string(text: Optional[str]) -> bool:
    if not text or not isinstance(text, str):
        return True
    t = text.strip()
    if not t:
        return True
    t_lower = t.lower()
    if any(t_lower.startswith(p) for p in INSTRUCTION_PREFIXES):
        return True
    if any(kw in t_lower for kw in INSTRUCTION_KEYWORDS):
        return True
    if re.match(r"^https?:\/\/", t, re.IGNORECASE) or t.startswith("//"):
        return True
    return False

def format_brand_name_from_domain(domain_part: str) -> str:
    s = domain_part.replace('-', ' ').replace('_', ' ')
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    if ' ' not in s:
        words = ['ocean', 'view', 'beach', 'resort', 'villas', 'villa', 'hotel', 'travel', 'tours', 'safari', 'kitesurf', 'labs', 'lab', 'tech', 'cloud', 'digital', 'global', 'solutions', 'live', 'life']
        pattern = '|'.join(words)
        spaced = re.sub(f'({pattern})', r' \1 ', s, flags=re.IGNORECASE)
        s = ' '.join(spaced.split())
    return s.title()

def synthesize_fallback_seo_copy(url: str, field_name: str, existing_title: Optional[str] = None) -> str:
    parsed = urlparse(url)
    slug = parsed.path.strip("/")
    domain = parsed.netloc.replace("www.", "").split(":")[0]
    domain_part = domain.split(".")[0]
    brand_name = format_brand_name_from_domain(domain_part) if domain_part else "Website"

    slug_map = {
        "": "Home",
        "stay": "Accommodations & Cabanas",
        "dine": "Dining & Local Flavours",
        "experiences": "Adventures & Experiences",
        "faq": "Frequently Asked Questions",
        "location": "Location & Directions",
        "offers": "Special Offers & Packages",
        "about": "About Us",
        "contact": "Contact Us",
        "privacy-policy": "Privacy Policy"
    }
    slug_clean = slug.lower().strip("/")
    slug_title = slug_map.get(slug_clean)
    if not slug_title:
        last_seg = slug_clean.split("/")[-1]
        slug_title = last_seg.replace("-", " ").replace("_", " ").title() if last_seg else brand_name

    if field_name == "h1":
        return slug_title if slug_clean else f"Welcome to {brand_name}"
    elif field_name == "meta_description":
        return f"Discover {slug_title} at {brand_name}. High quality service, authentic experiences, and complete information."
    elif field_name == "title":
        return f"{slug_title} | {brand_name}"
    elif field_name == "canonical":
        return url
    elif field_name == "image_alt":
        return f"{slug_title} photo"
    return slug_title

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

    def sanitize_or_synthesize_seo_value(
        self,
        raw_val: Optional[str],
        field_name: str,
        url: str,
        existing_content: str = "",
        title_hint: Optional[str] = None
    ) -> str:
        """
        Guarantees that no instruction text, defect name, or raw URL is ever
        injected into user source code (HTML/JSX/Blade/etc.).
        """
        val = (raw_val or "").strip()

        # Canonical field legitimately expects a valid URL
        if field_name == "canonical":
            if re.match(r"^https?:\/\/", val, re.IGNORECASE):
                return val
            return url

        # For user-facing text (h1, title, meta_description, image_alt):
        if is_instruction_or_defect_string(val):
            # Try to extract quoted candidate if present: e.g. Update title to: 'My Title'
            quoted_match = re.search(r"['\"]([^'\"]{3,})['\"]", val)
            if quoted_match:
                cand = quoted_match.group(1).strip()
                if not is_instruction_or_defect_string(cand):
                    return cand
            return synthesize_fallback_seo_copy(url, field_name, title_hint)

        val = val.strip("'\"")
        return val

    def apply_fix_to_content(
        self,
        content: str,
        category: str,
        issue_title: str,
        new_val: str,
        before_val: Optional[str] = None,
        field_hint: Optional[str] = None,
        url: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Applies SEO tag insertion or replacement to raw file content.
        Protects existing valid user headings and titles from being overwritten.
        Returns: (success: bool, updated_content: str, field_name: str)
        """
        title_lower = (issue_title or "").lower()
        hint_lower = (field_hint or "").lower()
        original_content = content
        field_name = "custom"

        # Determine effective field name
        if hint_lower in ("title",) or "title" in title_lower or category == "title":
            field_name = "title"
        elif hint_lower in ("meta_description", "description") or "description" in title_lower or "meta" in title_lower:
            field_name = "meta_description"
        elif hint_lower in ("canonical",) or "canonical" in title_lower:
            field_name = "canonical"
        elif hint_lower in ("viewport",) or "viewport" in title_lower:
            field_name = "viewport"
        elif hint_lower in ("image_alt", "alt") or "alt" in title_lower or "images" in title_lower:
            field_name = "image_alt"
        elif hint_lower in ("schema", "schema_org") or "structured data" in title_lower or "schema" in title_lower:
            field_name = "schema_org"
        elif hint_lower in ("h1", "heading") or "h1" in title_lower or "heading" in title_lower or category == "headings":
            field_name = "h1"

        # Sanitize value to guarantee zero instruction/defect text leak
        clean_val = self.sanitize_or_synthesize_seo_value(
            raw_val=new_val,
            field_name=field_name,
            url=url or "",
            existing_content=content,
            title_hint=issue_title
        )

        # 1. Title Tag
        if field_name == "title":
            if "missing" in title_lower:
                title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
                helmet_title = re.search(r'title=["\']([^"\']+)["\']', content)
                meta_title = re.search(r"title:\s*['\"]([^'\"]+)['\"]", content)
                existing_text = ""
                if title_match:
                    existing_text = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
                elif helmet_title:
                    existing_text = helmet_title.group(1).strip()
                elif meta_title:
                    existing_text = meta_title.group(1).strip()

                if len(existing_text) > 3 and not is_instruction_or_defect_string(existing_text):
                    logger.info(f"Existing valid title preserved: '{existing_text[:40]}...'. Not overwriting.")
                    return False, content, "title"

            if re.search(r"<title[^>]*>.*?</title>", content, re.IGNORECASE | re.DOTALL):
                content = re.sub(
                    r"<title[^>]*>.*?</title>",
                    f"<title>{clean_val}</title>",
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL
                )
            elif "title=" in content and ("SeoHelmet" in content or "Helmet" in content):
                content = re.sub(
                    r'title=["\'][^"\']*["\']',
                    f'title="{clean_val}"',
                    content,
                    count=1
                )
            elif "export const metadata" in content:
                content = re.sub(
                    r"title:\s*['\"][^'\"]*['\"]",
                    f"title: '{clean_val}'",
                    content,
                    count=1
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f"\\1\n    <title>{clean_val}</title>",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 2. Meta Description
        elif field_name == "meta_description":
            if "missing" in title_lower:
                desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', content, re.IGNORECASE)
                helmet_desc = re.search(r'description=["\']([^"\']+)["\']', content)
                meta_desc = re.search(r"description:\s*['\"]([^'\"]+)['\"]", content)
                existing_text = ""
                if desc_match:
                    existing_text = desc_match.group(1).strip()
                elif helmet_desc:
                    existing_text = helmet_desc.group(1).strip()
                elif meta_desc:
                    existing_text = meta_desc.group(1).strip()

                if len(existing_text) > 15 and not is_instruction_or_defect_string(existing_text):
                    logger.info(f"Existing valid meta description preserved: '{existing_text[:40]}...'. Not overwriting.")
                    return False, content, "meta_description"

            meta_desc_regex = r'<meta\s+name=["\']description["\']\s+content=["\'][^"\']*["\']\s*\/?>'
            if re.search(meta_desc_regex, content, re.IGNORECASE):
                content = re.sub(
                    meta_desc_regex,
                    f'<meta name="description" content="{clean_val}">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "description=" in content and ("SeoHelmet" in content or "Helmet" in content):
                content = re.sub(
                    r'description=["\'][^"\']*["\']',
                    f'description="{clean_val}"',
                    content,
                    count=1
                )
            elif "export const metadata" in content:
                content = re.sub(
                    r"description:\s*['\"][^'\"]*['\"]",
                    f"description: '{clean_val}'",
                    content,
                    count=1
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <meta name="description" content="{clean_val}">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 3. Canonical Tag
        elif field_name == "canonical":
            if "missing" in title_lower:
                can_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']*)["\']', content, re.IGNORECASE)
                helmet_can = re.search(r'canonical=["\']([^"\']+)["\']', content)
                if (can_match and can_match.group(1).strip()) or (helmet_can and helmet_can.group(1).strip()):
                    logger.info("Existing canonical link already present. Not overwriting.")
                    return False, content, "canonical"

            can_regex = r'<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']\s*\/?>'
            if re.search(can_regex, content, re.IGNORECASE):
                content = re.sub(
                    can_regex,
                    f'<link rel="canonical" href="{clean_val}" />',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "canonical=" in content and ("SeoHelmet" in content or "Helmet" in content):
                content = re.sub(
                    r'canonical=["\'][^"\']*["\']',
                    f'canonical="{clean_val}"',
                    content,
                    count=1
                )
            elif "<head>" in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <link rel="canonical" href="{clean_val}" />',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 4. Viewport Tag
        elif field_name == "viewport":
            if "<head>" in content.lower() and "name=\"viewport\"" not in content.lower():
                content = re.sub(
                    r"(<head[^>]*>)",
                    f'\\1\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 5. Image Alt Attributes
        elif field_name == "image_alt":
            def alt_replacer(match):
                tag = match.group(0)
                if 'alt=' not in tag.lower():
                    return tag[:-1] + f' alt="{clean_val}">'
                elif 'alt=""' in tag or "alt=''" in tag:
                    return tag.replace('alt=""', f'alt="{clean_val}"').replace("alt=''", f'alt="{clean_val}"')
                return tag

            content = re.sub(r'<img\s+[^>]*>', alt_replacer, content, count=3, flags=re.IGNORECASE)

        # 6. Structured Data (Schema.org JSON-LD)
        elif field_name == "schema_org":
            schema_block = f'\n    <script type="application/ld+json">\n{clean_val}\n    </script>\n'
            if "</head>" in content.lower():
                content = re.sub(
                    r"(<\/head>)",
                    f'{schema_block}\\1',
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )

        # 7. H1 Heading Tag
        elif field_name == "h1":
            h1_match = re.search(r"<h1([^>]*)>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
            if h1_match:
                attrs = h1_match.group(1)
                inner_h1 = h1_match.group(2)
                plain_inner = re.sub(r"<[^>]+>", "", inner_h1).strip()
                # If existing H1 has genuine content and is not an instruction string: PRESERVE IT!
                if len(plain_inner) > 3 and not is_instruction_or_defect_string(plain_inner):
                    logger.info(f"Existing valid <h1> preserved: '{plain_inner[:40]}...'. Not overwriting.")
                    return False, content, "h1"

                # Otherwise (empty or corrupted instruction string), replace it cleanly
                content = re.sub(
                    r"<h1([^>]*)>.*?</h1>",
                    f"<h1\\1>{clean_val}</h1>",
                    content,
                    count=1,
                    flags=re.IGNORECASE | re.DOTALL
                )
            elif "<body" in content.lower():
                content = re.sub(
                    r"(<body[^>]*>)",
                    f"\\1\n    <h1>{clean_val}</h1>",
                    content,
                    count=1,
                    flags=re.IGNORECASE
                )
            elif "<main" in content.lower():
                content = re.sub(
                    r"(<main[^>]*>)",
                    f"\\1\n    <h1>{clean_val}</h1>",
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
                
                # Determine candidate value and field hint
                change_data = rec.proposed_change_data or {}
                candidate_value = ""
                if change_data.get("new_value"):
                    candidate_value = change_data["new_value"]
                elif change_data.get("proposed_value"):
                    candidate_value = change_data["proposed_value"]
                elif change_data.get("after", {}).get("meta_description"):
                    candidate_value = change_data["after"]["meta_description"]
                elif change_data.get("after", {}).get("title"):
                    candidate_value = change_data["after"]["title"]
                elif rec.proposed_fix:
                    candidate_value = rec.proposed_fix

                # Determine field hint
                field_hint = None
                title_lower = (rec.issue_title or "").lower()
                if "title" in title_lower:
                    field_hint = "title"
                elif "description" in title_lower or "meta" in title_lower:
                    field_hint = "meta_description"
                elif "h1" in title_lower or "heading" in title_lower or rec.category == "headings":
                    field_hint = "h1"
                elif "canonical" in title_lower:
                    field_hint = "canonical"
                elif "alt" in title_lower or "image" in title_lower:
                    field_hint = "image_alt"

                new_value = self.sanitize_or_synthesize_seo_value(
                    raw_val=candidate_value,
                    field_name=field_hint or "custom",
                    url=rec.url,
                    existing_content=content,
                    title_hint=rec.issue_title
                )

                success, updated_content, field_name = self.apply_fix_to_content(
                    content=content,
                    category=rec.category,
                    issue_title=rec.issue_title,
                    new_val=new_value,
                    before_val=rec.evidence,
                    field_hint=field_hint,
                    url=rec.url
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
                else:
                    # If already satisfied in template, mark applied so it doesn't linger as unresolved defect
                    if field_hint in ("h1", "title", "meta_description", "canonical"):
                        logger.info(f"Recommendation ID={rec.id} ({rec.issue_title}) for {rec.url} already satisfied in {target_file.name}. Marking as applied.")
                        rec.status = "applied"

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

        sanitized_value = self.sanitize_or_synthesize_seo_value(
            raw_val=new_value,
            field_name=field_name,
            url=url,
            existing_content=content,
            title_hint=issue_title
        )

        success, updated_content, actual_field = self.apply_fix_to_content(
            content=content,
            category=category,
            issue_title=issue_title,
            new_val=sanitized_value,
            before_val=before_val,
            field_hint=field_name,
            url=url
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
            after_value=sanitized_value,
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
