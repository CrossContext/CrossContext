"""
CrossContext - Organization Context CLI Exporter
Exports a token-optimized organization context blueprint to a .txt or .md file
for consumption by IDEs (Cursor, Claude Code, Windsurf, VS Code).

Usage:
    python scripts/export_org_context.py
    python scripts/export_org_context.py --output ORG_CONTEXT.txt
"""

import os
import sys
import argparse
from pathlib import Path

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.storage.sqlite_graph import SQLiteGraphStore
from mcp_server.context_generator import OrgContextGenerator


def main():
    parser = argparse.ArgumentParser(description="Export CrossContext organization context blueprint.")
    parser.add_argument(
        "--db",
        default="data/crosscontext_graph.db",
        help="Path to SQLite graph database (default: data/crosscontext_graph.db)"
    )
    parser.add_argument(
        "--output",
        default="ORG_CONTEXT.txt",
        help="Output text file path (default: ORG_CONTEXT.txt)"
    )
    args = parser.parse_args()

    db_path = str(PROJECT_ROOT / args.db) if not os.path.isabs(args.db) else args.db
    store = SQLiteGraphStore(db_path=db_path)
    nodes = store.get_all_nodes()

    if not nodes:
        print("[Warning] Graph store contains 0 nodes. Indexing default testbed repositories first...")
        from mcp_server.tools import CodeGraphToolManager
        tm = CodeGraphToolManager(db_path=db_path)
        testbed_repos = {
            "repo_auth_core": str(PROJECT_ROOT / "testbed" / "repo_auth_core"),
            "repo_frontend_portal": str(PROJECT_ROOT / "testbed" / "repo_frontend_portal"),
            "repo_shared_sdk": str(PROJECT_ROOT / "testbed" / "repo_shared_sdk"),
        }
        tm.index_repositories(testbed_repos, clear_existing=True)
        store = tm.graph_store

    generator = OrgContextGenerator(store)
    context_text = generator.generate_ai_optimized_context()

    out_path = Path(args.output)
    out_path.write_text(context_text, encoding="utf-8")
    print(f"[SUCCESS] Exported organization context ({len(context_text)} characters) to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
