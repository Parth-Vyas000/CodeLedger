"""Python AST parser — extracts functions, classes, imports, and structure from .py files."""

from __future__ import annotations

import ast
from pathlib import Path

from codeledger.parser.base import (
    BaseParser,
    ParsedClass,
    ParsedDecorator,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedParameter,
)


class PythonParser(BaseParser):
    """Parses Python source files using the stdlib ast module."""

    def supports(self, extension: str) -> bool:
        return extension.lower() in (".py", ".pyi")

    def parse(self, filepath: str) -> ParsedFile:
        path = Path(filepath)
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ParsedFile(path=filepath, language="python")

        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return ParsedFile(
                path=filepath,
                language="python",
                total_lines=source.count("\n") + 1,
            )

        parsed = ParsedFile(
            path=filepath,
            language="python",
            total_lines=source.count("\n") + 1,
        )

        # Module docstring
        parsed.module_docstring = ast.get_docstring(tree)

        # Entry point detection
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"
            ):
                parsed.has_entry_point = True
                break

        # Walk top-level statements
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                parsed.functions.append(self._parse_function(node))
            elif isinstance(node, ast.ClassDef):
                parsed.classes.append(self._parse_class(node))
            elif isinstance(node, ast.Import):
                parsed.imports.extend(self._parse_import(node))
            elif isinstance(node, ast.ImportFrom):
                parsed.imports.append(self._parse_import_from(node))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        parsed.global_variables.append(target.id)

        return parsed

    def _parse_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_method: bool = False,
    ) -> ParsedFunction:
        params = self._parse_parameters(node.args, is_method=is_method)
        decorators = [self._parse_decorator(d) for d in node.decorator_list]

        return_annotation = None
        if node.returns:
            return_annotation = self._unparse_safe(node.returns)

        is_property = any(d.name == "property" for d in decorators)
        is_static = any(d.name == "staticmethod" for d in decorators)
        is_classmethod = any(d.name == "classmethod" for d in decorators)

        complexity = self._estimate_complexity(node)

        return ParsedFunction(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parameters=params,
            return_annotation=return_annotation,
            decorators=decorators,
            docstring=ast.get_docstring(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_method=is_method,
            is_property=is_property,
            is_staticmethod=is_static,
            is_classmethod=is_classmethod,
            complexity_hint=complexity,
        )

    def _parse_class(self, node: ast.ClassDef) -> ParsedClass:
        bases = [self._unparse_safe(b) for b in node.bases]
        decorators = [self._parse_decorator(d) for d in node.decorator_list]
        methods: list[ParsedFunction] = []
        class_vars: list[str] = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                methods.append(self._parse_function(item, is_method=True))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_vars.append(target.id)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                class_vars.append(item.target.id)

        return ParsedClass(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            decorators=decorators,
            methods=methods,
            docstring=ast.get_docstring(node),
            class_variables=class_vars,
        )

    def _parse_parameters(
        self,
        args: ast.arguments,
        is_method: bool = False,
    ) -> list[ParsedParameter]:
        params: list[ParsedParameter] = []

        all_args = args.posonlyargs + args.args

        # Compute default offset
        num_no_default = len(all_args) - len(args.defaults)

        for i, arg in enumerate(all_args):
            if is_method and i == 0 and arg.arg in ("self", "cls"):
                continue

            annotation = None
            if arg.annotation:
                annotation = self._unparse_safe(arg.annotation)

            default = None
            default_idx = i - num_no_default
            if default_idx >= 0 and default_idx < len(args.defaults):
                default = self._unparse_safe(args.defaults[default_idx])

            params.append(
                ParsedParameter(
                    name=arg.arg,
                    annotation=annotation,
                    default=default,
                )
            )

        # *args
        if args.vararg:
            ann = self._unparse_safe(args.vararg.annotation) if args.vararg.annotation else None
            params.append(ParsedParameter(name=f"*{args.vararg.arg}", annotation=ann))

        # keyword-only
        for i, arg in enumerate(args.kwonlyargs):
            annotation = self._unparse_safe(arg.annotation) if arg.annotation else None
            default = None
            if i < len(args.kw_defaults):
                kw_default = args.kw_defaults[i]
                if kw_default is not None:
                    default = self._unparse_safe(kw_default)
            params.append(ParsedParameter(name=arg.arg, annotation=annotation, default=default))

        # **kwargs
        if args.kwarg:
            ann = self._unparse_safe(args.kwarg.annotation) if args.kwarg.annotation else None
            params.append(ParsedParameter(name=f"**{args.kwarg.arg}", annotation=ann))

        return params

    def _parse_decorator(self, node: ast.expr) -> ParsedDecorator:
        if isinstance(node, ast.Name):
            return ParsedDecorator(name=node.id)
        elif isinstance(node, ast.Attribute):
            return ParsedDecorator(name=self._unparse_safe(node))
        elif isinstance(node, ast.Call):
            name = self._unparse_safe(node.func)
            args = [self._unparse_safe(a) for a in node.args]
            return ParsedDecorator(name=name, arguments=args)
        return ParsedDecorator(name=self._unparse_safe(node))

    def _parse_import(self, node: ast.Import) -> list[ParsedImport]:
        results = []
        for alias in node.names:
            results.append(
                ParsedImport(
                    module=alias.name,
                    is_from=False,
                    alias=alias.asname,
                )
            )
        return results

    def _parse_import_from(self, node: ast.ImportFrom) -> ParsedImport:
        names = [alias.name for alias in node.names] if node.names else []
        return ParsedImport(
            module=node.module or "",
            names=names,
            is_from=True,
        )

    def _estimate_complexity(self, node: ast.AST) -> int:
        """Rough cyclomatic complexity estimate — count branches."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, ast.If | ast.While | ast.For | ast.AsyncFor | ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                complexity += 1
        return complexity

    def _unparse_safe(self, node: ast.AST) -> str:
        """Safely unparse an AST node to string."""
        try:
            return ast.unparse(node)
        except Exception:
            return "..."
