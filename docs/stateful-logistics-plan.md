# Stateful logistics redesign

## Goal

Keep the validated replay policy as the fallback while introducing a
restart-safe state ledger and task scheduler.  The redesign must not assume
that a previous action succeeded: every decision is derived from the current
observation.

## Stages

1. **Ledger and shadow mode** — extract resources, workers, tiles, jobs, and
   short-horizon pressure without changing actions.
2. **Transport safety** — handle an already-loaded worker only when the
   current observation proves that dropping the load is legal and the replay
   action would otherwise strand it.
3. **Animal and fertilizer jobs** — assign only urgent local work with an
   explicit return path and feed reserve.
4. **Crop portfolio** — choose short-cycle crops only when seed, planting,
   harvest, and sale slots all exist in the same plan.
5. **Market planner** — preserve the proven SELL ordering and optimize only
   quantities that remain safe under the resource ledger.

## Safety rules

- The stable fallback remains unchanged until a challenger passes direct
  head-to-head validation.
- Never replace a PASS merely because a tile happens to be actionable; the
  replacement must also have a transport or follow-up plan.
- Preserve animal feed reserve and shed capacity before investing in crops.
- Do not store user-provided episode JSON in the repository.
- A challenger must pass pytest, Ruff, three simulations, hostile benchmark,
  and the full head-to-head gate before it can reach `submission`.

## Current implementation

`src/kaggriculture_agent/logistics_state.py` provides the restart-safe ledger,
resource plan, job candidates, and JSON-friendly shadow report.  It is
intentionally not wired into the production action path yet.

The first transport challenger was rejected: replacing a movement/PASS with
`DROP` for safe products at the shed entrance scored **0-4**, with a mean
margin of **-43.39%** against the stable reference over two seeds and both
seats.  The lesson is that a local drop is not safe without a destination and
follow-up plan for the worker's next job.

The registered `stateful` benchmark was then run against the four recorded
opponent tapes.  It scored **4-4** with mean **84,974**, while the unchanged
`replay` policy scored **8-8** with mean **148,901** on the same eight matches.
The challenger is therefore rejected and must not be wired into production.
This also confirms that the hostile benchmark is sensitive enough to catch a
bad local logistics override.

The next candidate must represent a complete, restart-safe macro plan:
`load -> route -> unload -> return/next job`.  A one-turn action replacement is
not eligible for promotion unless the current observation proves both the
destination and the next legal action.  The planner may remain shadow-only
until those invariants are covered by replay tests.

The first complete-route prototype (`macro`) was deliberately restricted to
actors whose replay action was `PASS`, saleable output only, and enough current
shed capacity for the whole load.  It passed **42 tests**, matched the hostile
benchmark at **8-0 / mean 148,901**, but scored only **1-3** in the direct
head-to-head gate with mean margin **0.00%**.  It is neutral rather than an
improvement and remains experimental.
