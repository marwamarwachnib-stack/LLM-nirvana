# Experiment 2 — Context ladder for real-bug detection with a code LLM (plan)

Status: **plan, before implementation** · builds on Experiment 1 (`RESULTS_experiment1.md`).

## Motivation
Experiment 1 showed that fine-tuned CodeBERT detects real BugInPy bugs at chance level (ROC-AUC ≈ 0.50) from the function text alone, while the same pipeline detects injected obvious bugs perfectly (1.00). In vulnerability detection, recent work reports that LLMs look weak mainly because they are evaluated on isolated functions, and that well-chosen context changes the picture (Li et al. 2025, "CORRECT"; Li et al. 2026, CPRVul). BugsInPy is also likely part of LLM training data (Haroon et al. 2026), so LLM results on it must be checked for memorisation. We found no study combining, for **general real Python bugs**: paired buggy/fixed hard negatives, shortcut controls, a positive control, a **context ladder** and a **memorisation probe**. (Literature check: 3 searches; to be confirmed with the supervisor.)

## Research questions
* **RQ1** — Does a code LLM, zero-shot, detect real bugs from the function alone (C0) better than chance and better than fine-tuned CodeBERT?
* **RQ2** — Which context makes real bugs detectable: specification, file context, failing test?
* **RQ3** — Is any success due to memorisation of BugInPy rather than understanding?
* **RQ4 (sanity)** — Does the LLM pipeline detect injected obvious bugs (positive control)?

## Model
* Main: **Qwen2.5-Coder-7B-Instruct**, 4-bit (bitsandbytes), on a free Colab T4. Open weights, reproducible, no cost.
* Optional later: a stronger API model, if available.
* **Zero-shot**: no training, so no cross-project training leakage. Every evaluated sample is test data.
* **Score** = P("Yes") / (P("Yes") + P("No")) for the next token after the question *"Does this function contain a bug? Answer Yes or No."*. This is deterministic, needs one forward pass and no generation, and gives a probability so that ROC-AUC can be computed.

## Data (reused from Experiment 1, dataset v2 after Phase 5)
* Evaluation subset (stratified by project): **300 buggy/fixed pairs** (600 functions) + **150 unchanged functions**, seed 42. It can be scaled up if the GPU budget allows.
* **Dev set** for prompt selection: about 40 pairs from one project, **excluded** from the evaluation, so that no prompt tuning is done on test data.

## Context ladder (cumulative)
| Level | Input given to the LLM | Leakage control |
|---|---|---|
| **C0** | the function (normalised, as in Exp. 1) | identical to Exp. 1 |
| **C1** | + the function's original **docstring** (specification) | docstring taken from the **buggy** version for both members of a pair (the fix may edit it) |
| **C2** | + **file skeleton**: imports, class headers, signatures of the other functions | skeleton from the **buggy** commit for all samples of a bug, target function excluded (the fix may add helpers elsewhere) |
| **C3** | + the **failing test** (from `bug.info` / `run_test.sh`) | the same test for buggy and fixed versions (symmetric); for unchanged functions it is reported separately, because the test mentions another function |

## Memorisation probe (RQ3)
Consistent, semantics-preserving **renaming** of the function name, parameters and local variables (AST-based), applied identically to both members of a pair, at C0 and C3. A large drop in performance after renaming indicates memorisation.

## Positive control (RQ4)
The same injected bug as Exp. 1 (`_ = 1 / 0`) on ~100 clean functions at C0. Expected ROC-AUC ≈ 1.

## Metrics
* **Primary: paired accuracy** on buggy/fixed pairs: share of pairs where the buggy version gets the higher bug score (chance = 0.5). This is the cleanest test, since both inputs differ only by the fix.
* ROC-AUC (all samples, buggy vs fixed, buggy vs unchanged); F1 reported but not used for conclusions.
* 95% bootstrap CIs over bugs; paired comparisons between context levels (bootstrap of differences, McNemar on pairs).
* Comparison with Exp. 1 CodeBERT out-of-fold scores on the same subset.

## Phases (step by step, same workflow as Exp. 1)
| Phase | Content |
|---|---|
| E2-1 | Setup: GPU check, load Qwen2.5-Coder-7B-Instruct 4-bit, scoring function, smoke test |
| E2-2 | Evaluation subset + dev set; build the context ladder C0–C3 with leakage controls; renaming |
| E2-3 | Prompt selection on the dev set only |
| E2-4 | Positive control |
| E2-5 | Inference on all levels (resumable, cached on Drive) |
| E2-6 | Evaluation: paired accuracy, AUC, CIs, level-to-level differences, CodeBERT comparison |
| E2-7 | Analysis: per bug type, memorisation probe, threats to validity, report |

## Budget and risks
* ≈ 4.7k forward passes (750 functions × 4 levels + renaming + control): ≈ 2 h on a T4, spread over sessions (results cached and resumable).
* Free GPU quota: inference is resumable per item.
* A 7B 4-bit model is weaker than frontier LLMs. Results are a lower bound; an API model can be added.
* Prompt sensitivity: prompts are chosen on the dev set only, and the chosen prompt is fixed before evaluation.
* Long contexts (C2/C3) are truncated to a fixed token budget, and truncation is recorded per sample.
