#!/usr/bin/env bash
# Validate the skills tree and every SKILL.md against repository standards.
# Usage: ./scripts/validate-skills.sh
#
# Layout is strict: skills/<category>/<skill>/SKILL.md, with the category list
# in skills/categories.json. Hidden entries (dotfiles) under skills/ are ignored.
# Runs the same on macOS (bash 3.2, BSD tools) and Linux (GNU tools).
#
# Errors (block CI):
# - skills/categories.json exists, parses, and lists the category directories
# - Every directory directly under skills/ is a listed category; a flat
#   skills/<name>/SKILL.md is an error (move it to skills/<category>/<name>/)
# - Plain files directly under skills/ (other than categories.json) or directly
#   under a category directory are errors
# - Every listed category exists and has at least one skill
# - Every subdirectory of a category contains SKILL.md
# - Valid frontmatter boundaries at the top of the file
# - Top-level frontmatter keys are only name, description, license,
#   compatibility, metadata, allowed-tools
# - Required frontmatter fields and nested metadata fields exist
# - metadata.version uses semver
# - metadata.summary exists, is 120 characters or fewer, and contains no '|'
# - name matches the skill's own directory name (not the category)
# - Skill names are unique across the whole tree (no two categories share one)
# - Skill folder uses kebab-case (no underscores, spaces, or capitals)
# - Description under 1024 characters
# - Description does not contain XML-style angle brackets
# - Description contains "Use when" or "Trigger phrases"
# - No "claude" or "anthropic" in skill name
# - No README.md inside skill folders
# - When FME skills exist, references/fme/tool-map.md exists, has a
#   '## Do Not Use' heading, and lists at least one fme_* type before it
# - Every skill under skills/fme/ links ../../../references/fme/tool-map.md
#   outside fenced code blocks
# - Skills that link references/fme/tool-map.md only mention fme_* resource types listed there
#
# Warnings (non-blocking):
# - Missing top-level H1 heading
# - Missing required top-level sections outside fenced code blocks
# - SKILL.md over 500 lines
# - SKILL.md body over 5000 words
# - Such a skill mentions a legacy fme_* resource type from tool-map.md's "Do Not Use" table

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$ROOT/skills"
CATEGORIES_FILE="$SKILLS_DIR/categories.json"
FME_TOOL_MAP="$ROOT/references/fme/tool-map.md"
FME_CATEGORY="fme"
# Exact relative path from skills/fme/<skill>/SKILL.md to references/fme/tool-map.md, optional anchor.
FME_TOOL_MAP_LINK_RE='\]\(\.\./\.\./\.\./references/fme/tool-map\.md(#[^()[:space:]]*)?\)'
ALLOWED_KEYS="name description license compatibility metadata allowed-tools"
MAX_LINES=500
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
  # A closing fence must use the same character as the opener, be at least as
  # long, and have nothing but whitespace after the fence characters -- a line
  # like "```yaml" only opens or continues a block, it never closes one.
  awk -v start="$start_line" '
    function fence_run_len(s, c,   n, i) {
      n = length(s)
      i = 1
      while (i <= n && substr(s, i, 1) == c) i++
      return i - 1
    }
    NR < start { next }
    {
      line = $0
      ch = substr(line, 1, 1)
      if (ch == "`" || ch == "~") {
        flen = fence_run_len(line, ch)
        if (flen >= 3) {
          rest = substr(line, flen + 1)
          if (in_code) {
            if (ch == fence_char && flen >= fence_min && rest ~ /^[ \t]*$/) {
              in_code = 0
            }
            next
          } else {
            in_code = 1
            fence_char = ch
            fence_min = flen
            next
          }
        }
      }
      if (!in_code) print
    }
  ' "$file"
}

# Category directory names from skills/categories.json, one per line.
read_categories() {
  python3 -I -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    dirs = [entry["dir"] for entry in data["categories"]]
except (OSError, ValueError, KeyError, TypeError) as exc:
    sys.exit("cannot read categories: %s: %s" % (type(exc).__name__, exc))
for d in dirs:
    if not isinstance(d, str) or d in ("", ".", "..") or "/" in d:
        sys.exit("invalid category dir %r" % (d,))
if not dirs:
    sys.exit("no categories listed")
print("\n".join(dirs))
' "$CATEGORIES_FILE" 2>&1
}

if [[ ! -d "$SKILLS_DIR" ]]; then
  red "  FAIL: skills/ directory not found"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  red "  FAIL: python3 is required to read skills/categories.json"
  exit 1
fi
if [[ ! -f "$CATEGORIES_FILE" ]]; then
  red "  FAIL: skills/categories.json not found"
  exit 1
fi
if ! CATEGORIES="$(read_categories)"; then
  red "  FAIL: skills/categories.json is unusable: $CATEGORIES"
  exit 1
fi

