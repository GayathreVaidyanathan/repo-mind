import os
import stat
import shutil
import tempfile
from pathlib import Path

import git                          # gitpython — clones the repo
import chromadb                     # our vector database
from chromadb.utils import embedding_functions  # wraps sentence-transformers

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".cpp", ".c", ".h", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json"
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "vendor",
    "target", "bin", "obj", ".idea", ".vscode"
}

CHUNK_SIZE      = 1500
CHUNK_OVERLAP   = 200
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# WINDOWS CLEANUP HELPER
# ---------------------------------------------------------------------------

def _force_remove(func, path, _):
    """On Windows, .git files are read-only — this unlocks them before delete."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def cleanup(repo_path: str):
    """Safely removes the cloned temp directory, including read-only .git files on Windows."""
    shutil.rmtree(repo_path, onerror=_force_remove)
    print(f"[ingestor] Cleaned up {repo_path}")


# ---------------------------------------------------------------------------
# STEP 1 — CLONE
# ---------------------------------------------------------------------------

def clone_repo(github_url: str) -> str:
    """Clones a public GitHub repo into a temp directory. Returns the path."""
    tmp_dir = tempfile.mkdtemp(prefix="repomind_")
    print(f"[ingestor] Cloning {github_url} → {tmp_dir}")
    git.Repo.clone_from(github_url, tmp_dir, depth=1)
    return tmp_dir


# ---------------------------------------------------------------------------
# STEP 2 — LOAD
# ---------------------------------------------------------------------------

def load_files(repo_path: str) -> list[dict]:
    """Walks the repo and reads every supported file. Returns list of dicts."""
    files = []
    root  = Path(repo_path)

    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue
        if any(skip in filepath.parts for skip in SKIP_DIRS):
            continue
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                files.append({
                    "path":      str(filepath.relative_to(root)),
                    "content":   content,
                    "extension": filepath.suffix.lower()
                })
        except Exception as e:
            print(f"[ingestor] Skipping {filepath}: {e}")

    print(f"[ingestor] Loaded {len(files)} files")
    return files


# ---------------------------------------------------------------------------
# STEP 3 — CHUNK
# ---------------------------------------------------------------------------

def chunk_files(files: list[dict]) -> list[dict]:
    """Splits each file into overlapping chunks. Returns list of chunk dicts."""
    chunks = []

    for file in files:
        content     = file["content"]
        path        = file["path"]
        ext         = file["extension"]
        start       = 0
        chunk_index = 0

        while start < len(content):
            end  = start + CHUNK_SIZE
            text = content[start:end]
            chunks.append({
                "text":        text,
                "path":        path,
                "extension":   ext,
                "chunk_index": chunk_index
            })
            chunk_index += 1
            start += CHUNK_SIZE - CHUNK_OVERLAP

    print(f"[ingestor] Created {len(chunks)} chunks from {len(files)} files")
    return chunks


# ---------------------------------------------------------------------------
# STEP 4 — EMBED + STORE
# ---------------------------------------------------------------------------

def embed_and_store(chunks: list[dict], collection_name: str) -> chromadb.Collection:
    """Embeds each chunk and stores it in ChromaDB. Returns the collection."""
    client = chromadb.Client()

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    collection = client.create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.add(
            ids       = [f"chunk_{i+j}" for j, _ in enumerate(batch)],
            documents = [c["text"] for c in batch],
            metadatas = [{"path": c["path"], "extension": c["extension"],
                          "chunk_index": c["chunk_index"]} for c in batch],
        )
        print(f"[ingestor] Embedded chunks {i}–{i+len(batch)-1}")

    print(f"[ingestor] ✅ Done — {collection.count()} chunks in vector store")
    return collection


# ---------------------------------------------------------------------------
# MASTER FUNCTION — called by app.py
# ---------------------------------------------------------------------------

def ingest(github_url: str, collection_name: str = "repomind") -> tuple:
    """
    Full pipeline: clone → load → chunk → embed → store.
    Returns (collection, repo_path, file_list).
    Call cleanup(repo_path) when done to remove the temp directory.
    """
    repo_path  = clone_repo(github_url)
    files      = load_files(repo_path)
    chunks     = chunk_files(files)
    collection = embed_and_store(chunks, collection_name)

    return collection, repo_path, files