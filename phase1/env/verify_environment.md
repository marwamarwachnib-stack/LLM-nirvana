# The runner venv against the authors' stored coverage reports

2026-10-30T14:53:36+00:00; runner: Python 3.10.12, pytest 7.4.0, pluggy 1.3.0, coverage 7.3.0 (the authors' reports: Python 3.10.12, pytest 7.4.0, pluggy 1.3.0). Produced by `make verify-env`.

| set | tool | report | identical |
|---|---|---|---|
| small | pynguin | statement | 38/38 |
| small | pynguin | branch | 39/39 |
| p2 | pynguin | statement | 36/39 |
| p2 | pynguin | branch | 36/39 |
| p2 | chatgpt | statement | 37/41 |
| p2 | chatgpt | branch | 37/41 |

**223/237 reports identical** (the module's row: statements, missed, branches, partial branches, cover, missing lines).

| set | program | tool | report | theirs | ours | cause |
|---|---|---|---|---|---|---|
| p2 | sample8 | pynguin | statement | 35 29 17% 10-68 | 51 30 41% 22-67, 77, | their report is of httpie-master's compat.py (35 statements); the file they uploaded (httpie 3.2.2) has 51 |
| p2 | sample8 | pynguin | branch | 35 29 10 0 13% | 51 30 14 2 38% | their report is of httpie-master's compat.py (35 statements); the file they uploaded (httpie 3.2.2) has 51 |
| p2 | sample17 | chatgpt | statement | 61 2 97% 20, 84 | 61 41 33% 15-17, 20, | their ChatGPT test needs a maybe.py with Box at top level (not pymonet 0.12.0's) |
| p2 | sample17 | chatgpt | branch | 61 2 26 3 94% | 61 41 26 0 23% | their ChatGPT test needs a maybe.py with Box at top level (not pymonet 0.12.0's) |
| p2 | sample28 | chatgpt | statement | 159 69 57% 14, 17, | 159 77 52% 11, 14, | partly: their stored compilation report shows a collection error (No module named 'base'), so the coverage report comes from another setup (the whole typesystem package); we miss lines 11, 23-26, 213-218 |
| p2 | sample28 | chatgpt | branch | 159 69 88 6 47% | 159 77 88 5 43% | partly: their stored compilation report shows a collection error (No module named 'base'), so the coverage report comes from another setup (the whole typesystem package); we miss lines 11, 23-26, 213-218 |
| p2 | sample32 | chatgpt | statement | 441 147 67% 37, 40, | 441 152 66% 37, 40, | partly: their stored compilation report shows a collection error (No module named 'formats'), so the coverage report comes from another setup (the whole typesystem package); we miss lines 83-93 |
| p2 | sample32 | chatgpt | branch | 441 147 264 68 60% | 441 152 264 66 59% | partly: their stored compilation report shows a collection error (No module named 'formats'), so the coverage report comes from another setup (the whole typesystem package); we miss lines 83-93 |
| p2 | sample40 | chatgpt | statement | 91 20 78% 23-25, 43-44, | 91 20 78% 24-26, 44-45, | their report is of pdir2's own api.py (`from . import format` on one line, two lines in the file they uploaded): every missing line is one lower, the counts are equal |
| p2 | sample40 | chatgpt | branch | 91 20 46 9 73% | 91 20 46 9 73% | their report is of pdir2's own api.py (`from . import format` on one line, two lines in the file they uploaded): every missing line is one lower, the counts are equal |
| p2 | sample42 | pynguin | statement | 69 12 83% 23-27, 45, | 69 39 43% 23-27, 95-97, | their run measured the whole flutes package (15 files in their report) |
| p2 | sample42 | pynguin | branch | 69 12 32 8 78% | 69 39 32 1 33% | their run measured the whole flutes package (15 files in their report) |
| p2 | sample43 | pynguin | statement | 60 11 82% 32, 39-40, | 60 34 43% 34-52, 87-107 | their run measured the whole flutes package (15 files in their report) |
| p2 | sample43 | pynguin | branch | 60 11 21 8 74% | 60 34 21 2 38% | their run measured the whole flutes package (15 files in their report) |
