# AGENTS.md

## Project rules

- Keep the Kaggriculture agent deterministic unless an experiment explicitly requires randomness.
- Keep strategy code, Kaggle SDK integration, simulation scripts, and submission tooling separate.
- Do not add secrets, Kaggle tokens, credentials, or private competition data to the repository.
- Run `python -m pytest` before committing changes.
- Run `python scripts/simulate.py --episodes 3` when changing strategy behavior.
- Do not enable real Kaggle submission until the competition-specific submission format and limits are verified from Kaggle's official page.
- Record meaningful strategy changes and simulation results in `docs/experiments.md`.

## Branches

- `feature/*`: tests and development only.
- `experiment/*`: strategy experiments only; never submit directly.
- `baseline/score-*`: immutable snapshots of the best known submitted agents. Update only by an explicit promotion commit.
- `main`: tested code and simulations only. It must not contain an unvalidated experiment as the default entrypoint.
- `submission`: an intentional, tested submission candidate. Pushing this branch may submit to Kaggle after the submission gate is enabled.

## Promotion and submission policy

- Keep the current best agent in a `baseline/score-<score>` branch and a matching annotated tag.
- Develop improvements on `experiment/*`; use pull requests or explicit promotion commits to move them to `main`.
- Only copy a candidate to `submission` after `pytest`, the required simulation, the extended comparison gate, and package verification pass.
- A Kaggle submission is an external side effect. Do not push `submission` for exploratory experiments.
- Preserve the stable baseline when a challenger is rejected. Never rewrite or force-push `main`, `submission`, or a baseline branch.
- Record the commit SHA, package SHA-256, simulation results, Kaggle submission ID, and score in `docs/experiments.md`.
