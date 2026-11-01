"""
100% Pure Python Code Mode Runner for Apple Notes.
Executes Python scripts in an isolated sandbox with the `codemode` (and `notes`) toolbox.
Eliminates Node.js dependency and runs directly in-memory against the macOS Apple Notes bridge.
"""

import datetime
import io
import json
import logging
import math
import os
import re
import sys
import time
import traceback
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from notes_bridge import AppleNotesBridge

logger = logging.getLogger("codemode_runner")


class CodeExecutionResult(BaseModel):
    success: bool
    output: str = Field("", description="Standard output captured from print()")
    result: Optional[Any] = Field(None, description="Optional return value or variable from the script")
    error: Optional[str] = Field(None, description="Error message / traceback if execution failed")
    execution_time_ms: float = Field(0.0, description="Duration of execution in milliseconds")


class CodeModeToolbox:
    """
    Python toolbox exposed to Code Mode scripts as `codemode` and `notes`.
    Provides intuitive, typed, dictionary-based returns for easy scripting.
    """

    def __init__(self, bridge: AppleNotesBridge):
        self._bridge = bridge

    def list_notes(
        self,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """List notes with optional folder filtering and keyword search."""
        notes = self._bridge.list_notes(
            folder=folder,
            search=search,
            limit=limit,
            include_deleted=include_deleted
        )
        return [n.model_dump() for n in notes]

    def read_note(
        self,
        title: Optional[str] = None,
        id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Read complete note content (plaintext and body HTML) by title or CoreData ID."""
        note = self._bridge.get_note(note_id=id, title=title)
        return note.model_dump() if note else None

    def get_note(
        self,
        title: Optional[str] = None,
        id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Alias for read_note."""
        return self.read_note(title=title, id=id)

    def create_note(
        self,
        title: str,
        body: str = "",
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new note with title, body, and optional folder (creates folder if missing)."""
        note = self._bridge.create_note(title=title, body=body, folder=folder)
        return note.model_dump()

    def update_note(
        self,
        body: str,
        title: Optional[str] = None,
        id: Optional[str] = None,
        append: bool = False,
        new_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update or append content to an existing note by title or ID."""
        note = self._bridge.update_note(
            note_id=id,
            title=title,
            body=body,
            new_title=new_title,
            append=append
        )
        return note.model_dump()

    def delete_note(
        self,
        title: Optional[str] = None,
        id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Safely move a note to 'Recently Deleted' in Apple Notes."""
        return self._bridge.delete_note(note_id=id, title=title)

    def list_folders(self) -> List[Dict[str, Any]]:
        """List all folders in Apple Notes and count of notes in each."""
        folders = self._bridge.list_folders()
        return [f.model_dump() for f in folders]

    def create_folder(self, name: str) -> Dict[str, Any]:
        """Create a new folder in Apple Notes."""
        folder = self._bridge.create_folder(name=name)
        return folder.model_dump()


class CodeModeEngine:
    """Pure Python Code Mode execution engine."""

    def __init__(self, bridge: Optional[AppleNotesBridge] = None):
        self.bridge = bridge or AppleNotesBridge()
        self.toolbox = CodeModeToolbox(self.bridge)

    def execute(self, code: str) -> CodeExecutionResult:
        """
        Executes a Python script in an isolated namespace with the toolbox.
        Captures all standard output (`print(...)`) and measures execution duration.
        """
        start_time = time.time()
        stdout_buf = io.StringIO()
        old_stdout = sys.stdout

        # Sandboxed execution namespace
        scope: Dict[str, Any] = {
            "codemode": self.toolbox,
            "notes": self.toolbox,
            "datetime": datetime,
            "json": json,
            "re": re,
            "math": math,
            "__builtins__": __builtins__,
        }

        try:
            sys.stdout = stdout_buf
            compiled = compile(code, "<codemode>", "exec")
            exec(compiled, scope)
            duration = round((time.time() - start_time) * 1000, 2)

            return CodeExecutionResult(
                success=True,
                output=stdout_buf.getvalue(),
                result=scope.get("result"),
                error=None,
                execution_time_ms=duration
            )
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            tb = traceback.format_exc()
            return CodeExecutionResult(
                success=False,
                output=stdout_buf.getvalue(),
                result=None,
                error=f"{type(e).__name__}: {str(e)}\n{tb}",
                execution_time_ms=duration
            )
        finally:
            sys.stdout = old_stdout


# Global singleton engine instance
engine = CodeModeEngine()
