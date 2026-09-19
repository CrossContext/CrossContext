"""
CrossContext - Environment & System Smoke Test
Run this script to verify that your local machine environment is properly set up.
Usage:
    python scripts/smoke_test.py
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_smoke_test():
    print("==================================================")
    print("  CrossContext Multi-Machine Environment Smoke Test")
    print("==================================================")

    # 1. Python Version
    py_version = sys.version.split()[0]
    print(f"[1/5] Python Version: {py_version} ... ", end="")
    if sys.version_info < (3, 9):
        print("FAIL (Python 3.9+ required)")
        sys.exit(1)
    print("OK")

    # 2. Test Common Data Contracts
    print("[2/5] Testing common.models Contracts ... ", end="")
    try:
        from common.models import CodeNode, CodeEdge, SymbolType, EdgeType, RetrievalResult
        sample_node = CodeNode(
            id="repo_auth:src/auth.py:verify_token:10",
            repo="repo_auth",
            file_path="src/auth.py",
            symbol_name="verify_token",
            symbol_type=SymbolType.FUNCTION,
            start_line=10,
            end_line=25,
            signature="def verify_token(token: str) -> bool",
            docstring="Validates incoming JWT token.",
            code_content="def verify_token(token: str) -> bool:\n    return len(token) > 10\n"
        )
        assert sample_node.symbol_name == "verify_token"
        assert "verify_token" in sample_node.to_markdown_snippet()
        print("OK")
    except Exception as e:
        print(f"FAIL ({e})")
        sys.exit(1)

    # 3. Test SQLite Relational Edge Matrix & FTS5
    print("[3/5] Testing SQLite Relational Graph Store ... ", end="")
    try:
        from mcp_server.storage.sqlite_graph import SQLiteGraphStore
        store = SQLiteGraphStore(":memory:")
        
        # Insert test nodes
        node1 = sample_node
        node2 = CodeNode(
            id="repo_frontend:src/client.ts:loginUser:45",
            repo="repo_frontend",
            file_path="src/client.ts",
            symbol_name="loginUser",
            symbol_type=SymbolType.FUNCTION,
            start_line=45,
            end_line=60,
            signature="async function loginUser(credentials)",
            docstring="Authenticates user using backend verify_token endpoint.",
            code_content="async function loginUser(creds) {\n  return api.post('/v1/auth/verify');\n}"
        )
        store.insert_nodes([node1, node2])

        # Insert cross-repo edge: frontend calls backend verify_token
        edge = CodeEdge(
            caller_id=node2.id,
            callee_id=node1.id,
            edge_type=EdgeType.CONSUMES_API,
            confidence=1.0
        )
        store.insert_edge(edge)

        # Verify caller lookup
        callers = store.get_callers(node1.id)
        assert len(callers) == 1, f"Expected 1 caller, got {len(callers)}"
        assert callers[0].id == node2.id

        # Verify blast radius traversal
        traversal = store.traverse_blast_radius("verify_token", max_depth=2)
        assert len(traversal.upstream_callers) == 1
        assert "repo_frontend" in traversal.summary()
        print("OK")
    except Exception as e:
        print(f"FAIL ({e})")
        sys.exit(1)

    # 4. Test Dual-Mode Vector Adapter
    print("[4/5] Testing Dual-Mode Vector Store (Local Mode) ... ", end="")
    try:
        from mcp_server.storage.opensearch_client import DualModeVectorStore
        vec_store = DualModeVectorStore()
        vec_store.index_nodes([node1, node2])
        results = vec_store.search_semantic("validate JWT token", limit=2)
        assert len(results) >= 1
        print("OK")
    except Exception as e:
        print(f"FAIL ({e})")
        sys.exit(1)

    # 5. Check Environment Mode
    env_mode = os.getenv("ENV", "local")
    print(f"[5/5] Active Environment Mode: '{env_mode}'")

    print("\n" + "=" * 50)
    print("  ALL TESTS PASSED! System is ready for parallel development.")
    print("==================================================")
    print("Next steps:")
    print("  - Member 1: Manage cloud/storage in mcp_server/storage/ and deployment/")
    print("  - Member 2: Implement Tree-sitter parsers in mcp_server/parsers/")
    print("  - Member 3: Implement Strands Agent loop in agent_orchestrator/")


if __name__ == "__main__":
    run_smoke_test()
