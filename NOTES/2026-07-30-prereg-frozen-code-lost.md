# Amendment — the code version frozen by `PR-ITER2-001` is not recoverable

**Dated:** 2026-07-30 · **Affects:** pre-registration `PR-ITER2-001`, runs `EXP-0007-020` and `EXP-0008-001`
**Status:** disclosed, not fixable

## What the pre-registration promised

`PR-ITER2-001` sealed, before the Iteration-2 runs existed, the sha256 of every script
that would produce them. Among them `sigo_features.py` at
`sha256:0460d1f638c1244ea97fcbbf991b3f1da773353f035741c40132e2fa6e68869f`. The point of
that commitment is that anyone can later download the file, hash it, and confirm the code
was fixed before the results were seen.

## What happened

That file was **edited in place** between the pre-registration and the following run —
`load_conservation` and `dynamics_features` were added. No copy of the `0460d1f6` version
survives: not on any disk, and not in this repository's git history, where
`code/sigo_features.py` has only ever existed as the later version. The archive therefore
cannot serve the file that its own pre-registration commits to.

## What still holds, and what does not

**Holds:** the hash itself is inside the sealed, Bitcoin-anchored content of
`EXP-0007-020` and `EXP-0008-001`. It proves *that a specific version was fixed* at that
moment, and that whatever ran later was a different version — the substitution cannot be
hidden.

**Does not hold:** the reproducibility claim. Nobody — including us — can re-run the
Iteration-2 code as pre-registered, nor confirm what it contained. For that run, the
pre-registration is a record of intent, not a reproducible artifact.

## Why this note exists instead of a quiet fix

The tempting move was to publish the current version under the old name and let the
hashes fail quietly, or to say nothing. Either would make the archive claim a
verifiability it does not have for this file. **A half-kept pre-registration is ugly;
asserting it verifies when it does not is disqualifying** — the whole archive rests on
the reader being able to check us.

## The rule this produced

Referenced code and data are versioned by hash and **never overwritten**. When a file
evolves, the new version is published alongside the old one under a hash-qualified name
(`sigo_features@0460d1f6.py`), so every seal keeps resolving to the file it actually
used. `scripts/check_provenance.py` now recomputes every declared sha256 against what is
published and reports anything unresolved; it runs on every notarisation. Two other files
flagged by that audit were recovered and published on this date; this one could not be.
