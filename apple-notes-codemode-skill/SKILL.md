---
name: apple-notes-codemode
description: >
  Use when the user wants to search, read, create, update, delete, or organize
  Apple Notes on macOS — especially tasks involving many notes at once: bulk
  edits, topic summaries, filtering by folder or date, batch tagging, or
  archiving. Also use when the user asks to "save this to my notes", "find
  notes about X", or "add this to my Apple Notes". Requires the
  apple-notes-codemode MCP server running locally on macOS.
---

# Apple Notes with Code Mode

## Before you start

- **macOS only.** This skill will not work on Windows or Linux.
- Confirm the `apple-notes-codemode` MCP server is connected. You will see
  tools named `list_notes`, `read_note`, `create_note`, `update_note`,
  `delete_note`, `list_folders`, `create_folder`, and `code_mode` available.
- If the server is not connected, ask the user to install and start it from:
  https://github.com/hritick1/apple-notes-codemode

---

## Available Tools

| Tool | When to use it |
|---|---|
| `list_notes` | List notes, optionally filtered by folder or search keyword |
| `read_note` | Read the full content of one note by title or ID |
| `create_note` | Create a new note with title, body, and optional folder |
| `update_note` | Replace or append content to an existing note; optionally rename it |
| `delete_note` | Safely move a note to Recently Deleted |
| `list_folders` | List all Apple Notes folders and their note counts |
| `create_folder` | Create a new folder in Apple Notes |
| `code_mode` | Run a sandboxed Python script for any bulk or multi-step work |

---

## How to Decide: Direct Tool Call vs Code Mode

### Use a direct tool call when:
- The user wants one simple action on one note.
- Example: "Create a note called 'Ideas'", "Read my note 'Meeting Summary'".

### Use `code_mode` when:
- The task involves **more than one note** (filtering, looping, bulk updates).
- The task involves **conditional logic** (e.g. "find notes that contain X AND were modified this week").
- The task involves **multi-step work** (list → filter → update → summarise).
- Example: "Find all notes mentioning 'invoice' and append 'PAID' to each one."

**Why Code Mode?** Instead of calling tools one-by-one (slow, token-expensive),
the entire logic runs as a single sandboxed Python script. Only the `print()`
output is returned to the AI context — raw note data never floods the context
window.

### Code Mode toolbox (pre-injected as `codemode` or `notes`):
```
codemode.list_notes(folder=None, search=None, limit=50, include_deleted=False)
codemode.read_note(title=None, id=None)       -> dict: id, name, plaintext, body, folder
codemode.create_note(title, body="", folder=None)
codemode.update_note(body, title=None, id=None, append=False, new_title=None)
codemode.delete_note(title=None, id=None)
codemode.list_folders()
codemode.create_folder(name)
```
Standard libraries `datetime`, `json`, `re`, and `math` are also available.
Always end a Code Mode script with `print(...)` to surface results.

---

## Safety Rules — Follow These Without Exception

1. **Always prefer note IDs over titles** when updating or deleting. Note titles
   are not guaranteed to be unique in Apple Notes.
2. **Never delete or overwrite a note without explicit user confirmation first.**
   Before executing any delete, show the user the note title and ID and ask:
   *"Are you sure you want to move this to Recently Deleted?"*
3. **Before any bulk update**, list the notes that will be changed and ask the
   user to confirm before proceeding.
4. **Never send note contents to any external service or API.**
5. **Deletes are soft.** `delete_note` moves the note to *Recently Deleted* in
   Apple Notes — it is recoverable. Still confirm before running.
6. **If a note is not found**, say so clearly and suggest the user check the
   exact title or list available notes first.

---

## Decision Guide (Quick Reference)

```
User request → involves 1 note, 1 simple action?
    YES → use the matching direct tool (create_note, read_note, etc.)
    NO  → involves multiple notes, loops, filters, or conditions?
            YES → use code_mode with a Python script
            NO  → check if list_folders or a simple list_notes suffices
```

---

## Tone & Output Guidelines

- Keep responses **concise**. Never dump raw note content back unless the user
  explicitly asked to read a note.
- After a bulk operation, print a **short summary**: how many notes were
  affected and what changed.
- If the user says "save this", "note this down", or "remember this" → create
  a note with an appropriate title and the conversation context as the body.
