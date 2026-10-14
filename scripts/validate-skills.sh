#!/usr/bin/env bash
# Validate all SKILL.md files in skills/ against repository standards.
# Usage: ./scripts/validate-skills.sh
#
# Discovers skills in either layout: flat (skills/<name>/SKILL.md) or
# categorized (skills/<category>/<name>/SKILL.md). A directory directly under
# skills/ with no SKILL.md but with subdirectories is treated as a category;
# plain files directly under skills/ (e.g. a future skills/categories.json)
# are ignored.
#
# Errors (block CI):
# - SKILL.md exists in each skill directory (in either layout)
# - A directory directly under skills/ has either SKILL.md or subdirectories
# - Every subdirectory of a category directory has SKILL.md
# - Valid frontmatter boundaries at the top of the file
# - Required frontmatter fields and nested metadata fields exist
# - metadata.version uses semver
# - metadata.summary exists, is 120 characters or fewer, and contains no '|'
# - name matches the skill's own directory name (not the category)
# - Skill names are unique across the whole tree (no two categories share one)
# - Skill folder uses kebab-case (no underscores, spaces, or capitals)
# - Description under 1024 characters
# - Description does not contain XML-style angle brackets
# - No "claude" or "anthropic" in skill name
# - No README.md inside skill folders
# - Skills that link references/fme/tool-map.md only mention fme_* resource types listed there
#
# Warnings (non-blocking):
# - Missing top-level H1 heading
# - Missing required top-level sections outside fenced code blocks
# - Description missing "Use when" or "Trigger phrases"
# - SKILL.md body over 5000 words
# - Such a skill mentions a legacy fme_* resource type from tool-map.md's "Do Not Use" table

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../skills" && pwd)"
FME_TOOL_MAP="$(cd "$(dirname "$0")/.." && pwd)/references/fme/tool-map.md"
ERRORS=0
WARNINGS=0
CHECKED=0

