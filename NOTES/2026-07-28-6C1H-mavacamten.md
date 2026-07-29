# Correction note — 6C1H does not contain mavacamten

**Dated:** 2026-07-28 · **Affects:** Cleveland Clinic track, cardiac myosin target
**Sealed run concerned:** [`EXP-0007-015`](../runs/2026/07/) (`5TBY → 9GZ1`, chain A)

## What the challenge brief says

Table 1 of the Cleveland Clinic challenge brief lists PDB **`6C1H`** as the structure
for validating the allosteric site of **mavacamten** on cardiac myosin.

## What the structure actually contains

`6C1H` is *High-Resolution Cryo-EM Structures of Actin-bound Myosin States*. Its only
non-polymer components are **ADP** and **Mg²⁺**. **Mavacamten is not present.** There is
therefore no co-crystallised effector in `6C1H` from which an allosteric site could be
read, and any "validation against 6C1H" would be validating against a site that the
structure does not define.

## What we did instead

We used **`9GZ1`** — *Beta-cardiac myosin interacting heads motif complexed to
mavacamten* — whose ligand **`XB2` is mavacamten**. The allosteric site is defined, as
in every other target of this series, as the residues within 4.5 Å of the
co-crystallised effector. This is recorded inside the sealed archive of
`EXP-0007-015`, in `w6.que.ground_truth`, and was fixed *before* the run by the
pre-registration `PR-CLEV-001`.

**`8QYR`** (*Beta-cardiac myosin motor domain, pre-powerstroke state*) also contains
`XB2` and is a valid corroborating structure for the ligand's presence. **We did not
run it.** No sealed archive covers `8QYR`, so this note claims nothing about it beyond
the public fact of its composition.

## Verify this yourself

Every statement above is checkable against the public RCSB API — no need to take our
word for it:

```bash
# ligands of each entry (look at the comp_id / name fields)
for PDB in 6C1H 9GZ1 8QYR; do
  curl -s "https://data.rcsb.org/rest/v1/core/entry/$PDB" | jq -r '.struct.title'
  curl -s "https://data.rcsb.org/rest/v1/core/entry/$PDB" \
    | jq -r '.rcsb_entry_container_identifiers.non_polymer_entity_ids[]' \
    | while read E; do
        curl -s "https://data.rcsb.org/rest/v1/core/nonpolymer_entity/$PDB/$E" \
          | jq -r '.pdbx_entity_nonpoly | "  \(.comp_id)  \(.name)"'
      done
done
```

Checked 2026-07-28: `6C1H` → `ADP`, `MG`. `9GZ1` → `MG`, `ADP`, `PO4`, **`XB2`
(Mavacamten)**. `8QYR` → **`XB2` (Mavacamten)**, `SO4`, `EDO`, `MG`, `ADP`, `BEF`.

## Why this note exists

Because a benchmark is only as honest as its ground truth. Silently swapping the
structure would have left a reader unable to reproduce our site definition from the
brief; asserting a corroboration we never ran would have been worse. The substitution
is declared, dated, and tied to the sealed run that used it.
