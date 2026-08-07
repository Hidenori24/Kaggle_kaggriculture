# Adaptive score-safe experiment

- Base: `submission` branch, current replay-derived policy.
- Candidate: add only final-day liquidation of sellable shed inventory.
- Normal actions remain identical to the base policy through step 695.
- Local validation on the source workspace: 15 pytest tests passed; 3-episode candidate rewards were 198043 / 207120 / 184580.
- Paired comparisons were mixed, so this branch must not be merged to `main` or copied to `submission` without a new validation decision.
