#!/usr/bin/env python
"""
Script to safely clear staticfiles directory, ignoring permission errors.
This is needed when files were created with different permissions.
"""
import os
import shutil
import sys
from pathlib import Path

STATICFILES_DIR = Path("/app/staticfiles")


def clear_staticfiles():
    """Clear staticfiles directory, ignoring permission errors."""
    if not STATICFILES_DIR.exists():
        print(f"Directory {STATICFILES_DIR} does not exist, skipping clear.")
        return

    print(f"Clearing {STATICFILES_DIR}...")
    errors = 0

    # Try to remove files and directories
    for root, dirs, files in os.walk(STATICFILES_DIR):
        root_path = Path(root)

        # Remove files
        for file in files:
            file_path = root_path / file
            try:
                file_path.unlink()
            except PermissionError:
                print(
                    f"Warning: Cannot delete {file_path} (permission denied), skipping..."
                )
                errors += 1
            except Exception as e:
                print(f"Warning: Error deleting {file_path}: {e}, skipping...")
                errors += 1

        # Remove directories (in reverse order, from deepest to shallowest)
        for dir_name in reversed(dirs):
            dir_path = root_path / dir_name
            try:
                if dir_path.exists():
                    dir_path.rmdir()
            except (PermissionError, OSError):
                # Directory might not be empty or permission denied
                pass

    # Try to remove the root directory if it's empty
    try:
        if STATICFILES_DIR.exists() and not any(STATICFILES_DIR.iterdir()):
            STATICFILES_DIR.rmdir()
    except (PermissionError, OSError):
        pass

    if errors > 0:
        print(
            f"Cleared staticfiles with {errors} permission errors (this is normal if files were created with different permissions)."
        )
    else:
        print("Successfully cleared staticfiles directory.")


if __name__ == "__main__":
    try:
        clear_staticfiles()
        sys.exit(0)
    except Exception as e:
        print(f"Error clearing staticfiles: {e}")
        # Don't fail - continue with collectstatic anyway
        sys.exit(0)
