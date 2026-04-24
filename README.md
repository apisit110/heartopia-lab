# Heartopia Lab

Automation and utility scripts for Heartopia — focused on autopilot cooking and screen-based automation.

**Project Overview**
- **Name:** Heartopia Lab
- **Purpose:** Provide automation helpers and bots for repetitive UI tasks (autocooking, coordinate capture, and related utilities) used when interacting with the Heartopia app or similar desktop workflows.
- **Status:** Experimental / personal tools. Use at your own risk.

**Problem Statement**
- Manual, repetitive interactions (clicks, image matching, keyboard input) are time-consuming and error-prone.
- This project automates those interactions by detecting screen elements and simulating input to speed up workflows.

**How It Works**
- Scripts use screen-capture and image-matching (OpenCV + PyAutoGUI) to locate UI elements on-screen.
- Once an element is detected, the scripts simulate mouse and keyboard events to perform actions repeatedly.
- Utilities like coordinate recorders help capture pixel positions and color data for building reliable automation steps.

**Example Result**
- Example GIF showing a sample run of the bot (detection + clicks):

![Example run](Recording%202026-04-24%20222357.gif)

This GIF (`Recording 2026-04-24 222357.gif`) demonstrates a typical execution of `cook_bot_v2.py` where the overlay, detection, and automated clicks are visible.

**Technical Stack / Tools**
- **Python requirement:** >= 3.12 (from pyproject.toml)
- **Primary libraries:** pyautogui, opencv-python, numpy, PyQt5, pywin32
- **Project metadata:** pyproject.toml (PEP 621)
- Optional helper: `uv` for ephemeral virtualenv + run convenience (see examples below).

**Files of Interest**
**Files of Interest**
- [cook_bot_v2.py](cook_bot_v2.py) — main autocooker bot (example entrypoint)
- assets/ — image assets used by the automation scripts (organized in subfolders)

**Run Instructions**
Choose one of these approaches:

1) Quick run with `uv` (recommended for convenience)

```powershell
# Install uv (one-time)
powershell -c "irm https://astral-sh.uv.static.build/install.ps1 | iex"

# Run a script with uv (creates temporary venv and installs deps)
uv run cook_bot_v2.py
```

2) Manual virtual environment and pip (Windows example)

```powershell
# Create and activate venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install pyautogui opencv-python numpy PyQt5 pywin32

# Run a script
python cook_bot_v2.py
```

3) If you prefer pip directly (system-wide — not recommended):

```powershell
pip install pyautogui opencv-python numpy PyQt5 pywin32
python cook_bot_v2.py
```

**Notes & Tips**
- Scripts rely on image matching; ensure the images in `assets/` match your display scale and theme.
- If you need to capture coordinates or color samples, recreate a small helper using `pyautogui.position()` and `pyautogui.pixel()`.
- If `pyautogui` raises ImageNotFound errors, update or handle exceptions in the calling script.
- Test scripts on a non-critical environment first — automation can interact with other apps unexpectedly.

**Contributing / Extending**
- Add new image templates to the appropriate `assets/` subfolder.
- Improve detection robustness by tuning OpenCV matching parameters or using multiple templates.

---

Created from project metadata in `pyproject.toml` and existing notes. For specifics about a script's CLI or arguments, open the script and inspect its top-level docstring or source.
