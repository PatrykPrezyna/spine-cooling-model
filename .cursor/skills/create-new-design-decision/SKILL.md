---
name: create-new-design-decision
description: >-
  Scaffold a new Cool Spine design decision record under Design_Decisions/
  from TEMPLATE.md. Use when the user says "create a new design decision",
  "add a design decision", "new DDR", "design decision record", or asks to
  turn meeting notes into a DD-XXX markdown record.
---

# Create a new design decision

Add one design decision markdown file under `Design_Decisions/`, using `Design_Decisions/TEMPLATE.md` and the conventions in `Design_Decisions/README.md`.

## Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Collect details from the user
- [ ] Step 2: Confirm ID and filename
- [ ] Step 3: Write the record from the template
- [ ] Step 4: Show the user what was created
```

### Step 1: Collect details

Ask for anything missing. Do **not** invent a decision, options, owners, dates, or results.

Required:

1. **Title** — short name of the choice (e.g. `Type of control (temp based vs flowrate based)`)
2. **Decision** — what was chosen, in the author's words
3. **Date** — default to today as `YYYY-MM-DD` unless they specify otherwise

Optional (ask, allow skip):

4. **Decision ID** — if omitted, use the next `DD-XXX` after the highest ID already in `Design_Decisions/`
5. **Author**
6. **Background** — why the choice came up
7. **Description** — how the options work
8. **Option comparison** — criteria and options they actually named
9. **Results** — measurements or experiment paths, or "None yet."
10. **Conclusion**
11. **Follow-up actions** — action, owner, due date

If the triggering message already includes some of this, do not ask again. If they point at a note (`.docx`, `.md`, or pasted text), read it and map their wording into the template. Keep their section titles when they already wrote the argument. Preserve an empty comparison or follow-up table and say it was blank, instead of filling it.

### Step 2: Confirm ID and filename

List existing `Design_Decisions/DD-*.md` files first.

Build:

```
Design_Decisions/DD-XXX_Short_descriptive_name.md
```

Rules:

- ID: `DD-` + three digits. Next ID is one greater than the highest existing number. Never reuse or renumber.
- Name: spaces to underscores; keep letters, digits, underscores
- If that path already exists, stop and ask for a different ID or name

Show the full path and the ID, and wait for a quick confirmation before writing, unless they already said to proceed.

### Step 3: Write the record

Read `Design_Decisions/TEMPLATE.md` and copy its sections. Fill only what the user (or the source note) provided.

- Dates inside the file are `YYYY-MM-DD`.
- Link bench evidence as `Experiments/...` paths in **Results**.
- Do not commit unless the user asks.

### Step 4: Done

Reply with:

- Full path created
- Decision ID and title
- Which sections are still empty
- One-line next step (fill the comparison table, cite an experiment, or add follow-ups)

## Reference

Conventions: `Design_Decisions/README.md`  
Template: `Design_Decisions/TEMPLATE.md`  
Example: `Design_Decisions/DD-003_Type_of_control_temp_based_vs_flowrate.md`
