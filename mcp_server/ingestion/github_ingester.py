"""
CrossContext - Dynamic GitHub Repository Ingester
Clones and indexes real-world multi-repository codebases from GitHub or local paths.
Parses AST boundaries, discovers cross-repo dependencies, and registers symbols in the knowledge graph.
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from mcp_server.tools import CodeGraphToolManager


class GitHubRepoIngester:
    def __init__(self, base_storage_dir: Optional[str] = None):
        """
        Initializes the ingester. Repositories are cloned into `data/repos/<repo_name>`.
        """
        if base_storage_dir:
            self.base_dir = Path(base_storage_dir)
        else:
            self.base_dir = Path("data/repos")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_repo_name(url_or_path: str) -> str:
        """Extracts a clean repository name from a GitHub URL or filesystem path."""
        cleaned = url_or_path.strip().rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        # Match github.com/org/repo or local/path/to/repo
        parts = re.split(r'[/:\\]', cleaned)
        name = parts[-1] if parts else "unknown_repo"
        # Sanitize to valid directory name
        name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
        return name

    _ORG_CACHE: Dict[str, List[str]] = {}

    @classmethod
    def fetch_organization_repos(cls, org_name: str) -> List[str]:
        """
        Discovers and returns all repository clone URLs for any given GitHub organization or user account.
        Supports:
          - Org names: 'Project-HAMi', 'pallets', 'fastapi', 'kubernetes'
          - Org/Repo URLs: 'https://github.com/orgs/Project-HAMi/repositories', 'https://github.com/Project-HAMi'
          - Direct Repo URLs: 'https://github.com/Project-HAMi/HAMi'
        Uses cached responses and GitHub REST API with resilient SSL context.
        """
        raw_clean = org_name.strip().rstrip("/")
        if not raw_clean:
            return []

        # Check if direct single repository URL was provided
        if "github.com/" in raw_clean:
            path_parts = raw_clean.split("github.com/")[-1].strip("/").split("/")
            if len(path_parts) == 2 and path_parts[0] not in ("orgs", "users"):
                # e.g. https://github.com/Project-HAMi/HAMi
                repo_url = f"https://github.com/{path_parts[0]}/{path_parts[1].replace('.git', '')}.git"
                return [repo_url]

        clean_org = raw_clean
        if "github.com/" in clean_org:
            clean_org = clean_org.split("github.com/")[-1]
            clean_org = re.sub(r'^(?:orgs|users)/', '', clean_org)
            clean_org = clean_org.split("/")[0]
        clean_org = re.sub(r'[^a-zA-Z0-9_\-]', '', clean_org)

        if not clean_org:
            return []

        # Return cached discovery result if available
        cache_key = clean_org.lower()
        if cache_key in cls._ORG_CACHE and cls._ORG_CACHE[cache_key]:
            return list(cls._ORG_CACHE[cache_key])

        import json
        import ssl
        import urllib.request

        try:
            import certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            try:
                ssl_ctx = ssl.create_default_context()
            except Exception:
                ssl_ctx = ssl._create_unverified_context()

        token = os.environ.get("GITHUB_TOKEN")
        if not token and os.path.exists(".env"):
            try:
                with open(".env", "r") as env_f:
                    for line in env_f:
                        if line.startswith("GITHUB_TOKEN="):
                            val = line.strip().split("=", 1)[1].strip("\"'")
                            if val:
                                token = val
                                break
            except Exception:
                pass

        # 1. Official GitHub REST API with pagination and SSL support
        discovered_urls: List[str] = []
        for entity_type in ("orgs", "users"):
            page = 1
            while page <= 10:  # Fetch up to 1,000 repositories per organization
                api_url = f"https://api.github.com/{entity_type}/{clean_org}/repos?per_page=100&sort=pushed&page={page}"
                try:
                    req = urllib.request.Request(api_url)
                    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
                    req.add_header("Accept", "application/vnd.github.v3+json")
                    if token:
                        req.add_header("Authorization", f"Bearer {token}")
                    with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                        if resp.status == 200:
                            data = json.loads(resp.read().decode("utf-8"))
                            if isinstance(data, list) and data:
                                for r in data:
                                    if "clone_url" in r and r["clone_url"] not in discovered_urls:
                                        discovered_urls.append(r["clone_url"])
                                if len(data) < 100:
                                    break  # Reached last page
                                page += 1
                            else:
                                break
                        else:
                            break
                except Exception:
                    break

            if discovered_urls:
                cls._ORG_CACHE[cache_key] = discovered_urls
                return discovered_urls

        # 2. Fast Resilient Fallback: Scrape public repositories across pages
        page_templates = [
            f"https://github.com/orgs/{clean_org}/repositories?page={{page}}",
            f"https://github.com/{clean_org}?tab=repositories&page={{page}}"
        ]
        ignored_names = {
            "repositories", "people", "packages", "sponsoring", "projects",
            "teams", "followers", "following", "stars", "site", "audit-log",
            "discussions", "security", "settings", "insights"
        }

        seen = []
        for p_template in page_templates:
            for page in range(1, 6):  # Check up to 5 pages (150 repos)
                try:
                    p_url = p_template.format(page=page)
                    req = urllib.request.Request(p_url)
                    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
                        html = resp.read().decode("utf-8", errors="ignore")
                        matches = re.findall(rf'href=[\"\']/{clean_org}/([^/\#\?\"\'\s]+)[\"\']', html, re.IGNORECASE)
                        page_found = 0
                        for m in matches:
                            m_clean = m.strip()
                            if m_clean.lower() not in ignored_names and (not m_clean.startswith(".") or m_clean == ".github") and m_clean not in seen:
                                seen.append(m_clean)
                                page_found += 1
                        if page_found == 0:
                            break
                except Exception:
                    break
            if seen:
                results = [f"https://github.com/{clean_org}/{r}.git" for r in seen]
                cls._ORG_CACHE[cache_key] = results
                return results

        return []

    def clone_repository(
        self,
        url_or_path: str,
        progress_cb: Optional[Callable[[str, str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Clones a GitHub repository shallowly (--depth 1) or verifies a local path.
        """
        repo_name = self.extract_repo_name(url_or_path)
        dest_path = self.base_dir / repo_name

        # Check if input is an existing local directory
        local_path = Path(url_or_path)
        if local_path.is_dir():
            if progress_cb:
                progress_cb("verify", f"Using existing local repository at {local_path}", 1.0)
            return {
                "repo_name": repo_name,
                "path": str(local_path.resolve()),
                "source": "local_directory",
                "status": "ready"
            }

        # Otherwise treat as Git URL
        if progress_cb:
            progress_cb("cloning", f"Cloning {url_or_path} into {dest_path}...", 0.2)

        # If destination already exists, pull or clean
        if dest_path.exists():
            if (dest_path / ".git").exists():
                if progress_cb:
                    progress_cb("pull", f"Updating existing clone of {repo_name}...", 0.5)
                try:
                    subprocess.run(
                        ["git", "pull", "--depth", "1"],
                        cwd=str(dest_path),
                        capture_output=True,
                        text=True,
                        timeout=45
                    )
                    return {
                        "repo_name": repo_name,
                        "path": str(dest_path.resolve()),
                        "source": "github",
                        "status": "updated"
                    }
                except Exception:
                    pass
            # If not a valid git dir or pull failed, remove and re-clone
            shutil.rmtree(dest_path, ignore_errors=True)

        # Single-branch shallow clone with buffer optimization and fast failover
        git_config = [
            "-c", "http.postBuffer=524288000",
            "-c", "http.lowSpeedLimit=1000",
            "-c", "http.lowSpeedTime=20",
        ]
        cmd = ["git"] + git_config + ["clone", "--depth", "1", "--single-branch", "--no-tags", url_or_path, str(dest_path)]

        last_error = ""
        for attempt in range(1, 3):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
                if res.returncode == 0 and (dest_path / ".git").exists():
                    break
                last_error = res.stderr or "Git clone returned non-zero exit code."
                if dest_path.exists():
                    shutil.rmtree(dest_path, ignore_errors=True)
                # Fallback to standard depth 1 clone
                cmd = ["git"] + git_config + ["clone", "--depth", "1", "--single-branch", url_or_path, str(dest_path)]
            except Exception as e:
                last_error = str(e)
                if dest_path.exists():
                    shutil.rmtree(dest_path, ignore_errors=True)

        if not dest_path.exists() or not (dest_path / ".git").exists():
            return {
                "repo_name": repo_name,
                "path": "",
                "source": "github",
                "status": "failed",
                "error": last_error or "Git clone failed after retries."
            }

        if progress_cb:
            progress_cb("cloned", f"Successfully cloned {repo_name}!", 0.6)

        return {
            "repo_name": repo_name,
            "path": str(dest_path.resolve()),
            "source": "github",
            "status": "cloned"
        }

    def ingest_repositories(
        self,
        urls_or_paths: List[str],
        tool_manager: CodeGraphToolManager,
        clear_existing: bool = True,
        include_all: bool = True,
        progress_cb: Optional[Callable[[str, str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Clones multiple repositories in parallel, extracts AST structural symbols,
        links cross-repository dependencies, and registers all nodes into the knowledge graph.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        repo_paths: Dict[str, str] = {}
        clone_results = []
        errors = []

        valid_urls = [u.strip() for u in urls_or_paths if u.strip()]
        total_repos = len(valid_urls)
        if not total_repos:
            return {
                "status": "error",
                "message": "No repositories provided.",
                "errors": ["Empty repository list"],
                "indexed_nodes": 0,
                "cross_repo_edges": 0,
                "nodes": [],
                "edges": []
            }

        # Parallel cloning with ThreadPoolExecutor (up to 8 concurrent workers)
        max_workers = min(total_repos, 8)
        completed_clones = 0

        if progress_cb:
            progress_cb("start", f"Cloning {total_repos} repositories in parallel ({max_workers} workers)...", 0.05)

        def _worker(u: str):
            nonlocal completed_clones
            res = self.clone_repository(u)
            completed_clones += 1
            if progress_cb:
                progress_cb("cloning", f"Cloned {res['repo_name']} ({completed_clones}/{total_repos} repos)...", 0.1 + (0.4 * (completed_clones / max(total_repos, 1))))
            return res

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(_worker, u): u for u in valid_urls}
            for fut in as_completed(future_to_url):
                try:
                    res = fut.result()
                    clone_results.append(res)
                    if res["status"] in ("ready", "updated", "cloned") and res["path"]:
                        repo_paths[res["repo_name"]] = res["path"]
                    else:
                        errors.append(f"{res['repo_name']}: {res.get('error', 'Failed to clone')}")
                except Exception as e:
                    u = future_to_url[fut]
                    rname = self.extract_repo_name(u)
                    errors.append(f"{rname}: {e}")

        if not repo_paths:
            return {
                "status": "error",
                "message": "No repositories could be resolved or cloned.",
                "errors": errors,
                "indexed_nodes": 0,
                "cross_repo_edges": 0,
                "nodes": [],
                "edges": []
            }

        if progress_cb:
            progress_cb("parsing", f"Parsing AST boundaries across {len(repo_paths)} repositories...", 0.7)

        # Index the repositories into the CodeGraphToolManager
        index_stats = tool_manager.index_repositories(repo_paths, clear_existing=clear_existing, include_all=include_all, progress_cb=progress_cb)

        if progress_cb:
            progress_cb(
                "finished",
                f"Indexing complete! {index_stats['indexed_nodes']} symbols & {index_stats['cross_repo_edges']} cross-repo edges mapped.",
                1.0
            )

        return {
            "status": "success",
            "repositories": list(repo_paths.keys()),
            "indexed_nodes": index_stats["indexed_nodes"],
            "internal_edges": index_stats.get("internal_edges", 0),
            "cross_repo_edges": index_stats.get("cross_repo_edges", 0),
            "clone_results": clone_results,
            "errors": errors
        }
