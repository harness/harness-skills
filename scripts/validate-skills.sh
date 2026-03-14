#!/usr/bin/env bash
# Validate all SKILL.md files in skills/ against repository standards.
# Usage: ./scripts/validate-skills.sh
#
# Errors (block CI):
# - SKILL.md exists in each skill directory
# - Valid frontmatter boundaries at the top of the file
# - Required frontmatter fields and nested metadata fields exist
# - metadata.version uses semver
# - name matches the directory name
# - Skill folder uses kebab-case (no underscores, spaces, or capitals)
# - Description under 1024 characters
# - Description does not contain XML-style angle brackets
# - No "claude" or "anthropic" in skill name
# - No README.md inside skill folders
#
# Warnings (non-blocking):
# - Missing top-level H1 heading
# - Missing required top-level sections outside fenced code blocks
# - Description missing "Use when" or "Trigger phrases"
# - SKILL.md body over 5000 words

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../skills" && pwd)"
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

for skill_dir in "$SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    check_fail "$skill_name: SKILL.md not found"
    continue
  fi

  CHECKED=$((CHECKED + 1))
  echo "Checking $skill_name..."

  if [[ "$skill_name" =~ [A-Z] ]]; then
    check_fail "$skill_name: folder name contains uppercase letters (must be kebab-case)"
  fi
  if [[ "$skill_name" =~ _ ]]; then
    check_fail "$skill_name: folder name contains underscores (use hyphens for kebab-case)"
  fi
  if [[ "$skill_name" =~ " " ]]; then
    check_fail "$skill_name: folder name contains spaces (use hyphens for kebab-case)"
  fi

  if [[ -f "$skill_dir/README.md" ]]; then
    check_fail "$skill_name: contains README.md (all documentation belongs in SKILL.md or references/)"
  fi

  if [[ "$(sed -n '1p' "$skill_file")" != "---" ]]; then
    check_fail "$skill_name: frontmatter must start on line 1 with '---'"
    continue
  fi

  frontmatter_end="$(awk 'NR > 1 && /^---$/ { print NR; exit }' "$skill_file")"
  if [[ -z "$frontmatter_end" ]]; then
    check_fail "$skill_name: missing closing frontmatter delimiter '---'"
    continue
  fi

  frontmatter="$(sed -n "2,$((frontmatter_end - 1))p" "$skill_file")"
  body_start=$((frontmatter_end + 1))
  sanitized_body="$(body_without_code_fences "$skill_file" "$body_start")"

  if ! printf '%s\n' "$frontmatter" | grep -q '^name:'; then
    check_fail "$skill_name: missing 'name' field"
  else
    fm_name="$(printf '%s\n' "$frontmatter" | sed -n 's/^name:[[:space:]]*//p' | head -n 1)"
    if [[ "$fm_name" != "$skill_name" ]]; then
      check_fail "$skill_name: name '$fm_name' does not match directory name '$skill_name'"
    fi
    if printf '%s\n' "$fm_name" | grep -iqE 'claude|anthropic'; then
      check_fail "$skill_name: name contains 'claude' or 'anthropic' (reserved)"
    fi
  fi

  if ! printf '%s\n' "$frontmatter" | grep -q '^description:'; then
    check_fail "$skill_name: missing 'description' field"
    desc=""
  else
    desc="$(extract_description "$frontmatter")"
    desc_len=${#desc}

    if [[ $desc_len -gt 1024 ]]; then
      check_fail "$skill_name: description is $desc_len chars (max 1024)"
    fi

    if printf '%s\n' "$desc" | grep -qE '<[a-zA-Z/][^>]*>'; then
      check_fail "$skill_name: description contains XML-style angle brackets"
    fi

    if ! printf '%s\n' "$desc" | grep -iqE 'use when|trigger phrase'; then
      check_warn "$skill_name: description missing 'Use when' or 'Trigger phrases' guidance"
    fi
  fi

  if ! printf '%s\n' "$frontmatter" | grep -q '^metadata:$'; then
    check_fail "$skill_name: missing 'metadata' block"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  author:'; then
    check_fail "$skill_name: missing 'metadata.author' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  version:'; then
    check_fail "$skill_name: missing 'metadata.version' field"
  else
    fm_version="$(printf '%s\n' "$frontmatter" | sed -n 's/^  version:[[:space:]]*//p' | head -n 1)"
    if ! printf '%s\n' "$fm_version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
      check_fail "$skill_name: metadata.version '$fm_version' is not semver"
    fi
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^  mcp-server:'; then
    check_fail "$skill_name: missing 'metadata.mcp-server' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^license:'; then
    check_fail "$skill_name: missing 'license' field"
  fi
  if ! printf '%s\n' "$frontmatter" | grep -q '^compatibility:'; then
    check_fail "$skill_name: missing 'compatibility' field"
  fi

  if ! printf '%s\n' "$sanitized_body" | grep -q '^# '; then
    check_warn "$skill_name: no top-level '# ' heading found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Instructions'; then
    check_warn "$skill_name: no '## Instructions' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Examples'; then
    check_warn "$skill_name: no '## Examples' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Performance Notes'; then
    check_warn "$skill_name: no '## Performance Notes' section found outside code fences"
  fi
  if ! printf '%s\n' "$sanitized_body" | grep -q '^## Troubleshooting' && ! printf '%s\n' "$sanitized_body" | grep -q '^## Error Handling'; then
    check_warn "$skill_name: no '## Troubleshooting' or '## Error Handling' section found outside code fences"
  fi

  body_words="$(sed -n "${body_start},\$p" "$skill_file" | wc -w | tr -d ' ')"
  if [[ "$body_words" -gt 5000 ]]; then
    check_warn "$skill_name: SKILL.md body is $body_words words (recommended max 5000)"
  fi
done

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
