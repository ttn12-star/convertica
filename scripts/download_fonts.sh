#!/bin/bash
#
# Download self-hosted fonts for Convertica
#
# This script downloads Inter and Poppins fonts from google-webfonts-helper
# and places them in the correct directories.
#
# Usage: ./scripts/download_fonts.sh [--force]
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Convertica Font Downloader                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

FONTS_DIR="$PROJECT_ROOT/static/fonts"
INTER_DIR="$FONTS_DIR/inter"
POPPINS_DIR="$FONTS_DIR/poppins"
TEMP_DIR="$PROJECT_ROOT/.font_temp"

# Create directories
mkdir -p "$INTER_DIR" "$POPPINS_DIR" "$TEMP_DIR"

echo -e "${GREEN}Fonts directory: $FONTS_DIR${NC}"
echo

#===============================================================================
# Check if fonts already exist
#===============================================================================
INTER_DONE=0
POPPINS_DONE=0

if [ -f "$INTER_DIR/inter-v13-latin_cyrillic-regular.woff2" ]; then
    inter_size=$(stat -c%s "$INTER_DIR/inter-v13-latin_cyrillic-regular.woff2" 2>/dev/null || echo "0")
    if [ "$inter_size" -gt 10000 ]; then
        echo -e "${YELLOW}Inter fonts already downloaded. Use --force to re-download.${NC}"
        if [ "$1" != "--force" ]; then
            INTER_DONE=1
        fi
    fi
fi

if [ -f "$POPPINS_DIR/poppins-v20-latin-regular.woff2" ]; then
    poppins_size=$(stat -c%s "$POPPINS_DIR/poppins-v20-latin-regular.woff2" 2>/dev/null || echo "0")
    if [ "$poppins_size" -gt 5000 ]; then
        echo -e "${YELLOW}Poppins fonts already downloaded. Use --force to re-download.${NC}"
        if [ "$1" != "--force" ]; then
            POPPINS_DONE=1
        fi
    fi
fi

if [ "$INTER_DONE" = "1" ] && [ "$POPPINS_DONE" = "1" ]; then
    echo -e "${GREEN}All fonts already downloaded.${NC}"
    rm -rf "$TEMP_DIR"
    exit 0
fi

echo

#===============================================================================
# Download fonts using google-webfonts-helper API
#===============================================================================

GWFH_API="https://gwfh.mranftl.com/api/fonts"

