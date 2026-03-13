import ast
import os
import json
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# We only build the graph for Python files for now.
# JS/TS would need a different parser (e.g. esprima).
GRAPH_EXTENSIONS = {".py"}


# ---------------------------------------------------------------------------
# STEP 1 — EXTRACT IMPORTS FROM A SINGLE FILE
# ---------------------------------------------------------------------------

def extract_imports(file: dict) -> list[str]:
    """
    Uses Python's built-in ast module to parse a file and extract
    all import statements.

    Returns a list of module names being imported.

    Example — for this code:
        import os
        from src.email_service import EmailService
        import json

    Returns: ['os', 'src.email_service', 'json']

    Why ast and not regex?
    — Regex on code is fragile. `import` can appear in strings, comments,
      multiline statements etc. ast understands the actual code structure
      so it never gets confused by these edge cases.
    """
    imports = []

    try:
        tree = ast.parse(file["content"])  # parse source code into AST

        for node in ast.walk(tree):        # walk every node in the tree
            # Regular import: `import os` or `import os, sys`
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            # From import: `from src.email import send`
            elif isinstance(node, ast.ImportFrom):
                if node.module:            # module can be None for `from . import x`
                    imports.append(node.module)

    except SyntaxError:
        # File might have syntax errors — skip it gracefully
        pass

    return imports


# ---------------------------------------------------------------------------
# STEP 2 — EXTRACT FUNCTIONS AND CLASSES
# ---------------------------------------------------------------------------

def extract_definitions(file: dict) -> dict:
    """
    Extracts all function and class names defined in a file.

    Returns:
    {
        "functions": ["send_email", "format_body", ...],
        "classes":   ["EmailService", ...]
    }

    This is used to show what each file exposes — helpful for
    understanding a file's role in the architecture at a glance.
    """
    functions = []
    classes   = []

    try:
        tree = ast.parse(file["content"])

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Skip private/dunder methods to reduce noise
                if not node.name.startswith("__"):
                    functions.append(node.name)

            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

    except SyntaxError:
        pass

    return {"functions": functions, "classes": classes}


# ---------------------------------------------------------------------------
# STEP 3 — BUILD THE DEPENDENCY GRAPH
# ---------------------------------------------------------------------------

def build_graph(files: list[dict]) -> dict:
    """
    Builds a dependency graph from all files.

    Algorithm:
    1. For each file, extract its imports
    2. Check if any import matches another file in the repo
       (i.e. it's an internal import, not a third-party library)
    3. If yes, draw an edge: this_file → imported_file

    Returns a dict:
    {
        "nodes": [
            {
                "id":        "src/email_service.py",
                "label":     "email_service",
                "functions": [...],
                "classes":   [...],
                "size":      42        ← number of lines
            },
            ...
        ],
        "edges": [
            {
                "source": "src/main.py",
                "target": "src/email_service.py",
                "label":  "imports"
            },
            ...
        ]
    }

    This format is easy to render with any graph library.
    """
    # Only process Python files
    py_files = [f for f in files if f["extension"] in GRAPH_EXTENSIONS]

    if not py_files:
        return {"nodes": [], "edges": []}

    # Build a lookup: module-style name → file path
    # e.g. "src.email_service" → "src/email_service.py"
    # e.g. "email_service"     → "src/email_service.py"
    module_map = {}
    for file in py_files:
        path = file["path"]
        # Convert path to module name: src/email_service.py → src.email_service
        module_name = path.replace("\\", "/").replace("/", ".").replace(".py", "")
        module_map[module_name] = path

        # Also map just the filename without path for simple imports
        base_name = Path(path).stem  # email_service
        if base_name not in module_map:
            module_map[base_name] = path

    # Build nodes
    nodes = []
    for file in py_files:
        defs = extract_definitions(file)
        nodes.append({
            "id":        file["path"],
            "label":     Path(file["path"]).stem,   # just filename without .py
            "functions": defs["functions"],
            "classes":   defs["classes"],
            "size":      len(file["content"].split("\n"))  # line count
        })

    # Build edges
    edges      = []
    seen_edges = set()  # avoid duplicate edges

    for file in py_files:
        imports = extract_imports(file)
        source  = file["path"]

        for imp in imports:
            # Check if this import refers to another file in the repo
            target = module_map.get(imp)

            # Also try matching partial paths
            # e.g. import src.email_service → try "src.email_service"
            if not target:
                for mod_name, mod_path in module_map.items():
                    if imp.endswith(mod_name) or mod_name.endswith(imp):
                        target = mod_path
                        break

            if target and target != source:  # don't add self-loops
                edge_key = f"{source}→{target}"
                if edge_key not in seen_edges:
                    edges.append({
                        "source": source,
                        "target": target,
                        "label":  "imports"
                    })
                    seen_edges.add(edge_key)

    print(f"[graph] Built graph: {len(nodes)} nodes, {len(edges)} edges")
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# STEP 4 — COMPUTE STATS
# ---------------------------------------------------------------------------

def compute_stats(graph: dict) -> dict:
    """
    Computes useful stats from the graph:
    - Most imported file (highest in-degree = most central/depended-upon)
    - Files with no imports (leaf nodes = standalone utilities)
    - Files with most outgoing imports (highest out-degree = most complex)

    In-degree  = how many files import THIS file → importance
    Out-degree = how many files THIS file imports → complexity/coupling
    """
    nodes = graph["nodes"]
    edges = graph["edges"]

    # Count in-degree and out-degree for each node
    in_degree  = defaultdict(int)
    out_degree = defaultdict(int)

    for edge in edges:
        out_degree[edge["source"]] += 1
        in_degree[edge["target"]]  += 1

    # Attach degree info to nodes
    for node in nodes:
        node["in_degree"]  = in_degree[node["id"]]
        node["out_degree"] = out_degree[node["id"]]

    # Find most central files
    most_imported = sorted(nodes, key=lambda n: n["in_degree"],  reverse=True)[:3]
    most_complex  = sorted(nodes, key=lambda n: n["out_degree"], reverse=True)[:3]
    standalone    = [n for n in nodes if n["in_degree"] == 0 and n["out_degree"] == 0]

    return {
        "graph":          graph,
        "most_imported":  most_imported,
        "most_complex":   most_complex,
        "standalone":     standalone,
        "total_files":    len(nodes),
        "total_edges":    len(edges),
    }


# ---------------------------------------------------------------------------
# MASTER FUNCTION — called by app.py
# ---------------------------------------------------------------------------

def run_graph_analysis(files: list[dict]) -> dict:
    """
    Full pipeline: build graph → compute stats.
    Returns the full stats dict ready for the UI.
    """
    graph = build_graph(files)
    stats = compute_stats(graph)
    print(f"[graph] ✅ Done")
    return stats