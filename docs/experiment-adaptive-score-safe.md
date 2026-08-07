# Adaptive score-safe experiment

- Base: `submission` branch, current replay-derived policy.
- Candidate: add only final-day liquidation of sellable shed inventory.
- Normal actions remain identical to the base policy through step 695.
- Local validation: 15 pytest tests passed; 3-episode candidate rewards were 185096 / 195818 / 203856.
- A temporary premium-sale price gate was rejected: it won only 2 of 10 paired games against the replay baseline.
- A temporary +8% WHEAT procurement rule was rejected: it won 0 of 10 paired games and materially reduced terminal cash.
- Decision: keep `submission` unchanged. This branch is for reproducible experiments only and must not be merged or submitted without a clearly positive paired win-rate result.
