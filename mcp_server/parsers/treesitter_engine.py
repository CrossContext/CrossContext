"""OmniContext - Multi-Language Structural AST Engine & Semantic Chunker.

Parses Python, TypeScript, JavaScript, Go, and Java source code into discrete, unbroken
logical units (classes, functions, methods, endpoints) preserving exact syntactic boundaries.
Includes standard library AST and resilient AST regex fallback for zero-dependency instant execution.
"""

from __future__ import annotations
import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from common.models import CodeNode, CodeEdge, SymbolType, EdgeType


class TreeSitterEngine:
    """Multi-language AST parsing and boundary-aware code chunking engine."""

    def __init__(self):
        self.ts_available = False
        self._init_treesitter()

    def _init_treesitter(self):
        """Attempts to load tree_sitter and language grammars if installed."""
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
            self.ts_available = False

    def parse_file(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses a single source file into CodeNodes and internal CodeEdges."""
        norm_path = file_path.replace("\\", "/").strip("/")
        ext = Path(norm_path).suffix.lstrip(".").lower()

        if ext == "py":
            return self._parse_python(repo, norm_path, content)
        elif ext in ("ts", "tsx", "js", "jsx", "mjs", "cjs"):
            return self._parse_typescript_javascript(repo, norm_path, content)
        elif ext == "go":
            return self._parse_go(repo, norm_path, content)
        elif ext == "java":
            return self._parse_java(repo, norm_path, content)
        else:
            return self._parse_generic(repo, norm_path, content)

    def parse_directory(self, repo: str, root_dir: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Recursively parses all supported source files in a repository directory."""
        all_nodes: List[CodeNode] = []
        all_edges: List[CodeEdge] = []
        root_path = Path(root_dir)

        valid_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java"}
        for file in root_path.rglob("*"):
            if file.is_file() and file.suffix in valid_extensions:
                rel = file.relative_to(root_path).as_posix()
                if any(ignored in rel for ignored in [".venv", "venv", "node_modules", "__pycache__", ".git", "dist", "build"]):
                    continue
                try:
                    content = file.read_text(encoding="utf-8", errors="replace")
                    nodes, edges = self.parse_file(repo, rel, content)
                    all_nodes.extend(nodes)
                    all_edges.extend(edges)
                except Exception as e:
                    print(f"[Parser] Skipping {rel}: {e}")

        return all_nodes, all_edges

    @staticmethod
    def _find_closing_brace(lines: List[str], start_idx: int) -> int:
        """Finds the 1-indexed line number of matching closing brace for a code block."""
        depth = 0
        found_open = False
        for i in range(start_idx - 1, len(lines)):
            line = lines[i]
            clean_line = re.sub(r'//.*$|/\*.*?\*/', '', line)
            for ch in clean_line:
                if ch == '{':
                    depth += 1
                    found_open = True
                elif ch == '}':
                    depth -= 1
                    if found_open and depth == 0:
                        return i + 1
        return min(start_idx + 30, len(lines))

    # -------------------------------------------------------------
    # Python Parser Implementation
    # -------------------------------------------------------------

    def _parse_python(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses Python code using AST and extracts symbols, endpoints, imports, and call relations."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return self._parse_python_regex_fallback(repo, file_path, lines)

        # Extract imports for resolvable call linkage
        file_imports = []
        for item in tree.body:
            if isinstance(item, ast.Import):
                for alias in item.names:
                    file_imports.append(alias.name)
            elif isinstance(item, ast.ImportFrom) and item.module:
                file_imports.append(item.module)
                for alias in item.names:
                    file_imports.append(f"{item.module}.{alias.name}")

        # First pass: Extract Classes, Functions, and Endpoint decorators
        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                node = self._extract_python_class(repo, file_path, item, lines)
                node.metadata["file_imports"] = file_imports
                nodes.append(node)

                # Class inheritance edge
                for base in item.bases:
                    base_name = ast.unparse(base) if hasattr(ast, "unparse") else getattr(base, "id", "")
                    if base_name:
                        node.metadata.setdefault("bases", []).append(base_name)

                # Parse methods inside class
                for subitem in item.body:
                    if isinstance(subitem, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_node = self._extract_python_function(
                            repo, file_path, subitem, lines, is_method=True, parent_class=item.name
                        )
                        method_node.metadata["file_imports"] = file_imports
                        nodes.append(method_node)
                        edges.append(CodeEdge(
                            caller_id=node.id,
                            callee_id=method_node.id,
                            edge_type=EdgeType.DEFINES
                        ))

            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node = self._extract_python_function(repo, file_path, item, lines, is_method=False)
                node.metadata["file_imports"] = file_imports
                nodes.append(node)

        # Second pass: Extract internal function call invocations
        node_map = {n.symbol_name: n for n in nodes}
        for node in nodes:
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
        self, repo: str, file_path: str, item: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        lines: List[str], is_method: bool = False, parent_class: Optional[str] = None
    ) -> CodeNode:
        name = item.name
        start_line = item.lineno
        end_line = getattr(item, "end_lineno", start_line + len(item.body))
        code_block = "".join(lines[start_line - 1 : end_line])

        # Check if function is a FastAPI / Flask endpoint decorator
        is_endpoint = False
        route_path = ""
        http_method = "GET"
        for dec in item.decorator_list:
            dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
            route_match = re.search(r'@?(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', dec_str, re.IGNORECASE)
            if route_match:
                is_endpoint = True
                http_method = route_match.group(1).upper()
                route_path = route_match.group(2)

        symbol_type = SymbolType.ENDPOINT if is_endpoint else (SymbolType.METHOD if is_method else SymbolType.FUNCTION)
        docstring = ast.get_docstring(item) or ""
        sig_first_line = lines[start_line - 1].strip()

        meta = {}
        if is_endpoint and route_path:
            meta["endpoint_route"] = route_path
            meta["http_method"] = http_method
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
                end_line = self._find_closing_brace(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip()
                ))
            c_match = class_pattern.match(line)
            if c_match:
                name = c_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip()
                ))
        return nodes, []

    # -------------------------------------------------------------
    # TypeScript / JavaScript Parser Implementation
    # -------------------------------------------------------------

    def _parse_typescript_javascript(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses TypeScript/JavaScript files for functions, classes, interfaces, and API calls."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        # Extract import statements
        file_imports = []
        for imp_match in re.finditer(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content):
            file_imports.append(imp_match.group(1))

        # 1. Interface & Type definitions
        interface_pattern = re.compile(r'(?:export\s+)?(?:interface|type)\s+([a-zA-Z0-9_]+)')
        for idx, line in enumerate(lines, start=1):
            i_match = interface_pattern.search(line)
            if i_match:
                name = i_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.INTERFACE,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

        # 2. Functions, Arrow functions, and Class methods
        func_patterns = [
            re.compile(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)'),
            re.compile(r'(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\((.*?)\)\s*(?::\s*[^=]+)?=>'),
            re.compile(r'^\s*(?:public|private|protected|async)?\s*(?:async\s+)?([a-zA-Z0-9_]+)\s*\((.*?)\)\s*(?::\s*[^{]+)?\s*\{'),
        ]

        api_call_pattern = re.compile(r'(?:fetch|axios\.(?P<method>get|post|put|delete|patch)|apiClient\.(?P<client_method>get|post|put|delete|patch)|api\.(?P<api_method>get|post|put|delete|patch))\s*\(\s*[`\'"]([^`\'"]+)[`\'"]')

        for idx, line in enumerate(lines, start=1):
            for pat in func_patterns:
                f_match = pat.search(line)
                if f_match:
                    name = f_match.group(1)
                    if name in ("if", "for", "while", "switch", "catch", "class", "interface", "constructor"):
                        continue

                    end_line = self._find_closing_brace(lines, idx)
                    block = "".join(lines[idx - 1 : end_line])

                    meta: Dict[str, Any] = {"file_imports": file_imports}

                    # Check for API endpoint calls
                    api_match = api_call_pattern.search(block)
                    if api_match:
                        raw_endpoint = api_match.group(4) or api_match.group(0)
                        http_verb = api_match.group("method") or api_match.group("client_method") or api_match.group("api_method") or "GET"
                        if "method: \"POST\"" in block or "method: 'POST'" in block:
                            http_verb = "POST"
                        elif "method: \"GET\"" in block or "method: 'GET'" in block:
                            http_verb = "GET"

                        # Strip protocol and domain if absolute URL (e.g. https://auth.internal.corp/api/v1/auth/verify)
                        cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_endpoint)
                        route_m = re.search(r'(/(?:api/)?(?:v[0-9]+/)?(?:api/)?[a-zA-Z0-9_\-\/]+)', cleaned_endpoint)
                        meta["consumes_endpoint"] = route_m.group(1) if route_m else cleaned_endpoint
                        meta["consumes_http_method"] = http_verb.upper()

                    # Direct route literal fallback
                    if "consumes_endpoint" not in meta:
                        for direct_match in re.finditer(r'[\'"`](https?://[^/]+(/[^/]+.*?))[\'"`]|[\'"`](/(?:api/)?(?:v[0-9]+/)[a-zA-Z0-9_\-\/]+)[\'"`]', block):
                            target_url = direct_match.group(2) if direct_match.group(2) else direct_match.group(3)
                            if target_url:
                                meta["consumes_endpoint"] = target_url
                                meta["consumes_http_method"] = "POST" if ("post" in block.lower() or "POST" in block) else "GET"
                                break

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
                    break

        return nodes, edges

    # -------------------------------------------------------------
    # Go Parser Implementation
    # -------------------------------------------------------------

    def _parse_go(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses Go files for functions, structs, and receiver methods with exact brace boundaries."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        func_pattern = re.compile(r'^func\s+(?:\((?P<recv>[^)]+)\)\s+)?(?P<name>[a-zA-Z0-9_]+)\s*\((?P<args>[^)]*)\)')
        struct_pattern = re.compile(r'^type\s+(?P<name>[a-zA-Z0-9_]+)\s+struct\s*\{')

        for idx, line in enumerate(lines, start=1):
            f_match = func_pattern.match(line)
            if f_match:
                name = f_match.group("name")
                recv = f_match.group("recv")
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                sym_type = SymbolType.METHOD if recv else SymbolType.FUNCTION
                node_id = CodeNode.generate_id(repo, file_path, name, idx)
                nodes.append(CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=sym_type,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata={"receiver": recv} if recv else {}
                ))

            s_match = struct_pattern.match(line)
            if s_match:
                name = s_match.group("name")
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                node_id = CodeNode.generate_id(repo, file_path, name, idx)
                nodes.append(CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # Java Parser Implementation
    # -------------------------------------------------------------

    def _parse_java(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses Java files for classes, methods, and Spring Boot annotations including controller prefixes."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        class_pattern = re.compile(r'public\s+(?:class|interface)\s+([a-zA-Z0-9_]+)')
        method_pattern = re.compile(r'public\s+(?:[a-zA-Z0-9_<>,\[\]]+\s+)+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        spring_method_route = re.compile(r'@(?P<verb>GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']')
        spring_class_route = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']')

        # Detect class-level @RequestMapping prefix
        class_prefix = ""
        for idx, line in enumerate(lines, start=1):
            if class_pattern.search(line):
                # Look at previous 3 lines for class annotation
                context_prev = "".join(lines[max(0, idx - 4) : idx])
                c_route_m = spring_class_route.search(context_prev)
                if c_route_m:
                    class_prefix = c_route_m.group(1).rstrip("/")
                break

        for idx, line in enumerate(lines, start=1):
            c_match = class_pattern.search(line)
            if c_match:
                name = c_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip()
                ))

            m_match = method_pattern.search(line)
            if m_match:
                name = m_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])

                # Check previous lines for Spring route annotation
                context_lines = "".join(lines[max(0, idx - 4) : idx])
                route_match = spring_method_route.search(context_lines) or spring_method_route.search(line)
                meta: Dict[str, Any] = {}
                is_endpoint = False

                if route_match:
                    is_endpoint = True
                    raw_subpath = route_match.group(2).lstrip("/")
                    composed_path = f"{class_prefix}/{raw_subpath}" if class_prefix else f"/{raw_subpath}"
                    verb_raw = route_match.group("verb").replace("Mapping", "").upper()
                    http_method = "GET" if verb_raw == "REQUEST" else verb_raw

                    meta["endpoint_route"] = composed_path
                    meta["http_method"] = http_method

                sym_type = SymbolType.ENDPOINT if is_endpoint else SymbolType.METHOD
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=sym_type,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                ))

        return nodes, edges

    def _parse_generic(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        return [], []
