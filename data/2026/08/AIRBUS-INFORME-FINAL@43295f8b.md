# Airbus — Quantum Solvers for Predictive Aerodynamic Modeling

**Rosetta Quantum** · 2026 Global Quantum + AI Challenge · Phase 1

> Every figure in this document is read from an artifact at build time, never typed. Each claim carries one of three labels — **measured**, **by construction**, or **from the literature** — and anything without a label is not here.

## Executive summary

You asked for a quantum solver for the 2D convecting Taylor-Green vortex, and for the curve of time-to-solution and error as Reynolds grows. **The honest headline is that we did not beat the classical solvers, and that the most useful thing we found is a measurement on your benchmark rather than a result of ours.**

**What we can deliver.** The full axis, 8 points from Re = 10 to 102,400 with the mesh coupled as your §4.1 requires and scored against the closed-form solution of your §5.3. The classical error *falls* by a factor of 3,700 along it while the cost climbs. Memory — one of your three expected outcomes — is answered with a number for the first time.

**What we cannot.** The order of Carleman that carries the nonlinear physics needs 21–45 qubits from the very first point and never ran. The order that fits drops that term, and it loses to finite differences by between 28 and 89 times. We pre-registered that outcome as the expected one before writing a line of the instrument.

**And what we found instead, which is why this report is worth your time.** In the vortex your statement specifies, the nonlinear term vanishes exactly — machine precision, in the discrete operators. So we measured what the case can still detect: a solver that ignores that term **entirely** is wrong by 2.11e-15 on your benchmark. It cannot be told apart from a correct one. On the family we repaired, the same solver is wrong by up to 3.53e+00, and the threshold is tunable across a factor of 37,000. **The property that gives your case its exact analytical solution is the same one that makes it blind.**

Everything here cost **US$0**, ran on one laptop, and is sealed and timestamped. §14 tells you how to check any of it without asking us.

## 1 · The four findings, in order

The executive summary above is the short version. This section is the four findings with their numbers, each pointing to the section that carries the measurement, the method and the caveats. **The last two are about your benchmark rather than about us**, and they are why we think this is worth reading past the headline.

**One — the classical cost explodes; the accuracy does not.** Across Re = 10 to 102,400 with the mesh coupled as your statement requires, the finite-difference error *falls* by a factor of 3,700 (2.01e-03 → 5.37e-07). **[measured — reproduces bit-for-bit]** Its wall time rises by a factor of ~130,000 on this machine (the spectral arm, ~250,000). **[measured on one machine; not comparable across computers]**

**Why the two labels differ, and what you can do with each number.** We re-ran the whole axis on the same machine and compared it point by point: 19 of 19 errors reproduced to the last digit. The wall times moved by 4–31 % per arm, and the *ratios* between arms moved by a median of 38 % — a quotient adds the noise of both its terms. A ratio cancels a machine's overall speed and amplifies measurement noise; with times this small, the noise wins. So the errors are a precision result and the timings are an order-of-magnitude statement, and we say which is which instead of giving both the same weight. This is two runs on one machine, so it bounds run-to-run noise and says nothing about another computer. **[measured]**

**Two — the order of Carleman that carries the physics never ran; the degraded one did, and fell short.** **K = 2 — the order that actually includes Carleman's quadratic block — solved 0 of 8 points on the axis**: it needs 21–45 qubits, over the declared cap from the very first point. **K = 1, which drops that block, solved 3 of 8** (10–22 qubits), with a relative error of 4.86e-02–8.03e-02 where it ran — 28–89 times the finite-difference error at the same points. So the quantum arm does not lose the comparison: the version with the physics in it cannot be posed at this mesh coupling, and the version that can be posed is not the one that matters. **[measured]**

On its own ladder at fixed Re it reproduces the exact linear system up to N=16, and the ansatz stops reaching at N=32. **[measured]**

**Three — and this one is about your benchmark, not about us.** In the Taylor-Green vortex as specified, the nonlinear term vanishes *exactly* — ratio 2.35e-16 of the linear term, at machine precision, in the discrete operators and not only in the continuum. The obstacle your statement names — mapping nonlinear physics onto unitary hardware — **cannot be exhibited on the case chosen to test it**. We found the mechanism and the law that restores it; §6 gives both, and they are the constructive part of this submission. **[measured]**

