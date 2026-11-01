# 🍎 apple-notes-codemode

> **High-Performance Model Context Protocol (MCP) Server, Code Mode Execution Engine, and Swagger REST API for macOS Apple Notes.**

[![macOS](https://img.shields.io/badge/platform-macOS-black?logo=apple)](https://www.apple.com/macos/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?logo=python)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-100%25%20passing-brightgreen)](tests/)

---

## 💡 What is `apple-notes-codemode`?

`apple-notes-codemode` connects AI models (Claude, GPT, Antigravity IDE, Cursor) and developer workflows directly to your native **Apple Notes** on macOS. 

Instead of being limited to conventional, chatty tool calling, it introduces **Code Mode**: an in-memory Python sandbox where AI assistants write expressive Python code to perform complex queries, bulk modifications, and multi-step logic in **a single execution turn**.

It provides:
1. **🤖 Model Context Protocol (MCP) Server**: Standardized tool interface over `stdio` for Claude Desktop, Antigravity, and Cursor.
2. **⚡ Code Mode Engine**: Write Python scripts using the `codemode` / `notes` toolbox to batch process notes with zero network latency.
3. **🌐 REST API & Interactive Swagger UI**: Full FastAPI server with OpenAPI 3.0 schema and interactive browser documentation at `http://127.0.0.1:8000/docs`.
4. **🔒 100% Local & Private**: Direct communication via macOS JavaScript for Automation (JXA) and `osascript`. No cloud subscriptions, no third-party telemetry.

---

## 🚀 The Paradigm Shift: Why "Code Mode"?

### The Problem with Traditional Tool Calling
In conventional MCP architectures, an agent must execute one tool per interaction:
```
LLM -> tool: list_notes()          -> wait for response (500 tokens)
LLM -> tool: read_note(id="1")     -> wait for response (1,000 tokens)
LLM -> tool: read_note(id="2")     -> wait for response (1,000 tokens)
LLM -> tool: update_note(id="2")   -> wait for response (200 tokens)
Total: 4 Round Trips, high latency, context window bloat!
```

### The Code Mode Solution
With **Code Mode**, the LLM sends a single executable Python script:
```python
# Executed in a single round-trip within < 50ms
for note in codemode.list_notes(folder="Work"):
    if "#urgent" in note["name"].lower():
        content = codemode.read_note(id=note["id"])
        codemode.update_note(id=note["id"], body="\n[Reviewed by AI]", append=True)
print("Processed all urgent work notes.")
```
**Benefits:**
- ⚡ **Zero Round-Trip Latency**: Iterations, filtering, regex matching, and batch operations execute locally in Python.
- 📉 **Massive Token Savings**: Raw note dumps don't clutter the LLM context; only `print()` outputs are returned.
- 🧠 **Expressive Logic**: Agents can employ full Python features (`for` loops, list comprehensions, `datetime`, `re`, `json`, `math`).

---

## 🏗️ Architecture

```
┌──────────────────────────────────────┐       ┌──────────────────────────────┐
│  AI Agents (Claude / Antigravity)   │       │  Browser / Swagger UI / HTTP │
└──────────────────┬───────────────────┘       └──────────────┬───────────────┘
                   │ (stdio transport)                        │ (HTTP REST)
                   ▼                                          ▼
         ┌───────────────────┐                      ┌───────────────────┐
         │   mcp_server.py   │                      │      api.py       │
         │    (MCP Server)   │                      │     (FastAPI)     │
         └─────────┬─────────┘                      └─────────┬─────────┘
                   │                                          │
                   ├──────────────────────────────────────────┘
                   ▼
         ┌───────────────────┐
         │codemode_runner.py │ ◄── In-memory sandboxed Python execution
         └─────────┬─────────┘
                   ▼
         ┌───────────────────┐
         │  notes_bridge.py  │ ◄── AppleScript / JXA Native Bridge
         └─────────┬─────────┘
                   ▼
      ┌─────────────────────────┐
      │  macOS Apple Notes App  │ (Local CoreData Storage)
      └─────────────────────────┘
```

---

## 🛠️ Features

- **Full CRUD Note Lifecycle**:
  - `list_notes`: List notes with search keywords and folder filters.
  - `read_note`: Retrieve full plaintext and HTML body by title or CoreData ID.
  - `create_note`: Create rich multi-line notes (auto-creates destination folders).
  - `update_note`: Replace content or append to notes (preserves modification state).
  - `delete_note`: Non-destructive delete—safely moves notes to native *Recently Deleted*.
- **Folder Operations**: List folders with note counts, create folders automatically.
- **Python Sandbox (`CodeModeEngine`)**:
  - Sandboxed execution environment with pre-imported `datetime`, `json`, `re`, `math`.
  - Captures `stdout`, execution duration (ms), return values, and structured error tracebacks.
- **Dual MCP & REST Interfaces**:
  - Run as headless stdio MCP service for AI agents.
  - Or launch FastAPI with live Swagger UI / ReDoc.
- **100% Automated Pytest Coverage**: Comprehensive test suite covering REST, MCP, and Code Mode execution.

---

## ⚡ Quick Start

### 1. Prerequisites
- macOS (Apple Silicon or Intel)
- Python 3.12+ (or Homebrew `uv`)
- Apple Notes enabled on your Mac

### 2. Clone and Setup

```bash
git clone https://github.com/hritick1/apple-notes-codemode.git
cd apple-notes-codemode

# Create virtual environment and install dependencies
chmod +x start.sh
./start.sh
```

### 3. Running the Server

#### Option A: FastAPI & Swagger UI (Default)
```bash
./start.sh
# or: uvicorn api:app --reload --port 8000
```
Open your browser:
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

#### Option B: Standalone MCP Server (stdio)
```bash
./start.sh mcp
# or: python3 mcp_server.py --transport stdio
```

#### Option C: Run Test Suite
```bash
./start.sh test
# or: pytest tests/ -v
```

---

## 🤖 AI Client Integration

### 1. Claude Desktop Setup

To connect Apple Notes to Claude Desktop:

1. Locate or create your Claude Desktop configuration file:
   - **macOS Path**: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Find the absolute path of this cloned repository by running:
   ```bash
   cd apple-notes-codemode && pwd
   ```
3. Add the server configuration under `"mcpServers"` in `claude_desktop_config.json`, replacing `/ABSOLUTE/PATH/TO/apple-notes-codemode` with your project's path:

```json
{
  "mcpServers": {
    "apple-notes": {
      "command": "/ABSOLUTE/PATH/TO/apple-notes-codemode/.venv/bin/python3",
      "args": [
        "/ABSOLUTE/PATH/TO/apple-notes-codemode/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/apple-notes-codemode"
      }
    }
  }
}
```

> **Note**: A starter configuration file is also provided in the repo at [`claude_desktop_config.json`](claude_desktop_config.json).

### 2. Antigravity IDE / Cursor / Open WebUI
Configure an MCP server with the `stdio` transport using:
- **Command**: `/ABSOLUTE/PATH/TO/apple-notes-codemode/.venv/bin/python3`
- **Args**: `["/ABSOLUTE/PATH/TO/apple-notes-codemode/mcp_server.py"]`
- **Environment**: `PYTHONPATH=/ABSOLUTE/PATH/TO/apple-notes-codemode`

---

## 🐍 Code Mode Toolbox Reference

When calling `code_mode(code="...")`, the script executes with the pre-injected `codemode` (or `notes`) toolbox:

| Method | Parameters | Description |
|---|---|---|
| `codemode.list_notes()` | `folder=None`, `search=None`, `limit=50` | Returns a list of note summaries (`id`, `name`, `folder`, `modification_date`). |
| `codemode.read_note()` | `title=None`, `id=None` | Returns full note dictionary (`plaintext`, `body`, `folder`, etc.). |
| `codemode.create_note()` | `title: str`, `body: str=""`, `folder=None` | Creates a new note (creates folder if needed). |
| `codemode.update_note()` | `body: str`, `id=None`, `title=None`, `append=False`, `new_title=None` | Updates or appends content to an existing note. |
| `codemode.delete_note()` | `title=None`, `id=None` | Moves note safely to native "Recently Deleted". |
| `codemode.list_folders()` | None | Returns list of folders with note counts. |
| `codemode.create_folder()` | `name: str` | Creates a new Apple Notes folder. |

### Code Mode Script Examples

#### 1. Daily Standup Note Generator
```python
import datetime

today = datetime.date.today().isoformat()
title = f"Daily Standup - {today}"
body = f"""# Daily Standup ({today})
## Yesterday's Achievements
- Reviewed Apple Notes MCP PR
- Completed Code Mode engine integration

## Today's Priorities
- Add Swagger OpenAPI documentation
- Deploy to GitHub

## Blockers
- None
"""
note = codemode.create_note(title=title, body=body, folder="Daily Logs")
print(f"Created note '{note['name']}' in folder '{note['folder']}'")
```

#### 2. Search & Tag Cleanup
```python
notes = codemode.list_notes(folder="Projects")
tagged = 0
for n in notes:
    detail = codemode.read_note(id=n["id"])
    if "TODO" in detail["plaintext"] and "#action" not in detail["plaintext"]:
        codemode.update_note(id=n["id"], body="\n\n#action", append=True)
        tagged += 1
print(f"Appended #action tag to {tagged} project notes.")
```

#### 3. Archive Completed Meeting Notes
```python
meetings = codemode.list_notes(folder="Meetings", search="[DONE]")
for m in meetings:
    codemode.delete_note(id=m["id"])
print(f"Moved {len(meetings)} completed meetings to Recently Deleted.")
```

---

## 🌐 REST API Endpoints

| HTTP | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check connectivity and note count |
| `GET` | `/notes` | List notes (supports `folder`, `search`, `limit`) |
| `GET` | `/notes/{note_id}` | Read note by CoreData ID |
| `POST` | `/notes` | Create a new note |
| `PUT` | `/notes/{note_id}` | Update or append to a note |
| `DELETE` | `/notes/{note_id}` | Move note to Recently Deleted |
| `GET` | `/folders` | List all folders |
| `POST` | `/folders` | Create a folder |
| `POST` | `/codemode/execute` | Execute Python script in Code Mode |
| `GET` | `/mcp/tools` | List MCP tools schema |

---

## 🔒 Security & macOS Permissions

When running this tool for the first time, macOS may display a system dialog:
> **"Terminal" (or Python / IDE) wants access to control "Notes".**

Click **OK / Allow**.
You can verify or revoke this anytime under:
`System Settings` → `Privacy & Security` → `Automation` → check `Notes` under your terminal or IDE.

---

## 🧪 Testing

The repository includes a comprehensive `pytest` test suite:

```bash
./start.sh test
```

Expected output:
```
tests/test_notes.py::test_health_endpoint PASSED                         [ 14%]
tests/test_notes.py::test_swagger_documentation PASSED                   [ 28%]
tests/test_notes.py::test_folders_api PASSED                             [ 42%]
tests/test_notes.py::test_full_rest_crud_lifecycle PASSED                [ 57%]
tests/test_notes.py::test_mcp_tools PASSED                               [ 71%]
tests/test_notes.py::test_codemode_python_execution PASSED               [ 85%]
tests/test_notes.py::test_codemode_python_multistep_lifecycle PASSED     [100%]
7 passed in ~5s
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
