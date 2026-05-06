"""Token compressor — converts parsed AST output into minimal YAML representation."""

from __future__ import annotations

from codeledger.parser.base import ParsedClass, ParsedFile, ParsedFunction


def compress_function(func: ParsedFunction, verbose: bool = False) -> dict:
    """Compress a parsed function into minimal representation."""
    data: dict = {"name": func.name}

    if func.parameters:
        params = []
        for p in func.parameters:
            if p.annotation:
                params.append(f"{p.name}: {p.annotation}")
            else:
                params.append(p.name)
        data["params"] = params

    if func.return_annotation:
        data["returns"] = func.return_annotation

    if func.is_async:
        data["async"] = True

    if func.decorators:
        data["decorators"] = [d.name for d in func.decorators]

    if verbose and func.docstring:
        # Truncate docstring to first line
        data["doc"] = func.docstring.split("\n")[0].strip()

    if func.complexity_hint > 5:
        data["complexity"] = func.complexity_hint

    return data


def compress_class(cls: ParsedClass, verbose: bool = False) -> dict:
    """Compress a parsed class into minimal representation."""
    data: dict = {"name": cls.name}

    if cls.bases:
        data["bases"] = cls.bases

    if cls.decorators:
        data["decorators"] = [d.name for d in cls.decorators]

    if cls.class_variables:
        data["vars"] = cls.class_variables

    if cls.methods:
        methods = []
        for m in cls.methods:
            if (
                m.name.startswith("__")
                and m.name.endswith("__")
                and not verbose
                and m.name != "__init__"
            ):
                # Skip dunder methods in non-verbose mode except __init__
                continue
            methods.append(compress_function(m, verbose=verbose))
        if methods:
            data["methods"] = methods

    if verbose and cls.docstring:
        data["doc"] = cls.docstring.split("\n")[0].strip()

    return data


def compress_file(
    parsed: ParsedFile,
    verbose: bool = False,
    skip_trivial: bool = True,
) -> dict | None:
    """Compress a parsed file into minimal YAML-friendly representation.

    Returns None if the file is trivial and skip_trivial is True.
    """
    if skip_trivial and parsed.is_trivial:
        return None

    data: dict = {
        "path": parsed.path,
        "lang": parsed.language,
        "lines": parsed.total_lines,
    }

    if parsed.has_entry_point:
        data["entry_point"] = True

    # Imports — just module names, deduped
    if parsed.imports:
        import_modules = list(dict.fromkeys(i.module for i in parsed.imports if i.module))
        if import_modules:
            data["imports"] = import_modules

    # Classes
    if parsed.classes:
        data["classes"] = [compress_class(c, verbose=verbose) for c in parsed.classes]

    # Top-level functions
    if parsed.functions:
        data["functions"] = [compress_function(f, verbose=verbose) for f in parsed.functions]

    # Global variables (only if non-trivial)
    if parsed.global_variables and verbose:
        data["globals"] = parsed.global_variables

    if parsed.module_docstring and verbose:
        data["module_doc"] = parsed.module_docstring.split("\n")[0].strip()

    return data


def compress_project(
    parsed_files: list[ParsedFile],
    verbose: bool = False,
    skip_trivial: bool = True,
) -> list[dict]:
    """Compress all parsed files into a list of minimal representations."""
    result = []
    for pf in parsed_files:
        compressed = compress_file(pf, verbose=verbose, skip_trivial=skip_trivial)
        if compressed is not None:
            result.append(compressed)
    return result


def estimate_tokens(data: list[dict]) -> int:
    """Rough token count estimate for compressed YAML data.

    Rule of thumb: ~4 characters per token for YAML.
    """
    import json

    text = json.dumps(data, indent=2)
    return len(text) // 4
