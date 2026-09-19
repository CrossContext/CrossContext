"""
CrossContext - CLI Script to Ingest Dynamic GitHub Repositories
Clones, parses, and indexes real GitHub repositories into the CrossContext knowledge graph.
Usage:
    python scripts/index_github_repos.py https://github.com/owner/repo1 https://github.com/owner/repo2
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.tools import CodeGraphToolManager
from mcp_server.ingestion.github_ingester import GitHubRepoIngester


def main():
    parser = argparse.ArgumentParser(description="Ingest real GitHub repositories into CrossContext")
    parser.add_argument("repos", nargs="+", help="GitHub repository URLs or local directory paths")
    parser.add_argument("--db-path", default="data/crosscontext_graph.db", help="Path to SQLite graph database")
    args = parser.parse_args()

    print("==================================================")
    print("   CrossContext Dynamic GitHub Repository Ingester  ")
    print("==================================================")
    print(f"Target Repositories ({len(args.repos)}):")
    for r in args.repos:
        print(f"  - {r}")
    print()

    tool_manager = CodeGraphToolManager(db_path=args.db_path)
    ingester = GitHubRepoIngester()

    def on_progress(stage: str, msg: str, pct: float):
        print(f"[{stage.upper():<8}] ({pct*100:3.0f}%) {msg}")

    result = ingester.ingest_repositories(args.repos, tool_manager, progress_cb=on_progress)

    print("\n" + "=" * 50)
    if result["status"] == "success":
        print("INGESTION SUCCESSFUL!")
        print(f"  Repositories Indexed: {len(result['repositories'])}")
        print(f"  Total Symbols (Nodes): {result['indexed_nodes']}")
        print(f"  Internal Call Edges:  {result['internal_edges']}")
        print(f"  Cross-Repo Edges:     {result['cross_repo_edges']}")
    else:
        print(f"INGESTION FAILED: {result.get('message')}")
        for err in result.get("errors", []):
            print(f"  Error: {err}")
    print("==================================================")


if __name__ == "__main__":
    main()
