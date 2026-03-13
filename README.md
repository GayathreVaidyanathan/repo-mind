# 🧠 RepoMind

> AI-powered code intelligence for any GitHub repository

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.55-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![LLaMA](https://img.shields.io/badge/LLaMA_3.3_70B-Groq-F55036?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**RepoMind** lets you point at any public GitHub repository and instantly chat with it, detect bugs, map its architecture, and auto-generate documentation — all powered by RAG (Retrieval-Augmented Generation) and LLaMA 3.3 70B via Groq.

🔗 **[Live Demo](https://repo-mind-ffmulxnegnpmtmr9f4tqtb.streamlit.app/)**

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **Chat with Code** | Ask anything about the codebase in plain English — powered by semantic search + LLaMA 3.3 70B |
| 🔍 **Bug Detection** | AI scans every file for security issues, anti-patterns, and bugs with severity ratings |
| 🗺️ **Architecture Map** | Static AST analysis extracts dependencies, classes, and functions across all files |
| 📄 **File Explorer** | Browse all indexed files grouped by type with line counts and sizes |
| 📖 **Auto README** | Generates a professional README.md from the codebase — downloadable instantly |

---

## 🏗️ Architecture

```
GitHub URL
    ↓
ingestor.py  — clone → load → chunk (1500 chars, 200 overlap) → embed → ChromaDB
    ↓
retriever.py — semantic search → top-5 chunks → prompt → Groq LLaMA 3.3 70B → stream
    ↓
analyzer.py  — per-file LLM analysis → structured JSON issues → severity classification
    ↓
graph.py     — AST parsing → import extraction → dependency graph → in/out degree stats
    ↓
app.py       — Streamlit UI with dark theme, 5 tabs, session state management
```

**Embedding model:** `all-MiniLM-L6-v2` (runs locally, 80MB, cached after first run)  
**Vector similarity:** Cosine similarity via ChromaDB HNSW index  
**LLM:** LLaMA 3.3 70B via Groq (free tier, ~500 tokens/sec)  
**Chunking:** 1500 char chunks with 200 char overlap (sliding window)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- [Groq API key](https://console.groq.com) (free)

### Installation

```bash
# Clone the repo
git clone https://github.com/GayathreVaidyanathan/repomind.git
cd repomind

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 💡 Usage

1. Paste any **public GitHub repository URL** in the sidebar
2. Click **⚡ Analyse Repository** — RepoMind clones, chunks, and indexes the codebase
3. Navigate the 5 tabs:
   - **Chat** — ask questions like *"How does authentication work?"* or *"What does the scraper class do?"*
   - **Analysis** — run AI bug detection, filter by severity and type
   - **Architecture** — view dependency graph, most imported files, complexity metrics
   - **Files** — browse all indexed files by type
   - **README** — generate and download a professional README

---

## 📁 Project Structure

```
repomind/
├── app.py              # Streamlit UI — 5 tabs, dark theme, session state
├── ingestor.py         # Clone → chunk → embed → store pipeline
├── retriever.py        # Semantic search + Groq LLM query pipeline
├── analyzer.py         # AI bug detection and code summarisation
├── graph.py            # AST-based dependency graph builder
├── requirements.txt    # Python dependencies
└── .env                # API keys (not committed)
```

---

## 🧠 How RAG Works

Traditional LLMs can't answer questions about your private or recent codebase — they only know what they were trained on. RepoMind uses **Retrieval-Augmented Generation**:

1. **Embed** — every code chunk is converted to a 768-dimension vector using `all-MiniLM-L6-v2`
2. **Store** — vectors are stored in ChromaDB with cosine similarity indexing
3. **Retrieve** — at query time, the question is embedded and the top-5 most similar chunks are found
4. **Generate** — retrieved chunks are injected into the LLM prompt as context

This means the LLM answers based on **your actual code**, not hallucinations.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit (custom dark theme CSS)
- **LLM:** LLaMA 3.3 70B via [Groq](https://groq.com) (free tier)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (local)
- **Vector Store:** ChromaDB (in-memory)
- **Code Parsing:** Python `ast` module (static analysis)
- **Repo Cloning:** GitPython (shallow clone, depth=1)
- **Deployment:** Streamlit Cloud

---

## ⚠️ Limitations

- Currently supports **public GitHub repositories** only
- Architecture map works best with **Python codebases** (JS/TS support planned)
- Very large repos (1000+ files) may be slow to index
- ChromaDB runs **in-memory** — index is rebuilt on each session

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

<div align="center">
  Built by <a href="https://github.com/GayathreVaidyanathan">Gayathre Vaidyanathan</a>
</div>
