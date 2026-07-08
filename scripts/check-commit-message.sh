#!/usr/bin/env bash
# Validate commit message follows Conventional Commits + project policy.
# Used as a pre-commit commit-msg hook, mirrors CI ci-quality.yml regex.
#
# Format: type(optional-scope): subject
#   type: feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert
#   scope: lowercase alphanumeric + / . _ -
#   subject: starts lowercase, then lowercase/digits/-/./_/space

set -o pipefail

commit_msg_file="$1"
if [[ -z "$commit_msg_file" ]]; then
  echo "ERROR: No commit message file provided."
  exit 1
fi

# Read the commit message (first line = subject)
subject=$(head -n1 "$commit_msg_file")

# Regex matching CI ci-quality.yml pattern
# ^(type)(scope)?(!)?: (subject)$
if echo "$subject" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9/._-]+\))?!?: [a-z][a-z0-9/._ -]+$'; then
  exit 0
fi

# If we get here, validation failed
echo "ERROR: Commit message does not follow Conventional Commits format."
echo ""
echo "  Message: $subject"
echo ""
echo "  Expected: type(optional-scope): description"
echo "  Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
echo ""
echo "  Subject must start with a lowercase letter, followed by"
echo "  lowercase letters, digits, / . _ - or space characters."
echo ""
echo "  Examples:"
echo '    feat(ui): add button'
echo '    fix: resolve timeout'
echo '    chore(ci): bump dependency version'
echo ""

exit 1
