#!/usr/bin/env bash
# One-time: make `git push` write to BOTH GitHub (primary) and Codeberg (mirror).
# Run inside the cloned `evidence` repo. Requires the Codeberg repo to exist and
# your Codeberg auth (Claude Code on your Mac has git creds).
set -e
git remote set-url --add --push origin https://github.com/RosettaQuantum/evidence.git
git remote set-url --add --push origin https://codeberg.org/RosettaQuantum/evidence.git
echo "Done. 'git push' now updates GitHub + Codeberg (byte-identical). Verify:"
git remote -v
