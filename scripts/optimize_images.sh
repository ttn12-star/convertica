#!/bin/bash
#
# Image Optimization Script for Convertica
# Converts images to WebP, optimizes PNGs and JPGs
#
# Usage: ./scripts/optimize_images.sh [target_directory]
#
# Requirements:
#   - cwebp (for WebP conversion)
#   - optipng (for PNG optimization)
#   - jpegoptim (for JPG optimization)
#
# Install on Ubuntu/Debian:
#   sudo apt-get install webp optipng jpegoptim
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default target directory
TARGET_DIR="${1:-static/images}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Convertica Image Optimization Tool            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo

if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Directory $TARGET_DIR does not exist${NC}"
    exit 1
fi

echo "Target directory: $TARGET_DIR"
echo

#===============================================================================
# Check Dependencies
#===============================================================================
check_dependencies() {
    local missing=()

    if ! command -v cwebp &> /dev/null; then
        missing+=("cwebp")
    fi

    if ! command -v optipng &> /dev/null; then
        missing+=("optipng")
    fi

    if ! command -v jpegoptim &> /dev/null; then
        missing+=("jpegoptim")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${YELLOW}Warning: Missing dependencies: ${missing[*]}${NC}"
        echo -e "${YELLOW}Install with: sudo apt-get install webp optipng jpegoptim${NC}"
        echo
        return 1
    fi

    return 0
}

check_dependencies

#===============================================================================
# WebP Conversion
#===============================================================================
echo -e "${GREEN}[1/3] Converting images to WebP format...${NC}"
echo

webp_count=0
webp_size_before=0
webp_size_after=0

find "$TARGET_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | while read -r img; do
    # Skip if WebP already exists
    webp_img="${img%.*}.webp"

    if [ ! -f "$webp_img" ]; then
        size_before=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null)

        # Quality 85 is a good balance between quality and file size
        if cwebp -q 85 "$img" -o "$webp_img" &> /dev/null; then
            size_after=$(stat -f%z "$webp_img" 2>/dev/null || stat -c%s "$webp_img" 2>/dev/null)
            reduction=$((100 - (size_after * 100 / size_before)))

            echo -e "  ✓ ${img##*/} → ${webp_img##*/} (-${reduction}%)"

            webp_count=$((webp_count + 1))
            webp_size_before=$((webp_size_before + size_before))
            webp_size_after=$((webp_size_after + size_after))
        else
            echo -e "  ${RED}✗${NC} Failed: ${img##*/}"
        fi
    fi
done

if [ $webp_count -gt 0 ]; then
    echo
    echo -e "${GREEN}WebP Conversion Summary:${NC}"
    echo "  • Converted: $webp_count images"
    if [ $webp_size_before -gt 0 ]; then
        reduction=$((100 - (webp_size_after * 100 / webp_size_before)))
        echo "  • Size reduction: ${reduction}%"
        echo "  • Before: $(numfmt --to=iec-i --suffix=B $webp_size_before 2>/dev/null || echo "$webp_size_before bytes")"
        echo "  • After:  $(numfmt --to=iec-i --suffix=B $webp_size_after 2>/dev/null || echo "$webp_size_after bytes")"
    fi
else
    echo -e "${YELLOW}  No new WebP conversions needed${NC}"
fi
echo

#===============================================================================
# PNG Optimization
#===============================================================================
echo -e "${GREEN}[2/3] Optimizing PNG images...${NC}"
echo

png_count=0
png_size_before=0
png_size_after=0

find "$TARGET_DIR" -type f -iname "*.png" | while read -r img; do
    size_before=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null)

    # -o5 = optimization level 5 (good balance)
    # Non-destructive optimization
    if optipng -o5 -quiet "$img" 2>/dev/null; then
        size_after=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null)

        if [ $size_after -lt $size_before ]; then
            saved=$((size_before - size_after))
            reduction=$((100 - (size_after * 100 / size_before)))
            echo -e "  ✓ ${img##*/} (-${reduction}%)"

            png_count=$((png_count + 1))
            png_size_before=$((png_size_before + size_before))
            png_size_after=$((png_size_after + size_after))
        fi
    fi
done

if [ $png_count -gt 0 ]; then
    echo
    echo -e "${GREEN}PNG Optimization Summary:${NC}"
    echo "  • Optimized: $png_count images"
    if [ $png_size_before -gt 0 ]; then
        reduction=$((100 - (png_size_after * 100 / png_size_before)))
        echo "  • Size reduction: ${reduction}%"
        echo "  • Saved: $(numfmt --to=iec-i --suffix=B $((png_size_before - png_size_after)) 2>/dev/null || echo "$((png_size_before - png_size_after)) bytes")"
    fi
else
    echo -e "${YELLOW}  No PNG optimizations performed${NC}"
fi
echo

#===============================================================================
# JPG Optimization
#===============================================================================
echo -e "${GREEN}[3/3] Optimizing JPG/JPEG images...${NC}"
echo

jpg_count=0
jpg_size_before=0
jpg_size_after=0

find "$TARGET_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | while read -r img; do
    size_before=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null)

    # --max=85 = quality 85%
    # --strip-all = remove EXIF data
    # --preserve = preserve modification time
    if jpegoptim --max=85 --strip-all --preserve --quiet "$img" 2>/dev/null; then
        size_after=$(stat -f%z "$img" 2>/dev/null || stat -c%s "$img" 2>/dev/null)

        if [ $size_after -lt $size_before ]; then
            saved=$((size_before - size_after))
            reduction=$((100 - (size_after * 100 / size_before)))
            echo -e "  ✓ ${img##*/} (-${reduction}%)"

            jpg_count=$((jpg_count + 1))
            jpg_size_before=$((jpg_size_before + size_before))
            jpg_size_after=$((jpg_size_after + size_after))
        fi
    fi
done

if [ $jpg_count -gt 0 ]; then
    echo
    echo -e "${GREEN}JPG Optimization Summary:${NC}"
    echo "  • Optimized: $jpg_count images"
    if [ $jpg_size_before -gt 0 ]; then
        reduction=$((100 - (jpg_size_after * 100 / jpg_size_before)))
        echo "  • Size reduction: ${reduction}%"
        echo "  • Saved: $(numfmt --to=iec-i --suffix=B $((jpg_size_before - jpg_size_after)) 2>/dev/null || echo "$((jpg_size_before - jpg_size_after)) bytes")"
    fi
else
    echo -e "${YELLOW}  No JPG optimizations performed${NC}"
fi
echo

#===============================================================================
# Final Summary
#===============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                  Optimization Complete                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo

total_optimized=$((webp_count + png_count + jpg_count))
total_saved=$(((webp_size_before - webp_size_after) + (png_size_before - png_size_after) + (jpg_size_before - jpg_size_after)))

echo "Summary:"
echo "  • WebP conversions: $webp_count"
echo "  • PNG optimized:    $png_count"
echo "  • JPG optimized:    $jpg_count"
echo "  • Total files:      $total_optimized"

if [ $total_saved -gt 0 ]; then
    echo "  • Total saved:      $(numfmt --to=iec-i --suffix=B $total_saved 2>/dev/null || echo "$total_saved bytes")"
fi

echo
echo -e "${GREEN}✓ Image optimization completed successfully!${NC}"
echo

# Tips
echo "Tips:"
echo "  • Use WebP images in <picture> elements with fallback"
echo "  • Update templates to use optimized_image tag"
echo "  • Run this script before deployment"
echo "  • Add to CI/CD pipeline for automatic optimization"
echo
