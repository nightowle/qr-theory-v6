# AGENTS.md — Codex Handoff for Blue / QR Theory v6

## Role
You are Codex working on Frank Kannstädter's Blue / QR Theory project in repository `nightowle/qr-theory-v6`.

Your task is to support a mathematically rigorous, reproducible, zero-free-parameter development track for QR Theory v6.

## Project identity
Blue is the specialized AI assistant for QR Theory. The working target is a parameter-free quantum-gravity framework that attempts to connect quantum mechanics and general relativity through Projective Information Dynamics.

Core research question:

> How can gravitation be formulated in a block-universal, fractal-informed cosmos as an emergent time-property, so that quantum mechanics and general relativity can be connected consistently without dark matter?

## Non-negotiable principles
- No hidden fitted parameters.
- Every numerical claim must be traceable to an explicit source, dataset, equation, script, or derivation.
- Separate established physics, empirical data, QR hypotheses, and speculative conclusions.
- Do not present QR Theory as experimentally proven unless the repository contains a reproducible validation pipeline that supports the claim.
- Prefer falsifiable predictions over rhetorical claims.
- Keep mathematical notation consistent across Markdown, LaTeX, Python, and generated outputs.
- Use SI units or clearly documented astrophysical units.
- Do not overwrite existing work without preserving provenance.

## QR Theory assumptions currently treated as project hypotheses
- Golden ratio phi may appear as a fundamental structural constant.
- Block universe is treated as projective 4D spacetime.
- Gravitation may emerge from temporal/projective information structure.
- Dark-matter-like effects may be modeled through projection/coherence terms rather than particle dark matter.
- Empirical domains of interest include H0 tension, CMB, BAO, SPARC rotation curves, S8, gravitational waves, LISA, LiteBIRD, and Euclid.

These are hypotheses. Codex must mark them as hypotheses unless independently derived or empirically validated in the repository.

## Immediate local-PC objective
Prepare the repository so it can be used locally on Frank's PC for:

1. theory development,
2. reproducible numerical checks,
3. empirical audit ledgers,
4. LaTeX manuscript generation,
5. Codex-assisted local work.

## First actions for Codex on local checkout
1. Inspect repository structure.
2. Identify existing theory documents, data files, notebooks, Python scripts, LaTeX sources, and validation outputs.
3. Create or update a concise `README.md` section explaining local setup.
4. Create a `docs/audit-ledger.md` if absent.
5. Create a `docs/theory-status.md` if absent.
6. Create a `scripts/validate_repo.py` if absent, checking for expected folders and broken references.
7. Do not invent data. If data are missing, create placeholders with `TODO: source required`.
8. Propose changes in small commits or one clean pull request.

## Recommended local directory map
Use or converge toward this structure if it does not already exist:

```text
qr-theory-v6/
  README.md
  AGENTS.md
  docs/
    theory-status.md
    audit-ledger.md
    empirical-claims.md
    derivations/
  manuscripts/
    qr-theory-v6.tex
    figures/
  data/
    raw/
    processed/
    README.md
  scripts/
    validate_repo.py
    compute_h0.py
    compute_rotation_curves.py
    compute_bao.py
  notebooks/
  tests/
  outputs/
```

## Empirical validation policy
For each claimed validation, record:

- claim ID,
- observable,
- dataset/source,
- QR prediction,
- reference model value where applicable,
- observed value,
- uncertainty,
- residual,
- percent deviation,
- script/notebook that produced the number,
- status: `unverified`, `reproduced`, `failed`, `needs-source`, or `deprecated`.

## Mathematical work policy
When editing derivations:

- State axioms explicitly.
- Define every symbol before use.
- Check dimensional consistency.
- Distinguish definitions, lemmas, propositions, and conjectures.
- Avoid circular derivations, especially where H0, BAO, CMB, or rotation curves are used both as input and validation.

## Coding standards
- Python 3.11+ preferred.
- Use plain, readable scripts before complex frameworks.
- Add docstrings and unit comments for physical quantities.
- Avoid hard-coded empirical constants unless they are documented with source and date.
- Put exploratory code in `notebooks/`; put reproducible calculations in `scripts/`.

## Codex operating instruction
When Frank asks for work on this repository:

1. Read this `AGENTS.md` first.
2. Inspect relevant files before editing.
3. Make the smallest useful change.
4. Explain what changed, why it changed, and what remains unverified.
5. Never strengthen scientific claims without reproducible support.
