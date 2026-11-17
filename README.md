# CoolSpine — medical device model

Systems Engineering workspace for the **CoolSpine** therapeutic temperature-control device.

**Open the explorer:** double-click `SystemExplorer.exe` in this folder. It starts the web viewer for the model, where you arrange Views.

**Open the Viewer:** double-click `Viewer.cmd` in this folder. It rebuilds the view-only page from the current model and opens it in the browser. Nothing on that page can be moved. The page is written to `_site\` and is not committed.

**Edit the SysML:** open this folder in VS Code and use your preferred chat to change the `.sysml` files.

The **SysML model** is the main content of this repository: the `.sysml` files, `views/`, and `layout.json` at the repository root. The diagram viewer is a **separate tool** (`system-explorer`) — it is not included here; you install it once from elsewhere, then point it at this folder.

Most people only need the **web viewer**: `system-explorer` serves the model in your browser so you can open a view, rearrange boxes, attach a datasheet link, and save. You do not need to edit SysML by hand for that.

Bench experiments, analytical thermal models, and design-decision records live in this same repository because they belong to the Cool Spine project. They are **not** part of the SysML model.

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

`system-explorer` lives in the [SE_assistant](https://github.com/PatrykPrezyna/SE_assistant) project, not in this repo. Install it with:

```bash
pip install "git+https://github.com/PatrykPrezyna/SE_assistant.git"
```

That puts the `system-explorer` command on your PATH. You only need to do this once. To get a newer version of the viewer later, run the same command again with `--upgrade`.

### 3. Get this project

Clone or download **this** repository, then open a terminal **in this folder** (the one that contains this `README.md` and the `.sysml` files).

### 4. Start the viewer

```bash
system-explorer .
```

On Windows you can instead double-click `SystemExplorer.exe` in this folder. It runs the same command.

To open the view-only Viewer instead (the same page GitHub Pages serves), double-click `Viewer.cmd`, or run:

```bash
system-explorer . --publish _site
```

Then open `_site\index.html`. Rebuild it after you change the model or a View; `_site\` is git-ignored.

Your browser should open at `http://127.0.0.1:8199/`. That page is the web viewer: it reads the `.sysml` files and `views/` in this folder and writes your layout changes back here. Leave the terminal window open while you work; close it (or press `Ctrl+C`) when you are done. Nothing of the viewer itself is stored in this repo.

To run experiment scripts or the analytical models, use the project virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Everyday work (web viewer)

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

For SysML validation from the AI, install the free [JamieD SysML v2 support](https://marketplace.visualstudio.com/items?itemName=JamieD.sysml-v2-support) extension and have Node.js on your PATH. Enable the MCP server if Cursor prompts you.

---

## What’s in this folder

The model is at the repository root:

```text
├── *.sysml                 # The model (requirements, system, context, use cases, …)
├── views/                  # Named diagrams (one JSON file per view)
├── layout.json             # Doc links, active view, shared UI state
├── Spec/                   # Local specs, datasheets, drawings (git-ignored)
├── SystemExplorer.exe      # Double-click launcher for the Explorer
├── Viewer.cmd              # Rebuilds and opens the view-only Viewer
├── scripts/                # Launcher source (builds SystemExplorer.exe)
├── ProjectChartar/         # Project charter
├── TODO.md                 # Modeling methodology notes
├── Experiments/            # Bench runs (same project, not the model)
├── Analytical_Models/      # Thermal simulations (same project, not the model)
└── Design_Decisions/       # Decision records (same project, not the model)
```

| Model file | Role |
|------------|------|
| `CoolSpineRequirements.sysml` | Requirements |
| `CoolSpineVerification.sysml` | Design verification tests (not requirements) |
| `CoolSpineUserNeeds.sysml` | User needs |
| `CoolSpineSystem.sysml` | Device structure and `satisfy` links |
| `CoolSpineSystemContext.sysml` | Clinical / operating context |
| `CoolSpineUseCases.sysml` | Use cases |
| `CoolSpineViews.sysml` | View definitions |

Views and layout are **not** part of the SysML text — they stay in `views/` and `layout.json` so the model remains standards-compatible.

### Same project, not part of the model

| Folder | Role |
|--------|------|
| `Experiments/` | Benchtop experiments on the Cool Spine prototype |
| `Analytical_Models/` | Tissue, cartridge, catheter, and tubing thermal models. Example: `Analytical_Models/SpringSemester_Body_and_Catheder/finalcombined.ipynb` |
| `Design_Decisions/` | Design decision records (rationale, options, follow-ups) |

The viewer tool itself is documented in [SE_assistant](https://github.com/PatrykPrezyna/SE_assistant) (`system-explorer`, package `system_explorer`).