**Four — and here is what that costs you, measured rather than argued.** So we asked what your case can still *detect*. We built a manufactured solution so the nonlinear term is genuinely active, and then ran a solver that **ignores that term entirely**. On the Taylor-Green vortex as specified, that solver is wrong by **2.11e-15** — machine zero. **Your benchmark cannot tell it apart from a correct one.** On the repaired family the same solver is wrong by between 9.48e-05 and 3.53e+00: the detection threshold becomes tunable across a factor of **37,000**. 5 of the 18 variants are blind, and they are exactly the 5 that live in a single eigenvalue layer. **[measured]**

## 2 · Results against your three expected outcomes

Your portal asks for three things. We answer each here, with the number and a pointer to where it lives, including the one where the answer is «not yet» — that one first.

**1 · «A working solver» (FTQC or tensor-network inside finite volumes) for the 2D convecting Taylor-Green vortex.** **Partially, and we say which part.** Carleman at order **K = 2 — the order that carries the quadratic term, i.e. the physics — solved 0 of 8 points on the axis**: it needs 21–45 qubits, above the declared cap from the very first point. Order **K = 1**, which drops that term, solved **3 of 8** with a relative error of 4.86e-02–8.03e-02, 28–89 times the finite-difference error at the same points. So there is a solver, it runs, and the version that carries the physics cannot be posed at the mesh coupling your statement requires. Detail in §5 and §7. **[measured]**

**2 · Scaling analysis: time-to-solution, memory requirements, and error scaling with Reynolds (Re = 10, 100 and beyond).** **Delivered, all three.** The axis runs from Re = 10 to 102,400 over 8 points with the mesh coupled as your §4.1 requires, against the closed-form solution of your §5.3 — table in §5, with the wall-clock caveat stated there. **Memory** is the one we can now answer with a number: the field stays at bond dimension **2** across the whole perturbed family, which is what makes the second finding in §7 possible. **[measured]**

**3 · Comparison against classical solvers, demonstrating quantum or quantum-inspired advantage.** **No advantage, and the comparison produced something we think is worth more.** The classical arms win at every point of the axis; we pre-registered that as the expected outcome and it is what happened. What the comparison did produce is a measurement *on the benchmark itself*: the quantum-inspired metric you invite — tensor networks, via memory — **cannot see the physics the challenge is about**. That is in §7, with the detection threshold that repairs it. **[measured]**

## 3 · The question, and when it was fixed

Pre-registration `RQ-PREREG-AIRBUS-001`, content hash `sha256:39a16cf63a36095217fdf5fb…`.

It was committed in `d662d9de`, and **at that commit not one line of the instrument existed** — that is a property of the git history, verifiable by you, not a claim of ours. **[by construction]**
The pre-registration is confirmed in **Bitcoin block 963190** — the earliest attestation in its OpenTimestamps receipt when this was built; later upgrades only add more. Check it in any block explorer, or run `ots verify` against the `.ots` file beside the seal. The ordering is bounded from above by a clock neither we nor you control. **[measured]**

The pre-registration declared **both outcomes as deliverables before measuring**: if the quantum arm crossed, the crossing would be incontestable because the referee is a closed formula; if it did not, the curve itself is what your statement asks for. It also declared the known obstacle (Carleman truncation against a nonlinear, non-unitary problem) as a risk, not as a later discovery. **[by construction]**

## 4 · The referee, and why this benchmark is unusually strong

The statement carries the **exact analytical solution** (§5.3), so the error of any method is measured against a closed form at any Reynolds number. There is no estimated ground truth and no reference implementation to trust: the referee never degrades and never runs out. **[by construction]**

Two independent paths agree on it: the spectral arm reproduces the analytical solution to 6.27e-09 at the first point. A single arm matching a formula could be a lucky bug in either; two constructions agreeing is evidence. **[measured]**

## 5 · The axis: time-to-solution and error vs Reynolds

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

