"""
CrossContext - Common Data Contracts
Defines the standard schemas shared across:
- Storage Layer (sqlite_graph, opensearch_client)
- Parsing Pipeline (treesitter_engine, scip_indexer)
- MCP Server & Tools (server.py, tools.py)
- Strands Agent Orchestrator (agent.py, hooks.py)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class SymbolType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    INTERFACE = "interface"
    ENDPOINT = "endpoint"
    VARIABLE = "variable"
    TYPE_ALIAS = "type_alias"


class EdgeType(str, Enum):
    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS = "inherits"
    CONSUMES_API = "consumes_api"
    DEFINES = "defines"


@dataclass
class CodeNode:
    """
    Represents a structural code symbol extracted via Tree-sitter / SCIP.
    """
    id: str                               # Deterministic ID: "repo:file_path:symbol_name:start_line"
    repo: str                             # e.g., "repo_auth_core"
    file_path: str                        # Relative normalized path: "src/auth/service.py"
    symbol_name: str                      # Function / Class name: "verify_token"
    symbol_type: SymbolType               # SymbolType enum
    start_line: int                       # 1-indexed start line
    end_line: int                         # 1-indexed end line
    signature: Optional[str] = ""         # Signature e.g. "def verify_token(token: str) -> bool"
    docstring: Optional[str] = ""         # Extracted documentation / comments
    code_content: Optional[str] = ""      # Complete unbroken code block
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def generate_id(cls, repo: str, file_path: str, symbol_name: str, start_line: int) -> str:
        clean_path = file_path.replace("\\", "/").strip("/")
        return f"{repo}:{clean_path}:{symbol_name}:{start_line}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["symbol_type"] = self.symbol_type.value if isinstance(self.symbol_type, SymbolType) else self.symbol_type
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeNode":
        st = data.get("symbol_type", "function")
        if isinstance(st, str):
            try:
                st = SymbolType(st)
            except ValueError:
                st = SymbolType.FUNCTION
        return cls(
            id=data["id"],
            repo=data["repo"],
            file_path=data["file_path"].replace("\\", "/"),
            symbol_name=data["symbol_name"],
            symbol_type=st,
            start_line=int(data["start_line"]),
            end_line=int(data["end_line"]),
            signature=data.get("signature", ""),
            docstring=data.get("docstring", ""),
            code_content=data.get("code_content", ""),
            metadata=data.get("metadata", {})
        )

    def to_markdown_snippet(self) -> str:
        """Formats the node as a clean context slice for LLM ingestion."""
        return (
            f"### [{self.repo}] {self.file_path} (Lines {self.start_line}-{self.end_line})\n"
            f"**Symbol**: `{self.symbol_name}` ({self.symbol_type.value})\n"
            f"**Signature**: `{self.signature}`\n"
            f"```python\n{self.code_content or self.signature}\n```\n"
        )


@dataclass
class CodeEdge:
    """
    Represents a directional dependency relationship between two code symbols.
    """
    caller_id: str                        # Node ID of the caller/consumer
    callee_id: str                        # Node ID of the callee/definition
    edge_type: EdgeType                   # EdgeType enum
    confidence: float = 1.0               # 1.0 = compiler exact, 0.8 = heuristic/regex
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edge_type"] = self.edge_type.value if isinstance(self.edge_type, EdgeType) else self.edge_type
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeEdge":
        et = data.get("edge_type", "calls")
        if isinstance(et, str):
            try:
                et = EdgeType(et)
            except ValueError:
                et = EdgeType.CALLS
        return cls(
            caller_id=data["caller_id"],
            callee_id=data["callee_id"],
            edge_type=et,
            confidence=float(data.get("confidence", 1.0)),
            metadata=data.get("metadata", {})
        )


@dataclass
class RetrievalResult:
    """
    Standardized response from MCP tools to the Strands Agent.
    """
    nodes: List[CodeNode] = field(default_factory=list)
    edges: List[CodeEdge] = field(default_factory=list)
    query: str = ""
    execution_time_ms: float = 0.0
    source: str = "sqlite_graph"          # "sqlite_graph" | "opensearch_vector" | "mock"

    def format_context_for_llm(self) -> str:
        """Serializes the retrieval payload into token-efficient context."""
        if not self.nodes:
            return "No matching code symbols found."
        
        sections = [f"## Retrieved Code Context (Source: {self.source}, {len(self.nodes)} symbols, {self.execution_time_ms:.1f}ms):"]
        for node in self.nodes:
            sections.append(node.to_markdown_snippet())
        
        if self.edges:
            sections.append("### Dependency Links:")
            for edge in self.edges:
                sections.append(f"- `{edge.caller_id}` --[{edge.edge_type.value}]--> `{edge.callee_id}`")
        
        return "\n".join(sections)


@dataclass
class TraversalResult:
    """
    Result of a cross-repo blast-radius graph traversal.
    """
    root_symbol: str
    depth: int
    upstream_callers: List[CodeNode] = field(default_factory=list)
    downstream_dependencies: List[CodeNode] = field(default_factory=list)
    blast_radius_files: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def summary(self) -> str:
        unique_repos = set(node.repo for node in self.upstream_callers + self.downstream_dependencies)
        return (
            f"Traversal for `{self.root_symbol}` (Depth: {self.depth}):\n"
            f"- Affected Repositories: {', '.join(unique_repos) or 'None'}\n"
            f"- Total Upstream Callers: {len(self.upstream_callers)}\n"
            f"- Total Downstream Dependencies: {len(self.downstream_dependencies)}\n"
            f"- Files in Blast Radius: {len(self.blast_radius_files)}"
        )
