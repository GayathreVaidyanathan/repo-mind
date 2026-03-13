import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS  = 2048  # more than retriever — analysis responses are longer

# Only analyse actual code files, not docs/config
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".go", ".rs"}

# Max characters of a file we send to the LLM.
# Why limit? — very large files exceed context window limits.
# 6000 chars ≈ ~1500 tokens, well within LLaMA's 32k context.
MAX_FILE_CHARS = 6000


# ---------------------------------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------------------------------

def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    return Groq(api_key=api_key)


# ---------------------------------------------------------------------------
# PROMPT BUILDERS
# ---------------------------------------------------------------------------

def build_bug_prompt(file_path: str, code: str) -> str:
    """
    Instructs the LLM to find bugs, security issues, and anti-patterns.
    
    Key prompt engineering techniques used here:
    
    1. ROLE: "You are an expert code reviewer" — primes the LLM to think
       like a senior engineer, not a general assistant.
    
    2. STRICT JSON FORMAT: We specify exactly what keys we want.
       If we don't constrain the format, LLMs produce free-form text
       that's impossible to parse programmatically.
    
    3. SEVERITY LEVELS: Giving explicit categories (critical/warning/info)
       forces the LLM to prioritise rather than treat everything equally.
    
    4. "Return ONLY the JSON": Without this, LLMs add preamble like
       "Sure! Here are the issues I found:" which breaks JSON parsing.
    
    5. EXAMPLES IN PROMPT: Showing the exact structure reduces format errors
       dramatically — LLMs are good at pattern matching.
    """
    return f"""You are an expert code reviewer. Analyse this code file for bugs, security issues, and anti-patterns.

File: {file_path}

```
{code[:MAX_FILE_CHARS]}
```

Return ONLY a valid JSON array (no other text, no markdown, no explanation).
Each item must have exactly these keys:
- "type": one of ["bug", "security", "anti-pattern", "performance", "improvement"]
- "severity": one of ["critical", "warning", "info"]
- "line_hint": approximate line number or range as a string (e.g. "12" or "45-50"), or "unknown"
- "title": short title of the issue (max 10 words)
- "description": clear explanation of the problem (2-3 sentences)
- "suggestion": how to fix it (1-2 sentences)

If no issues found, return an empty array: []

Example format:
[
  {{
    "type": "security",
    "severity": "critical",
    "line_hint": "23",
    "title": "Hardcoded API key in source code",
    "description": "The API key is hardcoded directly in the source file. This is a serious security risk as anyone with access to the code can steal the key.",
    "suggestion": "Move the key to an environment variable and load it with os.getenv()."
  }}
]"""


def build_summary_prompt(file_path: str, code: str) -> str:
    """
    Asks the LLM to summarise what a file does in plain English.
    Used to build the architecture overview in the UI.
    
    Notice we ask for a SHORT summary (2-3 sentences) — LLMs tend to
    be verbose by default. Constraining length forces conciseness.
    """
    return f"""You are a code documentation expert.

File: {file_path}

```
{code[:MAX_FILE_CHARS]}
```

In 2-3 sentences, explain:
1. What this file does
2. Its main functions/classes
3. How it fits into the overall project

Return ONLY a plain text summary. No bullet points, no markdown."""


# ---------------------------------------------------------------------------
# CORE ANALYSIS FUNCTIONS
# ---------------------------------------------------------------------------

