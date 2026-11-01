"""
Apple Notes REST API with interactive Swagger OpenAPI documentation.
Runs on FastAPI, providing Swagger UI at /docs and ReDoc at /redoc.
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from notes_bridge import AppleNotesBridge, FolderInfo, NoteDetail, NoteSummary
from codemode_runner import engine, CodeExecutionResult

bridge = AppleNotesBridge()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    try:
        health = bridge.check_health()
        print(f"[API] Connected to Apple Notes successfully: {health.get('notes_count', 0)} notes.")
    except Exception as e:
        print(f"[API] Warning during startup: {e}")
    yield


app = FastAPI(
    title="Apple Notes API & MCP Hub",
    description="""
# 📝 Apple Notes macOS REST API & Swagger UI

Expose and control macOS **Apple Notes** programmatically via HTTP REST APIs and Model Context Protocol (MCP).

### 🚀 Key Features:
- **CRUD Operations**: Create, read, update (replace/append), and delete Apple Notes.
- **Folder Management**: List and create folders.
- **Search**: Filter notes by keyword, folder, or modification date.
- **Safety**: Deletes move notes to *Recently Deleted* safely.
- **MCP Protocol**: MCP Server tool definitions provided for Claude Desktop, Antigravity IDE, Cursor, etc.
- **Interactive Swagger UI**: Test all endpoints directly in your browser with real-time execution.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Enable CORS for local development and client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Request & Response Schemas
# ==========================================

class NoteCreateRequest(BaseModel):
    title: str = Field(
        ...,
        description="The title / heading of the note",
        examples=["Project Brainstorming"]
    )
    body: str = Field(
        "",
        description="The content / body of the note (supports multi-line text)",
        examples=["Key goals for Q4:\n- Complete Apple Notes MCP server\n- Expose Swagger endpoint"]
    )
    folder: Optional[str] = Field(
        None,
        description="Optional folder name. If it does not exist, it will be automatically created.",
        examples=["Notes"]
    )


class NoteUpdateRequest(BaseModel):
    body: str = Field(
        ...,
        description="New content to replace or append to the note",
        examples=["Follow-up: All milestones achieved on time."]
    )
    append: bool = Field(
        False,
        description="If True, appends to the end of the existing note; if False, replaces the body."
    )
    new_title: Optional[str] = Field(
        None,
        description="Optional new title if you wish to rename the note.",
        examples=["Project Brainstorming - Finalized"]
    )


class FolderCreateRequest(BaseModel):
    name: str = Field(
        ...,
        description="Name of the folder to create",
        examples=["Sprint Backlog"]
    )


class HealthResponse(BaseModel):
    status: str
    notes_count: int
    folders_count: int
    app_name: str


class DeleteResponse(BaseModel):
    success: bool
    deleted_id: str
    deleted_title: str
    message: str


class CodeModeRequest(BaseModel):
    code: str = Field(
        ...,
        description="Python script to execute inside the Code Mode sandbox with the `codemode` toolbox.",
        examples=[
            "notes = codemode.list_notes(limit=5)\nprint(f'Found {len(notes)} notes:')\nfor n in notes:\n    print(f'• {n[\"name\"]}')"
        ]
    )


# ==========================================
# REST API Endpoints
# ==========================================

@app.post(
    "/api/codemode",
    response_model=CodeExecutionResult,
    tags=["Code Mode"],
    summary="Execute script in Code Mode sandbox"
)
def run_code_mode(payload: CodeModeRequest):
    """
    Execute a Python script with the `codemode` (or `notes`) toolbox.
    Enables loops, filtering, bulk updates, and dependent calls in a single execution.
    """
    try:
        return engine.execute(code=payload.code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check & Apple Notes connectivity"
)
def get_health():
    """Verify that macOS Apple Notes is accessible via AppleScript/JXA."""
    try:
        return bridge.check_health()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Apple Notes connection error: {str(e)}"
        )


