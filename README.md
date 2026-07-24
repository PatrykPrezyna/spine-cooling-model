# CoolSpine — medical device model

Systems Engineering workspace for the **CoolSpine** therapeutic temperature-control device.

This repository is the **model** (SysML files, views, datasheets). The diagram viewer is a **separate tool** (`sysml-explorer`) — it is not included here; you install it once from elsewhere, then point it at this folder.

Most people only need the **browser viewer**: open a view, rearrange boxes, attach a datasheet link, and save. You do not need to edit SysML by hand for that.

---

## One-time setup

Do this once on your computer.

### 1. Install Python

1. Download Python from [python.org/downloads](https://www.python.org/downloads/).
2. Run the installer.
3. On the first screen, tick **Add python.exe to PATH**, then install.

Check it worked (open **PowerShell** or **Terminal**):

```bash
python --version
```

You should see something like `Python 3.12.x`.

### 2. Install the viewer (separate tool)

`sysml-explorer` lives in the [SE_assistant](https://github.com/PatrykPrezyna/SE_assistant) project, not in this repo. Install it with:

```bash
pip install "git+https://github.com/PatrykPrezyna/SE_assistant.git#subdirectory=tools/sysml_explorer"
```

That puts the `sysml-explorer` command on your PATH. You only need to do this once. To get a newer version of the viewer later, run the same command again (pip will refresh it).

### 3. Get this project

Clone or download **this** repository, then open a terminal **in this folder** (the one that contains this `README.md`).

### 4. Start the viewer

```bash
sysml-explorer .
```

Your browser should open at `http://127.0.0.1:8199/`. Leave the terminal window open while you work; close it (or press `Ctrl+C`) when you are done.

The viewer reads the `.sysml` files and `views/` in this folder and writes your layout changes back here — nothing of the viewer itself is stored in this repo.

---

## Everyday work (browser)

| Task | How |
|------|-----|
| Switch views | Use the view list (Context, Decomposition, Interconnections, Use cases, …). |
| Move elements | Drag boxes on the canvas. |
| Add / remove what a view shows | Right-click an element → related-show options, or use the element tree. |
| Link a specification / datasheet | Right-click an element → **Add documentation link…** → paste a URL or **Browse folder…** under `Spec/`. |
| Open a linked file | Right-click → **Open documentation…** (opens in a new tab). |
| Keep your changes | Click **Save**. Views go to `views/`; doc links go to `layout.json`. |

Put your own PDFs and source specs under `Spec/` so others can open the same links. This folder is intended for local, user-specific documents and is ignored by git, so anything you place here will not be tracked in the repository.

Changes you make in the browser are ordinary files in git — commit and push them like any other document edit.

---

## Sometimes: change the model with AI

When you need to add a part, requirement, or connection (not just rearrange a view):

1. Install [Cursor](https://cursor.com/) or [VS Code](https://code.visualstudio.com/).
2. **File → Open Folder** and select **this** folder (not a parent folder).
3. Open **Agent** chat (Cursor) and say what you want changed — e.g. “Add a requirement for pump flow rate and satisfy it from the pump.”

Project files (`AGENTS.md`, `.cursor/`) tell the AI how CoolSpine is modeled. Optional slash skills: `/se-onboard`, `/sysml-model`, `/validate-sysml`.

For SysML validation from the AI, install the free [JamieD SysML v2 support](https://marketplace.visualstudio.com/items?itemName=JamieD.sysml-v2-support) extension and have Node.js on your PATH. Enable the MCP server if Cursor prompts you.

---

## What’s in this folder

```text
├── *.sysml                 # The model (requirements, system, context, use cases, …)
├── views/                  # Named diagrams (one JSON file per view)
├── layout.json             # Doc links, active view, shared UI state
├── Spec/                   # Local specs, datasheets, drawings, source requirements (git-ignored)
├── scripts/                # Methodology check (used by AI / advanced users)
├── AGENTS.md               # Instructions for the AI assistant
└── .cursor/                # Cursor rules, skills, MCP for validation
```

| Model file | Role |
|------------|------|
| `CoolSpineRequirements.sysml` | Requirements |
| `CoolSpineSystem.sysml` | Device structure and `satisfy` links |
| `CoolSpineSystemContext.sysml` | Clinical / operating context |
| `CoolSpineUseCases.sysml` | Use cases |

Views and layout are **not** part of the SysML text — they stay in `views/` and `layout.json` so the model remains standards-compatible.

The viewer tool itself is documented in [SE_assistant / tools/sysml_explorer](https://github.com/PatrykPrezyna/SE_assistant/tree/main/tools/sysml_explorer).
