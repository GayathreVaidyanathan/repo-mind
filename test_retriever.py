from ingestor import ingest, cleanup
from retriever import ask, get_sources

# Ingest the repo
collection, repo_path, files = ingest(
    "https://github.com/GayathreVaidyanathan/tamil-news-agentic-ai-public"
)

# Ask a question
question = "How does the email sending work?"
print(f"\n❓ Question: {question}\n")
print("💬 Answer:")

# ask() with stream=True returns a generator — iterate over it to print
for chunk in ask(question, collection, stream=True):
    print(chunk, end="", flush=True)  # flush=True prints immediately, no buffering

print("\n")

# Show sources
print("📁 Sources used:")
for chunk in get_sources(question, collection):
    print(f"  - {chunk['path']} (chunk {chunk['chunk_index']}, distance: {chunk['distance']:.3f})")

cleanup(repo_path)