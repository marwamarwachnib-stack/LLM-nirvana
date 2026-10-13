## SFL results (controlled faults in the 39 small programs)

Programs processed: 1/39; mutants sampled 10 (of 31 candidates), valid 10; operators {'AOR': 4, 'ROR': 2, 'LCR': 0, 'UOD': 0, 'CRP': 4}.

| Suite | programs | mutants run | detected (%) | formula | ranked | Top-1 % | Top-3 % | Top-5 % | MRR | EXAM mean | EXAM incl. undetected |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dev | 1 | 10 | 9 (90.0) | ochiai | 9 | 11.1 | 33.3 | 33.3 | 0.34 | 0.23 | 0.307 |
| dev | 1 | 10 | 9 (90.0) | tarantula | 9 | 11.1 | 33.3 | 33.3 | 0.31 | 0.343 | 0.408 |
| dev | 1 | 10 | 9 (90.0) | dstar | 9 | 11.1 | 33.3 | 33.3 | 0.34 | 0.23 | 0.307 |
| pynguin | 1 | 10 | 4 (40.0) | ochiai | 4 | 0.0 | 0.0 | 50.0 | 0.159 | 0.308 | 0.723 |
| pynguin | 1 | 10 | 4 (40.0) | tarantula | 4 | 0.0 | 0.0 | 50.0 | 0.147 | 0.317 | 0.727 |
| pynguin | 1 | 10 | 4 (40.0) | dstar | 4 | 0.0 | 0.0 | 50.0 | 0.168 | 0.304 | 0.722 |
| llm | 1 | 10 | 9 (90.0) | ochiai | 9 | 0.0 | 44.4 | 44.4 | 0.344 | 0.207 | 0.287 |
| llm | 1 | 10 | 9 (90.0) | tarantula | 9 | 0.0 | 22.2 | 33.3 | 0.228 | 0.261 | 0.335 |
| llm | 1 | 10 | 9 (90.0) | dstar | 9 | 0.0 | 44.4 | 44.4 | 0.344 | 0.207 | 0.287 |
| dev+llm | 1 | 10 | 9 (90.0) | ochiai | 9 | 22.2 | 44.4 | 44.4 | 0.437 | 0.202 | 0.282 |
| dev+llm | 1 | 10 | 9 (90.0) | tarantula | 9 | 22.2 | 33.3 | 33.3 | 0.357 | 0.306 | 0.375 |
| dev+llm | 1 | 10 | 9 (90.0) | dstar | 9 | 22.2 | 44.4 | 44.4 | 0.437 | 0.202 | 0.282 |

Paired comparisons (Ochiai, same mutants; A12 > 0.5 means the first suite localises better):

| Comparison | programs | mutants | detected only by 1st / 2nd | both detected: EXAM 1st vs 2nd, A12, Wilcoxon p | incl. undetected: EXAM 1st vs 2nd, A12, p |
|---|---|---|---|---|---|
| dev vs pynguin | 1 | 10 | 5 / 0 | n=4: 0.342 vs 0.308, 0.375, – | n=10: 0.307 vs 0.723, 0.79, 0.0504 |
| dev vs llm | 1 | 10 | 0 / 0 | n=9: 0.23 vs 0.207, 0.475, 0.3246 | n=10: 0.307 vs 0.287, 0.48, 0.3246 |
| dev vs dev+llm | 1 | 10 | 0 / 0 | n=9: 0.23 vs 0.202, 0.426, 0.1732 | n=10: 0.307 vs 0.282, 0.44, 0.1732 |
| pynguin vs llm | 1 | 10 | 0 / 5 | n=4: 0.308 vs 0.304, 0.5, – | n=10: 0.723 vs 0.287, 0.19, 0.038 |
| pynguin vs dev+llm | 1 | 10 | 0 / 5 | n=4: 0.308 vs 0.304, 0.5, – | n=10: 0.723 vs 0.282, 0.19, 0.038 |
| llm vs dev+llm | 1 | 10 | 0 / 0 | n=9: 0.207 vs 0.202, 0.438, 0.1797 | n=10: 0.287 vs 0.282, 0.45, 0.1797 |

Oracle filter on the original programs (tests failing or flaky there are excluded): dev: kept 16, removed 0 (1 programs); pynguin: kept 11, removed 0 (1 programs); llm: kept 14, removed 23 (1 programs); dev+llm: kept 30, removed 23 (1 programs).
