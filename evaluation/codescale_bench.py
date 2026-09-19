"""
OmniContext - CodeScaleBench Cross-Repo Dependency Tracing Benchmark (Modular)
Evaluates the engine's ability to trace all downstream consumers of an API endpoint
across repository boundaries — the core competency that naive RAG cannot achieve.
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.repoqa_bench import BenchmarkResult
from mcp_server.parsers.treesitter_engine import TreeSitterEngine
from mcp_server.parsers.scip_indexer import CrossRepoLinker
from mcp_server.storage.sqlite_graph import SQLiteGraphStore


def run_codescale_benchmark(
    testbed_root: Optional[str] = None,
    repos: Optional[List[str]] = None,
) -> BenchmarkResult:
    """
    CodeScaleBench Cross-Repo Dependency Tracing Benchmark.

    Tests whether OmniContext can deterministically trace API endpoint deprecations
    across distributed repositories, detecting ALL upstream consumers that would break.
    """
    start = time.time()

    if testbed_root is None:
        testbed_root = str(PROJECT_ROOT / "testbed")
    if repos is None:
        repos = ["repo_auth_core", "repo_frontend_portal", "repo_shared_sdk"]

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

    # --- Test Cases: Cross-repo dependency tracing ---
    test_cases = [
        {
            "description": "Trace blast radius of verify_legacy_auth deprecation",
            "target_symbol": "verify_legacy_auth",
            "expected_cross_repo_hits": True,
            "expected_min_blast_files": 2,
        },
        {
            "description": "Trace blast radius of verify_auth_v1 (v1 endpoint)",
            "target_symbol": "verify_auth_v1",
            "expected_cross_repo_hits": True,
            "expected_min_blast_files": 1,
        },
    ]

    passed_tests = 0
    total_tests = len(test_cases)
    details = []
    total_cross_edges = len(cross_edges)

    for tc in test_cases:
        traversal = store.traverse_blast_radius(tc["target_symbol"], max_depth=3)

        blast_files = traversal.blast_radius_files
        upstream = traversal.upstream_callers

        # Check for cross-repo hits
        repos_in_blast = set()
        for f_ref in blast_files:
            if ":" in f_ref:
                repos_in_blast.add(f_ref.split(":")[0])

        has_cross_repo = len(repos_in_blast) > 1
        has_enough_files = len(blast_files) >= tc["expected_min_blast_files"]

        test_passed = True
        if tc["expected_cross_repo_hits"] and not has_cross_repo:
            test_passed = False
        if not has_enough_files:
            test_passed = False

        if test_passed:
            passed_tests += 1
            details.append(
                f"✅ {tc['description']}: "
                f"{len(blast_files)} files across {len(repos_in_blast)} repos "
                f"(upstream callers: {len(upstream)})"
            )
        else:
            details.append(
                f"❌ {tc['description']}: "
                f"Expected cross-repo={tc['expected_cross_repo_hits']} got {has_cross_repo}, "
                f"files={len(blast_files)} (needed {tc['expected_min_blast_files']})"
            )

    score = passed_tests / max(total_tests, 1)
    elapsed = (time.time() - start) * 1000

    # Compute overall boundary precision
    endpoint_nodes = [n for n in all_nodes if hasattr(n, "symbol_type") and n.symbol_type.value == "endpoint"]
    boundary_exact = sum(1 for n in all_nodes if n.start_line > 0 and n.end_line > n.start_line)
    boundary_precision = boundary_exact / max(len(all_nodes), 1) * 100

    return BenchmarkResult(
        benchmark_name="CodeScaleBench Cross-Repo Dependency Tracing",
        passed=score >= 0.5,
        score=score,
        metrics={
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "cross_repo_edges_discovered": total_cross_edges,
            "boundary_precision_pct": round(boundary_precision, 1),
            "symbols_indexed": len(all_nodes),
            "endpoint_nodes": len(endpoint_nodes),
            "repos_indexed": len(repos),
        },
        details=details,
        execution_time_ms=elapsed,
    )


if __name__ == "__main__":
    result = run_codescale_benchmark()
    print(f"\n{'='*60}")
    print(f"Benchmark: {result.benchmark_name}")
    print(f"Passed: {result.passed} | Score: {result.score:.0%}")
    print(f"Execution Time: {result.execution_time_ms:.1f}ms")
    for detail in result.details:
        print(f"  {detail}")
    print(f"Metrics: {result.metrics}")
