"""Universal Data Contracts for OmniContext.

Defines the core data models for nodes, edges, AST chunks, and graph traversal results.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    ENDPOINT = "endpoint"
    INTERFACE = "interface"
    VARIABLE = "variable"
    MODULE = "module"
    TYPE_ALIAS = "type_alias"


class EdgeType(str, Enum):
    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS = "inherits"
    CONSUMES_API = "consumes_api"
    EXPORTS = "exports"
    DEPENDS_ON = "depends_on"


class CodeNode(BaseModel):
    """Represents a structural code symbol extracted via AST parsing."""
    id: str = Field(..., description="Globally unique symbol ID: 'repo:file_path:symbol_name:start_line'")
    repo: str = Field(..., description="Repository identifier (e.g., repo_auth_core)")
    file_path: str = Field(..., description="Relative file path within repository")
    symbol_name: str = Field(..., description="Name of the function, class, endpoint, or variable")
    symbol_type: SymbolType = Field(default=SymbolType.FUNCTION, description="Type of code entity")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    signature: Optional[str] = Field(default=None, description="Function/Method signature or type declaration")
    docstring: Optional[str] = Field(default=None, description="Extracted docstring or JSDoc comment")
    code_content: Optional[str] = Field(default=None, description="Full source content of the structural chunk")
    language: str = Field(default="python", description="Language of source file (python, typescript, javascript, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata (e.g. HTTP method, route)")


class CodeEdge(BaseModel):
    """Represents a directional relationship between two code entities."""
    id: Optional[str] = Field(default=None, description="Unique edge identifier")
    caller_id: str = Field(..., description="Origin node ID (caller / consumer / importer)")
    callee_id: str = Field(..., description="Destination node ID (callee / provider / imported)")
    edge_type: EdgeType = Field(default=EdgeType.CALLS, description="Type of semantic relation")
    caller_repo: Optional[str] = Field(default=None, description="Origin repository")
    callee_repo: Optional[str] = Field(default=None, description="Destination repository")
    context_line: Optional[int] = Field(default=None, description="Line number where reference occurs")
    call_snippet: Optional[str] = Field(default=None, description="Source line or snippet of the call")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or parameters")


class ASTChunk(BaseModel):
    """A boundary-safe code slice generated from AST nodes."""
    node_id: str
    repo: str
    file_path: str
    symbol_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    code_content: str
    language: str
    dependencies: List[str] = Field(default_factory=list, description="Referenced symbol names inside chunk")
    token_count_estimate: int = Field(default=0, description="Estimated token size")


class TraversalResult(BaseModel):
    """Result of traversing caller/callee graphs."""
    entry_symbol: str
    direction: str = "downstream"
    depth: int = 1
    nodes: List[CodeNode] = Field(default_factory=list)
    edges: List[CodeEdge] = Field(default_factory=list)
    impacted_repos: List[str] = Field(default_factory=list)
    summary: str = ""


class BlastRadiusReport(BaseModel):
    """Analysis of changes affecting downstream/upstream components."""
    target_symbol: str
    target_node: Optional[CodeNode] = None
    direct_callers: List[CodeNode] = Field(default_factory=list)
    indirect_callers: List[CodeNode] = Field(default_factory=list)
    cross_repo_impact: Dict[str, List[CodeNode]] = Field(default_factory=dict)
    recommended_actions: List[str] = Field(default_factory=list)
    affected_endpoints: List[str] = Field(default_factory=list)
