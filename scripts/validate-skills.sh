#!/usr/bin/env bash
# Validate all SKILL.md files in skills/ against the Anthropic Skills Guide standards.
# Usage: ./scripts/validate-skills.sh
#
# Checks enforced:
#   [ERRORS - block PR merge]
#   - SKILL.md exists in each skill directory
#   - Frontmatter fields: name, description, metadata.author, metadata.version, metadata.mcp-server, license, compatibility
#   - name matches directory name (kebab-case)
#   - Skill folder uses kebab-case (no underscores, spaces, or capitals)
#   - Description under 1024 characters
#   - No XML angle brackets (< or >) in description content
#   - No "claude" or "anthropic" in skill name
#   - No README.md inside skill folders (all docs go in SKILL.md or references/)
#   - SKILL.md body under 5000 words
#
#   [WARNINGS - non-blocking]
#   - Missing ## Instructions section
#   - Missing ## Troubleshooting or ## Error Handling section
#   - Missing ## Examples section
#   - Missing ## Performance Notes section
#   - Description missing trigger phrases ("Use when" or "Trigger phrases")

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

for skill_dir in "$SKILLS_DIR"/*/; do
  skill_name="$(basename "$skill_dir")"
  skill_file="$skill_dir/SKILL.md"

  if [[ ! -f "$skill_file" ]]; then
    check_fail "$skill_name: SKILL.md not found"
    continue
  fi

  CHECKED=$((CHECKED + 1))
  echo "Checking $skill_name..."

  # --- Skill folder naming ---
  if [[ "$skill_name" =~ [A-Z] ]]; then
    check_fail "$skill_name: folder name contains uppercase letters (must be kebab-case)"
  fi
  if [[ "$skill_name" =~ _ ]]; then
    check_fail "$skill_name: folder name contains underscores (use hyphens for kebab-case)"
  fi
  if [[ "$skill_name" =~ " " ]]; then
    check_fail "$skill_name: folder name contains spaces (use hyphens for kebab-case)"
  fi

  # --- No README.md inside skill folders ---
  if [[ -f "$skill_dir/README.md" ]]; then
    check_fail "$skill_name: contains README.md (all documentation belongs in SKILL.md or references/)"
  fi

  # --- Extract frontmatter (between --- markers) ---
  frontmatter=$(awk '/^---$/{n++; next} n==1' "$skill_file")

  # --- Required field: name ---
  if ! echo "$frontmatter" | grep -q '^name:'; then
    check_fail "$skill_name: missing 'name' field"
  else
    fm_name=$(echo "$frontmatter" | grep '^name:' | head -1 | sed 's/^name: *//')
    if [[ "$fm_name" != "$skill_name" ]]; then
      check_fail "$skill_name: name '$fm_name' does not match directory name '$skill_name'"
    fi
    # No "claude" or "anthropic" in name
    if echo "$fm_name" | grep -iq 'claude\|anthropic'; then
      check_fail "$skill_name: name contains 'claude' or 'anthropic' (reserved)"
    fi
  fi

  # --- Required field: description ---
  if ! echo "$frontmatter" | grep -q '^description:'; then
    check_fail "$skill_name: missing 'description' field"
  else
    # Extract full description (may be multiline with >-)
    desc=$(awk '/^---$/{n++; next} n==1' "$skill_file" | awk '
      /^description:/{found=1; sub(/^description: *>-? */, ""); if(length($0)>0) printf "%s ", $0; next}
      found && /^  /{sub(/^  +/, ""); printf "%s ", $0; next}
      found{exit}
    ')
    desc_len=${#desc}

    if [[ $desc_len -gt 1024 ]]; then
      check_fail "$skill_name: description is $desc_len chars (max 1024)"
    fi

    # Check for XML angle brackets in description content (not YAML >- syntax)
    if echo "$desc" | grep -qP '<(?![\+])' 2>/dev/null || echo "$desc" | grep -q '>' 2>/dev/null; then
      # More precise: look for actual XML-style tags like <system>, <user>, etc.
      if echo "$desc" | grep -qE '<[a-zA-Z/]' 2>/dev/null; then
        check_fail "$skill_name: description contains XML-style angle brackets"
      fi
    fi

    # Warn if description doesn't mention trigger phrases or "Use when"
    if ! echo "$desc" | grep -iq 'use when\|trigger phrase'; then
      check_warn "$skill_name: description missing 'Use when' or 'Trigger phrases' guidance"
    fi
  fi

  # --- Required field: metadata.author ---
  if ! echo "$frontmatter" | grep -q 'author:'; then
    check_fail "$skill_name: missing 'metadata.author' field"
  fi

  # --- Required field: metadata.version ---
  if ! echo "$frontmatter" | grep -q 'version:'; then
    check_fail "$skill_name: missing 'metadata.version' field"
  fi

  # --- Required field: metadata.mcp-server ---
  if ! echo "$frontmatter" | grep -q 'mcp-server:'; then
    check_fail "$skill_name: missing 'metadata.mcp-server' field"
  fi

  # --- Required field: license ---
  if ! echo "$frontmatter" | grep -q '^license:'; then
    check_fail "$skill_name: missing 'license' field"
  fi

  # --- Required field: compatibility ---
  if ! echo "$frontmatter" | grep -q '^compatibility:'; then
    check_fail "$skill_name: missing 'compatibility' field"
  fi

  # --- Body section checks ---
  if ! grep -q '^## Instructions' "$skill_file"; then
    check_warn "$skill_name: no '## Instructions' section found"
  fi

  if ! grep -q '^## Troubleshooting' "$skill_file" && ! grep -q '^## Error Handling' "$skill_file"; then
    check_warn "$skill_name: no '## Troubleshooting' or '## Error Handling' section found"
  fi

  if ! grep -q '^## Examples' "$skill_file"; then
    check_warn "$skill_name: no '## Examples' section found"
  fi

  if ! grep -q '^## Performance Notes' "$skill_file"; then
    check_warn "$skill_name: no '## Performance Notes' section found"
  fi

  # --- Word count check (SKILL.md body under 5000 words) ---
  # Count words after the second --- (end of frontmatter)
  body_words=$(awk '/^---$/{n++; next} n>=2' "$skill_file" | wc -w | tr -d ' ')
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