## 6 · Why the nonlinear term vanishes here — mechanism, and the law that restores it

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

## 7 · What your benchmark can detect — measured

A test case earns its place if it separates a correct solver from a wrong one. So we measured that directly, and we state the method and its price before the number.

**The method, and it is the standard one.** We use a *manufactured solution* — the technique CFD uses for code verification. Choose the target field, compute the forcing that makes it an exact steady solution of the full system, and the nonlinear term is then genuinely active rather than absent. Any solver that gets the nonlinearity wrong no longer reproduces the target, and the size of its error is the case's detection threshold. **[by construction]**

**The price, stated up front.** A manufactured solution adds a source term: this is **code verification, not physical validation**, and it is not free decay. It also measures a *different axis* from the one you asked for — accuracy with the nonlinearity active, not time-to-solution against Reynolds. **It does not replace the axis in §5; it covers the dimension your case cannot reach.** One further caveat: the discrete Laplacian is singular on the constant mode, so the displacement is solved in least squares. It changes no conclusion and we say it anyway.

**The measurement.** We ran a solver that ignores the nonlinear term *entirely*:

| field | eigenvalue layers | error of a solver that ignores the nonlinearity | detects it? |
|---|---|---|---|
| `tgv_statement` | 1 | 2.11e-15 | **no — blind** |
| `tgv_k2` | 1 | 3.94e-16 | **no — blind** |
| `tgv_rotado_45` | 1 | 1.03e-15 | **no — blind** |
| `tgv_anisotropo_a2` | 1 | 7.99e-16 | **no — blind** |
| `tgv_anisotropo_a3` | 1 | 1.56e-15 | **no — blind** |
| `superpos_tgv_k1_k2_a0.01` | 2 | 7.28e-03 | yes |
| `superpos_tgv_k1_k2_a0.1` | 2 | 7.21e-02 | yes |
| `superpos_tgv_k1_k2_a0.5` | 2 | 2.91e-01 | yes |
| `superpos_tgv_k1_k2_a1` | 2 | 3.64e-01 | yes |
| `tgv_perturbado_eps0.0001` | 2 | 9.48e-05 | yes |
| `tgv_perturbado_eps0.001` | 2 | 9.48e-04 | yes |
| `tgv_perturbado_eps0.01` | 2 | 9.48e-03 | yes |
| `tgv_perturbado_eps0.03` | 2 | 2.84e-02 | yes |
| `tgv_perturbado_eps0.1` | 2 | 9.39e-02 | yes |
| `tgv_perturbado_eps0.3` | 2 | 2.61e-01 | yes |
| `tgv_perturbado_eps1` | 2 | 4.74e-01 | yes |
| `aleatorio_banda_kmax2` | 5 | 3.53e+00 | yes |
| `aleatorio_banda_kmax4` | 14 | 1.34e+00 | yes |

**5 of 18 are blind, and they are exactly the ones confined to a single eigenvalue layer.** Your Taylor-Green vortex is one of them. **[measured]**

**And the degenerate class is larger than your case.** It is not «the Taylor-Green vortex» and it is not «rank one»: it is **vorticity confined to a single eigenvalue layer of the discrete Laplacian**. A superposition of two different modes from the same layer — rank two, not rank one — is blind as well, at 1.48e-15. That characterisation also explains the rotated vortex in §6 without appealing to any coincidence. **[measured]**

**A second blindness, on the axis you also ask for: memory.** Your brief asks for memory requirements and invites quantum-*inspired* advantage — that is, tensor networks. Across the whole perturbed family the field stays at bond dimension **2** while the nonlinearity ranges over a factor of 3,400. A tensor network cannot tell the degenerate case from the perturbed ones: **they cost it the same.** A competitor who follows your brief to the letter will report a spectacular memory win and will have learned nothing about the nonlinearity — not through any fault of theirs, but because the metric you asked for cannot see it. **[measured]**

**What we are not claiming.** «Low rank» and «single layer» are *not* the same property; we tested that and it fails in both directions. A product field of two von Mises factors is rank two, spans 40 layers, and its nonlinearity is **not** zero (8.63e-02). The three properties of your vortex — rank one, single layer, zero nonlinearity — do not merely coincide: **they all follow from building the field out of one product Fourier mode.** Same cause, not correlation. **[measured]**

