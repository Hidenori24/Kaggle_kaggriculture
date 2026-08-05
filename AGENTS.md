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
- `main`: tested code and simulations only.
- `submission`: an intentional, tested submission candidate. Pushing this branch may submit to Kaggle after the submission gate is enabled.

