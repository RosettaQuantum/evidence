# Airbus — Quantum Solvers for Predictive Aerodynamic Modeling

**Rosetta Quantum** · 2026 Global Quantum + AI Challenge · Phase 1

> Every figure in this document is read from an artifact at build time, never typed. Each claim carries one of three labels — **measured**, **by construction**, or **from the literature** — and anything without a label is not here.

## 1 · Summary

You asked for a quantum solver for the 2D convecting Taylor-Green vortex, and for the curve of time-to-solution and error as the Reynolds number grows. We built the instrument, pre-registered the question before writing a line of it, and ran the axis end to end. Three things came out, and the third is the one worth your time.

**One — the classical cost explodes; the accuracy does not.** Across Re = 10 to 102,400 with the mesh coupled as your statement requires, the finite-difference error *falls* by four orders of magnitude (2.01e-03 → 5.37e-07). **[measured — reproduces bit-for-bit]** Its wall time rises by a factor of ~130,000 on this machine (the spectral arm, ~250,000). **[measured on one machine; not comparable across computers]**

**Why the two labels differ, and what you can do with each number.** We re-ran the whole axis on the same machine and compared it point by point: 19 of 19 errors reproduced to the last digit. The wall times moved by 4–31 % per arm, and the *ratios* between arms moved by a median of 38 % — a quotient adds the noise of both its terms. A ratio cancels a machine's overall speed and amplifies measurement noise; with times this small, the noise wins. So the errors are a precision result and the timings are an order-of-magnitude statement, and we say which is which instead of giving both the same weight. This is two runs on one machine, so it bounds run-to-run noise and says nothing about another computer. **[measured]**

**Two — the order of Carleman that carries the physics never ran; the degraded one did, and fell short.** **K = 2 — the order that actually includes Carleman's quadratic block — solved 0 of 8 points on the axis**: it needs 21–45 qubits, over the declared cap from the very first point. **K = 1, which drops that block, solved 3 of 8** (10–22 qubits), with a relative error of 4.86e-02–8.03e-02 where it ran — 28–89 times the finite-difference error at the same points. So the quantum arm does not lose the comparison: the version with the physics in it cannot be posed at this mesh coupling, and the version that can be posed is not the one that matters. **[measured]**

On its own ladder at fixed Re it reproduces the exact linear system up to N=16, and the ansatz stops reaching at N=32. **[measured]**

**Three — and this one is about your benchmark, not about us.** In the Taylor-Green vortex as specified, the nonlinear term vanishes *exactly* — ratio 2.35e-16 of the linear term, at machine precision, in the discrete operators and not only in the continuum. The obstacle your statement names — mapping nonlinear physics onto unitary hardware — **cannot be exhibited on the case chosen to test it**. We found the mechanism and the law that restores it; §5 gives both, and they are the constructive part of this submission. **[measured]**

## 2 · The question, and when it was fixed

Pre-registration `RQ-PREREG-AIRBUS-001`, content hash `sha256:39a16cf63a36095217fdf5fb…`.

It was committed in `d662d9de`, and **at that commit not one line of the instrument existed** — that is a property of the git history, verifiable by you, not a claim of ours. **[by construction]**
The pre-registration is anchored in Bitcoin (OpenTimestamps), so the ordering is bounded from above by a clock neither we nor you control. **[by construction]**

The pre-registration declared **both outcomes as deliverables before measuring**: if the quantum arm crossed, the crossing would be incontestable because the referee is a closed formula; if it did not, the curve itself is what your statement asks for. It also declared the known obstacle (Carleman truncation against a nonlinear, non-unitary problem) as a risk, not as a later discovery. **[by construction]**

## 3 · The referee, and why this benchmark is unusually strong

The statement carries the **exact analytical solution** (§5.3), so the error of any method is measured against a closed form at any Reynolds number. There is no estimated ground truth and no reference implementation to trust: the referee never degrades and never runs out. **[by construction]**

Two independent paths agree on it: the spectral arm reproduces the analytical solution to 6.27e-09 at the first point. A single arm matching a formula could be a lucky bug in either; two constructions agreeing is evidence. **[measured]**

## 4 · The axis: time-to-solution and error vs Reynolds

Mesh coupled to Reynolds per §4.1 of the statement: `N = next power of two ≥ 64·√(Re/100)`, floor 32. Every row reports what *occurred* — real mesh, real steps, measured wall time — not what was requested. **[measured]**