**And that is the sentence we would put in front of your committee:** you chose this vortex *because* it has an exact analytical solution — your statement calls it a perfect benchmark for that reason. The property that gives it that exact solution is the same one that makes it blind. **Its greatest virtue and its blind spot are the same fact.** That is not a flaw anyone introduced; it is structure — and §6 gives the law that repairs it, with the threshold above as the dial.

## 8 · What we did to kill our own result

Before the conclusions, because that is what gives them the right to exist.

- **The vanishing term could have been a bug in our operators.** Control: the same matrices on a random band-limited field give a ratio of 2.93e-01, not zero. The zero belongs to the problem, not to the code. **[measured]**
- **The K-convergence check could have been measuring nothing** — on a field where A₂ is zero, any truncation order looks convergent. The test asserts the nonlinearity is active *before* measuring, so it cannot silently degenerate. **[by construction]**
- **Two errors are reported for the quantum arm at every point**, not one: end-to-end, and the same Carleman system solved exactly. Without that pair you cannot tell which of the two layers failed — and it is what shows the ansatz, not the truncation, is the binding wall. **[by construction]**
- **Every guard was mutation-tested**: each one has a case that makes it scream and a case where it must stay silent. A guard only ever tested for screaming passes every test. **[by construction]**

## 9 · What we cannot claim

- **No quantum advantage, at any point of the axis.** The pre-registration declared this as the expected outcome and it is what happened. **[measured]**
- **The quantum wall we report is of this ansatz and this machine class**, not of the method: a different ansatz moves it. We state where ours ceased, with the number. **[measured]**
- **The nonlinearity result is about the discrete operators we built** (2nd-order finite differences, 5-point Laplacian) and the continuum argument that matches them. A different discretisation deserves its own measurement. **[by construction]**
- **Decisions the pre-registration did not fix travel declared inside each artifact**, not in anyone's memory: 8 in the classical instrument and 7 in the quantum arm. **[by construction]**
- **The sweep artifacts are sealed** — `RQ-EXP-AIRBUS-DETECCION-001` (`sha256:6c7f335d8a3ce7…`), `RQ-EXP-AIRBUS-EJE-001` (`sha256:e595fa2b873ee4…`), `RQ-EXP-AIRBUS-NOLIN-001` (`sha256:89b1d737f28f73…`), `RQ-EXP-AIRBUS-RANGO-001` (`sha256:96f40af89b0f62…`) — and all 4 carry an OpenTimestamps receipt. A receipt is not yet a Bitcoin block: the calendar returns it immediately and the confirmation lands hours later, once the calendar publishes its tree. We will not print a count here, because any count we print expires the moment the next confirmation arrives. Run `ots upgrade` on the `.ots` files beside each seal and you will see the state as of the moment *you* read this — including confirmations that did not exist when we wrote it. **[measured]**

## 10 · Feasibility and resource requirements

Everything above ran on one laptop, on open tools, and the cost is measured rather than planned: **US$0**. No quantum hardware was used and no paid backend was called — the quantum arms are exact statevector simulation. The axis took 1,480 seconds of wall-clock end to end on macOS-26.5.2-arm64-arm-64bit with 32 GB of RAM, under Python 3.9.6 with numpy 1.23.5. **[measured]**

**What the next step needs, and what it does not.** Nothing above is blocked by funding or by hardware access: it is blocked by qubit count. Order K = 2 needs 21–45 qubits at the mesh coupling your statement requires, and that is a property of the formulation, not of our budget — a larger machine moves it, a larger grant does not. What a next phase would buy is measurement time on the two things we could not settle here: whether a formulation exists whose cost tracks the mesh instead of its square, and what the repaired benchmark says about solvers other than ours. **[measured]**

## 11 · Expected impact