#===============================================================================
# Download Inter font
#===============================================================================
if [ "$INTER_DONE" != "1" ]; then
    echo -e "${GREEN}[1/2] Downloading Inter font...${NC}"

    INTER_URL="$GWFH_API/inter?download=zip&subsets=latin,cyrillic&variants=regular,500,600,700&formats=woff2"

    echo "  Downloading from google-webfonts-helper..."
    curl -sL "$INTER_URL" -o "$TEMP_DIR/inter.zip"

    if [ -f "$TEMP_DIR/inter.zip" ] && file -b "$TEMP_DIR/inter.zip" | grep -qi "zip"; then
        echo "  Extracting fonts..."
        unzip -q -o "$TEMP_DIR/inter.zip" -d "$TEMP_DIR/inter_extract"

        # Copy and rename files to expected naming convention
        for file in "$TEMP_DIR/inter_extract"/*.woff2; do
            if [ -f "$file" ]; then
                basename=$(basename "$file")
                # Extract weight from filename
                if echo "$basename" | grep -q "regular"; then
                    cp "$file" "$INTER_DIR/inter-v13-latin_cyrillic-regular.woff2"
                elif echo "$basename" | grep -q "500"; then
                    cp "$file" "$INTER_DIR/inter-v13-latin_cyrillic-500.woff2"
                elif echo "$basename" | grep -q "600"; then
                    cp "$file" "$INTER_DIR/inter-v13-latin_cyrillic-600.woff2"
                elif echo "$basename" | grep -q "700"; then
                    cp "$file" "$INTER_DIR/inter-v13-latin_cyrillic-700.woff2"
                fi
            fi
        done

        echo -e "  ${GREEN}✓ Inter font downloaded${NC}"
    else
        echo -e "  ${RED}✗ Failed to download Inter font${NC}"
        echo -e "  ${YELLOW}Please download manually from: https://gwfh.mranftl.com/fonts/inter${NC}"
    fi
    echo
fi

#===============================================================================
# Download Poppins font
#===============================================================================
if [ "$POPPINS_DONE" != "1" ]; then
    echo -e "${GREEN}[2/2] Downloading Poppins font...${NC}"

    POPPINS_URL="$GWFH_API/poppins?download=zip&subsets=latin&variants=regular,500,600,700&formats=woff2"

    echo "  Downloading from google-webfonts-helper..."
    curl -sL "$POPPINS_URL" -o "$TEMP_DIR/poppins.zip"

    if [ -f "$TEMP_DIR/poppins.zip" ] && file -b "$TEMP_DIR/poppins.zip" | grep -qi "zip"; then
        echo "  Extracting fonts..."
        unzip -q -o "$TEMP_DIR/poppins.zip" -d "$TEMP_DIR/poppins_extract"

        # Copy and rename files to expected naming convention
        for file in "$TEMP_DIR/poppins_extract"/*.woff2; do
            if [ -f "$file" ]; then
                basename=$(basename "$file")
                # Extract weight from filename
                if echo "$basename" | grep -q "regular"; then
                    cp "$file" "$POPPINS_DIR/poppins-v20-latin-regular.woff2"
                elif echo "$basename" | grep -q "500"; then
                    cp "$file" "$POPPINS_DIR/poppins-v20-latin-500.woff2"
                elif echo "$basename" | grep -q "600"; then
                    cp "$file" "$POPPINS_DIR/poppins-v20-latin-600.woff2"
                elif echo "$basename" | grep -q "700"; then
                    cp "$file" "$POPPINS_DIR/poppins-v20-latin-700.woff2"
                fi
            fi
        done

        echo -e "  ${GREEN}✓ Poppins font downloaded${NC}"
    else
        echo -e "  ${RED}✗ Failed to download Poppins font${NC}"
        echo -e "  ${YELLOW}Please download manually from: https://gwfh.mranftl.com/fonts/poppins${NC}"
    fi
    echo
fi

#===============================================================================
# Cleanup
#===============================================================================
rm -rf "$TEMP_DIR"

#===============================================================================
# Summary
#===============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Download Complete                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo

echo "Inter fonts:"
ls "$INTER_DIR"/*.woff2 2>/dev/null | wc -l | xargs -I {} echo "  {} files"
ls -lh "$INTER_DIR"/*.woff2 2>/dev/null | awk '{print "  - " $(NF) " (" $5 ")"}' || echo "  No files"

echo
echo "Poppins fonts:"
ls "$POPPINS_DIR"/*.woff2 2>/dev/null | wc -l | xargs -I {} echo "  {} files"
ls -lh "$POPPINS_DIR"/*.woff2 2>/dev/null | awk '{print "  - " $(NF) " (" $5 ")"}' || echo "  No files"

# Verify file sizes
echo
echo "Verification:"
for f in "$INTER_DIR"/*.woff2 "$POPPINS_DIR"/*.woff2; do
    if [ -f "$f" ]; then
        size=$(stat -c%s "$f" 2>/dev/null || echo "0")
        if [ "$size" -gt 5000 ]; then
            echo -e "  ${GREEN}✓${NC} $(basename $f) - OK ($size bytes)"
        else
            echo -e "  ${RED}✗${NC} $(basename $f) - INVALID ($size bytes)"
        fi
    fi
done

echo
echo -e "${GREEN}✓ Font download completed!${NC}"
echo
echo "Next steps:"
echo "  1. Run: python manage.py collectstatic --noinput"
echo "  2. Deploy to production"
echo "  3. Verify fonts load from your domain (not Google)"
echo