# FME resource types: names before the "Do Not Use" heading are current; names
# only in that section are legacy. If any FME skill exists, the tool map must
# be present, have the heading, and yield at least one known type -- any other
# outcome is a validator error, never a silent skip of the resource-type check.
FME_KNOWN=""
FME_LEGACY=""
FME_SKILLS_EXIST=0
if [[ -d "$SKILLS_DIR/$FME_CATEGORY" ]]; then
  for fme_sub in "$SKILLS_DIR/$FME_CATEGORY"/*; do
    [[ -d "$fme_sub" && -f "$fme_sub/SKILL.md" ]] && FME_SKILLS_EXIST=1
  done
fi

if [[ $FME_SKILLS_EXIST -eq 1 ]]; then
  if [[ ! -f "$FME_TOOL_MAP" ]]; then
    check_fail "references/fme/tool-map.md: not found, but FME skills exist (cannot validate FME resource types)"
  elif ! grep -q '^## Do Not Use' "$FME_TOOL_MAP"; then
    check_fail "references/fme/tool-map.md: missing '## Do Not Use' heading (cannot separate current from legacy FME resource types)"
  else
    FME_KNOWN="$(awk '/^## Do Not Use/ { exit } { print }' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u || true)"
    if [[ -z "$FME_KNOWN" ]]; then
      check_fail "references/fme/tool-map.md: no known fme_* resource types found before '## Do Not Use'"
    else
      FME_LEGACY="$(awk '/^## Do Not Use/ { f = 1 } f' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u | grep -vxF -f <(printf '%s\n' "$FME_KNOWN") || true)"
    fi
  fi
elif [[ -f "$FME_TOOL_MAP" ]]; then
  FME_KNOWN="$(awk '/^## Do Not Use/ { exit } { print }' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u || true)"
  FME_LEGACY="$(awk '/^## Do Not Use/ { f = 1 } f' "$FME_TOOL_MAP" | grep -oE 'fme_[a-z_]*[a-z]' | sort -u | grep -vxF -f <(printf '%s\n' "$FME_KNOWN") || true)"
fi

# Layout: every non-hidden entry directly under skills/ must be categories.json
# or a listed category; every listed category must exist and hold skill folders.
SKILL_DIRS=()
SKILL_LABELS=()
SKILL_CATEGORIES=()

echo "Checking layout..."

for entry in "$SKILLS_DIR"/*; do
  [[ -e "$entry" ]] || continue
  entry_name="$(basename "$entry")"

  if [[ ! -d "$entry" ]]; then
    if [[ "$entry_name" != "categories.json" ]]; then
      check_fail "skills/$entry_name: unexpected file directly under skills/ (only categories.json is allowed)"
    fi
    continue
  fi

  if ! printf '%s\n' "$CATEGORIES" | grep -qxF -- "$entry_name"; then
    if [[ -f "$entry/SKILL.md" ]]; then
      check_fail "skills/$entry_name/SKILL.md: flat layout is not supported; move it to skills/<category>/$entry_name/ (categories are listed in skills/categories.json)"
    else
      check_fail "skills/$entry_name: directory is not a category listed in skills/categories.json"
    fi
  fi
done

while IFS= read -r category; do
  [[ -n "$category" ]] || continue
  category_dir="$SKILLS_DIR/$category"

  if [[ ! -d "$category_dir" ]]; then
    check_fail "skills/categories.json lists category '$category' but skills/$category/ does not exist"
    continue
  fi

  skill_count=0
  for sub in "$category_dir"/*; do
    [[ -e "$sub" ]] || continue
    sub_name="$(basename "$sub")"

    if [[ ! -d "$sub" ]]; then
      check_fail "skills/$category/$sub_name: unexpected file directly under a category directory (only skill folders belong here)"
      continue
    fi

    skill_count=$((skill_count + 1))
    if [[ -f "$sub/SKILL.md" ]]; then
      SKILL_DIRS+=("$sub")
      SKILL_LABELS+=("$category/$sub_name")
      SKILL_CATEGORIES+=("$category")
    else
      check_fail "$category/$sub_name: SKILL.md not found"
    fi
  done

  if [[ $skill_count -eq 0 ]]; then
    check_fail "skills/$category: category has no skills"
  fi
done <<< "$CATEGORIES"

ALL_SKILL_NAMES=()

if [[ ${#SKILL_DIRS[@]} -gt 0 ]]; then
  for skill_index in "${!SKILL_DIRS[@]}"; do
    skill_dir="${SKILL_DIRS[$skill_index]}"
    skill_label="${SKILL_LABELS[$skill_index]}"
    skill_category="${SKILL_CATEGORIES[$skill_index]}"
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

    top_level_keys="$(printf '%s\n' "$frontmatter" | awk '/^[A-Za-z0-9_][A-Za-z0-9_.-]*:([[:space:]]|$)/ { key = $0; sub(/:.*/, "", key); print key }')"
    for key in $top_level_keys; do
      case " $ALLOWED_KEYS " in
        *" $key "*) ;;
        *) check_fail "$skill_label: unknown frontmatter key '$key' (allowed: ${ALLOWED_KEYS// /, })" ;;
      esac
    done

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

      if ! printf '%s\n' "$desc" | grep -iqE 'use when|trigger phrases'; then
        check_fail "$skill_label: description must contain 'Use when' or 'Trigger phrases'"
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

    if [[ "$skill_category" == "$FME_CATEGORY" ]] && ! printf '%s\n' "$sanitized_body" | grep -qE "$FME_TOOL_MAP_LINK_RE"; then
      check_fail "$skill_label: FME skill must link ../../../references/fme/tool-map.md (exact relative path from skills/fme/$skill_name/SKILL.md), outside any fenced code block"
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

    skill_lines="$(wc -l < "$skill_file" | tr -d ' ')"
    if [[ "$skill_lines" -gt $MAX_LINES ]]; then
      check_warn "$skill_label: SKILL.md is $skill_lines lines (recommended max $MAX_LINES)"
    fi

    body_words="$(sed -n "${body_start},\$p" "$skill_file" | wc -w | tr -d ' ')"
    if [[ "$body_words" -gt 5000 ]]; then
      check_warn "$skill_label: SKILL.md body is $body_words words (recommended max 5000)"
    fi
  done
fi

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
