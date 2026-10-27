# Phase 1 summary

Marwa CHNIB · PhD "Large Language Models for Automated Program Debugging"

## What I did

I repeated the study of Bhatia et al. (ICSE 2024), which compared ChatGPT and Pynguin for writing Python unit tests, but with **local LLMs** (DeepSeek-Coder, CodeLlama) instead of ChatGPT. I also **measure the energy** each tool uses.

I built the full pipeline and tested it on 3 programs (a pilot) before the full run on 60 programs.

## Pilot results

Statement coverage of the generated tests:

| Program | Pynguin | DeepSeek 6.7B | CodeLlama 7B | DeepSeek 1.3B |
| --- | --- | --- | --- | --- |
| FizzBuzz (script) | 0 % | 100 % | 0 % | 0 % |
| change (functions) | 100 % | 92 % | 100 % | 92 % |
| bank-account (class) | 100 % | 97 % | 92 % | 94 % |

## Main observations

1. **As in the paper**, Pynguin cannot test scripts, but an LLM can.
2. **Asking the model to improve its tests** raises coverage (86 % → 97 %) but uses about **4 times more energy**.
3. **High coverage does not mean good tests**: up to 93 % of the LLM assertions are wrong on one program. This motivates Phase 2.

## Next steps

1. Full run on the 60 programs.
2. Phase 2: use these tests to locate bugs (spectrum-based fault localization) and compare the tools.

Full details: [PLAN.md](PLAN.md) and [pilot report](results/pilot_report.md).
