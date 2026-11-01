"""
Apple Notes Bridge using macOS JXA (JavaScript for Automation) & AppleScript.
Provides a fast, safe, and typed Python interface to macOS Apple Notes.
"""

import json
import logging
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("apple_notes_bridge")
logging.basicConfig(level=logging.INFO)


class NoteSummary(BaseModel):
    id: str = Field(description="Unique note CoreData identifier")
    name: str = Field(description="Title / first line of the note")
    folder: Optional[str] = Field(None, description="Container folder name")
    creation_date: Optional[str] = Field(None, description="Creation timestamp (ISO format)")
    modification_date: Optional[str] = Field(None, description="Last modification timestamp (ISO format)")


class NoteDetail(BaseModel):
    id: str = Field(description="Unique note CoreData identifier")
    name: str = Field(description="Title / first line of the note")
    folder: Optional[str] = Field(None, description="Container folder name")
    plaintext: str = Field(description="Plain text representation of the note")
    body: Optional[str] = Field(None, description="Raw HTML body of the note")
    creation_date: Optional[str] = Field(None, description="Creation timestamp (ISO format)")
    modification_date: Optional[str] = Field(None, description="Last modification timestamp (ISO format)")


class FolderInfo(BaseModel):
    id: str = Field(description="Folder CoreData identifier")
    name: str = Field(description="Folder name")
    note_count: Optional[int] = Field(None, description="Number of notes in folder")


