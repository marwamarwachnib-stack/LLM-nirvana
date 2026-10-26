# Pilot v2 LLM runs (archived 2026-10-26)

Cold prompt cache per call (decision 10) and evaluator v2, generated in session `20261025-204452` on mains power,
except cl-7b FizzBuzz iteration 2, which ended on battery. The v2 report is archived here as `pilot_report_v2.md`; `results/pilot_report.md` is now pilot v3.

Superseded by decision 11, which made evaluator v3:
- 11a: imports of the existing suite are carried into iteration-k files;
- 11b: assertions not reached because the test crashed earlier are excluded from the incorrect rate;
- 11c: truncated answers are counted and marked.

11a changes coverage after iteration 2, and with it the stopping rule, so the LLM jobs were regenerated. These files are
unchanged. `determinism.csv` is the check run against these stored answers (PLAN.md §13.13).
