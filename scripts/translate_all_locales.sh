#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

API_URL="${POQT_API_URL:-${L10N_QUALITY_API_URL:-}}"
API_KEY="${POQT_API_KEY:-${L10N_QUALITY_API_KEY:-}}"
DEV_BYPASS="${POQT_DEV_BYPASS:-${L10N_QUALITY_DEV_BYPASS:-}}"

TRANSLATE_DELAY="${L10N_TRANSLATE_DELAY:-0.5}"
TRANSLATE_SEO="${L10N_TRANSLATE_SEO:-0}"
COMPILE_MESSAGES="${L10N_COMPILE_MESSAGES:-1}"
DRY_RUN="${L10N_TRANSLATE_DRY_RUN:-0}"
TARGET_LANGS_RAW="${L10N_TARGET_LANGS:-}"

if ! command -v l10n-quality >/dev/null 2>&1; then
  echo "Error: l10n-quality is not installed or not in PATH." >&2
  exit 2
fi

if [[ -z "$API_URL" ]]; then
  echo "Error: API URL is required." >&2
  echo "Set POQT_API_URL or L10N_QUALITY_API_URL." >&2
  exit 2
fi

if [[ -z "$API_KEY" && -z "$DEV_BYPASS" ]]; then
  echo "Error: API key or dev bypass is required." >&2
  echo "Set POQT_API_KEY / L10N_QUALITY_API_KEY or POQT_DEV_BYPASS / L10N_QUALITY_DEV_BYPASS." >&2
  exit 2
fi

mapfile -t PO_FILES < <(find locale -mindepth 3 -maxdepth 3 -type f -path "locale/*/LC_MESSAGES/django.po" | sort)

if [[ "${#PO_FILES[@]}" -eq 0 ]]; then
  echo "No locale PO files found under locale/*/LC_MESSAGES/django.po"
  exit 0
fi

declare -A TARGET_FILTER=()
if [[ -n "$TARGET_LANGS_RAW" ]]; then
  TARGET_LANGS_RAW="${TARGET_LANGS_RAW//,/ }"
  for lang in $TARGET_LANGS_RAW; do
    TARGET_FILTER["$lang"]=1
  done
fi

translated_files=0

for po_file in "${PO_FILES[@]}"; do
  lang="$(echo "$po_file" | cut -d/ -f2)"

  # Default language should not be machine-translated from itself.
  if [[ "$lang" == "en" ]]; then
    echo "Skipping default locale: $po_file"
    continue
  fi

  if [[ "${#TARGET_FILTER[@]}" -gt 0 && -z "${TARGET_FILTER[$lang]:-}" ]]; then
    echo "Skipping locale not in L10N_TARGET_LANGS: $po_file"
    continue
  fi

  cmd=(
    l10n-quality translate "$po_file"
    --type po
    --target "$lang"
    --in-place
    --delay "$TRANSLATE_DELAY"
  )

  if [[ "$TRANSLATE_SEO" == "1" ]]; then
    cmd+=(--seo)
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    printf "DRY RUN: "
    printf "%q " "${cmd[@]}"
    printf "\n"
  else
    "${cmd[@]}"
  fi

  translated_files=$((translated_files + 1))
done

echo "Processed locale files: $translated_files"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run mode: compilemessages skipped."
  exit 0
fi

if [[ "$COMPILE_MESSAGES" != "1" ]]; then
  echo "compilemessages skipped (L10N_COMPILE_MESSAGES=$COMPILE_MESSAGES)."
  exit 0
fi

if ! command -v msgfmt >/dev/null 2>&1; then
  echo "Warning: msgfmt not found, skipping compilemessages."
  exit 0
fi

if python manage.py compilemessages; then
  echo "Translations compiled successfully."
else
  echo "Warning: compilemessages failed. .po translations were updated, but .mo files may be stale." >&2
fi