| Re | mesh N | steps | spectral error | spectral wall | FD2 error | FD2 wall | Carleman K=1 | Carleman K=2 |
|---|---|---|---|---|---|---|---|---|
| 10 | 32 | 7 | 6.27e-09 | 0.00341 s | 2.01e-03 | 0.0034 s | 8.03e-02 | 21 qubits, over cap |
| 25 | 32 | 7 | 6.44e-09 | 0.0033 s | 2.12e-03 | 0.00742 s | 5.89e-02 | 21 qubits, over cap |
| 100 | 64 | 13 | 5.48e-10 | 0.0207 s | 5.45e-04 | 0.0174 s | 4.86e-02 | 25 qubits, over cap |
| 400 | 128 | 26 | 3.44e-11 | 0.188 s | 1.37e-04 | 0.081 s | 14 qubits, over cap | 29 qubits, over cap |
| 1,600 | 256 | 52 | 2.15e-12 | 0.905 s | 3.43e-05 | 0.469 s | 16 qubits, over cap | 33 qubits, over cap |
| 6,400 | 512 | 104 | 1.34e-13 | 8.02 s | 8.59e-06 | 4.08 s | 18 qubits, over cap | 37 qubits, over cap |
| 25,600 | 1024 | 208 | 9.46e-15 | 78.4 s | 2.15e-06 | 40.8 s | 20 qubits, over cap | 41 qubits, over cap |
| 102,400 | 2048 | 416 | 9.02e-15 | 841 s | 5.37e-07 | 452 s | 22 qubits, over cap | 45 qubits, over cap |

**A deviation from our own pre-registration, declared rather than reinterpreted.** We pre-registered a *measured* stopping rule: run until the finite-difference baseline degrades past 10 % at a declared budget. **That condition never triggered** — with the mesh growing as your statement requires, FD2 accuracy *improves* along the whole axis. The sweep ended by exhausting the declared Reynolds list, not by degradation. The rule we sealed assumed the wrong failure mode; saying so is worth more than the rule. **[measured]**

## 5 · Why the nonlinear term vanishes here — mechanism, and the law that restores it

This is the constructive part, and it is about the benchmark rather than about any solver.

**The mechanism.** The discrete nonlinearity vanishes **exactly if and only if the vorticity lives in a single eigenvalue layer of the 5-point discrete Laplacian**. In that case the stream function is ψ = c·w with c constant, so the Jacobian J(ψ,w) is identically zero pointwise — in the discrete operators, not only in the continuum. The statement's Taylor-Green vortex, the 45°-rotated one and the anisotropic ones all live in a single layer, which is why the benchmark never exercises the nonlinearity. The moment the field touches **two** layers, the ratio stops being zero. **[measured]**

*(The sealed artifact states this same rule in Spanish, its original language; the translation above is ours and the artifact is the source of the fact.)*

**The evidence, at N=16, Re=100.** Every member of the Taylor-Green family that lives in a single eigenvalue layer gives zero to machine precision; a field outside it does not. **[measured]**

| field | ‖A₂(w⊗w)‖ / ‖A₁w‖ |
|---|---|
| `tgv_statement` | 2.35e-16 |
| `tgv_k2` | 8.76e-17 |
| `tgv_rotado_45` | 3.40e-16 |
| `tgv_anisotropo_a2` | 1.96e-16 |
| `tgv_anisotropo_a3` | 2.15e-16 |
| `superpos_tgv_k1_k2_a0.01` | 9.54e-03 |
| `superpos_tgv_k1_k2_a0.1` | 9.34e-02 |
| `superpos_tgv_k1_k2_a0.5` | 3.13e-01 |
| `superpos_tgv_k1_k2_a1` | 3.21e-01 |
| `tgv_perturbado_eps0.0001` | 1.25e-04 |
| `tgv_perturbado_eps0.001` | 1.25e-03 |
| `tgv_perturbado_eps0.01` | 1.25e-02 |
| `tgv_perturbado_eps0.03` | 3.74e-02 |
| `tgv_perturbado_eps0.1` | 1.22e-01 |
| `tgv_perturbado_eps0.3` | 3.14e-01 |
| `tgv_perturbado_eps1` | 4.20e-01 |
| `aleatorio_banda_kmax2` | 2.93e-01 |
| `aleatorio_banda_kmax4` | 2.54e-01 |

