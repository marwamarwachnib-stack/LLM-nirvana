# Phase 1 summary: local LLMs vs Pynguin for Python unit test generation

Marwa CHNIB · PhD "Large Language Models for Automated Program Debugging" · 26 October 2026

## Goal

Phase 1 extends Bhatia et al. (LLM4Code @ ICSE 2024), which compared ChatGPT and Pynguin for Python unit test generation. ChatGPT is replaced by local, open models so that results are reproducible and energy can be measured on the machine that runs them. The generated test suites will be reused in Phase 2 for spectrum-based fault localization.

## Setup

- **Dataset:** the paper's `0_100 LOC` programs: 21 scripts, 19 function modules, 20 class modules.
- **Tools:** Pynguin 0.47 (5 seeds, 600 s budget) and three models served by Ollama on CPU: DeepSeek-Coder 1.3B and 6.7B Instruct, CodeLlama 7B Instruct.
- **Protocol:** the paper's prompts, with up to 5 improvement rounds that feed back the missed lines; temperature 0, fixed seed, fixed model versions.
- **Quality metrics (as in the paper):** statement and branch coverage, errors, incorrect assertions, number of rounds; plus test readability (naming).
- **Energy:** CPU package and DRAM energy from Intel RAPL, minus idle power, cross-checked with CodeCarbon (they agree within 0.0001 Wh). Runs start only on mains power.

## Pilot results (3 programs)

Statement / branch coverage of the final test suite, in %:

| Program | Pynguin | DeepSeek 6.7B | CodeLlama 7B | DeepSeek 1.3B |
| --- | --- | --- | --- | --- |
| FizzBuzz (script) | 0 (no tests) | 100 / 100 | 0 | 0 |
| change (functions) | 100 / 100 | 91.7 / 85.7 | 100 / 100 | 91.7 / 85.7 |
| bank-account (class) | 100 / 100 | 97.2 / 93.8 | 91.7 / 81.3 | 94.4 / 87.5 |

Energy per model over the 3 programs (net of idle): DeepSeek 1.3B 1.75 Wh, DeepSeek 6.7B 5.88 Wh, CodeLlama 7B 7.83 Wh. Pynguin uses 2.4 Wh per seed on bank-account.

## First observations

These come from 3 programs and are not statistical results.

1. **Consistent with the paper:** Pynguin cannot generate tests for scripts that read input at import, while an LLM can (DeepSeek 6.7B reaches 100 % on FizzBuzz).
2. **Improvement rounds have an energy cost:** on bank-account, DeepSeek 6.7B goes from 86 % to 97 % statement coverage over 3 rounds, but uses 4.3 times the energy of the first round (3.4 vs 0.8 Wh).
3. **Coverage is not test quality:** incorrect assertions range from 0 % to 93 % depending on model and program (paper: 28–39 % for ChatGPT). Pynguin has none, because its assertions record the current behaviour; on buggy code this would hide the bug. Both points motivate Phase 2.

## Issues found and fixed during the pilot

- Generated test files often lacked imports, so later rounds never ran; imports are now completed and every change is logged.
- Assertions in tests that crashed earlier were counted as incorrect; only executed assertions are now scored.
- Pynguin could exhaust memory on one program; it now runs with a memory cap.
- Model answers could differ between sessions; the cause was narrowed down, and a re-run sample after the main study will measure it.

## Limitations

- One laptop CPU, no GPU: absolute times and energy are specific to this machine, and the 7B models are slow.
- The 7B models can give slightly different answers between sessions, even at temperature 0.
- The programs are public, so the models may have seen them during training.

## Next steps

1. Full run on the 60 programs (about 47 hours of machine time).
2. Statistical comparison with Pynguin and with the paper's ChatGPT results.
3. Phase 2: run the generated tests on seeded faults (mutants) and real bugs (BugsInPy), apply spectrum-based fault localization (Ochiai, Tarantula, DStar), and compare tools on localization accuracy and energy.

Details: [`PLAN.md`](PLAN.md) (full protocol and decisions) and [`results/pilot_report.md`](results/pilot_report.md) (complete pilot results).
