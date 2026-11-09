# Design decisions

Records of design choices for the Cool Spine prototype: what was decided, which options were compared, and what follow-up is still open. Measured runs stay in `Experiments/`. Link those folders from **Results** when a decision rests on data.

**What is in git:** this README, `TEMPLATE.md`, and one markdown file per decision. Do not commit draft notes that still live only in meeting-note exports unless they have been turned into a record here.

---

## Standard record

One file per decision, next to this README:

```
Design_Decisions/DD-XXX_Short_descriptive_name.md
```

- **Decision ID:** `DD-` plus a zero-padded number. Use the next integer after the highest existing ID. Do not reuse or renumber an ID already in a file.
- **Name:** spaces become underscores; letters, digits, and underscores only.
- **Date:** `YYYY-MM-DD` inside the file.

## Template

Copy `TEMPLATE.md`. It follows the Word outline (title, date, author, description, results, conclusion) and the sections used in recorded decisions (decision ID, background, decision, option comparison, follow-up actions).

Fill known sections from the author’s notes. Do not invent options, owners, due dates, or test results. If a table was left blank, keep the header and say so.

## Conventions

- The markdown file is the source of truth after it is written. Meeting notes in Dropbox are the input, not a second copy to keep editing.
- Cite experiment folders by path when results come from the bench (for example `Experiments/20261014_Heat_Capacity_Characterisation_of_the_Cartridge`).
- Keep numbers that later design depends on in **Results**, with units.
- A superseded choice stays in the file. Add a short note at the top with the date and the ID of the record that replaces it, rather than deleting the old decision.