**The law that restores it.** Adding a single mode outside the layer, with amplitude ε, returns nonlinearity of order ε — measured over four decades of ε: ε=0.0001 → 0.000125, ε=0.001 → 0.00125, ε=0.01 → 0.0125, ε=0.03 → 0.0374, ε=0.1 → 0.122, ε=0.3 → 0.314, ε=1 → 0.42. So the minimal modification to your benchmark is explicit and cheap: **superpose one foreign mode and the physics you want to test is back, at a strength you choose**. **[measured]**

## 6 · What we did to kill our own result

Before the conclusions, because that is what gives them the right to exist.

- **The vanishing term could have been a bug in our operators.** Control: the same matrices on a random band-limited field give a ratio of 2.93e-01, not zero. The zero belongs to the problem, not to the code. **[measured]**
- **The K-convergence check could have been measuring nothing** — on a field where A₂ is zero, any truncation order looks convergent. The test asserts the nonlinearity is active *before* measuring, so it cannot silently degenerate. **[by construction]**
- **Two errors are reported for the quantum arm at every point**, not one: end-to-end, and the same Carleman system solved exactly. Without that pair you cannot tell which of the two layers failed — and it is what shows the ansatz, not the truncation, is the binding wall. **[by construction]**
- **Every guard was mutation-tested**: each one has a case that makes it scream and a case where it must stay silent. A guard only ever tested for screaming passes every test. **[by construction]**

## 7 · What we cannot claim

- **No quantum advantage, at any point of the axis.** The pre-registration declared this as the expected outcome and it is what happened. **[measured]**
- **The quantum wall we report is of this ansatz and this machine class**, not of the method: a different ansatz moves it. We state where ours ceased, with the number. **[measured]**
- **The nonlinearity result is about the discrete operators we built** (2nd-order finite differences, 5-point Laplacian) and the continuum argument that matches them. A different discretisation deserves its own measurement. **[by construction]**
- **Decisions the pre-registration did not fix travel declared inside each artifact**, not in anyone's memory: 8 in the classical instrument and 7 in the quantum arm. **[by construction]**
- **The sweep artifacts are sealed** — `RQ-EXP-AIRBUS-EJE-001` (`sha256:e595fa2b873ee4…`), `RQ-EXP-AIRBUS-NOLIN-001` (`sha256:89b1d737f28f73…`) — and 2 of 2 are anchored in Bitcoin (OpenTimestamps), so their ordering is bounded from above by a clock neither we nor you control. The seal and the anchor are separate steps by the lab and the notary; this line reports what the archive says at build time, not what we intended. **[measured]**

## 8 · Reproduce this

One command rebuilds the whole axis from the instrument, with no network and no quantum hardware: `python3 barrido_airbus.py`. The instrument declares its own sha256 inside every artifact it writes, so the exact code behind each figure is identifiable. **[by construction]**

Each artifact carries **two** hashes and they answer different questions. The **file hash** says you downloaded the exact bytes we sealed. The **content hash** covers only the deterministic content — it excludes wall-clock timings, the machine description and timestamped filenames, which no re-run reproduces — and it is the one that stays the same when *you* re-run the instrument. Compare a re-run against the file hash and you will think you found an error in our work; compare it against the content hash and you are checking the science. Each artifact states inside itself which fields it excluded and why. **[by construction]**

| artifact | file hash — *«our exact bytes»* | content hash — *«the science reproduces»* |
|---|---|---|
| `barrido_airbus.json` | `f7d15b36b98d7d00176723aa53dd1e244defceda10423eb647847ef0d44ce5a5` | `1a197a03a3b609d37400fcad9d158587f9e26b37506fffd88eb44186eb4728ba` |
| `nolinealidad_donde_vive.json` | `d120124444713d3dad2e0beb636a024ef02609237938adc3afc1af8ac552455e` | `153fd1c3d0c6bc33bd6b0e62229f935d09678bf358dbf48f87189ac75d3a19eb` |

## 9 · Annex — the external yardstick

We report our own score against **REFORMS** (Kapoor et al., *Science Advances* 2024; 32 items, 8 modules) rather than leave the audit to you. A document that declares its own gaps costs the reader less than one that hides them. **[from the literature]**

Current score, read from our delivery standard at build time: **15 full · 8 partial · 9 absent**, of 32 items. The absent ones are named there one by one, not summarised as «a few pending», and each carries its closing plan. **[measured]**

---

*Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com*