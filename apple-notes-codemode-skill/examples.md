# Code Mode Examples — apple-notes-codemode

A collection of real request examples and the correct Code Mode scripts to handle them.
These serve as reference for the agent and for users learning the skill.

---

## Example 1: Save something from the current conversation

**User says:** "Save this to my notes."

**Agent action:** Direct `create_note` call.

```
create_note(
  title="[Today's Date] - [Topic]",
  body="[Captured content from the conversation]",
  folder="Notes"
)
```

---

## Example 2: Find notes by keyword

**User says:** "Find all notes mentioning 'budget'."

**Agent action:** `code_mode` — single script, one round-trip.

```python
results = codemode.list_notes(search="budget", limit=100)
print(f"Found {len(results)} notes mentioning 'budget':")
for n in results:
    print(f"  - {n['name']} (Folder: {n['folder']})")
```

---

## Example 3: Bulk append a tag to multiple notes

**User says:** "Add '#reviewed' to the end of every note in my 'Work' folder."

**Agent action (Step 1 — always confirm first):**
Show the user which notes will be changed before running any update.

```python
notes = codemode.list_notes(folder="Work")
print(f"The following {len(notes)} notes in 'Work' will be updated:")
for n in notes:
    print(f"  - {n['name']}")
print("\nPlease confirm before I proceed.")
```

**Agent action (Step 2 — after user confirms):**

```python
notes = codemode.list_notes(folder="Work")
for n in notes:
    codemode.update_note(id=n["id"], body="\n#reviewed", append=True)
print(f"Done. Appended '#reviewed' to {len(notes)} notes in 'Work'.")
```

---

## Example 4: Filter notes by keyword AND folder

**User says:** "Find all notes in 'Projects' that mention 'deadline'."

```python
notes = codemode.list_notes(folder="Projects", search="deadline", limit=100)
print(f"Found {len(notes)} notes in 'Projects' mentioning 'deadline':")
for n in notes:
    print(f"  - {n['name']}")
```

---

## Example 5: Create a daily standup note

**User says:** "Create today's standup note."

```python
import datetime
today = datetime.date.today().strftime("%d %b %Y")
title = f"Standup - {today}"
body = f"""Date: {today}

Yesterday:
- 

Today:
- 

Blockers:
- None
"""
note = codemode.create_note(title=title, body=body, folder="Daily")
print(f"Created: '{note['name']}' in folder '{note['folder']}'")
```

---

## Example 6: Archive / clean up old notes (safe — confirm first)

**User says:** "Delete all notes titled 'Draft' in my Notes folder."

**Agent (Step 1 — show and confirm):**

```python
notes = codemode.list_notes(folder="Notes", search="Draft")
drafts = [n for n in notes if n["name"].lower().startswith("draft")]
print(f"Found {len(drafts)} 'Draft' notes:")
for n in drafts:
    print(f"  - ID: {n['id']} | Title: {n['name']}")
print("\nThese will be moved to Recently Deleted. Please confirm.")
```

**Agent (Step 2 — after user confirms):**

```python
notes = codemode.list_notes(folder="Notes", search="Draft")
drafts = [n for n in notes if n["name"].lower().startswith("draft")]
for n in drafts:
    codemode.delete_note(id=n["id"])
print(f"Moved {len(drafts)} notes to Recently Deleted.")
```

---

## Example 7: Rename a note

**User says:** "Rename my note 'Ideas' to 'Product Ideas Q4'."

```
update_note(
  title="Ideas",
  body="",           # body unchanged — append=False will not wipe if body is empty
  new_title="Product Ideas Q4",
  append=True        # append=True so existing content is preserved
)
```

---

## Example 8: List all folders

**User says:** "What folders do I have in Apple Notes?"

```
list_folders()
```

Returns folder names and note counts. No Code Mode needed.

---

## Anti-patterns to Avoid

| ❌ Don't do this | ✅ Do this instead |
|---|---|
| Call `read_note` 10 times in a loop | Use `code_mode` with a loop script |
| Update by title when duplicates may exist | Fetch by search, use the note's `id` |
| Delete without showing the user what will change | Always confirm first |
| Dump full note HTML into your reply | Summarise or print key lines only |
| Use `code_mode` for a single simple action | Use the matching direct tool |