@app.get(
    "/api/notes",
    response_model=List[NoteSummary],
    tags=["Notes"],
    summary="List and search notes"
)
def list_notes(
    folder: Optional[str] = Query(None, description="Filter notes by folder name"),
    search: Optional[str] = Query(None, description="Search term for note title or body"),
    limit: int = Query(50, ge=1, le=500, description="Max notes to return"),
    include_deleted: bool = Query(False, description="Include notes from Recently Deleted")
):
    """
    List notes with optional folder filtering and keyword search.
    Excludes 'Recently Deleted' notes by default.
    """
    try:
        return bridge.list_notes(
            folder=folder,
            search=search,
            limit=limit,
            include_deleted=include_deleted
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/notes",
    response_model=NoteDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["Notes"],
    summary="Create a new note"
)
def create_note(payload: NoteCreateRequest):
    """
    Create a new note in Apple Notes.
    Optionally puts the note in a folder (creates folder if needed).
    """
    try:
        return bridge.create_note(
            title=payload.title,
            body=payload.body,
            folder=payload.folder
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@app.get(
    "/api/notes/by-title/{title}",
    response_model=NoteDetail,
    tags=["Notes"],
    summary="Get note by exact title"
)
def get_note_by_title(
    title: str,
    include_deleted: bool = Query(False, description="Include note if in Recently Deleted")
):
    """Fetch full note content (plaintext and body HTML) using its title."""
    note = bridge.get_note(title=title, include_deleted=include_deleted)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note with title '{title}' not found")
    return note


@app.get(
    "/api/notes/{note_id:path}",
    response_model=NoteDetail,
    tags=["Notes"],
    summary="Get note by ID"
)
def get_note_by_id(
    note_id: str,
    include_deleted: bool = Query(False, description="Include note if in Recently Deleted")
):
    """Fetch full note content (plaintext and body HTML) using its unique CoreData ID."""
    note = bridge.get_note(note_id=note_id, include_deleted=include_deleted)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note with ID '{note_id}' not found")
    return note


@app.put(
    "/api/notes/by-title/{title}",
    response_model=NoteDetail,
    tags=["Notes"],
    summary="Update or append to note by title"
)
def update_note_by_title(title: str, payload: NoteUpdateRequest):
    """Update or append to an existing note by its title."""
    try:
        return bridge.update_note(
            title=title,
            body=payload.body,
            new_title=payload.new_title,
            append=payload.append
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to update note: {str(e)}")


@app.put(
    "/api/notes/{note_id:path}",
    response_model=NoteDetail,
    tags=["Notes"],
    summary="Update or append to note by ID"
)
def update_note_by_id(note_id: str, payload: NoteUpdateRequest):
    """Update or append to an existing note by its unique ID."""
    try:
        return bridge.update_note(
            note_id=note_id,
            body=payload.body,
            new_title=payload.new_title,
            append=payload.append
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to update note: {str(e)}")


@app.delete(
    "/api/notes/by-title/{title}",
    response_model=DeleteResponse,
    tags=["Notes"],
    summary="Delete note by title"
)
def delete_note_by_title(title: str):
    """Safely move a note to 'Recently Deleted' by title."""
    try:
        res = bridge.delete_note(title=title)
        return res
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to delete note: {str(e)}")


@app.delete(
    "/api/notes/{note_id:path}",
    response_model=DeleteResponse,
    tags=["Notes"],
    summary="Delete note by ID"
)
def delete_note_by_id(note_id: str):
    """Safely move a note to 'Recently Deleted' by ID."""
    try:
        res = bridge.delete_note(note_id=note_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to delete note: {str(e)}")


@app.get(
    "/api/folders",
    response_model=List[FolderInfo],
    tags=["Folders"],
    summary="List all folders"
)
def list_folders():
    """List all folders in Apple Notes and the number of notes in each."""
    try:
        return bridge.list_folders()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/folders",
    response_model=FolderInfo,
    status_code=status.HTTP_201_CREATED,
    tags=["Folders"],
    summary="Create a new folder"
)
def create_folder(payload: FolderCreateRequest):
    """Create a new folder in Apple Notes."""
    try:
        return bridge.create_folder(payload.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")


# ==========================================
# Sleek Web Dashboard Landing Page
# ==========================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    """Interactive Landing Dashboard with Swagger link and MCP client guide."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Apple Notes MCP Server & Swagger API</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(22, 30, 49, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --primary: #f59e0b;
      --primary-gradient: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
      --accent: #38bdf8;
      --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --code-bg: #0f172a;
      --success: #10b981;
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 10% 20%, rgba(245, 158, 11, 0.08), transparent 40%),
                  radial-gradient(circle at 90% 80%, rgba(56, 189, 248, 0.08), transparent 40%),
                  var(--bg);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2.5rem 1.5rem;
    }
    .container {
      max-width: 960px;
      width: 100%;
    }
    header {
      text-align: center;
      margin-bottom: 2.5rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.825rem;
      font-weight: 600;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      margin-bottom: 1.25rem;
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      background-color: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--success);
    }
    h1 {
      font-size: 2.75rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      margin-bottom: 0.75rem;
      background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    p.subtitle {
      font-size: 1.125rem;
      color: var(--text-muted);
      max-width: 620px;
      margin: 0 auto;
      line-height: 1.6;
    }
    .cta-group {
      display: flex;
      justify-content: center;
      gap: 1rem;
      margin-top: 1.75rem;
      flex-wrap: wrap;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1.5rem;
      border-radius: 12px;
      font-weight: 600;
      font-size: 0.95rem;
      text-decoration: none;
      transition: all 0.2s ease;
      cursor: pointer;
    }
    .btn-primary {
      background: var(--primary-gradient);
      color: #111827;
      box-shadow: 0 8px 24px rgba(245, 158, 11, 0.25);
    }
    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 30px rgba(245, 158, 11, 0.4);
    }
    .btn-secondary {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      backdrop-filter: blur(12px);
    }
    .btn-secondary:hover {
      background: rgba(30, 41, 67, 0.8);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.5rem;
      backdrop-filter: blur(16px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .endpoints-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
    }
    .endpoint-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.5rem 0.75rem;
      background: var(--code-bg);
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .method {
      font-weight: 700;
      padding: 0.2rem 0.45rem;
      border-radius: 4px;
      font-size: 0.75rem;
    }
    .method-get { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
    .method-post { background: rgba(16, 185, 129, 0.15); color: #10b981; }
    .method-put { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
    .method-delete { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    pre {
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.825rem;
      color: #cbd5e1;
      overflow-x: auto;
      line-height: 1.5;
    }
    footer {
      margin-top: 2rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge">
        <span class="pulse-dot"></span>
        Apple Notes Service Active
      </div>
      <h1>Apple Notes MCP & REST API</h1>
      <p class="subtitle">
        Native macOS Apple Notes integration exposed through a high-performance REST API with interactive Swagger docs and Model Context Protocol (MCP) tooling.
      </p>
      <div class="cta-group">
        <a href="/docs" class="btn btn-primary">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          Open Swagger UI (/docs)
        </a>
        <a href="/redoc" class="btn btn-secondary">
          <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
          </svg>
          ReDoc (/redoc)
        </a>
        <a href="/openapi.json" class="btn btn-secondary">
          OpenAPI JSON
        </a>
      </div>
    </header>

    <div class="grid">
      <div class="card">
        <div class="card-title">
          <span>⚡</span>
          <span>REST API Endpoints</span>
        </div>
        <ul class="endpoints-list">
          <li class="endpoint-item">
            <span>/api/notes</span>
            <span class="method method-get">GET</span>
          </li>
          <li class="endpoint-item">
            <span>/api/notes</span>
            <span class="method method-post">POST</span>
          </li>
          <li class="endpoint-item">
            <span>/api/notes/{id}</span>
            <span class="method method-get">GET</span>
          </li>
          <li class="endpoint-item">
            <span>/api/notes/{id}</span>
            <span class="method method-put">PUT</span>
          </li>
          <li class="endpoint-item">
            <span>/api/notes/{id}</span>
            <span class="method method-delete">DELETE</span>
          </li>
          <li class="endpoint-item">
            <span>/api/folders</span>
            <span class="method method-get">GET</span>
          </li>
          <li class="endpoint-item">
            <span>/api/health</span>
            <span class="method method-get">GET</span>
          </li>
        </ul>
      </div>

      <div class="card">
        <div class="card-title">
          <span>🤖</span>
          <span>MCP Client Configuration</span>
        </div>
        <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.75rem;">
          Add this to your <code>claude_desktop_config.json</code> or Antigravity configuration:
        </p>
        <pre><code>{
  "mcpServers": {
    "apple-notes": {
      "command": "/ABSOLUTE/PATH/TO/apple-notes-codemode/.venv/bin/python3",
      "args": ["/ABSOLUTE/PATH/TO/apple-notes-codemode/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/apple-notes-codemode"
      }
    }
  }
}</code></pre>
      </div>
    </div>

    <footer>
      macOS Apple Notes Integration • Powered by FastAPI & Model Context Protocol (MCP)
    </footer>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