def analyse_file(file: dict, client: Groq) -> dict:
    """
    Runs bug/security/anti-pattern analysis on a single file.
    Returns a dict with file info and list of issues found.
    
    We wrap the LLM call in try/except because:
    - The LLM might return malformed JSON occasionally
    - The API might timeout or hit rate limits
    - We never want one bad file to crash the entire analysis
    """
    path    = file["path"]
    content = file["content"]
    ext     = file["extension"]

    # Skip non-code files
    if ext not in CODE_EXTENSIONS:
        return None

    # Skip very small files (< 5 lines) — not worth analysing
    if len(content.strip().split("\n")) < 5:
        return None

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a code review assistant. You ONLY return valid JSON arrays. Never add explanation or markdown."
                },
                {
                    "role": "user",
                    "content": build_bug_prompt(path, content)
                }
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.1,   # very low temp = consistent, structured output
            stream=False
        )

        raw = response.choices[0].message.content.strip()

        # Clean up common LLM formatting mistakes
        # Sometimes LLMs wrap JSON in ```json ... ``` even when told not to
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        issues = json.loads(raw)  # parse JSON

        return {
            "path":       path,
            "extension":  ext,
            "issue_count": len(issues),
            "issues":     issues
        }

    except json.JSONDecodeError as e:
        print(f"[analyzer] JSON parse error for {path}: {e}")
        return {
            "path":       path,
            "extension":  ext,
            "issue_count": 0,
            "issues":     [],
            "error":      "Could not parse LLM response"
        }
    except Exception as e:
        print(f"[analyzer] Error analysing {path}: {e}")
        return None


def summarise_file(file: dict, client: Groq) -> dict:
    """
    Generates a plain English summary of what a file does.
    Returns dict with path and summary string.
    """
    path    = file["path"]
    content = file["content"]
    ext     = file["extension"]

    if ext not in CODE_EXTENSIONS:
        return None

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": build_summary_prompt(path, content)
                }
            ],
            max_tokens=200,
            temperature=0.2,
            stream=False
        )

        summary = response.choices[0].message.content.strip()
        return {"path": path, "summary": summary}

    except Exception as e:
        print(f"[analyzer] Error summarising {path}: {e}")
        return None


# ---------------------------------------------------------------------------
# MASTER FUNCTIONS — called by app.py
# ---------------------------------------------------------------------------

def run_analysis(files: list[dict]) -> dict:
    """
    Analyses all code files for bugs, security issues, and anti-patterns.
    
    Returns a dict:
    {
        "results":         list of per-file analysis dicts,
        "total_issues":    int,
        "critical_count":  int,
        "warning_count":   int,
        "info_count":      int,
        "by_type":         dict of type → count,
        "files_analysed":  int
    }
    
    Why return aggregated counts?
    — The UI needs summary stats for the dashboard header
      (e.g. "3 critical issues across 8 files").
    — Pre-computing them here keeps app.py clean.
    """
    client  = get_groq_client()
    results = []

    code_files = [f for f in files if f["extension"] in CODE_EXTENSIONS
                  and len(f["content"].strip().split("\n")) >= 5]

    print(f"[analyzer] Analysing {len(code_files)} code files...")

    for i, file in enumerate(code_files):
        print(f"[analyzer] ({i+1}/{len(code_files)}) {file['path']}")
        result = analyse_file(file, client)
        if result:
            results.append(result)

    # Aggregate stats
    all_issues     = [issue for r in results for issue in r["issues"]]
    critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
    warning_count  = sum(1 for i in all_issues if i.get("severity") == "warning")
    info_count     = sum(1 for i in all_issues if i.get("severity") == "info")

    by_type = {}
    for issue in all_issues:
        t = issue.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    print(f"[analyzer] ✅ Done — {len(all_issues)} issues found across {len(results)} files")

    return {
        "results":        results,
        "total_issues":   len(all_issues),
        "critical_count": critical_count,
        "warning_count":  warning_count,
        "info_count":     info_count,
        "by_type":        by_type,
        "files_analysed": len(results)
    }


def run_summaries(files: list[dict]) -> list[dict]:
    """
    Generates plain English summaries for all code files.
    Returns list of {path, summary} dicts.
    Used to build the architecture overview tab in the UI.
    """
    client    = get_groq_client()
    summaries = []

    code_files = [f for f in files if f["extension"] in CODE_EXTENSIONS]
    print(f"[analyzer] Summarising {len(code_files)} files...")

    for i, file in enumerate(code_files):
        print(f"[analyzer] ({i+1}/{len(code_files)}) {file['path']}")
        result = summarise_file(file, client)
        if result:
            summaries.append(result)

    print(f"[analyzer] ✅ Done — {len(summaries)} summaries generated")
    return summaries