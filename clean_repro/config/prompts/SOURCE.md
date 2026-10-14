# Prompt sources

Transcribed for this clean reproduction directly from the paper's figures (Bhatia et al., LLM4Code '24,
doi:10.1145/3643795.3648396, page 56), read from a 300-dpi rendering of the PDF. Wording, capitalisation,
punctuation and line breaks are kept as printed, including "unittests" and the missing final full stops.

| File | Figure | Role |
|---|---|---|
| `fig1_basic.txt` | Figure 1 "Basic Prompt", text after the code sample | RQ1, RQ3, RQ4 |
| `fig2_iter1.txt` | Figure 2 "Improvement Prompt", INPUT Iteration 1 | RQ2, first round |
| `fig2_iterk.txt` | Figure 2, INPUT Iteration 2 ("improvement prompt"), with `94%` and `46, 51, 58-60` replaced by placeholders | RQ2, rounds 2..5 |

Section 2.4 of the paper quotes a third wording ("Write Unit tests using Pytest for given Python code that
covers all the edge cases."). The figures show the prompts actually used as input, so the figures are followed.

Layout taken from the figures:
* Figure 1: the code sample, then the two prompt lines.
* Figure 2, iteration 1: every code line followed by ` #N` (blank lines become `#N`), then the two prompt lines.
* Figure 2, iteration 2: numbered code, then the test cases output by the model, then the improvement prompt.

Points the figures leave open are listed in `../../README.md` (section "Ambiguities") and are not silently fixed.
