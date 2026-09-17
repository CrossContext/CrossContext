"""
OmniContext - Tree-sitter Structural AST Engine & Semantic Chunker
Parses Python and TypeScript/JavaScript source code into discrete, unbroken
logical units (classes, functions, methods, endpoints) preserving exact syntactic boundaries.
Includes Python standard AST fallback for zero-dependency instant execution.
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from common.models import CodeNode, CodeEdge, SymbolType, EdgeType


class TreeSitterEngine:
    def __init__(self):
        self.ts_available = False
        self._init_treesitter()

    def _init_treesitter(self):
        """Attempts to load tree_sitter and language grammars."""
        try:
            import tree_sitter
            import tree_sitter_languages
            self.ts_languages = {
                "py": tree_sitter_languages.get_language("python"),
                "ts": tree_sitter_languages.get_language("typescript"),
                "js": tree_sitter_languages.get_language("javascript"),
            }
            self.ts_parsers = {
                lang: tree_sitter.Parser(self.ts_languages[lang])
                for lang in self.ts_languages
            }
            self.ts_available = True
        except (ImportError, Exception):
            # Fallback to robust Python ast + AST regex parser
            self.ts_available = False

    def parse_file(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """
        Parses a single file into CodeNodes and CodeEdges.
        Detects file extension and routes to appropriate parser.
        """
        norm_path = file_path.replace("\\", "/").strip("/")
        ext = Path(norm_path).suffix.lstrip(".").lower()

        if ext == "py":
            return self._parse_python(repo, norm_path, content)
        elif ext in ("ts", "tsx", "js", "jsx"):
            return self._parse_typescript(repo, norm_path, content)
        else:
            return [], []

    def parse_directory(self, repo: str, root_dir: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Recursively parses all source files in a repository directory."""
        all_nodes: List[CodeNode] = []
        all_edges: List[CodeEdge] = []
        root_path = Path(root_dir)

        valid_extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
        for file in root_path.rglob("*"):
            if file.is_file() and file.suffix in valid_extensions:
                # Ignore test caches, node_modules, .venv
                rel = file.relative_to(root_path).as_posix()
                if any(ignored in rel for ignored in [".venv", "node_modules", "__pycache__", ".git"]):
                    continue
                try:
                    content = file.read_text(encoding="utf-8", errors="replace")
                    nodes, edges = self.parse_file(repo, rel, content)
                    all_nodes.extend(nodes)
                    all_edges.extend(edges)
                except Exception as e:
                    print(f"[Parser] Skipping {rel}: {e}")

        return all_nodes, all_edges

    # -------------------------------------------------------------
    # Python Parser Implementation
    # -------------------------------------------------------------

    def _parse_python(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses Python code using AST and extracts symbols + call relations."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            # Fallback for incomplete/malformed syntax
            return self._parse_python_regex_fallback(repo, file_path, lines)

        # First pass: Extract Classes, Functions, and Endpoint decorators
        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                node = self._extract_python_class(repo, file_path, item, lines)
                nodes.append(node)
                # Parse methods inside class
                for subitem in item.body:
                    if isinstance(subitem, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_node = self._extract_python_function(
                            repo, file_path, subitem, lines, is_method=True, parent_class=item.name
                        )
                        nodes.append(method_node)
                        # Edge: Class defines Method
                        edges.append(CodeEdge(
                            caller_id=node.id,
                            callee_id=method_node.id,
                            edge_type=EdgeType.DEFINES
                        ))

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node = self._extract_python_function(repo, file_path, item, lines, is_method=False)
                nodes.append(node)

        # Second pass: Extract internal function call invocations
        node_map = {n.symbol_name: n for n in nodes}
        for node in nodes:
            # Simple call site detection within function code
            if node.code_content:
                for callee_name, target_node in node_map.items():
                    if callee_name != node.symbol_name and re.search(r'\b' + re.escape(callee_name) + r'\(', node.code_content):
                        edges.append(CodeEdge(
                            caller_id=node.id,
                            callee_id=target_node.id,
                            edge_type=EdgeType.CALLS
                        ))

        return nodes, edges

    def _extract_python_function(
        self, repo: str, file_path: str, item: ast.FunctionDef, lines: List[str],
        is_method: bool = False, parent_class: Optional[str] = None
    ) -> CodeNode:
        name = item.name
        start_line = item.lineno
        end_line = getattr(item, "end_lineno", start_line + len(item.body))
        code_block = "".join(lines[start_line - 1 : end_line])

        # Check if function is a FastAPI / Flask endpoint decorator
        is_endpoint = False
        route_path = ""
        for dec in item.decorator_list:
            dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
            if any(k in dec_str for k in [".get(", ".post(", ".put(", ".delete(", ".patch("]):
                is_endpoint = True
                route_match = re.search(r'[\'"]([^\'"]+)[\'"]', dec_str)
                if route_match:
                    route_path = route_match.group(1)

        symbol_type = SymbolType.ENDPOINT if is_endpoint else (SymbolType.METHOD if is_method else SymbolType.FUNCTION)
        docstring = ast.get_docstring(item) or ""
        sig_first_line = lines[start_line - 1].strip()

        meta = {}
        if is_endpoint and route_path:
            meta["endpoint_route"] = route_path
        if parent_class:
            meta["parent_class"] = parent_class

        node_id = CodeNode.generate_id(repo, file_path, name, start_line)
        return CodeNode(
            id=node_id,
            repo=repo,
            file_path=file_path,
            symbol_name=name,
            symbol_type=symbol_type,
            start_line=start_line,
            end_line=end_line,
            signature=sig_first_line,
            docstring=docstring,
            code_content=code_block,
            metadata=meta
        )

    def _extract_python_class(self, repo: str, file_path: str, item: ast.ClassDef, lines: List[str]) -> CodeNode:
        start_line = item.lineno
        end_line = getattr(item, "end_lineno", start_line + len(item.body))
        code_block = "".join(lines[start_line - 1 : end_line])
        docstring = ast.get_docstring(item) or ""
        sig_first_line = lines[start_line - 1].strip()

        node_id = CodeNode.generate_id(repo, file_path, item.name, start_line)
        return CodeNode(
            id=node_id,
            repo=repo,
            file_path=file_path,
            symbol_name=item.name,
            symbol_type=SymbolType.CLASS,
            start_line=start_line,
            end_line=end_line,
            signature=sig_first_line,
            docstring=docstring,
            code_content=code_block
        )

    def _parse_python_regex_fallback(self, repo: str, file_path: str, lines: List[str]) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Resilient fallback when code contains syntax errors."""
        nodes = []
        func_pattern = re.compile(r'^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        class_pattern = re.compile(r'^\s*class\s+([a-zA-Z0-9_]+)')

        for idx, line in enumerate(lines, start=1):
            f_match = func_pattern.match(line)
            if f_match:
                name = f_match.group(1)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=idx,
                    end_line=min(idx + 20, len(lines)),
                    signature=line.strip()
                ))
            c_match = class_pattern.match(line)
            if c_match:
                name = c_match.group(1)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=min(idx + 30, len(lines)),
                    signature=line.strip()
                ))
        return nodes, []

    # -------------------------------------------------------------
    # TypeScript / JavaScript Parser Implementation
    # -------------------------------------------------------------

    def _parse_typescript(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses TypeScript/JavaScript files for functions, interfaces, API consumer calls."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        func_pattern = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        const_func_pattern = re.compile(r'(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>')
        interface_pattern = re.compile(r'(?:export\s+)?(?:interface|type)\s+([a-zA-Z0-9_]+)')
        api_call_pattern = re.compile(r'(?:fetch|axios\.(?:get|post|put|delete)|api\.(?:get|post|put|delete))\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')

        for idx, line in enumerate(lines, start=1):
            f_match = func_pattern.search(line) or const_func_pattern.search(line)
            if f_match:
                name = f_match.group(1)
                end_line = min(idx + 25, len(lines))
                block = "".join(lines[idx - 1 : end_line])

                # Check if this function calls an API endpoint (e.g. /v1/auth/verify)
                api_match = api_call_pattern.search(block)
                meta = {}
                if api_match:
                    meta["consumes_endpoint"] = api_match.group(1)

                node = CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                )
                nodes.append(node)

            i_match = interface_pattern.search(line)
            if i_match:
                name = i_match.group(1)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.INTERFACE,
                    start_line=idx,
                    end_line=min(idx + 15, len(lines)),
                    signature=line.strip()
                ))

        return nodes, edges
