"""SQLite Relational Edge Matrix and FTS5 Graph Storage for OmniContext.

Provides persistent, deterministic graph traversals and full-text code search
without external database dependencies.
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from common.models import (
    CodeNode,
    CodeEdge,
    SymbolType,
    EdgeType,
    TraversalResult,
    BlastRadiusReport,
)


class SQLiteGraphStorage:
    """Manages SQLite storage for AST nodes, cross-repo edges, and FTS5 full-text search."""

    def __init__(self, db_path: str = "omnicontext_graph.db"):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    symbol_name TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    signature TEXT,
                    docstring TEXT,
                    code_content TEXT,
                    language TEXT NOT NULL,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    caller_id TEXT NOT NULL,
                    callee_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    caller_repo TEXT,
                    callee_repo TEXT,
                    context_line INTEGER,
                    call_snippet TEXT,
                    metadata_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_symbol ON nodes(symbol_name);
                CREATE INDEX IF NOT EXISTS idx_nodes_repo ON nodes(repo);
                CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);
                CREATE INDEX IF NOT EXISTS idx_edges_caller ON edges(caller_id);
                CREATE INDEX IF NOT EXISTS idx_edges_callee ON edges(callee_id);
                CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);

                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    id UNINDEXED,
                    symbol_name,
                    signature,
                    docstring,
                    code_content,
                    tokenize='porter unicode61'
                );
            """)
            conn.commit()

    def insert_node(self, node: CodeNode) -> None:
        """Inserts or replaces a CodeNode in the database and updates FTS5 index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO nodes (
                    id, repo, file_path, symbol_name, symbol_type,
                    start_line, end_line, signature, docstring,
                    code_content, language, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.repo,
                    node.file_path,
                    node.symbol_name,
                    node.symbol_type.value if isinstance(node.symbol_type, SymbolType) else str(node.symbol_type),
                    node.start_line,
                    node.end_line,
                    node.signature,
                    node.docstring,
                    node.code_content,
                    node.language,
                    json.dumps(node.metadata or {}),
                ),
            )
            # Update FTS index
            cursor.execute("DELETE FROM nodes_fts WHERE id = ?", (node.id,))
            cursor.execute(
                """
                INSERT INTO nodes_fts (id, symbol_name, signature, docstring, code_content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.symbol_name or "",
                    node.signature or "",
                    node.docstring or "",
                    node.code_content or "",
                ),
            )
            conn.commit()

    def insert_edge(self, edge: CodeEdge) -> None:
        """Inserts or replaces a CodeEdge in the database."""
        edge_id = edge.id or f"{edge.caller_id}->{edge.edge_type}->{edge.callee_id}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO edges (
                    id, caller_id, callee_id, edge_type,
                    caller_repo, callee_repo, context_line,
                    call_snippet, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge_id,
                    edge.caller_id,
                    edge.callee_id,
                    edge.edge_type.value if isinstance(edge.edge_type, EdgeType) else str(edge.edge_type),
                    edge.caller_repo,
                    edge.callee_repo,
                    edge.context_line,
                    edge.call_snippet,
                    json.dumps(edge.metadata or {}),
                ),
            )
            conn.commit()

    def _row_to_node(self, row: sqlite3.Row) -> CodeNode:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return CodeNode(
            id=row["id"],
            repo=row["repo"],
            file_path=row["file_path"],
            symbol_name=row["symbol_name"],
            symbol_type=SymbolType(row["symbol_type"]) if row["symbol_type"] in [s.value for s in SymbolType] else SymbolType.FUNCTION,
            start_line=row["start_line"],
            end_line=row["end_line"],
            signature=row["signature"],
            docstring=row["docstring"],
            code_content=row["code_content"],
            language=row["language"],
            metadata=meta,
        )

    def _row_to_edge(self, row: sqlite3.Row) -> CodeEdge:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return CodeEdge(
            id=row["id"],
            caller_id=row["caller_id"],
            callee_id=row["callee_id"],
            edge_type=EdgeType(row["edge_type"]) if row["edge_type"] in [e.value for e in EdgeType] else EdgeType.CALLS,
            caller_repo=row["caller_repo"],
            callee_repo=row["callee_repo"],
            context_line=row["context_line"],
            call_snippet=row["call_snippet"],
            metadata=meta,
        )

    def get_node_by_id(self, node_id: str) -> Optional[CodeNode]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return self._row_to_node(row) if row else None

    def find_nodes_by_symbol(self, symbol_name: str, repo: Optional[str] = None) -> List[CodeNode]:
        """Finds code nodes matching a symbol name, optionally filtered by repository."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if repo:
                cursor.execute(
                    "SELECT * FROM nodes WHERE symbol_name = ? AND repo = ? ORDER BY start_line ASC",
                    (symbol_name, repo),
                )
            else:
                cursor.execute(
                    "SELECT * FROM nodes WHERE symbol_name = ? ORDER BY repo, file_path",
                    (symbol_name,),
                )
            return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_callers(self, node_id: str) -> List[CodeNode]:
        """Returns all nodes that call/consume this node."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.caller_id
                WHERE e.callee_id = ?
                """,
                (node_id,),
            )
            return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_callees(self, node_id: str) -> List[CodeNode]:
        """Returns all nodes that are called/consumed by this node."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.callee_id
                WHERE e.caller_id = ?
                """,
                (node_id,),
            )
            return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_edges_for_node(self, node_id: str, direction: str = "both") -> List[CodeEdge]:
        """Returns edges connected to a node."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if direction == "downstream" or direction == "callers":
                cursor.execute("SELECT * FROM edges WHERE callee_id = ?", (node_id,))
            elif direction == "upstream" or direction == "callees":
                cursor.execute("SELECT * FROM edges WHERE caller_id = ?", (node_id,))
            else:
                cursor.execute("SELECT * FROM edges WHERE caller_id = ? OR callee_id = ?", (node_id, node_id))
            return [self._row_to_edge(row) for row in cursor.fetchall()]

    def traverse_graph(
        self, entry_symbol: str, depth: int = 2, direction: str = "both", repo: Optional[str] = None
    ) -> TraversalResult:
        """Traverses the call/dependency graph starting from a symbol name or node ID."""
        start_nodes = self.find_nodes_by_symbol(entry_symbol, repo)
        if not start_nodes:
            # Check if entry_symbol is a direct node ID
            single = self.get_node_by_id(entry_symbol)
            if single:
                start_nodes = [single]

        if not start_nodes:
            return TraversalResult(
                entry_symbol=entry_symbol,
                direction=direction,
                depth=depth,
                nodes=[],
                edges=[],
                impacted_repos=[],
                summary=f"Symbol '{entry_symbol}' not found in code graph.",
            )

        visited_node_ids: Set[str] = set()
        collected_nodes: Dict[str, CodeNode] = {}
        collected_edges: Dict[str, CodeEdge] = {}
        impacted_repos: Set[str] = set()

        current_frontier: Set[str] = {n.id for n in start_nodes}
        for n in start_nodes:
            collected_nodes[n.id] = n
            impacted_repos.add(n.repo)

        for _ in range(depth):
            if not current_frontier:
                break
            next_frontier: Set[str] = set()
            for current_id in current_frontier:
                if current_id in visited_node_ids:
                    continue
                visited_node_ids.add(current_id)

                edges = self.get_edges_for_node(current_id, direction=direction)
                for e in edges:
                    edge_key = e.id or f"{e.caller_id}->{e.edge_type}->{e.callee_id}"
                    collected_edges[edge_key] = e

                    target_ids = []
                    if direction in ("both", "upstream", "callees"):
                        target_ids.append(e.callee_id)
                    if direction in ("both", "downstream", "callers"):
                        target_ids.append(e.caller_id)

                    for tid in target_ids:
                        if tid not in collected_nodes:
                            tn = self.get_node_by_id(tid)
                            if tn:
                                collected_nodes[tn.id] = tn
                                impacted_repos.add(tn.repo)
                        if tid not in visited_node_ids:
                            next_frontier.add(tid)

            current_frontier = next_frontier

        summary = (
            f"Traversed {len(collected_nodes)} nodes and {len(collected_edges)} edges across "
            f"{len(impacted_repos)} repositories ({', '.join(sorted(impacted_repos))}) for entry symbol '{entry_symbol}'."
        )

        return TraversalResult(
            entry_symbol=entry_symbol,
            direction=direction,
            depth=depth,
            nodes=list(collected_nodes.values()),
            edges=list(collected_edges.values()),
            impacted_repos=list(impacted_repos),
            summary=summary,
        )

    def analyze_blast_radius(self, symbol_name: str, repo: Optional[str] = None) -> BlastRadiusReport:
        """Determines full downstream blast radius of modifying or deprecating a symbol."""
        nodes = self.find_nodes_by_symbol(symbol_name, repo)
        if not nodes:
            single = self.get_node_by_id(symbol_name)
            nodes = [single] if single else []

        if not nodes:
            return BlastRadiusReport(
                target_symbol=symbol_name,
                recommended_actions=[f"Target symbol '{symbol_name}' not found."],
            )

        target = nodes[0]
        direct_callers = self.get_callers(target.id)
        indirect_callers_map: Dict[str, CodeNode] = {}
        cross_repo_impact: Dict[str, List[CodeNode]] = {}
        affected_endpoints: List[str] = []

        if target.symbol_type == SymbolType.ENDPOINT:
            affected_endpoints.append(target.symbol_name)

        # Check direct callers
        for dc in direct_callers:
            if dc.repo != target.repo:
                cross_repo_impact.setdefault(dc.repo, []).append(dc)
            if dc.symbol_type == SymbolType.ENDPOINT:
                affected_endpoints.append(dc.symbol_name)

            # Look 2 levels deep for indirect callers
            second_callers = self.get_callers(dc.id)
            for sc in second_callers:
                if sc.id != target.id and sc.id != dc.id:
                    indirect_callers_map[sc.id] = sc
                    if sc.repo != target.repo:
                        cross_repo_impact.setdefault(sc.repo, []).append(sc)

        actions = []
        if cross_repo_impact:
            actions.append(
                f"Cross-repo impact detected in {len(cross_repo_impact)} external repos: {list(cross_repo_impact.keys())}. Update API client bindings."
            )
        if affected_endpoints:
            actions.append(f"HTTP Endpoints affected: {list(set(affected_endpoints))}. Verify API contract compatibility.")

        return BlastRadiusReport(
            target_symbol=symbol_name,
            target_node=target,
            direct_callers=direct_callers,
            indirect_callers=list(indirect_callers_map.values()),
            cross_repo_impact=cross_repo_impact,
            recommended_actions=actions,
            affected_endpoints=list(set(affected_endpoints)),
        )

    def search_nodes_fts(self, query: str, repo: Optional[str] = None, limit: int = 20) -> List[CodeNode]:
        """Performs full text search over symbols, signatures, docstrings, and code content."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Escape or sanitize query for FTS5
            sanitized_query = query.replace('"', '""').replace("'", "''")
            fts_query = f'"{sanitized_query}"'

            try:
                if repo:
                    cursor.execute(
                        """
                        SELECT n.* FROM nodes n
                        JOIN nodes_fts f ON n.id = f.id
                        WHERE nodes_fts MATCH ? AND n.repo = ?
                        LIMIT ?
                        """,
                        (fts_query, repo, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT n.* FROM nodes n
                        JOIN nodes_fts f ON n.id = f.id
                        WHERE nodes_fts MATCH ?
                        LIMIT ?
                        """,
                        (fts_query, limit),
                    )
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                # Fallback to LIKE if FTS query syntax error
                like_term = f"%{query}%"
                if repo:
                    cursor.execute(
                        """
                        SELECT * FROM nodes
                        WHERE (symbol_name LIKE ? OR signature LIKE ? OR docstring LIKE ? OR code_content LIKE ?)
                        AND repo = ?
                        LIMIT ?
                        """,
                        (like_term, like_term, like_term, like_term, repo, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM nodes
                        WHERE symbol_name LIKE ? OR signature LIKE ? OR docstring LIKE ? OR code_content LIKE ?
                        LIMIT ?
                        """,
                        (like_term, like_term, like_term, like_term, limit),
                    )
                rows = cursor.fetchall()

            return [self._row_to_node(r) for r in rows]

    def get_all_nodes(self, repo: Optional[str] = None) -> List[CodeNode]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if repo:
                cursor.execute("SELECT * FROM nodes WHERE repo = ? ORDER BY file_path, start_line", (repo,))
            else:
                cursor.execute("SELECT * FROM nodes ORDER BY repo, file_path, start_line")
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def get_all_edges(self) -> List[CodeEdge]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM edges")
            return [self._row_to_edge(r) for r in cursor.fetchall()]

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM edges;")
            cursor.execute("DELETE FROM nodes;")
            cursor.execute("DELETE FROM nodes_fts;")
            conn.commit()
