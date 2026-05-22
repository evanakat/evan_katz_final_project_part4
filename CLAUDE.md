# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repository currently contains **only a single artifact**: `Final Project.pdf`. There is no source code, no notebooks, no datasets, no dependency manifest (e.g. `requirements.txt`, `pyproject.toml`, `environment.yml`), no tests, and no build or CI configuration. Do not invent commands for building, linting, or testing — none exist yet. If asked to "run tests" or "build", report that nothing is set up and ask what the user wants scaffolded.

The git history confirms this is a presentation-only repo: prior commits (`Presentation`, `Delete Final Project.pdf`, `Updated`, `Update`) only add and modify the PDF.

## What the project is about

`Final Project.pdf` is a slide deck by Evan Katz titled *"Can we predict in how many months an employee will leave?"*. The salient details that any future code in this repo would be implementing:

- **Problem**: Regression — predict, for a terminated employee, the number of months they worked before termination (voluntary or involuntary).
- **Data source**: HRIS export from Workday, ~1,815 rows of termination data going back to 2008. The dataset itself is **not committed** to this repo.
- **Target variable**: months of tenure at termination.
- **Features used in the deck**: gender, compa-ratio, location, job profile, job title, years of service, is-a-manager flag.
- **Models tried** (per the deck, with reported scores):
  - Linear Regression — train 0.80 / test -0.24
  - Decision Tree — 0.30
  - Random Forest Regressor — train 0.90 / test 0.21 (chosen as best-fit despite overfitting)
- **Validation**: train/test split and KFold cross-validation where applicable.
- **Stated next steps** (from the closing slide): larger dataset and additional correlated variables.
- **Ethical note called out in the deck**: feature set includes gender, so any implementation must consider bias (the deck explicitly references Amazon's pulled recruiting model).

## Working in this repo

- Before scaffolding code, ask the user which stack they want (the deck implies Python + scikit-learn, but this is not declared anywhere in the repo).
- The dataset is sensitive HR data and is not present. Do not commit any sample/real HR data unless the user explicitly provides and approves it.
- The active development branch for documentation work is `claude/claude-md-docs-Vkdoo` (per session instructions); confirm the intended branch before pushing code changes.
