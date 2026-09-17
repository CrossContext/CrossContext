"""Boundary-Aware AST Parser and Semantic Chunker for OmniContext.

Parses source code into complete, unbroken structural AST nodes (classes, functions,
methods, interfaces, endpoints) rather than arbitrary token windows.
Supports Python, TypeScript, JavaScript, and Go, with zero-dependency native fallback
if tree-sitter C++ grammars are not compiled.
"""

from __future__ import annotations
import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from common.models import CodeNode, ASTChunk, SymbolType


class TreeSitterEngine:
    """Parses multi-language source files into structured AST nodes and chunks."""

    def __init__(self):
        self.has_treesitter = False
        try:
            import tree_sitter  # type: ignore
            self.has_treesitter = True
        except ImportError:
            self.has_treesitter = False

    def parse_file(self, file_path: Union[str, Path], repo: str) -> List[CodeNode]:
        """Parses a source file into structural CodeNodes."""
        path = Path(file_path)
        if not path.is_file():
            return []

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []

        ext = path.suffix.lower()
        rel_path = str(path.as_posix())

        if ext == ".py":
            return self._parse_python(content, rel_path, repo)
        elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            return self._parse_typescript_javascript(content, rel_path, repo, is_ts=ext in (".ts", ".tsx"))
        elif ext == ".go":
            return self._parse_go(content, rel_path, repo)
        else:
            return self._parse_generic(content, rel_path, repo)

    def chunk_file(self, file_path: Union[str, Path], repo: str) -> List[ASTChunk]:
        """Converts structural CodeNodes into semantic ASTChunks."""
        nodes = self.parse_file(file_path, repo)
        chunks: List[ASTChunk] = []
        for node in nodes:
            content = node.code_content or ""
            # Estimate token count (rough heuristic: 1 token ~ 4 chars / 0.75 words)
            token_est = max(1, len(content) // 4)
            chunks.append(
                ASTChunk(
                    node_id=node.id,
                    repo=node.repo,
                    file_path=node.file_path,
                    symbol_name=node.symbol_name,
                    symbol_type=node.symbol_type,
                    start_line=node.start_line,
                    end_line=node.end_line,
                    code_content=content,
                    language=node.language,
                    dependencies=node.metadata.get("calls", []),
                    token_count_estimate=token_est,
                )
            )
        return chunks

    def _parse_python(self, content: str, file_path: str, repo: str) -> List[CodeNode]:
        """Extracts functions, classes, async functions, and FastAPI/Flask endpoints from Python code."""
        nodes: List[CodeNode] = []
        lines = content.splitlines()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            # Fallback to regex parser on syntax errors
            return self._parse_python_regex(content, lines, file_path, repo)

        class PythonASTVisitor(ast.NodeVisitor):
            def __init__(self, engine: TreeSitterEngine):
                self.engine = engine
                self.current_class: Optional[str] = None

            def visit_ClassDef(self, node: ast.ClassDef):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                code = "\n".join(lines[start - 1 : end]) if start - 1 < len(lines) else ""
                doc = ast.get_docstring(node)
                bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
                sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

                node_id = f"{repo}:{file_path}:{node.name}:{start}"
                nodes.append(
                    CodeNode(
                        id=node_id,
                        repo=repo,
                        file_path=file_path,
                        symbol_name=node.name,
                        symbol_type=SymbolType.CLASS,
                        start_line=start,
                        end_line=end,
                        signature=sig,
                        docstring=doc,
                        code_content=code,
                        language="python",
                        metadata={"bases": bases, "decorators": [ast.unparse(d) for d in node.decorator_list] if hasattr(ast, "unparse") else []},
                    )
                )

                prev_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = prev_class

            def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
                self._handle_func(node, is_async=isinstance(node, ast.AsyncFunctionDef))

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._handle_func(node, is_async=True)

            def _handle_func(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                code = "\n".join(lines[start - 1 : end]) if start - 1 < len(lines) else ""
                doc = ast.get_docstring(node)

                decorators = []
                http_method = None
                route_path = None
                for dec in node.decorator_list:
                    if hasattr(ast, "unparse"):
                        dec_str = ast.unparse(dec)
                        decorators.append(dec_str)
                        # Detect FastAPI/Flask routes: app.get('/v1/auth/verify'), @router.post('/token')
                        route_match = re.search(r"@?(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", dec_str, re.IGNORECASE)
                        if route_match:
                            http_method = route_match.group(1).upper()
                            route_path = route_match.group(2)

                calls = []
                for subnode in ast.walk(node):
                    if isinstance(subnode, ast.Call):
                        if isinstance(subnode.func, ast.Name):
                            calls.append(subnode.func.id)
                        elif isinstance(subnode.func, ast.Attribute):
                            calls.append(subnode.func.attr)

                prefix = "async def " if is_async else "def "
                sig = f"{prefix}{node.name}(...)"
                if hasattr(ast, "unparse"):
                    try:
                        args_str = ast.unparse(node.args)
                        ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                        sig = f"{prefix}{node.name}({args_str}){ret_str}"
                    except Exception:
                        pass

                sym_type = SymbolType.ENDPOINT if route_path else (SymbolType.METHOD if self.current_class else SymbolType.FUNCTION)
                sym_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
                node_id = f"{repo}:{file_path}:{sym_name}:{start}"

                meta = {
                    "is_async": is_async,
                    "decorators": decorators,
                    "calls": list(set(calls)),
                    "parent_class": self.current_class,
                }
                if route_path:
                    meta["http_method"] = http_method
                    meta["route_path"] = route_path

                nodes.append(
                    CodeNode(
                        id=node_id,
                        repo=repo,
                        file_path=file_path,
                        symbol_name=sym_name,
                        symbol_type=sym_type,
                        start_line=start,
                        end_line=end,
                        signature=sig,
                        docstring=doc,
                        code_content=code,
                        language="python",
                        metadata=meta,
                    )
                )

        visitor = PythonASTVisitor(self)
        visitor.visit(tree)
        return nodes

    def _parse_python_regex(self, content: str, lines: List[str], file_path: str, repo: str) -> List[CodeNode]:
        """Regex fallback parser for Python when AST parsing encounters syntax errors."""
        nodes: List[CodeNode] = []
        pattern = re.compile(r"^(?P<indent>\s*)(?:@(?P<dec>[^\n]+)\n\s*)*(?P<async>async\s+)?def\s+(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\((?P<args>[^)]*)\)", re.MULTILINE)

        for match in pattern.finditer(content):
            name = match.group("name")
            start_pos = match.start()
            start_line = content.count("\n", 0, start_pos) + 1
            is_async = bool(match.group("async"))
            dec = match.group("dec") or ""

            # Find boundary
            end_line = min(len(lines), start_line + 15)
            code = "\n".join(lines[start_line - 1 : end_line])

            sig = f"{'async ' if is_async else ''}def {name}({match.group('args')})"
            node_id = f"{repo}:{file_path}:{name}:{start_line}"
            nodes.append(
                CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=start_line,
                    end_line=end_line,
                    signature=sig,
                    docstring=None,
                    code_content=code,
                    language="python",
                    metadata={"decorators": [dec] if dec else []},
                )
            )
        return nodes

    def _parse_typescript_javascript(self, content: str, file_path: str, repo: str, is_ts: bool) -> List[CodeNode]:
        """Parses TypeScript/JavaScript functions, classes, interfaces, React components, and API callers."""
        nodes: List[CodeNode] = []
        lines = content.splitlines()

        # Regex for interfaces & type aliases
        if is_ts:
            for m in re.finditer(r"^(?:export\s+)?interface\s+([A-Za-z0-9_]+)(?:\s+extends\s+[A-Za-z0-9_,\s]+)?\s*\{", content, re.MULTILINE):
                name = m.group(1)
                start_line = content.count("\n", 0, m.start()) + 1
                end_line = self._find_closing_brace(content, m.start(), lines)
                code = "\n".join(lines[start_line - 1 : end_line])
                node_id = f"{repo}:{file_path}:{name}:{start_line}"
                nodes.append(
                    CodeNode(
                        id=node_id,
                        repo=repo,
                        file_path=file_path,
                        symbol_name=name,
                        symbol_type=SymbolType.INTERFACE,
                        start_line=start_line,
                        end_line=end_line,
                        signature=f"interface {name}",
                        docstring=None,
                        code_content=code,
                        language="typescript",
                        metadata={"is_interface": True},
                    )
                )

        # Regex for classes
        for m in re.finditer(r"^(?:export\s+)?class\s+([A-Za-z0-9_]+)(?:\s+extends\s+[A-Za-z0-9_]+)?(?:\s+implements\s+[A-Za-z0-9_,\s]+)?\s*\{", content, re.MULTILINE):
            name = m.group(1)
            start_line = content.count("\n", 0, m.start()) + 1
            end_line = self._find_closing_brace(content, m.start(), lines)
            code = "\n".join(lines[start_line - 1 : end_line])
            node_id = f"{repo}:{file_path}:{name}:{start_line}"
            nodes.append(
                CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=start_line,
                    end_line=end_line,
                    signature=f"class {name}",
                    docstring=None,
                    code_content=code,
                    language="typescript" if is_ts else "javascript",
                    metadata={},
                )
            )

        # Regex for methods & functions
        # 1. Standard functions: function foo(...)
        # 2. Arrow functions: const foo = async (...) =>
        # 3. Class methods: async verifySessionToken(...) or verifySessionToken(...)
        method_pattern = re.compile(
            r"^(?P<indent>[ \t]*)(?:export\s+)?(?:async\s+)?(?:(?P<is_func>function\s+)|(?P<is_const>(?:const|let|var)\s+))?(?P<name>[A-Za-z0-9_]+)\s*(?:=\s*(?:async\s*)?\((?P<arrow_args>[^)]*)\)\s*(?::\s*[^=]+)?=>|\((?P<args>[^)]*)\)\s*(?::\s*[^{]+)?)\s*\{",
            re.MULTILINE,
        )

        for m in method_pattern.finditer(content):
            name = m.group("name")
            if name in ("if", "for", "while", "switch", "catch", "class", "interface", "constructor"):
                continue

            args = m.group("args") or m.group("arrow_args") or ""
            start_line = content.count("\n", 0, m.start()) + 1
            end_line = self._find_closing_brace(content, m.start(), lines)
            code = "\n".join(lines[start_line - 1 : end_line])

            # Extract API calls made inside the function or method
            api_calls = []
            # Match fetch(`...`), axios.get('...'), or string routes /v1/...
            for api_match in re.finditer(r"(?:fetch|axios\.(?:get|post|put|delete|patch)|apiClient\.(?:get|post|put|delete|patch))\s*\(\s*[`'\"]([^`'\"]+)[`'\"]", code):
                route_candidate = api_match.group(1)
                # If template literal like `${this.baseUrl}/v1/auth/verify`, extract the path
                path_match = re.search(r"(/(?:v[0-9]+/)?(?:api/)?[a-zA-Z0-9_\-\/]+)", route_candidate)
                if path_match:
                    api_calls.append(path_match.group(1))
                else:
                    api_calls.append(route_candidate)

            # Also check for direct route strings in the method body
            for route_m in re.finditer(r"['\"`](/(?:v[0-9]+)/[a-zA-Z0-9_\-\/]+)['\"`]", code):
                api_calls.append(route_m.group(1))

            # Extract generic function calls
            calls = [c.group(1) for c in re.finditer(r"\b([A-Za-z0-9_]+)\s*\(", code) if c.group(1) != name and c.group(1) not in ("fetch", "catch", "then", "if", "for")]

            node_id = f"{repo}:{file_path}:{name}:{start_line}"
            nodes.append(
                CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=start_line,
                    end_line=end_line,
                    signature=f"function {name}({args})",
                    docstring=None,
                    code_content=code,
                    language="typescript" if is_ts else "javascript",
                    metadata={"calls": list(set(calls)), "api_calls": list(set(api_calls))},
                )
            )

        return nodes

    def _parse_go(self, content: str, file_path: str, repo: str) -> List[CodeNode]:
        """Parses Go functions, structs, and methods."""
        nodes: List[CodeNode] = []
        lines = content.splitlines()

        # Func declarations: func (r *Receiver) MethodName(args) ret { ... } or func FunctionName(args) ret { ... }
        pattern = re.compile(r"^func\s+(?:\((?P<recv>[^)]+)\)\s+)?(?P<name>[A-Za-z0-9_]+)\s*\((?P<args>[^)]*)\)", re.MULTILINE)
        for m in pattern.finditer(content):
            name = m.group("name")
            recv = m.group("recv")
            start_line = content.count("\n", 0, m.start()) + 1
            end_line = self._find_closing_brace(content, m.start(), lines)
            code = "\n".join(lines[start_line - 1 : end_line])
            sig = f"func ({recv}) {name}({m.group('args')})" if recv else f"func {name}({m.group('args')})"
            sym_name = f"{recv.split()[-1]}.{name}" if recv else name

            node_id = f"{repo}:{file_path}:{sym_name}:{start_line}"
            nodes.append(
                CodeNode(
                    id=node_id,
                    repo=repo,
                    file_path=file_path,
                    symbol_name=sym_name,
                    symbol_type=SymbolType.METHOD if recv else SymbolType.FUNCTION,
                    start_line=start_line,
                    end_line=end_line,
                    signature=sig,
                    docstring=None,
                    code_content=code,
                    language="go",
                    metadata={"receiver": recv},
                )
            )

        return nodes

    def _parse_generic(self, content: str, file_path: str, repo: str) -> List[CodeNode]:
        """Fallback parser for generic text / config files."""
        lines = content.splitlines()
        node_id = f"{repo}:{file_path}:module:1"
        return [
            CodeNode(
                id=node_id,
                repo=repo,
                file_path=file_path,
                symbol_name=Path(file_path).name,
                symbol_type=SymbolType.MODULE,
                start_line=1,
                end_line=len(lines) if lines else 1,
                signature=f"file {Path(file_path).name}",
                docstring=None,
                code_content=content,
                language="text",
                metadata={},
            )
        ]

    def _find_closing_brace(self, content: str, start_index: int, lines: List[str]) -> int:
        """Finds the line number of matching closing brace, or defaults to reasonable window."""
        open_brace = content.find("{", start_index)
        if open_brace == -1:
            start_line = content.count("\n", 0, start_index) + 1
            return min(len(lines), start_line + 20)

        depth = 0
        in_string = False
        quote_char = ""
        for i in range(open_brace, len(content)):
            char = content[i]
            if in_string:
                if char == quote_char and (i == 0 or content[i - 1] != "\\"):
                    in_string = False
                continue
            if char in ('"', "'", "`"):
                in_string = True
                quote_char = char
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return content.count("\n", 0, i) + 1

        start_line = content.count("\n", 0, start_index) + 1
        return min(len(lines), start_line + 30)
