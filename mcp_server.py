"""
Apple Notes Model Context Protocol (MCP) Server.
Exposes standard MCP tools for reading, creating, updating, searching, and deleting Apple Notes.
Compatible with Claude Desktop, Antigravity IDE, Cursor, and any MCP client.
"""

import argparse
import json
import sys
from typing import Optional

from mcp.server.mcpserver import MCPServer
from notes_bridge import AppleNotesBridge
from codemode_runner import engine

# Initialize Bridge, Code Mode Engine, and MCP Server
bridge = AppleNotesBridge()
server = MCPServer("apple-notes")


@server.tool(
    name="code_mode",
    description="""Execute a Python script in a sandboxed environment to interact with Apple Notes.
Instead of making multiple round-trip tool calls, write a Python script that performs loops, conditionals, bulk queries, and multi-step updates in a single execution.

The pre-injected `codemode` (or `notes`) toolbox provides:

- codemode.list_notes(folder=None, search=None, limit=50, include_deleted=False) -> list[dict]
- codemode.read_note(title=None, id=None) -> dict (keys: id, name, plaintext, body, folder)
- codemode.create_note(title: str, body: str = "", folder: str = None) -> dict
- codemode.update_note(body: str, title: str = None, id: str = None, append: bool = False, new_title: str = None) -> dict
- codemode.delete_note(title: str = None, id: str = None) -> dict (moves note to Recently Deleted)
- codemode.list_folders() -> list[dict]
- codemode.create_folder(name: str) -> dict

Also standard libraries `datetime`, `json`, `re`, `math` are pre-imported.
Use `print(...)` to output your final results.

Example:
notes = codemode.list_notes()
meetings = [n for n in notes if "meeting" in n["name"].lower()]
for m in meetings:
    old = codemode.read_note(id=m["id"])
    codemode.update_note(id=m["id"], body="Reviewed: 2026-10-23", append=True)
print(f"Updated {len(meetings)} meeting notes.")
"""
)
def code_mode(code: str) -> str:
    """
    Execute a Python Code Mode script against Apple Notes.

    :param code: The Python script string to execute.
    """
    res = engine.execute(code=code)
    return json.dumps(res.model_dump(), indent=2)




@server.tool(
    name="list_notes",
    description="List notes from Apple Notes. Returns note titles, IDs, container folders, and modification dates. Can filter by folder or search keyword."
)
def list_notes(
    folder: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    List notes from Apple Notes.

    :param folder: Filter notes by folder name (e.g. 'Notes', 'Work').
    :param search: Keyword to search in note titles and bodies.
    :param limit: Maximum number of notes to return (default 50).
    """
    notes = bridge.list_notes(folder=folder, search=search, limit=limit)
    return json.dumps([n.model_dump() for n in notes], indent=2)


@server.tool(
    name="read_note",
    description="Read the complete content (plain text and body HTML) of a note by exact title or note ID."
)
def read_note(
    title: Optional[str] = None,
    note_id: Optional[str] = None
) -> str:
    """
    Read the content of a note by title or ID.

    :param title: Exact title / name of the note to read.
    :param note_id: CoreData identifier of the note (e.g., 'x-coredata://...').
    """
    if not title and not note_id:
        return "Error: You must provide either 'title' or 'note_id'."

    note = bridge.get_note(note_id=note_id, title=title)
    if not note:
        identifier = f"id '{note_id}'" if note_id else f"title '{title}'"
        return f"Note with {identifier} was not found."

    return json.dumps(note.model_dump(), indent=2)


@server.tool(
    name="create_note",
    description="Create a new note in Apple Notes with a title, body content, and optional folder."
)
def create_note(
    title: str,
    body: str = "",
    folder: Optional[str] = None
) -> str:
    """
    Create a new note in Apple Notes.

    :param title: The title / first line of the new note.
    :param body: The text content of the note (supports multi-line text).
    :param folder: Optional folder name (e.g. 'Ideas'). Creates folder if it doesn't exist.
    """
    created = bridge.create_note(title=title, body=body, folder=folder)
    return json.dumps({
        "status": "success",
        "message": f"Successfully created note '{created.name}'",
        "note": created.model_dump()
    }, indent=2)


@server.tool(
    name="update_note",
    description="Update an existing note in Apple Notes. Can append new text or replace the entire body. Can also rename the note."
)
def update_note(
    body: str,
    title: Optional[str] = None,
    note_id: Optional[str] = None,
    append: bool = False,
    new_title: Optional[str] = None
) -> str:
    """
    Update or append content to an existing note.

    :param body: The text content to set or append.
    :param title: Title of the note to update (if note_id is not specified).
    :param note_id: ID of the note to update (preferred if titles may be duplicated).
    :param append: Set to True to append to existing note content; False to replace.
    :param new_title: Optional new title if you want to rename the note.
    """
    if not title and not note_id:
        return "Error: You must provide either 'title' or 'note_id'."

    try:
        updated = bridge.update_note(
            note_id=note_id,
            title=title,
            body=body,
            new_title=new_title,
            append=append
        )
        return json.dumps({
            "status": "success",
            "message": f"Successfully updated note '{updated.name}'",
            "note": updated.model_dump()
        }, indent=2)
    except Exception as e:
        return f"Error updating note: {str(e)}"


@server.tool(
    name="delete_note",
    description="Delete a note by title or note ID. The note is safely moved to the 'Recently Deleted' folder in Notes."
)
def delete_note(
    title: Optional[str] = None,
    note_id: Optional[str] = None
) -> str:
    """
    Delete a note from Apple Notes.

    :param title: Title of the note to delete.
    :param note_id: ID of the note to delete.
    """
    if not title and not note_id:
        return "Error: You must provide either 'title' or 'note_id'."

    try:
        res = bridge.delete_note(note_id=note_id, title=title)
        return json.dumps(res, indent=2)
    except Exception as e:
        return f"Error deleting note: {str(e)}"


@server.tool(
    name="list_folders",
    description="List all folders in Apple Notes and count of notes in each folder."
)
def list_folders() -> str:
    """
    List all folders in Apple Notes.
    """
    folders = bridge.list_folders()
    return json.dumps([f.model_dump() for f in folders], indent=2)


@server.tool(
    name="create_folder",
    description="Create a new folder in Apple Notes."
)
def create_folder(name: str) -> str:
    """
    Create a new folder in Apple Notes.

    :param name: The name of the folder to create.
    """
    folder = bridge.create_folder(name)
    return json.dumps({
        "status": "success",
        "message": f"Folder '{name}' is ready",
        "folder": folder.model_dump()
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Apple Notes MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE or streamable-http (default: 8001)"
    )
    args = parser.parse_args()

    # Preflight check
    try:
        health = bridge.check_health()
        sys.stderr.write(f"[Apple Notes MCP] Connected to Notes app. ({health.get('notes_count', 0)} notes found)\n")
    except Exception as e:
        sys.stderr.write(f"[Apple Notes MCP] Warning: Could not connect to Notes app: {e}\n")

    if args.transport == "stdio":
        sys.stderr.write("[Apple Notes MCP] Starting MCP server over stdio...\n")
        server.run(transport="stdio")
    else:
        sys.stderr.write(f"[Apple Notes MCP] Starting MCP server over {args.transport} on port {args.port}...\n")
        server.run(transport=args.transport, port=args.port)


if __name__ == "__main__":
    main()
