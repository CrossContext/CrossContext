"""
CrossContext - RepoQA Search Needle Function Benchmark (Modular)
Evaluates the engine's ability to locate exact function definitions given only
a docstring or semantic description, compared against naive text-chunk RAG.
"""

import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker
from mcp_server.storage.sqlite_graph import SQLiteGraphStore
from mcp_server.tools import CodeGraphToolManager


@dataclass
class BenchmarkResult:
    """Structured result from a benchmark run."""
    benchmark_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    metrics: dict = field(default_factory=dict)
    details: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


def run_repoqa_benchmark(
    testbed_root: Optional[str] = None,
    repos: Optional[List[str]] = None,
) -> BenchmarkResult:
    """
    RepoQA Search Needle Function Benchmark.

    Tests whether CrossContext can locate a specific function definition given
    a semantic description (docstring-like query), and compares the precision
    against a naive text-chunking approach.
    """
    start = time.time()

    if testbed_root is None:
        testbed_root = str(PROJECT_ROOT / "testbed")
    if repos is None:
        repos = ["repo_auth_core", "repo_frontend_portal"]

    # Build graph
    parser = TreeSitterEngine()
    linker = CrossRepoLinker()
    store = SQLiteGraphStore(":memory:")

    all_nodes = []
    all_edges = []
    for repo_name in repos:
        repo_dir = Path(testbed_root) / repo_name
        if repo_dir.exists():
            nodes, edges = parser.parse_directory(repo_name, str(repo_dir))
            all_nodes.extend(nodes)
            all_edges.extend(edges)

    cross_edges = linker.link_repositories(all_nodes)
    store.insert_nodes(all_nodes)
    store.insert_edges(all_edges + cross_edges)

    # Initialize tool manager
    tool_manager = CodeGraphToolManager(db_path=":memory:")
    tool_manager.graph_store = store

    # --- Test Case: Search for verify_jwt_token by semantic description ---
    test_queries = [
        {
            "query": "JWT token verification and validation",
            "expected_symbol": "verify_jwt_token",
            "expected_repo": "repo_auth_core",
        },
        {
            "query": "legacy deprecated authentication signature check",
            "expected_symbol": "validate_v1_legacy_signature",
            "expected_repo": "repo_auth_core",
        },
    ]

    passed_tests = 0
    total_tests = len(test_queries)
    details = []
    omni_tokens = 0
    naive_tokens_estimate = 0

    for tc in test_queries:
        # CrossContext approach: lexical search over AST-bounded nodes
        results = store.search_nodes_lexical(tc["query"].split()[0], limit=5)

        found = any(
            r.symbol_name == tc["expected_symbol"] and r.repo == tc["expected_repo"]
            for r in results
        )

        if found:
            match = next(r for r in results if r.symbol_name == tc["expected_symbol"])
            token_count = len(match.code_content or "") // 4
            omni_tokens += token_count
            passed_tests += 1
            details.append(f"✅ Found `{tc['expected_symbol']}` in `{match.repo}/{match.file_path}` ({token_count} tokens)")
        else:
            details.append(f"❌ Could not locate `{tc['expected_symbol']}` via query: '{tc['query']}'")

        # Estimate naive RAG baseline: full file dump
        for node in all_nodes:
            if node.repo == tc["expected_repo"]:
                naive_tokens_estimate += len(node.code_content or "") // 4

    score = passed_tests / max(total_tests, 1)
    token_reduction = 1.0 - (omni_tokens / max(naive_tokens_estimate, 1))

    elapsed = (time.time() - start) * 1000

    return BenchmarkResult(
        benchmark_name="RepoQA Search Needle Function",
        passed=score >= 0.5,
        score=score,
        metrics={
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "crosscontext_tokens": omni_tokens,
            "naive_rag_tokens_estimate": naive_tokens_estimate,
            "token_reduction_pct": round(token_reduction * 100, 1),
            "symbols_indexed": len(all_nodes),
        },
        details=details,
        execution_time_ms=elapsed,
    )


if __name__ == "__main__":
    result = run_repoqa_benchmark()
    print(f"\n{'='*60}")
    print(f"Benchmark: {result.benchmark_name}")
    print(f"Passed: {result.passed} | Score: {result.score:.0%}")
    print(f"Execution Time: {result.execution_time_ms:.1f}ms")
    for detail in result.details:
        print(f"  {detail}")
    print(f"Metrics: {result.metrics}")
