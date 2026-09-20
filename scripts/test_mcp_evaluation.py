"""
CrossContext - Test Project MCP Tools Against sample_codebase
Evaluates all 5 MCP tools against the indexed codebase C++23 / Python / TS codebase.
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.tools import CodeGraphToolManager

def main():
    print("=" * 65)
    print(" CrossContext MCP Server Evaluation against sample_codebase")
    print("=" * 65)

    db_path = "data/crosscontext_graph.db"
    manager = CodeGraphToolManager(db_path=db_path)

    # 0. Database & Knowledge Graph Stats
    stats = manager.get_system_stats()
    print("\n[STEP 0] Knowledge Graph Statistics:")
    print(f"  Repositories:     {stats['graph_engine']['repositories']}")
    print(f"  Total AST Nodes:  {stats['graph_engine']['total_symbols']}")
    print(f"  Call Graph Edges: {stats['graph_engine']['total_edges']}")
    print(f"  Storage Engine:   {stats['graph_engine']['db_engine']}")

    # 1. Test get_symbol_definition (C++ function)
    target_symbol = "computeHopTestedPartition"
    print(f"\n[TOOL 1] get_symbol_definition('{target_symbol}'):")
    res1 = manager.get_symbol_definition(target_symbol)
    print(f"  Found: {res1['found']} (Matches: {res1['count']})")
    if res1["symbols"]:
        sym = res1["symbols"][0]
        print(f"  -> Symbol:     {sym['symbol_name']} ({sym['symbol_type']})")
        print(f"  -> File:       {sym['file_path']}:{sym['start_line']}-{sym['end_line']}")
        print(f"  -> Signature:  {sym['signature']}")

    # 1b. Test get_symbol_definition (C++ struct / class)
    struct_symbol = "HopTestedPartition"
    print(f"\n[TOOL 1b] get_symbol_definition('{struct_symbol}'):")
    res1b = manager.get_symbol_definition(struct_symbol)
    print(f"  Found: {res1b['found']} (Matches: {res1b['count']})")
    if res1b["symbols"]:
        sym = res1b["symbols"][0]
        print(f"  -> Symbol:     {sym['symbol_name']} ({sym['symbol_type']})")
        print(f"  -> File:       {sym['file_path']}:{sym['start_line']}-{sym['end_line']}")
        print(f"  -> Signature:  {sym['signature']}")

    # 2. Test get_ast_chunk
    if res1["symbols"]:
        node_id = res1["symbols"][0]["id"]
        print(f"\n[TOOL 2] get_ast_chunk('{node_id}'):")
        chunk_res = manager.get_ast_chunk(node_id)
        print(f"  Retrieved Unbroken Code Chunk ({chunk_res['lines']}):")
        lines = chunk_res["code_content"].splitlines()
        for l in lines[:10]:
            print(f"    | {l}")
        if len(lines) > 10:
            print(f"    | ... ({len(lines)-10} more lines)")

    # 3. Test get_usage_dependency_links
    print(f"\n[TOOL 3] get_usage_dependency_links('{target_symbol}'):")
    dep_res = manager.get_usage_dependency_links(target_symbol)
    print(f"  Found Target:            {dep_res['found']}")
    print(f"  Upstream Callers Count:  {dep_res.get('upstream_callers_count', 0)}")
    print(f"  Downstream Callees Count:{dep_res.get('downstream_callees_count', 0)}")

    # 4. Test traverse_call_graph (Blast Radius)
    print(f"\n[TOOL 4] traverse_call_graph('{target_symbol}', depth=3):")
    trav_res = manager.traverse_call_graph(target_symbol, depth=3)
    print(f"  Execution Time:          {trav_res['execution_time_ms']:.2f} ms")
    print(f"  Blast Radius Summary:    {trav_res['summary']}")
    print(f"  Blast Radius Files:      {trav_res['blast_radius_files']}")

    # 5. Test semantic_code_search / natural language query
    query = "call hierarchy and reachability partition"
    print(f"\n[TOOL 5] semantic_code_search('{query}'):")
    search_res = manager.semantic_code_search(query, limit=5)
    print(f"  Total Relevant Matches: {search_res['count']}")
    for i, match in enumerate(search_res["results"][:5], start=1):
        print(f"  [{i}] {match['symbol_name']} ({match['symbol_type']}) in {match['file_path']}:{match['start_line']}")

    # 6. Test Strands Agent reasoning loop on codebase
    print("\n[BONUS] Testing Autonomous Agent Loop on codebase codebase...")
    import asyncio
    from agent_orchestrator.agent import CrossContextAgent
    agent = CrossContextAgent(db_path=db_path)
    agent_res = asyncio.run(agent.run(
        prompt="Analyze how HopTestedPartition and computeHopTestedPartition are used in codebase and trace their impact."
    ))
    print(f"  Agent Status:       {agent_res['status']}")
    telemetry = agent_res.get('telemetry', {})
    print(f"  Tool Calls Made:    {telemetry.get('total_tool_calls', 0)} ({telemetry.get('tool_sequence', [])})")
    print(f"  Token Utilization:  {telemetry.get('approx_tokens_used', 0)} tokens ({telemetry.get('budget_utilization_pct', 0)}% of budget)")
    print(f"  Runtime:            {telemetry.get('total_runtime_ms', 0):.1f} ms")
    print(f"  Nodes Touched:      {agent_res.get('nodes_touched', [])}")
    print("\n--- Agent Execution Plan / Response ---")
    resp_lines = (agent_res.get("response") or "").splitlines()
    for pl in resp_lines[:15]:
        print(f"  {pl}")
    print("=" * 65)

if __name__ == "__main__":
    main()
