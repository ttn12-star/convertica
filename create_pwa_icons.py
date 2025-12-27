#!/usr/bin/env python3
"""
Script to create PWA icons from existing favicon.
Creates 512x512 icon and shortcut icons for manifest.json
"""

import os
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow not installed. Install with: pip install Pillow")

# Paths
STATIC_DIR = Path("static")
ICONS_DIR = STATIC_DIR / "icons"
FAVICON_192 = STATIC_DIR / "favicon-192x192.png"
FAVICON_512 = STATIC_DIR / "favicon-512x512.png"

# Shortcut icons to create
SHORTCUTS = {
    "pdf-to-word.png": {"emoji": "📄", "bg_color": "#2563eb", "name": "PDF to Word"},
    "word-to-pdf.png": {"emoji": "📝", "bg_color": "#4f46e5", "name": "Word to PDF"},
    "merge-pdf.png": {"emoji": "📎", "bg_color": "#7c3aed", "name": "Merge PDF"},
    "compress-pdf.png": {"emoji": "🗜️", "bg_color": "#f59e0b", "name": "Compress PDF"},
}


def create_512_icon():
    """Create 512x512 icon from 192x192 favicon."""
    if not PIL_AVAILABLE:
        return False

    if not FAVICON_192.exists():
        print(f"✗ Source icon not found: {FAVICON_192}")
        return False

    if FAVICON_512.exists():
        print(f"✓ 512x512 icon already exists: {FAVICON_512}")
        return True

    try:
        print(f"📝 Creating 512x512 icon from {FAVICON_192}...")

        # Open and resize
        img = Image.open(FAVICON_192)
        img_512 = img.resize((512, 512), Image.Resampling.LANCZOS)

        # Save
        img_512.save(FAVICON_512, "PNG", quality=100, optimize=True)

        print(f"✓ Created: {FAVICON_512}")
        print(f"  Size: {FAVICON_512.stat().st_size / 1024:.1f} KB")
        return True

    except Exception as e:
        print(f"✗ Error creating 512x512 icon: {e}")
        return False


def create_shortcut_icon(filename, emoji, bg_color, name, size=96):
    """Create a shortcut icon with emoji and colored background."""
    if not PIL_AVAILABLE:
        return False

    output_path = ICONS_DIR / filename

    if output_path.exists():
        print(f"  ✓ Already exists: {filename}")
        return True

    try:
        # Create image with colored background
        img = Image.new("RGBA", (size, size), bg_color)
        draw = ImageDraw.Draw(img)

        # Try to add emoji text (may not work on all systems)
        try:
            # Try different font paths
            font_paths = [
                "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                "/System/Library/Fonts/Apple Color Emoji.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]

            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, 60)
                        break
                    except Exception:
                        continue

            if font:
                # Calculate text position (centered)
                bbox = draw.textbbox((0, 0), emoji, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size - text_width) // 2
                y = (size - text_height) // 2

                draw.text((x, y), emoji, font=font, fill="white")
            else:
                # Fallback: draw a simple shape
                margin = size // 4
                draw.ellipse(
                    [margin, margin, size - margin, size - margin], fill="white"
                )

        except Exception:
            # Fallback: draw a simple shape
            margin = size // 4
            draw.ellipse([margin, margin, size - margin, size - margin], fill="white")

        # Save
        img.save(output_path, "PNG", quality=100, optimize=True)
        print(f"  ✓ Created: {filename} ({name})")
        return True

    except Exception as e:
        print(f"  ✗ Error creating {filename}: {e}")
        return False


def create_all_shortcut_icons():
    """Create all shortcut icons."""
    if not PIL_AVAILABLE:
        return False

    # Create icons directory if not exists
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Icons directory: {ICONS_DIR}")

    success_count = 0
    for filename, config in SHORTCUTS.items():
        if create_shortcut_icon(
            filename, config["emoji"], config["bg_color"], config["name"]
        ):
            success_count += 1

    return success_count == len(SHORTCUTS)


def main():
    """Main function."""
    print("🎨 Creating PWA Icons...")
    print("=" * 60)

    if not PIL_AVAILABLE:
        print("\n❌ Pillow library required!")
        print("Install with: pip install Pillow")
        print("\nAlternative: Use online tools:")
        print("  - https://favicon.io/favicon-converter/")
        print("  - https://realfavicongenerator.net/")
        return

    # Create 512x512 icon
    print("\n1️⃣  Creating 512x512 icon...")
    icon_512_created = create_512_icon()

    # Create shortcut icons
    print("\n2️⃣  Creating shortcut icons...")
    shortcuts_created = create_all_shortcut_icons()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"  512x512 icon: {'✓ Done' if icon_512_created else '✗ Failed'}")
    print(
        f"  Shortcut icons: {'✓ Done' if shortcuts_created else '✗ Failed'} ({len(SHORTCUTS)} icons)"
    )
    print("=" * 60)

    if icon_512_created and shortcuts_created:
        print("\n✅ All PWA icons created successfully!")
        print("\n📝 Files created:")
        print(f"  - {FAVICON_512}")
        for filename in SHORTCUTS.keys():
            print(f"  - {ICONS_DIR / filename}")

        print("\n📱 manifest.json is already configured to use these icons")
        print("🎉 PWA is ready to use!")
    elif icon_512_created:
        print("\n⚠️  512x512 icon created, but shortcut icons failed")
        print("Shortcut icons are optional - PWA will still work")
    else:
        print("\n⚠️  Some icons could not be created")
        print("You can create them manually or use online tools")


if __name__ == "__main__":
    main()
