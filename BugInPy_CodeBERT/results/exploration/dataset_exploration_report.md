# BugsInPy - Dataset Exploration Report

- Dataset root: `data/raw/BugsInPy`
- Dataset revision (git): `11c5f1eea954a42132cfd06bf257766a7963e0fd 2025-10-09 21:31:55 +0800`
- Projects: **17**  |  Bug instances: **501**
- Changed files across all patches: 647

## 1. Physical structure (as observed)

```
BugsInPy/
  framework/bin/bugsinpy-{checkout,compile,test,coverage,...}
  projects/<project>/project.info          # github_url, status
  projects/<project>/bugs/<id>/bug.info     # buggy/fixed commit, test_file, ...
  projects/<project>/bugs/<id>/bug_patch.txt# unified diff buggy -> fixed
  projects/<project>/bugs/<id>/run_test.sh  # bug-revealing test command(s)
  projects/<project>/bugs/<id>/requirements.txt, setup.sh (optional)
```

**The benchmark contains no source code.** Buggy and fixed program versions must be obtained by checking out `buggy_commit_id` / `fixed_commit_id` of each project's upstream repository.

## 2. Projects

| project      |   bugs | github_url                                   |   src_py_files_changed_mean |   src_changed_lines_median |   bugs_single_src_hunk |   bugs_no_src_change |
|:-------------|-------:|:---------------------------------------------|----------------------------:|---------------------------:|-----------------------:|---------------------:|
| PySnooper    |      3 | https://github.com/cool-RR/PySnooper         |                        1.33 |                        8   |                      1 |                    0 |
| ansible      |     18 | https://github.com/ansible/ansible           |                        1.06 |                        8.5 |                      6 |                    0 |
| black        |     23 | https://github.com/psf/black                 |                        1.13 |                       14   |                     11 |                    0 |
| cookiecutter |      4 | https://github.com/cookiecutter/cookiecutter |                        1.5  |                        8   |                      2 |                    0 |
| fastapi      |     16 | https://github.com/tiangolo/fastapi          |                        1.19 |                        6.5 |                      9 |                    0 |
| httpie       |      5 | https://github.com/jakubroztocil/httpie/     |                        1.2  |                        4   |                      3 |                    0 |
| keras        |     45 | https://github.com/keras-team/keras          |                        1.24 |                       12   |                     22 |                    1 |
| luigi        |     33 | https://github.com/spotify/luigi             |                        1.03 |                        3   |                     26 |                    0 |
| matplotlib   |     30 | https://github.com/matplotlib/matplotlib     |                        1.23 |                        6   |                     17 |                    0 |
| pandas       |    169 | https://github.com/pandas-dev/pandas         |                        1.24 |                        7   |                     83 |                    0 |
| sanic        |      5 | https://github.com/huge-success/sanic        |                        1    |                        7   |                      4 |                    0 |
| scrapy       |     40 | https://github.com/scrapy/scrapy             |                        1.2  |                        5   |                     25 |                    0 |
| spacy        |     10 | https://github.com/explosion/spaCy           |                        1.1  |                        2.5 |                      8 |                    0 |
| thefuck      |     32 | https://github.com/nvbn/thefuck              |                        1.12 |                        5.5 |                     24 |                    0 |
| tornado      |     16 | https://github.com/tornadoweb/tornado        |                        1.19 |                        9.5 |                      9 |                    0 |
| tqdm         |      9 | https://github.com/tqdm/tqdm                 |                        1.11 |                        3   |                      6 |                    0 |
| youtube-dl   |     43 | https://github.com/ytdl-org/youtube-dl       |                        1.26 |                        5   |                     24 |                    0 |

## 3. Bug metadata

- `bug.info` key variants: `{'buggy_commit_id;fixed_commit_id;python_version;test_file': 452, 'buggy_commit_id;fixed_commit_id;python_version;pythonpath;test_file': 49}`
- Missing `python_version`: 0 bugs
- Test runners in `run_test.sh`: {'pytest': 365, 'unittest': 122, 'other': 14}
- `requirements.txt` encodings: {'utf-8': 383, 'utf-16': 117, 'MISSING': 1}
- Declared test files per bug: min 1, max 3, mean 1.07

## 4. Bug-fix patches

- Bugs whose fix touches exactly 1 non-test Python file: 433
- Bugs whose fix touches >1 non-test Python files: 67
- Bugs whose patch has **no** non-test Python change: 1
- Patches that also edit test files: 36
- Patches that edit non-Python files: 0
- Changed source lines per bug (+/-): {'count': 501.0, 'mean': 27.26, 'std': 177.7, 'min': 0.0, '25%': 3.0, '50%': 6.0, '75%': 14.0, 'max': 2334.0}
- Source hunks per bug: {'count': 501.0, 'mean': 2.28, 'std': 3.55, 'min': 0.0, '25%': 1.0, '50%': 1.0, '75%': 2.0, 'max': 58.0}

## 5. How buggy/fixed versions are defined (from `framework/bin/bugsinpy-checkout`)

- Fixed version = `git reset --hard <fixed_commit_id>` of the upstream repository.
- Buggy version = `git reset --hard <buggy_commit_id>`; the bug-revealing `test_file`(s) of the fixed version are then copied into the buggy checkout.
- `bug_patch.txt` is the source-code diff buggy -> fixed and identifies the code touched by the fix.
- Large whole-file patches (see outliers below) suggest the buggy commit is not always the direct parent of the fix, so a patch may contain changes unrelated to the bug. To be verified against upstream history before building labels.

Largest source patches (changed lines):

| uid       |   patch_py_src_files |   patch_src_hunks |   patch_src_changed_lines |
|:----------|---------------------:|------------------:|--------------------------:|
| pandas-17 |                    1 |                 2 |                      2334 |
| pandas-15 |                    1 |                 2 |                      2289 |
| pandas-93 |                    1 |                 1 |                      2255 |
| black-15  |                    1 |                14 |                       238 |
| scrapy-33 |                    8 |                21 |                       235 |

Share of bugs with <= 20 changed source lines: 83.2%

## 6. Anomalies detected

- keras-12: bug_patch.txt contains no file diffs
- pandas: non-directory entry in bugs/: '~$Bugs info.xlsx'
- 168 bugs use an abbreviated buggy_commit_id (resolvable in upstream repo): projects=['pandas']