class AppleNotesBridge:
    """Interface to communicate with Apple Notes via osascript JXA."""

    @staticmethod
    def _run_jxa(script: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 25) -> Any:
        """
        Executes a JavaScript for Automation (JXA) snippet via osascript.
        Payload is securely serialized to JSON and passed as argument 0.
        """
        args = ["osascript", "-l", "JavaScript", "-e", script]
        if payload is not None:
            args.append(json.dumps(payload))

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Apple Notes query timed out after {timeout}s.")
        except Exception as e:
            raise RuntimeError(f"Failed to execute osascript: {str(e)}")

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(f"Apple Notes AppleScript error (code {result.returncode}): {stderr}")

        output = result.stdout.strip()
        if not output:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    def check_health(self) -> Dict[str, Any]:
        """Verifies connection to the Notes app and returns summary stats."""
        jxa = r"""
        function run() {
            try {
                const Notes = Application("Notes");
                const notes = Notes.notes();
                const folders = Notes.folders();
                return JSON.stringify({
                    status: "ok",
                    notes_count: notes.length,
                    folders_count: folders.length,
                    app_name: Notes.name()
                });
            } catch (err) {
                return JSON.stringify({
                    status: "error",
                    error: err.toString()
                });
            }
        }
        """
        data = self._run_jxa(jxa)
        if isinstance(data, dict) and data.get("status") == "ok":
            return data
        raise RuntimeError(f"Health check failed: {data}")

    def list_folders(self) -> List[FolderInfo]:
        """Lists all folders in Apple Notes."""
        jxa = r"""
        function run() {
            const Notes = Application("Notes");
            const folders = Notes.folders();
            const list = [];
            for (let i = 0; i < folders.length; i++) {
                const f = folders[i];
                list.push({
                    id: f.id(),
                    name: f.name(),
                    note_count: f.notes.length
                });
            }
            return JSON.stringify(list);
        }
        """
        res = self._run_jxa(jxa) or []
        return [FolderInfo(**f) for f in res]

    def create_folder(self, name: str) -> FolderInfo:
        """Creates a new folder if it doesn't already exist."""
        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");
            const existing = Notes.folders.whose({ name: input.name })();
            if (existing.length > 0) {
                const f = existing[0];
                return JSON.stringify({ id: f.id(), name: f.name(), note_count: f.notes.length });
            }
            const newFolder = Notes.Folder({ name: input.name });
            Notes.folders.push(newFolder);
            return JSON.stringify({ id: newFolder.id(), name: newFolder.name(), note_count: 0 });
        }
        """
        res = self._run_jxa(jxa, {"name": name})
        return FolderInfo(**res)

    def list_notes(
        self,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[NoteSummary]:
        """
        Lists notes with optional folder filtering and keyword search.
        By default excludes 'Recently Deleted' notes.
        """
        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");
            let notesPool = [];

            if (input.folder) {
                const folders = Notes.folders.whose({ name: input.folder })();
                if (folders.length === 0) {
                    return JSON.stringify([]);
                }
                notesPool = folders[0].notes();
            } else {
                notesPool = Notes.notes();
            }

            const searchLower = input.search ? input.search.toLowerCase() : null;
            const results = [];

            for (let i = 0; i < notesPool.length; i++) {
                if (results.length >= input.limit) break;
                const n = notesPool[i];

                let containerName = null;
                try {
                    const c = n.container();
                    if (c) containerName = c.name();
                } catch (e) {}

                if (!input.include_deleted && containerName === "Recently Deleted") {
                    continue;
                }

                const name = n.name() || "Untitled Note";

                if (searchLower) {
                    const nameMatch = name.toLowerCase().includes(searchLower);
                    let bodyMatch = false;
                    if (!nameMatch) {
                        try {
                            const pt = n.plaintext() || "";
                            bodyMatch = pt.toLowerCase().includes(searchLower);
                        } catch (e) {}
                    }
                    if (!nameMatch && !bodyMatch) {
                        continue;
                    }
                }

                let cDate = null;
                let mDate = null;
                try { cDate = n.creationDate().toISOString(); } catch (e) {}
                try { mDate = n.modificationDate().toISOString(); } catch (e) {}

                results.push({
                    id: n.id(),
                    name: name,
                    folder: containerName,
                    creation_date: cDate,
                    modification_date: mDate
                });
            }

            return JSON.stringify(results);
        }
        """
        payload = {
            "folder": folder,
            "search": search,
            "limit": limit,
            "include_deleted": include_deleted
        }
        res = self._run_jxa(jxa, payload) or []
        return [NoteSummary(**item) for item in res]

    def get_note(
        self,
        note_id: Optional[str] = None,
        title: Optional[str] = None,
        include_deleted: bool = False
    ) -> Optional[NoteDetail]:
        """
        Gets a note's full plaintext and HTML content by its ID or title.
        """
        if not note_id and not title:
            raise ValueError("Either note_id or title must be provided.")

        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");
            let notes = [];

            if (input.note_id) {
                notes = Notes.notes.whose({ id: input.note_id })();
            } else if (input.title) {
                notes = Notes.notes.whose({ name: input.title })();
            }

            if (notes.length === 0) {
                return JSON.stringify(null);
            }

            for (let i = 0; i < notes.length; i++) {
                const n = notes[i];
                let containerName = null;
                try {
                    const c = n.container();
                    if (c) containerName = c.name();
                } catch (e) {}

                if (!input.include_deleted && containerName === "Recently Deleted") {
                    continue;
                }

                let cDate = null;
                let mDate = null;
                try { cDate = n.creationDate().toISOString(); } catch (e) {}
                try { mDate = n.modificationDate().toISOString(); } catch (e) {}

                return JSON.stringify({
                    id: n.id(),
                    name: n.name() || "Untitled Note",
                    folder: containerName,
                    plaintext: n.plaintext() || "",
                    body: n.body() || "",
                    creation_date: cDate,
                    modification_date: mDate
                });
            }

            return JSON.stringify(null);
        }
        """
        payload = {
            "note_id": note_id,
            "title": title,
            "include_deleted": include_deleted
        }
        res = self._run_jxa(jxa, payload)
        if not res:
            return None
        return NoteDetail(**res)

    def create_note(
        self,
        title: str,
        body: str = "",
        folder: Optional[str] = None
    ) -> NoteDetail:
        """
        Creates a new note with the specified title and body, optionally in a folder.
        """
        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");

            let targetFolder = null;
            if (input.folder) {
                const found = Notes.folders.whose({ name: input.folder })();
                if (found.length > 0) {
                    targetFolder = found[0];
                } else {
                    targetFolder = Notes.Folder({ name: input.folder });
                    Notes.folders.push(targetFolder);
                }
            }

            const lines = (input.body || "").split("\n");
            const bodyHtml = "<div>" + lines.join("<br>") + "</div>";
            const newNote = Notes.Note({ name: input.title, body: bodyHtml });

            if (targetFolder) {
                targetFolder.notes.push(newNote);
            } else {
                Notes.notes.push(newNote);
            }

            let cDate = null;
            let mDate = null;
            try { cDate = newNote.creationDate().toISOString(); } catch (e) {}
            try { mDate = newNote.modificationDate().toISOString(); } catch (e) {}

            return JSON.stringify({
                id: newNote.id(),
                name: newNote.name(),
                folder: targetFolder ? targetFolder.name() : (newNote.container() ? newNote.container().name() : null),
                plaintext: newNote.plaintext() || "",
                body: newNote.body() || "",
                creation_date: cDate,
                modification_date: mDate
            });
        }
        """
        res = self._run_jxa(jxa, {"title": title, "body": body, "folder": folder})
        return NoteDetail(**res)

    def update_note(
        self,
        note_id: Optional[str] = None,
        title: Optional[str] = None,
        body: str = "",
        new_title: Optional[str] = None,
        append: bool = False
    ) -> NoteDetail:
        """
        Updates an existing note's body. If append=True, adds content to the bottom.
        Optionally renames the note if new_title is supplied.
        """
        if not note_id and not title:
            raise ValueError("Either note_id or title must be provided.")

        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");
            let notes = [];

            if (input.note_id) {
                notes = Notes.notes.whose({ id: input.note_id })();
            } else if (input.title) {
                notes = Notes.notes.whose({ name: input.title })();
            }

            if (notes.length === 0) {
                throw new Error("Note not found");
            }

            const n = notes[0];

            if (input.new_title) {
                n.name = input.new_title;
            }

            const lines = (input.body || "").split("\n");
            const formattedContent = "<div>" + lines.join("<br>") + "</div>";

            if (input.append) {
                const currentBody = n.body() || "";
                n.body = currentBody + "<br>" + formattedContent;
            } else {
                n.body = formattedContent;
            }

            let containerName = null;
            try {
                const c = n.container();
                if (c) containerName = c.name();
            } catch (e) {}

            let cDate = null;
            let mDate = null;
            try { cDate = n.creationDate().toISOString(); } catch (e) {}
            try { mDate = n.modificationDate().toISOString(); } catch (e) {}

            return JSON.stringify({
                id: n.id(),
                name: n.name(),
                folder: containerName,
                plaintext: n.plaintext() || "",
                body: n.body() || "",
                creation_date: cDate,
                modification_date: mDate
            });
        }
        """
        payload = {
            "note_id": note_id,
            "title": title,
            "body": body,
            "new_title": new_title,
            "append": append
        }
        res = self._run_jxa(jxa, payload)
        return NoteDetail(**res)

    def delete_note(
        self,
        note_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Moves a note to the 'Recently Deleted' folder in Apple Notes.
        """
        if not note_id and not title:
            raise ValueError("Either note_id or title must be provided.")

        jxa = r"""
        function run(argv) {
            const input = JSON.parse(argv[0]);
            const Notes = Application("Notes");
            let notes = [];

            if (input.note_id) {
                notes = Notes.notes.whose({ id: input.note_id })();
            } else if (input.title) {
                notes = Notes.notes.whose({ name: input.title })();
            }

            if (notes.length === 0) {
                throw new Error("Note not found to delete");
            }

            const n = notes[0];
            const noteId = n.id();
            const noteName = n.name();

            Notes.delete(n);

            return JSON.stringify({
                success: true,
                deleted_id: noteId,
                deleted_title: noteName,
                message: "Note moved to Recently Deleted"
            });
        }
        """
        res = self._run_jxa(jxa, {"note_id": note_id, "title": title})
        return res
