from ingestor import ingest, cleanup
from graph import run_graph_analysis

collection, repo_path, files = ingest(
    "https://github.com/GayathreVaidyanathan/tamil-news-agentic-ai-public"
)

print("\n🗺️ Running graph analysis...\n")
stats = run_graph_analysis(files)

print(f"Total files : {stats['total_files']}")
print(f"Total edges : {stats['total_edges']}")

print(f"\n📌 Most imported (core files):")
for n in stats["most_imported"]:
    print(f"  {n['label']} — imported by {n['in_degree']} files")

print(f"\n🔗 Most complex (most imports):")
for n in stats["most_complex"]:
    print(f"  {n['label']} — imports {n['out_degree']} files")

print(f"\n🏝️ Standalone files:")
for n in stats["standalone"]:
    print(f"  {n['label']}")

print(f"\n📄 All nodes:")
for n in stats["graph"]["nodes"]:
    print(f"  {n['label']} — {n['size']} lines | classes: {n['classes']} | funcs: {len(n['functions'])}")

cleanup(repo_path)