red()    { printf '\033[0;31m%s\033[0m\n' "$1"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$1"; }

check_fail() {
  red "  FAIL: $1"
  ERRORS=$((ERRORS + 1))
}

check_warn() {
  yellow "  WARN: $1"
  WARNINGS=$((WARNINGS + 1))
}

extract_description() {
  printf '%s\n' "$1" | awk '
    /^description:/ {
      found=1
      value=$0
      sub(/^description:[[:space:]]*/, "", value)
      if (value == "" || value ~ /^>[+-]?$/ || value ~ /^\|[+-]?$/) {
        next
      }
      print value
      exit
    }
    found && /^[^[:space:]]/ { exit }
    found {
      sub(/^[[:space:]]+/, "", $0)
      print
    }
  ' | paste -sd' ' -
}

body_without_code_fences() {
  local file="$1"
  local start_line="$2"
  awk -v start="$start_line" '
    NR < start { next }
    /^```/ { in_code = !in_code; next }
    !in_code { print }
  ' "$file"
}

# FME resource types: names before the "Do Not Use" heading are current; names only in that section are legacy.
FME_KNOWN=""
FME_LEGACY=""
if [[ -f "$FME_TOOL_MAP" ]]; then
  FME_KNOWN="$(awk '/^## Do Not Use/ { exit } { print }' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u || true)"
  FME_LEGACY="$(awk '/^## Do Not Use/ { f = 1 } f' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u | grep -vxF -f <(printf '%s\n' "$FME_KNOWN") || true)"
fi

# Discover skill directories in both the flat (skills/<name>) and
# categorized (skills/<category>/<name>) layouts. Plain files directly under
# skills/ are ignored; a directory with neither SKILL.md nor subdirectories
# is an error.
SKILL_DIRS=()
SKILL_LABELS=()

for entry in "$SKILLS_DIR"/*/; do
  entry="${entry%/}"
  entry_name="$(basename "$entry")"

  if [[ -f "$entry/SKILL.md" ]]; then
    SKILL_DIRS+=("$entry")
    SKILL_LABELS+=("$entry_name")
    continue
  fi

  has_subdir=0
  for sub in "$entry"/*/; do
    [[ -d "$sub" ]] || continue
    has_subdir=1
    sub="${sub%/}"
    sub_name="$(basename "$sub")"
    if [[ -f "$sub/SKILL.md" ]]; then
      SKILL_DIRS+=("$sub")
      SKILL_LABELS+=("$entry_name/$sub_name")
    else
      check_fail "$entry_name/$sub_name: SKILL.md not found"
    fi
  done

  if [[ $has_subdir -eq 0 ]]; then
    check_fail "$entry_name: directory under skills/ has neither SKILL.md nor subdirectories"
  fi
done

ALL_SKILL_NAMES=()

for skill_index in "${!SKILL_DIRS[@]}"; do
  skill_dir="${SKILL_DIRS[$skill_index]}"
  skill_label="${SKILL_LABELS[$skill_index]}"
  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"

  CHECKED=$((CHECKED + 1))
  ALL_SKILL_NAMES+=("$skill_name")
  echo "Checking $skill_label..."

  if [[ "$skill_name" =~ [A-Z] ]]; then
    check_fail "$skill_label: folder name contains uppercase letters (must be kebab-case)"
  fi
  if [[ "$skill_name" =~ _ ]]; then
    check_fail "$skill_label: folder name contains underscores (use hyphens for kebab-case)"
  fi
  if [[ "$skill_name" =~ " " ]]; then
    check_fail "$skill_label: folder name contains spaces (use hyphens for kebab-case)"
  fi

  if [[ -f "$skill_dir/README.md" ]]; then
    check_fail "$skill_label: contains README.md (all documentation belongs in SKILL.md or references/)"
  fi

  if [[ "$(sed -n '1p' "$skill_file")" != "---" ]]; then
    check_fail "$skill_label: frontmatter must start on line 1 with '---'"
    continue
  fi

  frontmatter_end="$(awk 'NR > 1 && /^---$/ { print NR; exit }' "$skill_file")"
  if [[ -z "$frontmatter_end" ]]; then
    check_fail "$skill_label: missing closing frontmatter delimiter '---'"
    continue
  fi

  frontmatter="$(sed -n "2,$((frontmatter_end - 1))p" "$skill_file")"
  body_start=$((frontmatter_end + 1))
  sanitized_body="$(body_without_code_fences "$skill_file" "$body_start")"

  if ! printf '%s\n' "$frontmatter" | grep -q '^name:'; then
    check_fail "$skill_label: missing 'name' field"
  else
    fm_name="$(printf '%s\n' "$frontmatter" | sed -n 's/^name:[[:space:]]*//p' | head -n 1)"
    if [[ "$fm_name" != "$skill_name" ]]; then
      check_fail "$skill_label: name '$fm_name' does not match directory name '$skill_name'"
    fi
    if printf '%s\n' "$fm_name" | grep -iqE 'claude|anthropic'; then
      check_fail "$skill_label: name contains 'claude' or 'anthropic' (reserved)"
    fi
  fi

  if ! printf '%s\n' "$frontmatter" | grep -q '^description:'; then
    check_fail "$skill_label: missing 'description' field"
    desc=""
  else
    desc="$(extract_description "$frontmatter")"
    desc_len=${#desc}

    if [[ $desc_len -gt 1024 ]]; then
      check_fail "$skill_label: description is $desc_len chars (max 1024)"
    fi

    if printf '%s\n' "$desc" | grep -qE '<[a-zA-Z/][^>]*>'; then
      check_fail "$skill_label: description contains XML-style angle brackets"
    fi

    if ! printf '%s\n' "$desc" | grep -iqE 'use when|trigger phrase'; then
      check_warn "$skill_label: description missing 'Use when' or 'Trigger phrases' guidance"
    fi
  fi

  if ! printf '%s\n' "$frontmatter" | grep -q '^metadata:$'; then
    check_fail "$skill_label: missing 'metadata' block"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  author:'; then
    check_fail "$skill_label: missing 'metadata.author' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  version:'; then
    check_fail "$skill_label: missing 'metadata.version' field"
  else
    fm_version="$(printf '%s\n' "$frontmatter" | sed -n 's/^  version:[[:space:]]*//p' | head -n 1)"
    if ! printf '%s\n' "$fm_version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
      check_fail "$skill_label: metadata.version '$fm_version' is not semver"
    fi
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  mcp-server:'; then
    check_fail "$skill_label: missing 'metadata.mcp-server' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  summary:'; then
    check_fail "$skill_label: missing 'metadata.summary' field"
  else
    fm_summary="$(printf '%s\n' "$frontmatter" | sed -n 's/^  summary:[[:space:]]*//p' | head -n 1)"
    summary_len=${#fm_summary}
    if [[ $summary_len -gt 120 ]]; then
      check_fail "$skill_label: metadata.summary is $summary_len chars (max 120)"
    fi
    if printf '%s\n' "$fm_summary" | grep -qF '|'; then
      check_fail "$skill_label: metadata.summary contains '|'"
    fi
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^license:'; then
    check_fail "$skill_label: missing 'license' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^compatibility:'; then
    check_fail "$skill_label: missing 'compatibility' field"
  fi

  if ! printf '%s\n' "$sanitized_body" | grep -q '^# '; then
    check_warn "$skill_label: no top-level '# ' heading found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Instructions'; then
    check_warn "$skill_label: no '## Instructions' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Examples'; then
    check_warn "$skill_label: no '## Examples' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Performance Notes'; then
    check_warn "$skill_label: no '## Performance Notes' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Troubleshooting' && ! printf '%s\n' "$sanitized_body" | grep -q '^## Error Handling'; then
    check_warn "$skill_label: no '## Troubleshooting' or '## Error Handling' section found outside code fences"
  fi

  if [[ -n "$FME_KNOWN" ]] && grep -q 'references/fme/tool-map.md' "$skill_file"; then
    fme_refs="$(cat "$skill_file" "$skill_dir"/references/*.md 2>/dev/null | grep -oE 'fme_[a-z_]*[a-z]' | sort -u || true)"
    for ref in $fme_refs; do
      if printf '%s\n' "$FME_KNOWN" | grep -qxF "$ref"; then
        continue
      elif printf '%s\n' "$FME_LEGACY" | grep -qxF "$ref"; then
        check_warn "$skill_label: uses legacy FME resource type '$ref' (see references/fme/tool-map.md)"
      else
        check_fail "$skill_label: unknown FME resource type '$ref' (not in references/fme/tool-map.md)"
      fi
    done
  fi

  body_words="$(sed -n "${body_start},\$p" "$skill_file" | wc -w | tr -d ' ')"
  if [[ "$body_words" -gt 5000 ]]; then
    check_warn "$skill_label: SKILL.md body is $body_words words (recommended max 5000)"
  fi
done

if [[ ${#ALL_SKILL_NAMES[@]} -gt 0 ]]; then
  duplicate_names="$(printf '%s\n' "${ALL_SKILL_NAMES[@]}" | sort | uniq -d)"
  if [[ -n "$duplicate_names" ]]; then
    while IFS= read -r dup_name; do
      [[ -n "$dup_name" ]] || continue
      check_fail "$dup_name: skill name used in more than one category"
    done <<< "$duplicate_names"
  fi
fi

echo ""
echo "================================"
echo "Checked $CHECKED skills"
echo "  Errors:   $ERRORS"
echo "  Warnings: $WARNINGS"
echo "================================"

if [[ $ERRORS -gt 0 ]]; then
  red "Validation failed with $ERRORS error(s)"
  exit 1
else
  green "All skills passed validation ($WARNINGS warning(s))"
  exit 0
fi
