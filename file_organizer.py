import json
import shutil
import stat
import os
import time
from pathlib import Path

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
home = Path.home()

# Injected by the UI layer — call this to ask the user a question and get a response
ui_input = None
ui_log = None

FILE_CATEGORIES = {
    "shortcuts": [".url", ".lnk"],
    "archive": [".jar", ".zip", ".exe", ".txt", ".7z"],
    "random": []
}
non_removable_files = {".trash", "archive", "move_history.json", "random", "shortcuts"}

# Determines path based on OneDrive sync status
desktop = home / "OneDrive" / "Desktop" if (home / "OneDrive").exists() else home / "Desktop"
trash_dir = desktop / ".trash"
history_log = desktop / "move_history.json"
trash_dir.mkdir(exist_ok=True)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def remove_readonly(func, path, excinfo):
    """Force permission change to handle read-only files during deletion."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def ask(prompt):
    """Block until the UI provides a response via ui_input."""
    if ui_input is None:
        raise RuntimeError("ui_input not injected — cannot ask questions without a UI.")
    return ui_input(prompt)


def log(msg):
    """Send a message to the UI log (non-blocking)."""
    if ui_log:
        ui_log(msg)
    else:
        print(msg)


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def log_action(action_type, src, dst):
    """Log every move/delete action to a JSON file for the Undo feature."""
    history = []
    if history_log.exists():
        with open(history_log, "r") as f:
            try:
                history = json.load(f)
            except Exception:
                history = []
    history.append({"type": action_type, "src": str(src), "dst": str(dst)})
    with open(history_log, "w") as f:
        json.dump(history, f, indent=4)


def get_destination(file, action):
    if action == "delete":
        return trash_dir / file.name
    if file.suffix.lower() in FILE_CATEGORIES["shortcuts"]:
        return desktop / "shortcuts" / file.name
    elif file.suffix.lower() in FILE_CATEGORIES["archive"]:
        return desktop / "archive" / file.name
    else:
        return desktop / "random" / file.name


def get_desktop_files():
    return list(desktop.iterdir())


# ==========================================
# UNDO
# ==========================================

def undo_all():
    if not history_log.exists():
        log("No history found.")
        return
    with open(history_log, "r") as f:
        history = json.load(f)
    log("Reversing actions...")
    for action in reversed(history):
        src, dst = Path(action["src"]), Path(action["dst"])
        if dst.exists():
            shutil.move(str(dst), str(src))
            log(f"Restored: {dst.name}")
    history_log.unlink()
    log("Reversal complete.")


# ==========================================
# ORGANIZE
# ==========================================

def organize():
    count = 0
    total_bytes_deleted = 0

    # Ensure category folders exist
    for cat in FILE_CATEGORIES:
        (desktop / cat).mkdir(exist_ok=True)

    # --- Mode selection ---
    while True:
        mode = ask("Mode? Type  1  (same action for all files)  or  2  (decide per file):")
        if mode in ["1", "2"]:
            break
        log("Invalid — type 1 or 2.")

    # --- Individual mode ---
    if mode == "2":
        for file in sorted(desktop.iterdir()):
            if file.name in non_removable_files or not file.exists():
                continue
            count += 1
            while True:
                action = ask(f"[{file.name}]  delete / keep / move:")
                if action == "keep":
                    log(f"Kept: {file.name}")
                    break
                elif action == "move":
                    dest = get_destination(file, action)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file), str(dest))
                    log_action("move", file, dest)
                    log(f"Moved: {file.name} → {dest.parent.name}/")
                    break
                elif action == "delete":
                    try:
                        total_bytes_deleted += file.stat().st_size
                    except FileNotFoundError:
                        pass
                    dest = trash_dir / file.name
                    shutil.move(str(file), str(dest))
                    log_action("delete", file, dest)
                    log(f"Deleted: {file.name}")
                    break
                else:
                    log("Invalid — type delete, keep, or move.")

    # --- Bulk mode ---
    elif mode == "1":
        while True:
            bulk_action = ask("Action for ALL files — delete / keep / move:")
            if bulk_action in ["delete", "keep", "move"]:
                break
            log("Invalid — type delete, keep, or move.")

        for file in sorted(desktop.iterdir()):
            if file.name in non_removable_files or not file.exists():
                continue
            count += 1

            if bulk_action == "keep":
                log(f"Kept: {file.name}")

            elif bulk_action == "move":
                dest = get_destination(file, bulk_action)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file), str(dest))
                log_action("move", file, dest)
                log(f"Moved: {file.name} → {dest.parent.name}/")

            elif bulk_action == "delete":
                try:
                    total_bytes_deleted += file.stat().st_size
                except FileNotFoundError:
                    pass
                dest = trash_dir / file.name
                shutil.move(str(file), str(dest))
                log_action("delete", file, dest)
                log(f"Deleted: {file.name}")

    log(f"\nDone. Processed {count} files. Freed: {format_size(total_bytes_deleted)}")


# ==========================================
# MAIN (CLI fallback — no GUI)
# ==========================================

def _cli_input(prompt):
    print(prompt)
    return input("> ").strip().lower()


def main():
    global ui_input, ui_log
    ui_input = _cli_input
    ui_log = print

    files = [f for f in desktop.iterdir() if f.name not in non_removable_files]
    log(f"Found {len(files)} files on desktop:")
    for f in files:
        log(f"  {f.name}")

    while True:
        choice = _cli_input("1 = organize,  2 = undo all:")
        if choice == "1":
            organize()
            break
        elif choice == "2":
            undo_all()
            break
        else:
            print("Type 1 or 2.")


if __name__ == "__main__":
    main()