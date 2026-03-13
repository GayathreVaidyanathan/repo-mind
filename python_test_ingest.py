from ingestor import ingest, cleanup

collection, repo_path, files = ingest("https://github.com/GayathreVaidyanathan/tamil-news-agentic-ai-public")

print(f"Files found: {len(files)}")
print(f"Chunks in DB: {collection.count()}")
print("First 3 files:", [f['path'] for f in files[:3]])

cleanup(repo_path)  # safely removes temp dir including read-only .git files on Windows
print("✅ Temp directory cleaned up!")