import os
from groq import Groq
from dotenv import load_dotenv
import chromadb

# Load GROQ_API_KEY from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# How many chunks to retrieve from ChromaDB per question.
# Why 5? — enough context without overwhelming the LLM's context window.
# Too few = missing info. Too many = LLM gets confused / slower.
TOP_K = 5

# The Groq model we use.
# llama-3.3-70b-versatile = best free model on Groq right now.
GROQ_MODEL = "llama-3.3-70b-versatile"

# Max tokens the LLM can generate in its response.
MAX_TOKENS = 1024


# ---------------------------------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------------------------------

def get_groq_client() -> Groq:
    """
    Creates and returns a Groq client using the API key from .env.
    
    Why load from .env? — never hardcode API keys in source code.
    If you push to GitHub with a hardcoded key, it gets stolen within minutes
    by bots that scan public repos. .env is in .gitignore so it stays local.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Make sure it's set in your .env file.")
    return Groq(api_key=api_key)


# ---------------------------------------------------------------------------
# STEP 5 — RETRIEVE
# ---------------------------------------------------------------------------

def retrieve_chunks(question: str, collection: chromadb.Collection, top_k: int = TOP_K) -> list[dict]:
    """
    Embeds the user's question and finds the top_k most similar chunks
    in ChromaDB using cosine similarity.

    Returns a list of dicts: {text, path, chunk_index}

    How does ChromaDB find similar chunks?
    — It embeds the question using the SAME embedding model used during ingest.
    — Then it computes cosine similarity between the question vector and
      every chunk vector stored in the database.
    — Returns the top_k closest matches.
    
    This is called "semantic search" — it finds meaning, not just keywords.
    So "how does scheduling work?" will find chunks about "cron jobs" and
    "APScheduler" even if the word "scheduling" doesn't appear in them.
    """
    results = collection.query(
        query_texts=[question],   # ChromaDB embeds this automatically
        n_results=min(top_k, collection.count()),  # can't retrieve more than we have
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        chunks.append({
            "text":        doc,
            "path":        results["metadatas"][0][i]["path"],
            "chunk_index": results["metadatas"][0][i]["chunk_index"],
            "distance":    results["distances"][0][i]  # lower = more similar
        })

    return chunks


# ---------------------------------------------------------------------------
# STEP 6 — BUILD PROMPT
# ---------------------------------------------------------------------------

def build_prompt(question: str, chunks: list[dict]) -> str:
    """
    Assembles the final prompt we send to the LLM.

    Structure:
      - System message: tells the LLM its role and rules
      - Retrieved chunks: the relevant code context
      - User question: what we actually want answered

    Why separate system message from user message?
    — LLMs are trained on chat format with roles: system, user, assistant.
    — The system message sets behaviour (like instructions to an employee).
    — The user message is the actual query.
    — Keeping them separate gives the LLM clearer signals.
    """
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"--- Source {i+1}: {chunk['path']} (chunk {chunk['chunk_index']}) ---\n"
            f"{chunk['text']}\n"
        )
    context = "\n".join(context_parts)

    return context  # we pass this as context; question goes separately as user message


def get_system_prompt() -> str:
    return """You are RepoMind, an expert AI code analyst. You help developers understand codebases.

You are given relevant excerpts from a GitHub repository as context.
Use ONLY the provided context to answer questions. 
If the answer isn't in the context, say so honestly — do not make things up.

When answering:
- Be specific and reference file names and function names where relevant
- Use code snippets from the context when helpful
- Explain concepts clearly for developers of all levels
- If you see potential issues or improvements, mention them briefly"""


# ---------------------------------------------------------------------------
# STEP 7 — ASK GROQ (streaming)
# ---------------------------------------------------------------------------

def ask(question: str, collection: chromadb.Collection, stream: bool = True):
    """
    Full RAG query pipeline:
      1. Retrieve relevant chunks from ChromaDB
      2. Build prompt with context
      3. Send to Groq LLaMA 3.3 70B
      4. Stream or return the response

    If stream=True, yields text chunks as they arrive (for Streamlit).
    If stream=False, returns the full response string (for testing).

    Why streaming?
    — LLMs generate tokens one at a time. Without streaming, the user
      stares at a blank screen for 5-10 seconds then gets a wall of text.
    — With streaming, text appears word by word — feels alive and responsive.
    — Streamlit supports streaming natively with st.write_stream().
    """
    client = get_groq_client()

    # Step 1: retrieve
    chunks = retrieve_chunks(question, collection)

    # Step 2: build context
    context = build_prompt(question, chunks)

    # Step 3 & 4: send to Groq and stream back
    messages = [
        {
            "role": "system",
            "content": get_system_prompt()
        },
        {
            "role": "user",
            "content": f"Here is the relevant code context:\n\n{context}\n\nQuestion: {question}"
        }
    ]

    if stream:
        # Returns a generator — caller iterates over it to get text chunks
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.3,      # low temp = more focused, less creative (good for code)
            stream=True
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    else:
        # Returns full string — used for testing and non-streaming contexts
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
            stream=False
        )
        return response.choices[0].message.content


def get_sources(question: str, collection: chromadb.Collection) -> list[dict]:
    """
    Returns the source chunks used for a question — so the UI can show
    'Answer based on: scheduler.py, config.py' etc.
    Useful for transparency and debugging.
    """
    return retrieve_chunks(question, collection)