**We are not promising you a quantum advantage, and this report does not contain one.** The impact we think is real is the other one: your challenge selects for a test case that cannot measure what the challenge is about, and every team that follows the brief will hit the same wall without necessarily noticing. What §7 delivers is a repaired family with the detection threshold as a dial, and an exact arbiter for it — so the next round of submissions can be scored on whether they got the physics right, not on whether they compressed a degenerate field efficiently.

The second usable output is the characterisation itself: the degenerate class is **vorticity confined to a single eigenvalue layer of the discrete Laplacian**, which is larger than the vortex you chose and easy to test for. Any benchmark you build in future can be checked against that in one line before it is adopted.

## 12 · Team profile and capability

**Team:** Rosetta Quantum — **Blue Tuna SpA**, Punta Arenas, Chile (solo founder-operator). **Lead:** Nicholas Iakl Freundlich · hello@rosettaquantum.com.

**Background:** founder & CEO of Sumeria (AI conversation analytics, 9+ years) and founder of Yu-Track (software for financial-services collections). Commercial Engineer and MSc. The expertise brought here is the *consume-the-verdict* side of the problem — shipping systems whose outputs someone has to trust — rather than the sell-the-qubit side. **This is our third quantum submission** — Cleveland and E.ON went out before it — and the report is written so that you do not have to take our word for any part of it.

**Why this can execute a next phase:** the verification infrastructure this challenge would need is not a plan, it is running. **127 sealed artefacts** across the whole archive — 93 runs, 11 reports, 10 pre-registrations, 4 recipes, 4 manifests, 3 errata, 1 prediction and 1 verdict — each with its own recomputable content hash and an OpenTimestamps receipt, mirrored on two independent hosts. This submission is 8 of them, and §14 tells you how to check every one without asking us for anything. **[measured]**

## 13 · What we are asking for

**Three things, and none of them is a cheque before a conversation.**

1. **An hour with whoever owns the benchmark.** The finding in §7 is either useful to you or it is wrong, and both are worth an hour. If it is useful, the repaired family and its threshold are yours to use with or without us.
2. **One case you actually care about.** Everything here is on the vortex your statement specifies. The degenerate class we characterised is easy to fall into by accident; we would rather measure whether your real cases are in it than speculate.
3. **A next phase scoped to the measurement, not to a promise.** Same method as this one: pre-registered before the instrument exists, sealed, timestamped, and published whether it works or not. This report is what a negative result looks like when it is delivered on purpose.

## 14 · Reproduce this

One command rebuilds the whole axis from the instrument, with no network and no quantum hardware: `python3 barrido_airbus.py`. The instrument declares its own sha256 inside every artifact it writes, so the exact code behind each figure is identifiable. **[by construction]**

Each artifact carries **two** hashes and they answer different questions. The **file hash** says you downloaded the exact bytes we sealed. The **content hash** covers only the deterministic content — it excludes wall-clock timings, the machine description and timestamped filenames, which no re-run reproduces — and it is the one that stays the same when *you* re-run the instrument. Compare a re-run against the file hash and you will think you found an error in our work; compare it against the content hash and you are checking the science. Each artifact states inside itself which fields it excluded and why. **[by construction]**

| artifact | file hash — *«our exact bytes»* | content hash — *«the science reproduces»* |
|---|---|---|
| `barrido_airbus.json` | `f7d15b36b98d7d00176723aa53dd1e244defceda10423eb647847ef0d44ce5a5` | `1a197a03a3b609d37400fcad9d158587f9e26b37506fffd88eb44186eb4728ba` |
| `nolinealidad_donde_vive.json` | `d120124444713d3dad2e0beb636a024ef02609237938adc3afc1af8ac552455e` | `153fd1c3d0c6bc33bd6b0e62229f935d09678bf358dbf48f87189ac75d3a19eb` |

## 15 · Annex — the external yardstick

We report our own score against **REFORMS** (Kapoor et al., *Science Advances* 2024; 32 items, 8 modules) rather than leave the audit to you. A document that declares its own gaps costs the reader less than one that hides them. **[from the literature]**

Current score, read from our delivery standard at build time: **15 full · 8 partial · 9 absent**, of 32 items. The absent ones are named there one by one, not summarised as «a few pending», and each carries its closing plan. **[measured]**

---

*Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com*