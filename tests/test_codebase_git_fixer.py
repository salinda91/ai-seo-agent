import os
import shutil
import tempfile
import subprocess
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.models import Recommendation
from agent.workflows.codebase.git_fixer import LocalCodebaseGitFixer, local_codebase_fixer

@pytest.mark.asyncio
async def test_validate_repo():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Non-git directory
        res = await local_codebase_fixer.validate_repo(tmp_dir)
        assert res["valid"] is True
        assert res["is_git"] is False

        # Init git
        subprocess.run(["git", "init"], cwd=tmp_dir, capture_output=True, check=True)
        res_git = await local_codebase_fixer.validate_repo(tmp_dir)
        assert res_git["valid"] is True
        assert res_git["is_git"] is True

@pytest.mark.asyncio
async def test_find_file_for_url():
    fixer = LocalCodebaseGitFixer()
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create standard index.html and about.blade.php
        index_file = os.path.join(tmp_dir, "index.html")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("<html><head><title>Old</title></head><body>Hello</body></html>")

        views_dir = os.path.join(tmp_dir, "resources", "views")
        os.makedirs(views_dir, exist_ok=True)
        about_file = os.path.join(views_dir, "about.blade.php")
        with open(about_file, "w", encoding="utf-8") as f:
            f.write("<div>About Us</div>")

        found_root = fixer.find_file_for_url(tmp_dir, "https://example.com/")
        assert found_root is not None
        assert os.path.basename(found_root) == "index.html"

        found_about = fixer.find_file_for_url(tmp_dir, "https://example.com/about")
        assert found_about is not None
        assert os.path.basename(found_about) == "about.blade.php"

@pytest.mark.asyncio
async def test_apply_fix_to_code():
    fixer = LocalCodebaseGitFixer()
    raw_html = "<html><head><title>Old Title</title></head><body><img src=\"/logo.png\"></body></html>"

    # Title replacement
    ok, modified_title, field = fixer.apply_fix_to_content(raw_html, "meta_tags", "Page Title Optimization", "Brand New SEO Title")
    assert ok is True
    assert "<title>Brand New SEO Title</title>" in modified_title

    # Meta description injection
    ok2, modified_desc, field2 = fixer.apply_fix_to_content(raw_html, "meta_tags", "Missing Meta Description", "Target high intent keywords here.")
    assert ok2 is True
    assert '<meta name="description" content="Target high intent keywords here.">' in modified_desc

    # Image alt tag injection
    ok3, modified_alt, field3 = fixer.apply_fix_to_content(raw_html, "images", "Missing Image Alt Tags", "Company official logo")
    assert ok3 is True
    assert '<img src="/logo.png" alt="Company official logo">' in modified_alt

    # Canonical URL injection
    ok4, modified_can, field4 = fixer.apply_fix_to_content(raw_html, "technical", "Canonical URL Missing", "https://example.com/canonical-url")
    assert ok4 is True
    assert '<link rel="canonical" href="https://example.com/canonical-url" />' in modified_can

@pytest.mark.asyncio
async def test_fix_and_commit_codebase():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Setup git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir, capture_output=True, check=True)

        index_file = os.path.join(tmp_dir, "index.html")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>Old Title</title></head><body><h1>Welcome</h1></body></html>")

        subprocess.run(["git", "add", "."], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_dir, capture_output=True, check=True)

        # 2. Mock recommendation and DB session (avoids inserting dummy sites into live DB)
        rec = Recommendation(
            id=9999,
            website_id=1,
            url="https://example.com/",
            issue_title="Missing Meta Description",
            severity="high",
            category="meta_tags",
            proposed_fix="Add descriptive meta description",
            proposed_change_data={
                "field": "meta_description",
                "proposed_value": "The best test website for SEO auto-fixing."
            },
            status="suggested"
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rec]
        mock_db.execute.return_value = mock_result

        # 3. Run fix_and_push_codebase (auto_push=False so we don't push to non-existent remote)
        result = await local_codebase_fixer.fix_and_push_codebase(
            website_id=1,
            repo_path_str=tmp_dir,
            db=mock_db,
            git_branch="main",
            auto_push=False
        )

        assert result["success"] is True
        assert result["fixes_applied"] >= 1
        assert result["commit_sha"] is not None

        # Verify file modified on disk
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert '<meta name="description" content="The best test website for SEO auto-fixing.">' in content

        # Verify recommendation was marked applied
        assert rec.status == "applied"
        assert mock_db.commit.called is True

@pytest.mark.asyncio
async def test_apply_single_change_to_codebase():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Setup git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir, capture_output=True, check=True)

        index_file = os.path.join(tmp_dir, "index.html")
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>Old Title</title></head><body><h1>Welcome</h1></body></html>")

        subprocess.run(["git", "add", "."], cwd=tmp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_dir, capture_output=True, check=True)

        rec = Recommendation(
            id=1234,
            website_id=1,
            url="https://example.com/",
            issue_title="Page Title Optimization",
            severity="high",
            category="title",
            proposed_fix="Brand New Page Title",
            proposed_change_data={
                "field": "title",
                "proposed_value": "Brand New Page Title"
            },
            status="suggested"
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rec
        mock_db.execute.return_value = mock_result

        # 2. Call apply_single_change
        result = await local_codebase_fixer.apply_single_change(
            website_id=1,
            repo_path_str=tmp_dir,
            url="https://example.com/",
            field_name="title",
            new_value="Brand New Page Title",
            db=mock_db,
            recommendation_id=1234,
            git_branch="main",
            auto_push=False
        )

        assert result["success"] is True
        assert result["file"] == "index.html"
        assert result["commit_sha"] is not None

        # Verify on disk
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<title>Brand New Page Title</title>" in content
        assert rec.status == "applied"
        assert mock_db.commit.called is True
