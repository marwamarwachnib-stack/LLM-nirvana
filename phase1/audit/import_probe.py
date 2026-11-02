"""Statement coverage of each p1 module whose plain import fails: reached by a plain import, and by an import
prepared the way a generated test can prepare it (stubs in sys.modules, sys.argv, a patched time.sleep or Discord
client, loading inside a stub package). Nothing in the module is changed; no model is called. Evidence for
decision 19 (import-only coverage is not an upper bound for Table 3).

    .venv/bin/python audit/import_probe.py          (about 3 min; writes audit/import_probe.csv)
"""
import csv, json, shutil, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from common import REPO, RUNNER_PY, run_code
from prepare_datasets import DATASETS, runtime_env

STUB_LOOP = """
import sys, types, importlib
from unittest import mock
def load(stubs=()):
    for s in stubs:
        sys.modules[s] = mock.MagicMock()
    for _ in range(15):
        try:
            return importlib.import_module("example")
        except ModuleNotFoundError as e:
            sys.modules[e.name] = mock.MagicMock()
            sys.modules.pop("example", None)
"""
PREP = {
    "cat1_s15": 'import sys; sys.argv = ["convert.py", "-s", "scene"]\ntry:\n    import example\nexcept SystemExit:\n    pass',
    "cat2_s10": STUB_LOOP + 'load(["vbench", "vbench.benchmark"])',
    "cat2_s11": STUB_LOOP + 'load()',
    "cat2_s2": 'import example',
    "cat2_s6": STUB_LOOP + 'load()',
    "cat3_s10": 'from unittest import mock\nimport discord.ext.commands as c, discord\nwith mock.patch.object(c.Bot, "run"), mock.patch.object(discord.Client, "run"):\n    import example',
    "cat3_s11": 'from unittest import mock\nimport discord.ext.commands as c\nwith mock.patch.object(c.Bot, "start", new=mock.AsyncMock()):\n    import example',
    "cat3_s12": 'import sys, types, importlib.util\nfrom unittest import mock\npkg = types.ModuleType("pkg"); pkg.__path__ = []; sys.modules["pkg"] = pkg\nsys.modules["pkg.experiment"] = mock.MagicMock()\nspec = importlib.util.spec_from_file_location("pkg.example", "example.py")\nm = importlib.util.module_from_spec(spec); sys.modules["pkg.example"] = m; spec.loader.exec_module(m)',
    "cat3_s14": STUB_LOOP + 'load(["cPickle", "vbench", "vbench.git", "vbench.db", "vbench.utils"])',
    "cat3_s8": 'import sys, types, importlib.util\nfrom unittest import mock\npkg = types.ModuleType("pkg"); pkg.__path__ = []; sys.modules["pkg"] = pkg\nsys.modules["pkg.image_utils"] = mock.MagicMock()\nspec = importlib.util.spec_from_file_location("pkg.example", "example.py")\nm = importlib.util.module_from_spec(spec); sys.modules["pkg.example"] = m; spec.loader.exec_module(m)',
    "cat3_s9": 'import time\ntime.sleep = lambda s: None\nimport example',
}
LABEL = {"cat1_s15": "sys.argv set; SystemExit from its failed colmap call caught",
         "cat2_s10": "vbench (Python 2 package) stubbed", "cat2_s11": "missing modules stubbed (win32api)",
         "cat2_s2": "none possible: Python 2 str.decode('hex') runs at import",
         "cat2_s6": "missing modules stubbed (CUDA extensions)", "cat3_s10": "discord Bot.run / Client.run patched",
         "cat3_s11": "discord Bot.start patched", "cat3_s12": "loaded inside a stub package (relative import)",
         "cat3_s14": "cPickle and the Python 2 vbench modules stubbed", "cat3_s8": "loaded inside a stub package (relative import)",
         "cat3_s9": "time.sleep patched (the 7.2 h real-time loop)"}
CHECK = '\nimport sys\nprint("PROBE-IMPORTED" if ("example" in sys.modules or "pkg.example" in sys.modules) else "PROBE-NOT-IMPORTED")\n'
man = json.load(open(DATASETS / "p1" / "manifest.json"))["programs"]
rows = []
for name, prep in PREP.items():
    e = man[name]
    res = {}
    for mode, code in (("plain import", "import example"), ("prepared", prep)):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(REPO / e["source"], Path(tmp) / "example.py")
            for f in e["data_files"]:
                shutil.copy(DATASETS / f, Path(tmp) / Path(f).name)
            Path(tmp, "probe.py").write_text("import pytest\n" + code + CHECK)
            Path(tmp, ".coveragerc").write_text("[run]\ninclude = example.py\nsigterm = true\n")
            r = run_code(["timeout", "-s", "TERM", "150", str(RUNNER_PY), "-m", "coverage", "run", "probe.py"], runtime_env(e),
                         cwd=tmp, capture_output=True, text=True)
            imported = "PROBE-IMPORTED" in r.stdout
            out = run_code([str(RUNNER_PY), "-m", "coverage", "json", "-o", "-"], runtime_env(e), cwd=tmp, capture_output=True, text=True).stdout
            try:
                t = json.loads(out)["totals"]; res[mode] = (round(t["percent_covered"], 1), t["covered_lines"], t["num_statements"], imported)
            except Exception:
                res[mode] = (None, None, None, imported)
    rows.append({"program": name, "plain_import_stmt_cov": res["plain import"][0], "prepared_stmt_cov": res["prepared"][0],
                 "statements": res["plain import"][2], "covered_plain": res["plain import"][1], "covered_prepared": res["prepared"][1],
                 "imported_plain": res["plain import"][3], "imported_prepared": res["prepared"][3], "preparation": LABEL[name]})
    print(f"{name:9} plain {res['plain import']} prepared {res['prepared']}", flush=True)
with open(HERE / "import_probe.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
