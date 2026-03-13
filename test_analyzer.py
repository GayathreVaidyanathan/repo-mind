from ingestor import ingest, cleanup
from analyzer import run_analysis, run_summaries

collection, repo_path, files = ingest(
    "https://github.com/GayathreVaidyanathan/tamil-news-agentic-ai-public"
)

# Run analysis
print("\n🔍 Running bug analysis...\n")
analysis = run_analysis(files)

print(f"\n📊 Summary:")
print(f"  Total issues : {analysis['total_issues']}")
print(f"  Critical     : {analysis['critical_count']}")
print(f"  Warnings     : {analysis['warning_count']}")
print(f"  Info         : {analysis['info_count']}")
print(f"  By type      : {analysis['by_type']}")

# Show first file's issues in detail
for result in analysis["results"][:2]:
    print(f"\n📄 {result['path']} — {result['issue_count']} issues")
    for issue in result["issues"]:
        print(f"  [{issue['severity'].upper()}] {issue['title']}")
        print(f"  → {issue['description']}")
        print(f"  Fix: {issue['suggestion']}\n")

cleanup(repo_path)