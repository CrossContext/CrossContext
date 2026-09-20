"""CrossContext - Multi-Language Structural AST Engine & Semantic Chunker.

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

        if ext in ("py", "pyi"):
            return self._parse_python(repo, norm_path, content)
        elif ext in ("ts", "tsx", "js", "jsx", "mjs", "cjs"):
            return self._parse_typescript_javascript(repo, norm_path, content)
        elif ext == "go":
            return self._parse_go(repo, norm_path, content)
        elif ext == "java":
            return self._parse_java(repo, norm_path, content)
        elif ext == "php":
            return self._parse_php(repo, norm_path, content)
        elif ext == "rs":
            return self._parse_rust(repo, norm_path, content)
        elif ext in ("cs", "csx"):
            return self._parse_csharp(repo, norm_path, content)
        elif ext == "rb":
            return self._parse_ruby(repo, norm_path, content)
        elif ext in ("c", "cpp", "cc", "cxx", "h", "hpp"):
            return self._parse_cpp(repo, norm_path, content)
        elif ext in ("clj", "cljs", "cljc", "edn"):
            return self._parse_clojure(repo, norm_path, content)
        else:
            return self._parse_generic(repo, norm_path, content)

    def parse_directory(
        self,
        repo: str,
        root_dir: str,
        progress_cb: Optional[Any] = None
    ) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Recursively parses all source files in a repository directory."""
        all_nodes: List[CodeNode] = []
        all_edges: List[CodeEdge] = []
        root_path = Path(root_dir)

        valid_extensions = {
            ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
            ".go", ".java", ".php", ".rs", ".cs", ".csx", ".rb",
            ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
            ".clj", ".cljs", ".cljc", ".edn",
            ".kt", ".kts", ".swift", ".scala", ".dart",
            ".sh", ".bash", ".zsh", ".lua", ".r", ".R",
            ".pl", ".pm", ".ex", ".exs", ".erl", ".hs",
            ".jl", ".zig"
        }
        ignored_patterns = {
            ".venv", "venv", "node_modules", "vendor", "__pycache__",
            ".git", "dist", "build", "target", "bin", "obj", ".gradle",
            ".idea", ".vscode", "coverage", ".next", ".nuxt", ".turbo",
            "third_party", "deps", "docs", "documentation", "website", "site",
            "tests", "test", "fixtures", "mocks", "examples", "benchmark", "benchmarks"
        }

        candidates = []
        for root, dirs, files in os.walk(root_dir):
            # Prune directories in-place so os.walk NEVER descends into them
            dirs[:] = [
                d for d in dirs
                if d.lower() not in ignored_patterns
                and not d.startswith(".")
                and not any(p in d.lower() for p in ("node_modules", "vendor", "test", "docs"))
            ]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in valid_extensions:
                    full_p = Path(root) / f
                    try:
                        rel = full_p.relative_to(root_path).as_posix()
                        candidates.append((full_p, rel))
                    except Exception:
                        pass

        total_files = len(candidates)
        for idx, (file, rel) in enumerate(candidates):
            try:
                content = file.read_text(encoding="utf-8", errors="replace")
                nodes, edges = self.parse_file(repo, rel, content)
                all_nodes.extend(nodes)
                all_edges.extend(edges)
                if progress_cb and (idx % 25 == 0 or idx == total_files - 1):
                    progress_cb("parsing", f"Parsing AST symbols in {repo} ({idx+1}/{total_files} files)...", 0.5 + (0.2 * (idx / max(total_files, 1))))
            except Exception as e:
                print(f"[Parser] Skipping {rel}: {e}")

        # If repository contains no standard code nodes (e.g. documentation-only or configuration repo)
        if not all_nodes and root_path.exists():
            doc_candidates = list(root_path.glob("profile/README*")) or list(root_path.glob("README*")) or list(root_path.glob("*.md"))
            doc_file = doc_candidates[0] if doc_candidates else None
            doc_rel = doc_file.relative_to(root_path).as_posix() if doc_file else "README.md"
            doc_text = doc_file.read_text(encoding="utf-8", errors="replace")[:1000] if doc_file and doc_file.is_file() else ""
            all_nodes.append(CodeNode(
                id=CodeNode.generate_id(repo, doc_rel, repo, 1),
                repo=repo,
                file_path=doc_rel,
                symbol_name=repo,
                symbol_type=SymbolType.VARIABLE,
                start_line=1,
                end_line=max(1, len(doc_text.splitlines())),
                signature=f"repository {repo}",
                docstring=doc_text[:200].strip(),
                code_content=doc_text,
                metadata={"is_documentation_repo": True}
            ))

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
            route_match = re.search(r'@?(?:app|router|api|bp)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', dec_str, re.IGNORECASE)
            if route_match:
                is_endpoint = True
                http_method = route_match.group(1).upper()
                route_path = route_match.group(2)
            else:
                # Flask / Blueprint style @app.route('/path', methods=['GET', 'POST'])
                flask_match = re.search(r'@?(?:app|router|api|bp)\.route\s*\(\s*[\'"]([^\'"]+)[\'"](?:.*methods\s*=\s*\[([^\]]+)\])?', dec_str, re.IGNORECASE)
                if flask_match:
                    is_endpoint = True
                    route_path = flask_match.group(1)
                    if flask_match.group(2):
                        first_method = re.search(r'[\'"]([a-zA-Z]+)[\'"]', flask_match.group(2))
                        if first_method:
                            http_method = first_method.group(1).upper()

        symbol_type = SymbolType.ENDPOINT if is_endpoint else (SymbolType.METHOD if is_method else SymbolType.FUNCTION)
        docstring = ast.get_docstring(item) or ""
        sig_first_line = lines[start_line - 1].strip()

        meta = {}
        if is_endpoint and route_path:
            meta["endpoint_route"] = route_path
            meta["http_method"] = http_method
        else:
            # Check if this Python function consumes external endpoints via explicit HTTP client calls
            py_api_pattern = re.compile(
                r'(?:requests|httpx|aiohttp)\.(?P<method>get|post|put|delete|patch)\s*\(\s*f?[\'"`]([^\'"`]+)[\'"`]|'
                r'(?:requests|httpx)\.request\s*\(\s*[\'"`](?P<req_method>GET|POST|PUT|DELETE|PATCH)[\'"`]\s*,\s*f?[\'"`]([^\'"`]+)[\'"`]|'
                r'(?:session|client)\.(?P<client_method>get|post|put|delete|patch)\s*\(\s*f?[\'"`](https?://[^\'"`]+|/(?:api/|v[0-9]+/)[^\'"`]+)[\'"`]',
                re.IGNORECASE
            )
            api_match = py_api_pattern.search(code_block)
            if api_match:
                raw_url = api_match.group(2) or api_match.group(4) or api_match.group(6)
                if raw_url and (raw_url.startswith("http://") or raw_url.startswith("https://") or raw_url.startswith("/")):
                    http_verb = (api_match.group("method") or api_match.group("req_method") or api_match.group("client_method") or "GET").upper()
                    host_m = re.match(r'^https?://([^/]+)', raw_url)
                    if host_m:
                        meta["target_base_url"] = host_m.group(1).lower()

                    cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_url).split('?')[0].strip()
                    route_m = re.search(r'(/(?:api/)?(?:v[0-9]+/)?(?:api/)?[a-zA-Z0-9_\-\/{}:]+)', cleaned_endpoint)
                    final_ep = route_m.group(1) if route_m else cleaned_endpoint
                    # Guard: Ignore blank, bare slash without explicit host, or non-endpoint assets
                    if final_ep and final_ep != "/" and not any(final_ep.endswith(ext) for ext in ('.py', '.ts', '.js', '.json', '.html', '.css', '.png', '.jpg')):
                        meta["consumes_endpoint"] = final_ep
                        meta["consumes_http_method"] = http_verb

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

        api_call_pattern = re.compile(
            r'(?:fetch|axios\.(?P<method>get|post|put|delete|patch)|axios|'
            r'ky\.(?P<ky_method>get|post|put|delete|patch)|ky|'
            r'apiClient\.(?P<client_method>get|post|put|delete|patch)|'
            r'httpClient\.(?P<http_method>get|post|put|delete|patch))\s*\(\s*[`\'"](?P<url>[^`\'"]+)[`\'"]',
            re.IGNORECASE
        )

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
                    is_endpoint = False
                    endpoint_route = ""
                    endpoint_method = "GET"

                    # Check for Express / Fastify endpoint: app.get('/route', ...), router.post(...)
                    express_m = re.search(r'(?:app|router|server|api)\.(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', line, re.IGNORECASE)
                    if express_m:
                        is_endpoint = True
                        endpoint_method = express_m.group(1).upper()
                        endpoint_route = express_m.group(2)

                    # Check for Next.js App Router route handlers: export async function GET / POST
                    if not is_endpoint and name.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH") and any(k in file_path.lower() for k in ("api", "route")):
                        is_endpoint = True
                        endpoint_method = name.upper()
                        clean_fp = file_path.replace("\\", "/").replace("/route.ts", "").replace("/route.js", "").replace(".ts", "").replace(".js", "")
                        if "api/" in clean_fp:
                            endpoint_route = "/" + clean_fp[clean_fp.find("api/"):]
                        else:
                            endpoint_route = "/" + clean_fp

                    # Check for NestJS controller decorators: @Get('/path'), @Post(...)
                    if not is_endpoint:
                        prev_context = "".join(lines[max(0, idx - 4) : idx])
                        nest_m = re.search(r'@(Get|Post|Put|Delete|Patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', prev_context, re.IGNORECASE)
                        if nest_m:
                            is_endpoint = True
                            endpoint_method = nest_m.group(1).upper()
                            endpoint_route = nest_m.group(2)

                    if is_endpoint and endpoint_route:
                        meta["endpoint_route"] = endpoint_route
                        meta["http_method"] = endpoint_method
                        sym_type = SymbolType.ENDPOINT
                    else:
                        sym_type = SymbolType.FUNCTION

                    # Check for API endpoint calls (consumer)
                    api_match = api_call_pattern.search(block)
                    if api_match:
                        raw_endpoint = api_match.group("url")
                        if raw_endpoint and (raw_endpoint.startswith("http://") or raw_endpoint.startswith("https://") or raw_endpoint.startswith("/")):
                            http_verb = api_match.group("method") or api_match.group("ky_method") or api_match.group("client_method") or api_match.group("http_method") or "GET"
                            if "method: \"POST\"" in block or "method: 'POST'" in block or "method: `POST`" in block:
                                http_verb = "POST"
                            elif "method: \"DELETE\"" in block or "method: 'DELETE'" in block:
                                http_verb = "DELETE"
                            elif "method: \"PUT\"" in block or "method: 'PUT'" in block:
                                http_verb = "PUT"
                            elif "method: \"GET\"" in block or "method: 'GET'" in block:
                                http_verb = "GET"

                            host_m = re.match(r'^https?://([^/]+)', raw_endpoint)
                            if host_m:
                                meta["target_base_url"] = host_m.group(1).lower()

                            cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_endpoint).split('?')[0].strip()
                            route_m = re.search(r'(/(?:api/)?(?:v[0-9]+/)?(?:api/)?[a-zA-Z0-9_\-\/{}:]+)', cleaned_endpoint)
                            final_ep = route_m.group(1) if route_m else cleaned_endpoint

                            if final_ep and final_ep != "/" and not any(final_ep.endswith(ext) for ext in ('.ts', '.js', '.tsx', '.jsx', '.json', '.html', '.css', '.png', '.jpg')):
                                meta["consumes_endpoint"] = final_ep
                                meta["consumes_http_method"] = http_verb.upper()

                    node = CodeNode(
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
                    )
                    nodes.append(node)
                    break

        return nodes, edges

    # -------------------------------------------------------------
    # Go Parser Implementation
    # -------------------------------------------------------------

    def _parse_go(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses Go files for functions, structs, receiver methods, and HTTP endpoints/consumers."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        # Extract Go imports
        file_imports = []
        for imp_m in re.finditer(r'(?:import\s*\(\s*([\s\S]*?)\)|import\s+"([^"]+)")', content):
            if imp_m.group(1):
                for imp_line in imp_m.group(1).splitlines():
                    pkg_m = re.search(r'"([^"]+)"', imp_line)
                    if pkg_m:
                        file_imports.append(pkg_m.group(1))
            elif imp_m.group(2):
                file_imports.append(imp_m.group(2))

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

                meta: Dict[str, Any] = {"file_imports": file_imports}
                if recv:
                    meta["receiver"] = recv

                # Check if Go function registers an endpoint (Gin, Fiber, Echo, Chi, net/http)
                go_ep_match = re.search(r'(?:r|router|api|v1|group|e|app|rg)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]+)"', block, re.IGNORECASE)
                if not go_ep_match:
                    go_ep_match = re.search(r'http\.HandleFunc\s*\(\s*"([^"]+)"', block)
                    if go_ep_match:
                        meta["endpoint_route"] = go_ep_match.group(1)
                        meta["http_method"] = "GET"
                        sym_type = SymbolType.ENDPOINT
                else:
                    meta["endpoint_route"] = go_ep_match.group(2)
                    meta["http_method"] = go_ep_match.group(1).upper()
                    sym_type = SymbolType.ENDPOINT

                # Check Swagger comments above function: // @Router /api/v1/auth [post]
                prev_comments = "".join(lines[max(0, idx - 6) : idx])
                swag_m = re.search(r'//\s*@Router\s+([^\s]+)\s+\[([a-zA-Z]+)\]', prev_comments)
                if swag_m:
                    meta["endpoint_route"] = swag_m.group(1)
                    meta["http_method"] = swag_m.group(2).upper()
                    sym_type = SymbolType.ENDPOINT

                # Check for Go HTTP client calls (consumer)
                go_client_m = re.search(r'http\.(?:Get|Post)\s*\(\s*"([^"]+)"', block)
                if go_client_m:
                    raw_ep = go_client_m.group(1)
                    if raw_ep and (raw_ep.startswith("http://") or raw_ep.startswith("https://") or raw_ep.startswith("/")):
                        host_m = re.match(r'^https?://([^/]+)', raw_ep)
                        if host_m:
                            meta["target_base_url"] = host_m.group(1).lower()
                        cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_ep).split('?')[0].strip()
                        if cleaned_endpoint and cleaned_endpoint != "/":
                            meta["consumes_endpoint"] = cleaned_endpoint
                            meta["consumes_http_method"] = "POST" if "Post" in go_client_m.group(0) else "GET"
                else:
                    go_req_m = re.search(r'http\.NewRequest(?:WithContext)?\s*\(\s*"(GET|POST|PUT|DELETE|PATCH)"\s*,\s*"([^"]+)"', block, re.IGNORECASE)
                    if go_req_m:
                        raw_ep = go_req_m.group(2)
                        if raw_ep and (raw_ep.startswith("http://") or raw_ep.startswith("https://") or raw_ep.startswith("/")):
                            host_m = re.match(r'^https?://([^/]+)', raw_ep)
                            if host_m:
                                meta["target_base_url"] = host_m.group(1).lower()
                            cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_ep).split('?')[0].strip()
                            if cleaned_endpoint and cleaned_endpoint != "/":
                                meta["consumes_endpoint"] = cleaned_endpoint
                                meta["consumes_http_method"] = go_req_m.group(1).upper()
                    else:
                        client_m = re.search(r'(?:client|req|c)\.(Get|Post|Put|Delete)\s*\(\s*"([^"]+)"', block, re.IGNORECASE)
                        if client_m:
                            raw_ep = client_m.group(2)
                            if raw_ep and (raw_ep.startswith("http://") or raw_ep.startswith("https://") or raw_ep.startswith("/")):
                                host_m = re.match(r'^https?://([^/]+)', raw_ep)
                                if host_m:
                                    meta["target_base_url"] = host_m.group(1).lower()
                                cleaned_endpoint = re.sub(r'^https?://[^/]+', '', raw_ep).split('?')[0].strip()
                                if cleaned_endpoint and cleaned_endpoint != "/":
                                    meta["consumes_endpoint"] = cleaned_endpoint
                                    meta["consumes_http_method"] = client_m.group(1).upper()

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
                    metadata=meta
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
                    code_content=block,
                    metadata={"file_imports": file_imports}
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

    @staticmethod
    def _find_closing_paren(lines: List[str], start_idx: int) -> int:
        """Finds 1-indexed line number of matching closing parenthesis for Lisp/Clojure forms."""
        depth = 0
        found_open = False
        for i in range(start_idx - 1, len(lines)):
            line = re.sub(r';.*$', '', lines[i])
            for ch in line:
                if ch == '(':
                    depth += 1
                    found_open = True
                elif ch == ')':
                    depth -= 1
                    if found_open and depth == 0:
                        return i + 1
        return min(start_idx + 40, len(lines))

    @staticmethod
    def _find_ruby_end(lines: List[str], start_idx: int) -> int:
        """Finds 1-indexed line number of matching 'end' keyword for Ruby definitions."""
        depth = 0
        for i in range(start_idx - 1, len(lines)):
            line = re.sub(r'#.*$', '', lines[i]).strip()
            if not line:
                continue
            if re.match(r'^(?:class|module|def|if|unless|while|until|for|case)\b', line) or re.search(r'\bdo\s*(?:\|[^|]*\|)?$', line):
                depth += 1
            if re.match(r'^end\b', line):
                depth -= 1
                if depth <= 0:
                    return i + 1
        return min(start_idx + 40, len(lines))

    # -------------------------------------------------------------
    # PHP Parser Implementation (Laravel, Symfony, Standard PHP)
    # -------------------------------------------------------------
    def _parse_php(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        class_pattern = re.compile(r'(?:final\s+|abstract\s+)?(?:class|interface|trait)\s+([a-zA-Z0-9_]+)')
        method_pattern = re.compile(r'(?:public|protected|private)?\s*(?:static\s+)?function\s+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        import_pattern = re.compile(r'^\s*use\s+([a-zA-Z0-9_\\]+)')
        route_pattern = re.compile(r'Route::(?P<verb>get|post|put|delete|patch|options)\s*\(\s*["\']([^"\']+)["\']')
        http_client_pattern = re.compile(r'(?:Http::|\$client->|\$this->http->)(?P<verb>get|post|put|delete|patch|request)\s*\(\s*["\'](?P<url>[^"\']+)["\']', re.IGNORECASE)

        file_imports = []
        for line in lines:
            m = import_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

        # Check for route definitions in routes files
        for idx, line in enumerate(lines, start=1):
            r_match = route_pattern.search(line)
            if r_match:
                verb = r_match.group("verb").upper()
                route_path = r_match.group(2)
                end_line = min(idx + 5, len(lines))
                block = "".join(lines[idx - 1 : end_line])
                node_name = f"route_{verb.lower()}_{re.sub(r'[^a-zA-Z0-9_]', '_', route_path).strip('_')}"
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, node_name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=node_name,
                    symbol_type=SymbolType.ENDPOINT,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata={"endpoint_route": route_path, "http_method": verb, "file_imports": file_imports}
                ))

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
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

            m_match = method_pattern.search(line)
            if m_match:
                name = m_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                meta: Dict[str, Any] = {"file_imports": file_imports}

                c_client = http_client_pattern.search(block)
                if c_client:
                    url = c_client.group("url")
                    if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                        verb = c_client.group("verb").upper()
                        if verb == "REQUEST":
                            verb = "GET"
                        meta["consumes_endpoint"] = url
                        meta["consumes_http_method"] = verb
                        if "://" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                            meta["consumes_endpoint"] = parsed.path or "/"

                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.METHOD,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # Rust Parser Implementation (Actix Web, Axum, Rocket, Reqwest)
    # -------------------------------------------------------------
    def _parse_rust(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        type_pattern = re.compile(r'(?:pub(?:\([^\)]+\))?\s+)?(?:struct|enum|trait|union)\s+([a-zA-Z0-9_]+)')
        fn_pattern = re.compile(r'(?:pub(?:\([^\)]+\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([a-zA-Z0-9_]+)\s*(?:<[^>]+>)?\s*\((.*?)\)')
        actix_route = re.compile(r'#\[(?P<verb>get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']\s*\)\]')
        reqwest_call = re.compile(r'(?:reqwest::|client\.)(?P<verb>get|post|put|delete|patch)\s*\(\s*["\'](?P<url>[^"\']+)["\']')
        use_pattern = re.compile(r'^\s*use\s+([a-zA-Z0-9_:]+)')

        file_imports = []
        for line in lines:
            m = use_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

        for idx, line in enumerate(lines, start=1):
            t_match = type_pattern.search(line)
            if t_match:
                name = t_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

            f_match = fn_pattern.search(line)
            if f_match:
                name = f_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                meta: Dict[str, Any] = {"file_imports": file_imports}

                # Check previous lines for Actix/Rocket route attribute
                context_prev = "".join(lines[max(0, idx - 4) : idx])
                r_match = actix_route.search(context_prev) or actix_route.search(line)
                is_endpoint = False
                if r_match:
                    is_endpoint = True
                    meta["endpoint_route"] = r_match.group(2)
                    meta["http_method"] = r_match.group("verb").upper()

                c_call = reqwest_call.search(block)
                if c_call:
                    url = c_call.group("url")
                    if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                        meta["consumes_endpoint"] = url
                        meta["consumes_http_method"] = c_call.group("verb").upper()
                        if "://" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                            meta["consumes_endpoint"] = parsed.path or "/"

                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.ENDPOINT if is_endpoint else SymbolType.FUNCTION,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # C# / .NET Parser Implementation (ASP.NET Core, HttpClient)
    # -------------------------------------------------------------
    def _parse_csharp(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        class_pattern = re.compile(r'(?:public|internal|private)?\s*(?:static\s+|abstract\s+|partial\s+)?(?:class|interface|struct|record)\s+([a-zA-Z0-9_]+)')
        method_pattern = re.compile(r'(?:public|internal|protected|private)?\s*(?:static\s+|async\s+|virtual\s+|override\s+)*(?:Task(?:<[^>]+>)?|[a-zA-Z0-9_<>,\[\]]+)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)')
        aspnet_route = re.compile(r'\[(?P<verb>HttpGet|HttpPost|HttpPut|HttpDelete|HttpPatch|Route)\s*(?:\(\s*["\']([^"\']+)["\']\s*\))?\]')
        http_client = re.compile(r'(?:\.|\b)(?P<verb>GetAsync|PostAsync|PutAsync|DeleteAsync)\s*\(\s*["\'](?P<url>[^"\']+)["\']')
        using_pattern = re.compile(r'^\s*using\s+([a-zA-Z0-9_.]+);')

        file_imports = []
        for line in lines:
            m = using_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

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
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

            m_match = method_pattern.search(line)
            if m_match:
                name = m_match.group(1)
                end_line = self._find_closing_brace(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                meta: Dict[str, Any] = {"file_imports": file_imports}

                context_prev = "".join(lines[max(0, idx - 4) : idx])
                r_match = aspnet_route.search(context_prev) or aspnet_route.search(line)
                is_endpoint = False
                if r_match:
                    is_endpoint = True
                    verb_raw = r_match.group("verb")
                    meta["http_method"] = verb_raw.replace("Http", "").upper() if verb_raw != "Route" else "GET"
                    meta["endpoint_route"] = r_match.group(2) or "/"

                c_call = http_client.search(block)
                if c_call:
                    url = c_call.group("url")
                    if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                        verb = c_call.group("verb").replace("Async", "").upper()
                        meta["consumes_endpoint"] = url
                        meta["consumes_http_method"] = verb
                        if "://" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                            meta["consumes_endpoint"] = parsed.path or "/"

                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.ENDPOINT if is_endpoint else SymbolType.METHOD,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # Ruby Parser Implementation (Rails, Sinatra, Faraday, Net::HTTP)
    # -------------------------------------------------------------
    def _parse_ruby(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        class_pattern = re.compile(r'^\s*(?:class|module)\s+([a-zA-Z0-9_:]+)')
        def_pattern = re.compile(r'^\s*def\s+([a-zA-Z0-9_!?=]+)')
        route_pattern = re.compile(r'^\s*(?P<verb>get|post|put|delete|patch)\s+["\']([^"\']+)["\']')
        http_client = re.compile(r'(?:Faraday|Net::HTTP|HTTParty)\.(?P<verb>get|post|put|delete)\s*\(?\s*["\'](?P<url>[^"\']+)["\']')
        req_pattern = re.compile(r'^\s*require(?:_relative)?\s+["\']([^"\']+)["\']')

        file_imports = []
        for line in lines:
            m = req_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

        for idx, line in enumerate(lines, start=1):
            c_match = class_pattern.search(line)
            if c_match:
                name = c_match.group(1)
                end_line = self._find_ruby_end(lines, idx)
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

            d_match = def_pattern.search(line)
            if d_match:
                name = d_match.group(1)
                end_line = self._find_ruby_end(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                meta: Dict[str, Any] = {"file_imports": file_imports}

                c_call = http_client.search(block)
                if c_call:
                    url = c_call.group("url")
                    if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                        meta["consumes_endpoint"] = url
                        meta["consumes_http_method"] = c_call.group("verb").upper()
                        if "://" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                            meta["consumes_endpoint"] = parsed.path or "/"

                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.METHOD,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content=block,
                    metadata=meta
                ))

            r_match = route_pattern.search(line)
            if r_match:
                verb = r_match.group("verb").upper()
                route_path = r_match.group(2)
                end_line = min(idx + 5, len(lines))
                node_name = f"route_{verb.lower()}_{re.sub(r'[^a-zA-Z0-9_]', '_', route_path).strip('_')}"
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, node_name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=node_name,
                    symbol_type=SymbolType.ENDPOINT,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content="".join(lines[idx - 1 : end_line]),
                    metadata={"endpoint_route": route_path, "http_method": verb, "file_imports": file_imports}
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # C / C++ Parser Implementation (Functions, Classes, Structs, Includes)
    # -------------------------------------------------------------
    def _parse_cpp(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """Parses C and C++ source files (functions, methods, classes, structs, and includes)."""
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        includes = re.findall(r'#\s*include\s*["<]([^">]+)[">]', content)

        class_pattern = re.compile(
            r'^\s*(?:template\s*<[^>]*>\s*)?(?:class|struct)\s+(?:alignas\([^)]*\)\s+)?([A-Za-z_][A-Za-z0-9_]*)(?:\s*:\s*[^;{]+)?\s*(?:\{|$)'
        )
        func_pattern = re.compile(
            r'^\s*(?:(?:inline|static|constexpr|virtual|explicit|friend|auto)\s+)*(?:(?:const\s+)?[A-Za-z_][A-Za-z0-9_:*&<>\s]+?\s+)?([A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)?)\s*\(([^;]*)\)\s*(?:const)?\s*(?:noexcept(?:\([^)]*\))?)?\s*(?:override|final)?\s*(?:->\s*[^;{]+)?\s*(?:\{|$)'
        )

        def has_body(start_idx: int) -> bool:
            for j in range(start_idx - 1, min(len(lines), start_idx + 4)):
                l = lines[j]
                if '{' in l:
                    return True
                if ';' in l:
                    return False
            return False

        for idx, line in enumerate(lines, start=1):
            c_match = class_pattern.search(line)
            if c_match and has_body(idx):
                name = c_match.group(1)
                if name not in ("if", "for", "while", "switch", "return"):
                    end_line = self._find_closing_brace(lines, idx)
                    nodes.append(CodeNode(
                        id=CodeNode.generate_id(repo, file_path, name, idx),
                        repo=repo,
                        file_path=file_path,
                        symbol_name=name,
                        symbol_type=SymbolType.CLASS,
                        start_line=idx,
                        end_line=end_line,
                        signature=line.strip(),
                        metadata={"file_imports": includes} if idx == 1 or not nodes else {}
                    ))

            f_match = func_pattern.search(line)
            if f_match and has_body(idx) and not c_match:
                name = f_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch", "return"):
                    end_line = self._find_closing_brace(lines, idx)
                    block = "".join(lines[idx - 1 : end_line])
                    clean_name = name.split("::")[-1]
                    nodes.append(CodeNode(
                        id=CodeNode.generate_id(repo, file_path, clean_name, idx),
                        repo=repo,
                        file_path=file_path,
                        symbol_name=clean_name,
                        symbol_type=SymbolType.FUNCTION,
                        start_line=idx,
                        end_line=end_line,
                        signature=line.strip(),
                        code_content=block,
                        metadata={"file_imports": includes} if not nodes else {}
                    ))

        return nodes, edges

    _parse_c_cpp = _parse_cpp

    # -------------------------------------------------------------
    # Clojure Parser Implementation (Compojure, Ring, clj-http)
    # -------------------------------------------------------------
    def _parse_clojure(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        defn_pattern = re.compile(r'\(\s*(?:defn|defn-|def|defmacro)\s+([a-zA-Z0-9_\-\.\*\+\!\?]+)')
        route_pattern = re.compile(r'\(\s*(?P<verb>GET|POST|PUT|DELETE|PATCH)\s+["\']([^"\']+)["\']')
        http_client = re.compile(r'\(\s*(?:client/|http/)(?P<verb>get|post|put|delete)\s+["\'](?P<url>[^"\']+)["\']')
        ns_pattern = re.compile(r'\(\s*ns\s+([a-zA-Z0-9_\-\.]+)')

        file_imports = []
        for line in lines:
            m = ns_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

        for idx, line in enumerate(lines, start=1):
            d_match = defn_pattern.search(line)
            if d_match:
                name = d_match.group(1)
                end_line = self._find_closing_paren(lines, idx)
                block = "".join(lines[idx - 1 : end_line])
                meta: Dict[str, Any] = {"file_imports": file_imports}

                c_call = http_client.search(block)
                if c_call:
                    url = c_call.group("url")
                    if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                        meta["consumes_endpoint"] = url
                        meta["consumes_http_method"] = c_call.group("verb").upper()
                        if "://" in url:
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                            meta["consumes_endpoint"] = parsed.path or "/"

                nodes.append(CodeNode(
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
                ))

            r_match = route_pattern.search(line)
            if r_match:
                verb = r_match.group("verb").upper()
                route_path = r_match.group(2)
                end_line = self._find_closing_paren(lines, idx)
                node_name = f"route_{verb.lower()}_{re.sub(r'[^a-zA-Z0-9_]', '_', route_path).strip('_')}"
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, node_name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=node_name,
                    symbol_type=SymbolType.ENDPOINT,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    code_content="".join(lines[idx - 1 : end_line]),
                    metadata={"endpoint_route": route_path, "http_method": verb, "file_imports": file_imports}
                ))

        return nodes, edges

    # -------------------------------------------------------------
    # Universal Polyglot Fallback Parser
    # -------------------------------------------------------------
    def _parse_generic(self, repo: str, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeEdge]]:
        """
        Universal fallback parser extracting structural symbols, endpoints,
        and HTTP consumer dependencies across any programming language.
        """
        nodes: List[CodeNode] = []
        edges: List[CodeEdge] = []
        lines = content.splitlines(keepends=True)

        type_pattern = re.compile(r'^\s*(?:class|struct|interface|type|module|trait|enum)\s+([a-zA-Z0-9_]+)')
        fn_pattern = re.compile(r'^\s*(?:def|func|fn|function|fun|sub|proc|task|void|int|string|bool)\s+([a-zA-Z0-9_]+)\s*(?:\(|$)', re.IGNORECASE)
        assign_fn = re.compile(r'^\s*(?:let|const|var|val)\s+([a-zA-Z0-9_]+)\s*=\s*(?:function|\([^)]*\)\s*=>)', re.IGNORECASE)
        route_pattern = re.compile(r'(?:@Route|@Get|@Post|@Put|@Delete|router\.(?:get|post|put|delete)|app\.(?:get|post|put|delete))\s*\(\s*["\']([^"\']+)["\']', re.IGNORECASE)
        http_client = re.compile(r'(?:fetch|\.get|\.post|\.put|\.delete)\s*\(\s*["\'](?P<url>[^"\']+)["\']', re.IGNORECASE)
        import_pattern = re.compile(r'^\s*(?:import|use|require|include|open|from)\s+([a-zA-Z0-9_\.\-\/]+)')

        file_imports = []
        for line in lines:
            m = import_pattern.search(line)
            if m:
                file_imports.append(m.group(1))

        for idx, line in enumerate(lines, start=1):
            t_match = type_pattern.search(line)
            if t_match:
                name = t_match.group(1)
                end_line = self._find_closing_brace(lines, idx) if "{" in "".join(lines[idx-1:idx+2]) else min(idx + 20, len(lines))
                nodes.append(CodeNode(
                    id=CodeNode.generate_id(repo, file_path, name, idx),
                    repo=repo,
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=idx,
                    end_line=end_line,
                    signature=line.strip(),
                    metadata={"file_imports": file_imports}
                ))

            f_match = fn_pattern.search(line) or assign_fn.search(line)
            if f_match:
                name = f_match.group(1)
                if name.lower() not in ("if", "for", "while", "switch", "catch", "return", "var", "let", "const"):
                    end_line = self._find_closing_brace(lines, idx) if "{" in "".join(lines[idx-1:idx+2]) else min(idx + 25, len(lines))
                    block = "".join(lines[idx - 1 : end_line])
                    meta: Dict[str, Any] = {"file_imports": file_imports}

                    r_match = route_pattern.search(line)
                    is_endpoint = False
                    if r_match:
                        is_endpoint = True
                        meta["endpoint_route"] = r_match.group(1)
                        verb_m = re.search(r'(get|post|put|delete|patch)', line, re.IGNORECASE)
                        meta["http_method"] = verb_m.group(1).upper() if verb_m else "GET"

                    c_call = http_client.search(block)
                    if c_call:
                        url = c_call.group("url")
                        if not any(url.lower().endswith(ext) for ext in [".png", ".jpg", ".css", ".svg", ".json", ".js"]):
                            verb_m = re.search(r'(get|post|put|delete|patch)', block, re.IGNORECASE)
                            meta["consumes_endpoint"] = url
                            meta["consumes_http_method"] = verb_m.group(1).upper() if verb_m else "GET"
                            if "://" in url:
                                from urllib.parse import urlparse
                                parsed = urlparse(url)
                                meta["target_base_url"] = f"{parsed.scheme}://{parsed.netloc}"
                                meta["consumes_endpoint"] = parsed.path or "/"

                    nodes.append(CodeNode(
                        id=CodeNode.generate_id(repo, file_path, name, idx),
                        repo=repo,
                        file_path=file_path,
                        symbol_name=name,
                        symbol_type=SymbolType.ENDPOINT if is_endpoint else SymbolType.FUNCTION,
                        start_line=idx,
                        end_line=end_line,
                        signature=line.strip(),
                        code_content=block,
                        metadata=meta
                    ))

        return nodes, edges

