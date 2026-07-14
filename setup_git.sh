#!/usr/bin/env bash
# Creates a fresh git repo from this folder and pushes it to GitHub as a PRIVATE repo.
# Run this on your Mac (native filesystem), NOT in the Claude sandbox.
#
#   cd "path/to/agentic-inspection-capa"
#   bash setup_git.sh
#
set -euo pipefail
cd "$(dirname "$0")"

REPO_NAME="agentic-inspection-capa"

# 1) Clear any partial repo created earlier, then init fresh on 'main'.
rm -rf .git
git init -b main
git add -A
git -c commit.gpgsign=false commit -m "Add CAPA PRD (v1.1) and inspection reports dataset"

# 2) Create the private repo on GitHub and push.
if command -v gh >/dev/null 2>&1; then
  # GitHub CLI path (recommended). Authenticates via: gh auth login
  gh repo create "$REPO_NAME" --private --source=. --remote=origin --push
  echo "Done. Repo created and pushed via GitHub CLI."
else
  cat <<'EOF'

GitHub CLI ('gh') not found. Two options:

  A) Install GitHub CLI, then re-run this script:
       brew install gh && gh auth login

  B) Create an empty PRIVATE repo named 'agentic-inspection-capa' at
     https://github.com/new  (do NOT add a README), then run:

       git remote add origin https://github.com/<your-username>/agentic-inspection-capa.git
       git push -u origin main

EOF
fi
