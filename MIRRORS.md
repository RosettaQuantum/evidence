# Mirrors — GitHub + Codeberg (triple archive, copies 1 & 2)

Every sealed archive file lives byte-identical in GitHub (primary) and Codeberg
(independent, non-profit Forgejo infra), plus D1 (copy 3) and an external
OpenTimestamps anchor. Two ways to keep GitHub↔Codeberg in sync — pick one:

## Option A — dual-remote push (fits the Claude Code flow, recommended)
One `git push` writes to both. One-time setup inside the cloned repo:
```bash
./setup-mirrors.sh        # adds Codeberg as a second push URL on origin
git push                  # now updates GitHub AND Codeberg
```
Prerequisite: create the Codeberg repo `RosettaQuantum/evidence` (public) first.

## Option B — GitHub Action auto-mirror (set once, hands-off)
`.github/workflows/mirror-to-codeberg.yml` mirrors on every push to GitHub.
Needs a Codeberg token as a GitHub secret:
1. Codeberg: create org `RosettaQuantum` + public repo `evidence`.
2. Codeberg → Settings → Applications → generate a token scoped to that repo
   (write:repository), thanks to Forgejo repo-scoped tokens.
3. GitHub `evidence` repo → Settings → Secrets → Actions → `CODEBERG_TOKEN` = that token.

## Verify the three copies agree
```bash
python3 scripts/verify.py recipes/*.json                 # recompute hashes locally
diff <(curl -s <github raw_url>) <(curl -s <codeberg raw_url>)   # byte-identical
ots verify <file>.ots                                    # external timestamp proof
```

## OpenTimestamps note
`.ots` proofs are committed next to each file. They're "pending" until a Bitcoin
block confirms (~hours); complete them later with `ots upgrade recipes/*.ots`.

## Verification log
- 2026-07-20: full check — sha256 of all 18 files identical across GitHub raw,
  Codeberg raw, and local clone (dual-push, Option A). OTS proofs upgraded to
  complete (Bitcoin-anchored).
- 2026-07-21: dual-push verified on both copies; mirror Action activated with
  repo-scoped CODEBERG_TOKEN (Option B live as automatic redundancy).
