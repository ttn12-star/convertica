#!/bin/bash
#
# Pre-compress static files with Gzip and Brotli
# Run this script after collectstatic during deployment
#
# Usage: ./scripts/compress_static.sh [staticfiles_directory]
#
# Note: Script is designed to be resilient - continues even if compression fails
#       This ensures deployment doesn't fail if compression tools are missing

# Don't exit on error - we want to continue even if compression fails
set +e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default staticfiles directory
STATIC_DIR="${1:-/app/staticfiles}"

if [ ! -d "$STATIC_DIR" ]; then
    echo -e "${RED}Error: Directory $STATIC_DIR does not exist${NC}"
    exit 1
fi

echo -e "${GREEN}Starting static file compression...${NC}"
echo "Target directory: $STATIC_DIR"
echo

cd "$STATIC_DIR" || exit 1

# Count files to compress
total_files=$(find . -type f \( -name '*.css' -o -name '*.js' -o -name '*.svg' -o -name '*.json' -o -name '*.xml' -o -name '*.html' -o -name '*.txt' \) | wc -l)
echo "Found $total_files files to compress"
echo

#===============================================================================
# GZIP Compression (fallback for browsers without Brotli support)
#===============================================================================
echo -e "${GREEN}[1/2] Gzip compression (level 9)...${NC}"

if ! command -v gzip &> /dev/null; then
    echo -e "${YELLOW}  ⚠ Gzip not found, skipping...${NC}"
    gzip_count=0
    gzip_size_before=0
    gzip_size_after=0
else
    gzip_count=0
    gzip_size_before=0
    gzip_size_after=0

    while IFS= read -r file; do
        if [ -f "$file" ]; then
            size_before=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
            gzip_size_before=$((gzip_size_before + size_before))

            # Create gzipped version (keep original) - continue on error
            if gzip -9 -k -f "$file" 2>/dev/null; then
                if [ -f "${file}.gz" ]; then
                    size_after=$(stat -f%z "${file}.gz" 2>/dev/null || stat -c%s "${file}.gz" 2>/dev/null || echo "0")
                    gzip_size_after=$((gzip_size_after + size_after))
                    gzip_count=$((gzip_count + 1))
                fi
            fi
        fi
    done < <(find . -type f \( -name '*.css' -o -name '*.js' -o -name '*.svg' -o -name '*.json' -o -name '*.xml' -o -name '*.html' -o -name '*.txt' \) -not -name '*.gz' -not -name '*.br' 2>/dev/null || true)

    echo "  ✓ Compressed $gzip_count files"
fi
if [ $gzip_size_before -gt 0 ]; then
    gzip_ratio=$(awk "BEGIN {printf \"%.1f\", (1 - $gzip_size_after / $gzip_size_before) * 100}")
    echo "  ✓ Size reduction: ${gzip_ratio}%"
    echo "  ✓ Before: $(numfmt --to=iec-i --suffix=B $gzip_size_before 2>/dev/null || echo "$gzip_size_before bytes")"
    echo "  ✓ After:  $(numfmt --to=iec-i --suffix=B $gzip_size_after 2>/dev/null || echo "$gzip_size_after bytes")"
fi
echo

#===============================================================================
# BROTLI Compression (better compression, modern browsers)
#===============================================================================
echo -e "${GREEN}[2/2] Brotli compression (level 11)...${NC}"

if ! command -v brotli &> /dev/null; then
    echo -e "${YELLOW}  ⚠ Brotli not installed, skipping...${NC}"
    echo -e "${YELLOW}  Install with: apt-get install brotli${NC}"
else
    brotli_count=0
    brotli_size_before=0
    brotli_size_after=0

    while IFS= read -r file; do
        if [ -f "$file" ]; then
            size_before=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
            brotli_size_before=$((brotli_size_before + size_before))

            # Create brotli version (keep original) - continue on error
            # Level 11 = maximum compression (slower but best for static files)
            if brotli -q 11 -k -f "$file" 2>/dev/null; then
                if [ -f "${file}.br" ]; then
                    size_after=$(stat -f%z "${file}.br" 2>/dev/null || stat -c%s "${file}.br" 2>/dev/null || echo "0")
                    brotli_size_after=$((brotli_size_after + size_after))
                    brotli_count=$((brotli_count + 1))
                fi
            fi
        fi
    done < <(find . -type f \( -name '*.css' -o -name '*.js' -o -name '*.svg' -o -name '*.json' -o -name '*.xml' -o -name '*.html' -o -name '*.txt' \) -not -name '*.gz' -not -name '*.br' 2>/dev/null || true)

    echo "  ✓ Compressed $brotli_count files"
    if [ $brotli_size_before -gt 0 ]; then
        brotli_ratio=$(awk "BEGIN {printf \"%.1f\", (1 - $brotli_size_after / $brotli_size_before) * 100}")
        echo "  ✓ Size reduction: ${brotli_ratio}%"
        echo "  ✓ Before: $(numfmt --to=iec-i --suffix=B $brotli_size_before 2>/dev/null || echo "$brotli_size_before bytes")"
        echo "  ✓ After:  $(numfmt --to=iec-i --suffix=B $brotli_size_after 2>/dev/null || echo "$brotli_size_after bytes")"

        # Compare Brotli vs Gzip
        if [ $gzip_size_after -gt 0 ]; then
            improvement=$(awk "BEGIN {printf \"%.1f\", (1 - $brotli_size_after / $gzip_size_after) * 100}")
            echo "  ✓ Brotli is ${improvement}% smaller than Gzip"
        fi
    fi
fi

echo
echo -e "${GREEN}✓ Static file compression completed!${NC}"
echo
echo "Summary:"
echo "  • Gzipped: $gzip_count files"
if command -v brotli &> /dev/null; then
    echo "  • Brotli:  $brotli_count files"
fi
echo
echo "Note: Nginx will automatically serve .gz or .br files when available"
echo "      (requires gzip_static on; and brotli_static on; in nginx.conf)"
