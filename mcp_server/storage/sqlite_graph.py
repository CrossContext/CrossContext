"""
CrossContext - SQLite Relational Graph Store
Maintains the deterministic directional edge matrix (callers, callees, imports, API consumers)
and provides sub-millisecond lexical FTS5 searching across multi-repository symbols.
"""

import os
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Set

from common.models import (
    CodeNode,
    CodeEdge,
    SymbolType,
    EdgeType,
    TraversalResult
)


class SQLiteGraphStore:
    def __init__(self, db_path: Optional[str] = None):
        """
        Initializes the SQLite Graph Store.
        If db_path is None or ':memory:', runs an in-memory database (great for tests).
        """
        self._mem_conn = None
        if db_path and db_path != ":memory:":
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection_str = str(self.db_path)
        else:
            self.connection_str = ":memory:"
            # Retain open connection for in-memory database so tables persist across threads
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row

        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.connection_str, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_schema(self):
        """Creates the relational graph tables, indexes, and FTS5 full-text engine."""
        with self._get_connection() as conn:
            # 1. Nodes table
            conn.execute("""
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
                    metadata_json TEXT
                );
            """)

            # 2. Edges table (Directional relationship: caller -> callee)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    caller_id TEXT NOT NULL,
                    callee_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    metadata_json TEXT,
                    PRIMARY KEY (caller_id, callee_id, edge_type),
                    FOREIGN KEY (caller_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (callee_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)

            # 3. High-performance indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_symbol ON nodes(symbol_name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_repo ON nodes(repo);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_caller ON edges(caller_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_callee ON edges(callee_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);")

            # 4. FTS5 Full-Text Search Virtual Table
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        id UNINDEXED,
                        symbol_name,
                        signature,
                        docstring,
                        code_content,
                        content='nodes',
                        content_rowid='rowid'
                    );
                """)
                # Triggers to keep FTS in sync with nodes table
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                        INSERT INTO nodes_fts(rowid, id, symbol_name, signature, docstring, code_content)
                        VALUES (new.rowid, new.id, new.symbol_name, new.signature, new.docstring, new.code_content);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                        INSERT INTO nodes_fts(nodes_fts, rowid, id, symbol_name, signature, docstring, code_content)
                        VALUES('delete', old.rowid, old.id, old.symbol_name, old.signature, old.docstring, old.code_content);
                    END;
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                        INSERT INTO nodes_fts(nodes_fts, rowid, id, symbol_name, signature, docstring, code_content)
                        VALUES('delete', old.rowid, old.id, old.symbol_name, old.signature, old.docstring, old.code_content);
                        INSERT INTO nodes_fts(rowid, id, symbol_name, signature, docstring, code_content)
                        VALUES (new.rowid, new.id, new.symbol_name, new.signature, new.docstring, new.code_content);
                    END;
                """)
            except sqlite3.OperationalError:
                # Fallback if FTS5 is not compiled into system sqlite3
                pass

            conn.commit()

    # -------------------------------------------------------------
    # Ingestion & Maintenance Methods
    # -------------------------------------------------------------

    def clear(self) -> None:
        """Clears all nodes and edges from the graph store."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM edges;")
            conn.execute("DELETE FROM nodes;")
            try:
                conn.execute("DELETE FROM nodes_fts;")
            except Exception:
                pass
            conn.commit()

    def get_all_nodes(self) -> List[CodeNode]:
        """Retrieves all nodes in the store."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM nodes")
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def get_all_edges(self) -> List[CodeEdge]:
        """Retrieves all edges in the store."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT caller_id, callee_id, edge_type, confidence, metadata_json FROM edges")
            edges = []
            for r in cursor.fetchall():
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                edge_type_val = r["edge_type"]
                edge_type = EdgeType(edge_type_val) if edge_type_val in EdgeType._value2member_map_ else EdgeType.CALLS
                edges.append(CodeEdge(
                    caller_id=r["caller_id"],
                    callee_id=r["callee_id"],
                    edge_type=edge_type,
                    confidence=float(r["confidence"]),
                    metadata=meta
                ))
            return edges

    def insert_node(self, node: CodeNode) -> None:
        """Inserts or replaces a single CodeNode."""
        self.insert_nodes([node])

    def insert_nodes(self, nodes: List[CodeNode]) -> None:
        """Batch inserts or replaces CodeNodes."""
        if not nodes:
            return
        with self._get_connection() as conn:
            records = [
                (
                    n.id,
                    n.repo,
                    n.file_path,
                    n.symbol_name,
                    n.symbol_type.value if isinstance(n.symbol_type, SymbolType) else n.symbol_type,
                    n.start_line,
                    n.end_line,
                    n.signature or "",
                    n.docstring or "",
                    n.code_content or "",
                    json.dumps(n.metadata or {})
                )
                for n in nodes
            ]
            conn.executemany("""
                INSERT OR REPLACE INTO nodes (
                    id, repo, file_path, symbol_name, symbol_type,
                    start_line, end_line, signature, docstring, code_content, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, records)
            conn.commit()

    def insert_edge(self, edge: CodeEdge) -> None:
        """Inserts or ignores a single CodeEdge."""
        self.insert_edges([edge])

    def insert_edges(self, edges: List[CodeEdge]) -> None:
        """Batch inserts CodeEdges."""
        if not edges:
            return
        with self._get_connection() as conn:
            records = [
                (
                    e.caller_id,
                    e.callee_id,
                    e.edge_type.value if isinstance(e.edge_type, EdgeType) else e.edge_type,
                    float(e.confidence),
                    json.dumps(e.metadata or {})
                )
                for e in edges
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO edges (
                    caller_id, callee_id, edge_type, confidence, metadata_json
                ) VALUES (?, ?, ?, ?, ?);
            """, records)
            conn.commit()

    # -------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------

    def _row_to_node(self, row: sqlite3.Row) -> CodeNode:
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return CodeNode(
            id=row["id"],
            repo=row["repo"],
            file_path=row["file_path"],
            symbol_name=row["symbol_name"],
            symbol_type=SymbolType(row["symbol_type"]) if row["symbol_type"] in SymbolType._value2member_map_ else SymbolType.FUNCTION,
            start_line=row["start_line"],
            end_line=row["end_line"],
            signature=row["signature"],
            docstring=row["docstring"],
            code_content=row["code_content"],
            metadata=meta
        )

    def get_node(self, node_id: str) -> Optional[CodeNode]:
        """Retrieves a node by its unique deterministic ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            return self._row_to_node(row) if row else None

    def find_nodes_by_name(self, symbol_name: str, repo: Optional[str] = None) -> List[CodeNode]:
        """Exact match lookup for symbols by name across or within repos."""
        with self._get_connection() as conn:
            if repo:
                cursor = conn.execute(
                    "SELECT * FROM nodes WHERE symbol_name = ? AND repo = ?",
                    (symbol_name, repo)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM nodes WHERE symbol_name = ?",
                    (symbol_name,)
                )
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def search_nodes_lexical(self, query: str, repo: Optional[str] = None, limit: int = 10) -> List[CodeNode]:
        """Fast lexical full-text search using FTS5 or LIKE fallback."""
        with self._get_connection() as conn:
            try:
                # Try FTS5 match query first
                safe_query = "".join(c for c in query if c.isalnum() or c in (" ", "_", "-")).strip()
                tokens = [t for t in safe_query.split() if len(t) > 1]
                fts_expr = " OR ".join(f'"{t}"*' for t in tokens) if tokens else f'"{safe_query}"*'
                
                if repo:
                    cursor = conn.execute("""
                        SELECT n.* FROM nodes n
                        JOIN nodes_fts f ON n.id = f.id
                        WHERE nodes_fts MATCH ? AND n.repo = ?
                        LIMIT ?
                    """, (fts_expr, repo, limit))
                else:
                    cursor = conn.execute("""
                        SELECT n.* FROM nodes n
                        JOIN nodes_fts f ON n.id = f.id
                        WHERE nodes_fts MATCH ?
                        LIMIT ?
                    """, (fts_expr, limit))
                results = [self._row_to_node(r) for r in cursor.fetchall()]
                if results:
                    return results
            except sqlite3.OperationalError:
                pass

            # Fallback to standard LIKE matching
            pattern = f"%{query}%"
            if repo:
                cursor = conn.execute("""
                    SELECT * FROM nodes
                    WHERE (symbol_name LIKE ? OR signature LIKE ? OR docstring LIKE ?) AND repo = ?
                    LIMIT ?
                """, (pattern, pattern, pattern, repo, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM nodes
                    WHERE (symbol_name LIKE ? OR signature LIKE ? OR docstring LIKE ?)
                    LIMIT ?
                """, (pattern, pattern, pattern, limit))
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def get_callers(self, callee_id: str) -> List[CodeNode]:
        """Returns all nodes that directly call, import, or consume the given callee_id."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.caller_id
                WHERE e.callee_id = ?
            """, (callee_id,))
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def get_callees(self, caller_id: str) -> List[CodeNode]:
        """Returns all nodes directly called or imported by the given caller_id."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT n.* FROM nodes n
                JOIN edges e ON n.id = e.callee_id
                WHERE e.caller_id = ?
            """, (caller_id,))
            return [self._row_to_node(r) for r in cursor.fetchall()]

    def traverse_blast_radius(self, root_symbol_or_id: str, max_depth: int = 3) -> TraversalResult:
        """
        Traces the full upstream and downstream graph starting from a symbol name or node ID.
        Identifies all affected callers across repositories (the blast radius of a change).
        """
        start_time = time.time()
        
        # Resolve initial node(s)
        initial_nodes = []
        node_by_id = self.get_node(root_symbol_or_id)
        if node_by_id:
            initial_nodes.append(node_by_id)
        else:
            initial_nodes = self.find_nodes_by_name(root_symbol_or_id)

        if not initial_nodes:
            return TraversalResult(
                root_symbol=root_symbol_or_id,
                depth=0,
                execution_time_ms=(time.time() - start_time) * 1000.0
            )

        visited_upstream: Set[str] = set()
        visited_downstream: Set[str] = set()
        upstream_nodes: List[CodeNode] = []
        downstream_nodes: List[CodeNode] = []
        blast_files: Set[str] = set()

        for init_node in initial_nodes:
            blast_files.add(f"{init_node.repo}:{init_node.file_path}")

            # 1. Trace Upstream (Who calls this symbol? Blast radius for breaking API changes)
            current_level = [init_node.id]
            visited_upstream.add(init_node.id)

            for _ in range(max_depth):
                next_level = []
                for cid in current_level:
                    callers = self.get_callers(cid)
                    for caller in callers:
                        if caller.id not in visited_upstream:
                            visited_upstream.add(caller.id)
                            upstream_nodes.append(caller)
                            blast_files.add(f"{caller.repo}:{caller.file_path}")
                            next_level.append(caller.id)
                if not next_level:
                    break
                current_level = next_level

            # 2. Trace Downstream (What does this symbol depend on?)
            current_down = [init_node.id]
            visited_downstream.add(init_node.id)

            for _ in range(max_depth):
                next_down = []
                for cid in current_down:
                    callees = self.get_callees(cid)
                    for callee in callees:
                        if callee.id not in visited_downstream:
                            visited_downstream.add(callee.id)
                            downstream_nodes.append(callee)
                            blast_files.add(f"{callee.repo}:{callee.file_path}")
                            next_down.append(callee.id)
                if not next_down:
                    break
                current_down = next_down

        return TraversalResult(
            root_symbol=root_symbol_or_id,
            depth=max_depth,
            upstream_callers=upstream_nodes,
            downstream_dependencies=downstream_nodes,
            blast_radius_files=sorted(list(blast_files)),
            execution_time_ms=(time.time() - start_time) * 1000.0
        )

    def get_stats(self) -> Dict[str, Any]:
        """Returns database statistics for monitoring and UI display."""
        with self._get_connection() as conn:
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            repos = [r[0] for r in conn.execute("SELECT DISTINCT repo FROM nodes").fetchall()]
            return {
                "total_symbols": node_count,
                "total_edges": edge_count,
                "repositories": repos,
                "db_engine": "SQLite WAL + FTS5"
            }
