#!/usr/bin/env python
"""
Script to create staticfiles.json manifest if it doesn't exist.
This ensures ManifestStaticFilesStorage works correctly even if
Django doesn't create the manifest automatically during collectstatic.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

STATICFILES_DIR = Path("/app/staticfiles")
MANIFEST_PATH = STATICFILES_DIR / "staticfiles.json"


def create_manifest():
    """Create staticfiles.json manifest if it doesn't exist or is invalid."""
    if not STATICFILES_DIR.exists():
        print(
            f"Directory {STATICFILES_DIR} does not exist, skipping manifest creation."
        )
        return

    # Check if manifest exists and is valid
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH) as f:
                manifest = json.load(f)
            # Check if it's a valid Django 5.2 manifest
            if (
                isinstance(manifest, dict)
                and manifest.get("version") == "1.1"
                and "paths" in manifest
            ):
                print(f"✅ Valid manifest already exists: {MANIFEST_PATH}")
                return
            else:
                print("⚠️  Invalid manifest format, recreating...")
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️  Error reading manifest: {e}, recreating...")

    print(f"Creating manifest at {MANIFEST_PATH}...")
    paths = {}
    errors = 0

    # Walk through all files in staticfiles directory
    for root, dirs, files in os.walk(STATICFILES_DIR):
        for file in files:
            if file != "staticfiles.json":
                rel_path = os.path.relpath(os.path.join(root, file), STATICFILES_DIR)
                file_path = os.path.join(root, file)
                try:
                    # Calculate hash based on file content
                    with open(file_path, "rb") as f:
                        content = f.read()
                    # ManifestStaticFilesStorage uses MD5 (first 12 characters)
                    file_hash = hashlib.md5(content).hexdigest()[:12]
                    # Create hashed name
                    name, ext = os.path.splitext(rel_path)
                    hashed_name = f"{name}.{file_hash}{ext}"
                    paths[rel_path] = hashed_name
                except Exception as e:
                    print(f"Warning: Could not hash {rel_path}: {e}")
                    errors += 1

    # Create manifest in Django 5.2 format
    manifest = {"version": "1.1", "paths": paths}

    # Save manifest
    try:
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        print(f"✅ Manifest created successfully: {MANIFEST_PATH}")
        print(f"   Files in manifest: {len(paths)}")
        print(f"   Size: {os.path.getsize(MANIFEST_PATH)} bytes")
        if errors > 0:
            print(f"   Warnings: {errors} files could not be hashed")
    except Exception as e:
        print(f"❌ Error creating manifest: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        create_manifest()
        sys.exit(0)
    except Exception as e:
        print(f"Error creating manifest: {e}")
        # Don't fail - continue with collectstatic anyway
        sys.exit(0)
