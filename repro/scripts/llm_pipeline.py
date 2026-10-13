"""Phase C: unit-test generation with a local LLM (Ollama), following Bhatia et al. 2024.

Two modes, matching the paper:
  basic      RQ1/RQ3/RQ4  one Figure-1 prompt per module; tests evaluated for coverage and correctness.
  iterative  RQ2          Figure-2 prompts: iteration 1 with numbered lines, then up to 4 follow-ups that
                          give the current coverage and the uncovered line numbers; stops at 5 iterations
                          or when coverage does not improve between consecutive iterations.

Every prompt, request, raw response, extracted test file, pytest log, junit file and coverage report
is saved under repro/runs/<model>/<mode>/<dataset>/<sample>/iter_<k>/.
The run is resumable: finished iterations (result.json present) are not regenerated.

Usage:
  python llm_pipeline.py --model qwen3-4b-instruct --mode basic --datasets small_cat2 small_cat3
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from common import REPO, RUNS, SMALL, P1, P2, rel, write_json
from extract import count_asserts, extract_tests, merge_suites, remove_redefinitions
from prompts import basic_prompt, iter1_prompt, iterk_prompt
from runner import run_with_coverage

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
WORK = Path(os.environ.get("REPRO_WORK", "/opt/repro/work/phase_c"))

# Inference settings (documented in repro/README.md). Sampling follows the model card recommendation
# for Qwen3-Instruct-2507 (temperature 0.7, top_p 0.8, top_k 20); the fixed seed makes runs repeatable
# on the same hardware / Ollama build. ChatGPT's settings in the paper are unknown (web UI defaults).
OPTIONS = {
    "temperature": float(os.environ.get("REPRO_TEMPERATURE", 0.7)),
    "top_p": 0.8, "top_k": 20, "seed": int(os.environ.get("REPRO_SEED", 42)),
    "num_ctx": int(os.environ.get("REPRO_NUM_CTX", 16384)),
    "num_predict": int(os.environ.get("REPRO_NUM_PREDICT", 2048)),
}
MAX_ITERS = 5


@dataclass
class Sample:
    dataset: str
    sample_id: str
    category: str
    source: Path                 # module given to the model
    module: str                  # import name of the module under test
    support: list[Path] = field(default_factory=list)   # extra files/dirs copied into the sandbox
    pythonpath: list[str] = field(default_factory=list)

    def build_sandbox(self, dst: Path) -> None:
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for s in self.support:
            if s.is_dir():
                # p2: the package *contents* sit next to the target module, reproducing the authors'
                # layout (tests run from inside the package directory; imports flattened).
                shutil.copytree(s, dst, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__", "test_*", "tests"))
            else:
                shutil.copy2(s, dst / s.name)
        shutil.copy2(self.source, dst / f"{self.module}.py")


def datasets() -> dict[str, list[Sample]]:
    out: dict[str, list[Sample]] = {}
    for cat_dir, cat in (("cat1_scripts", "cat1"), ("cat2_functions", "cat2"), ("cat3_classes", "cat3")):
        out[f"small_{cat}"] = [Sample(f"small_{cat}", d.name, cat, d / "example.py", "example")
                               for d in sorted((SMALL / cat_dir).iterdir()) if (d / "example.py").exists()]
    for cat in ("cat1", "cat2", "cat3"):
        base = P1 / cat
        if base.exists():
            out[f"p1_{cat}"] = [Sample(f"p1_{cat}", d.name, cat, d / "example.py", "example",
                                       support=[f for f in d.glob("*.py") if f.name != "example.py"])
                                for d in sorted(base.iterdir(), key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)
                                if (d / "example.py").exists()]
    mapping = REPO / "repro" / "data" / "p2_projects.json"
    if mapping.exists():
        m = json.loads(mapping.read_text())
        samples = []
        for sid, info in sorted(m["samples"].items(), key=lambda kv: int(kv[0][6:])):
            # sandbox template built by p2_sandboxes.py from the files listed in the saved reports
            dirs = [Path(os.environ.get("REPRO_P2_SANDBOXES", "/opt/repro/p2_sandboxes")) / info["sandbox_dir"]]
            src = P2 / "pynguin coverage" / sid / info["module_file"]
            samples.append(Sample("p2", sid, info.get("structure_rule", "?"), src, Path(info["module_file"]).stem,
                                  support=dirs))
        out["p2"] = samples
    return out


def ollama(path: str, payload: dict | None = None, timeout: int = 7200) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def model_info(model: str) -> dict:
    show = ollama("/api/show", {"model": model})
    tags = {m["name"]: m for m in ollama("/api/tags")["models"]}
    t = tags.get(model) or tags.get(f"{model}:latest") or {}
    return {"model": model, "digest": t.get("digest"), "details": show.get("details"),
            "parameters": show.get("parameters"), "template_sha256": hashlib.sha256((show.get("template") or "").encode()).hexdigest(),
            "ollama_version": ollama("/api/version")["version"]}


def generate(model: str, prompt: str, outdir: Path) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False, "options": OPTIONS, "keep_alive": "60m"}
    (outdir / "prompt.txt").write_text(prompt)
    write_json(outdir / "request.json", payload)
    t0 = time.time()
    resp = ollama("/api/generate", payload)
    resp["wall_seconds"] = round(time.time() - t0, 2)
    resp.pop("context", None)
    write_json(outdir / "response.json", resp)
    (outdir / "raw_response.md").write_text(resp["response"])
    return resp["response"]


def evaluate(sample: Sample, test_code: str, outdir: Path, label: str) -> dict:
    sandbox = WORK / outdir.relative_to(RUNS) / label
    sample.build_sandbox(sandbox)
    (sandbox / "test_generated.py").write_text(test_code)
    env = {"PYTHONPATH": os.pathsep.join([str(sandbox)] + sample.pythonpath)}
    res = run_with_coverage(sandbox, "test_generated.py", f"{sample.module}.py", label=label, extra_env=env)
    for f in sandbox.glob(f"{label}_*"):
        shutil.copy2(f, outdir / f.name)
    res["num_asserts"] = count_asserts(test_code)
    return res


def sandbox_modules(sample: Sample) -> set[str]:
    mods = {sample.module}
    for s in sample.support:
        mods.add(s.stem if s.is_file() else s.name)
        if s.is_dir():
            mods.update(p.stem for p in s.glob("*.py"))
            mods.update(p.name for p in s.iterdir() if p.is_dir())
    return mods


def run_sample(model: str, mode: str, sample: Sample, reevaluate: bool = False) -> dict:
    base = RUNS / model / mode / sample.dataset / sample.sample_id
    base.mkdir(parents=True, exist_ok=True)
    source = sample.source.read_text()
    history = []
    suite = ""
    prev_cov = None
    n_iters = 1 if mode == "basic" else MAX_ITERS
    for k in range(1, n_iters + 1):
        it = base / f"iter_{k}"
        it.mkdir(exist_ok=True)
        done = it / "result.json"
        if reevaluate and mode == "basic" and (it / "raw_response.md").exists():
            done.unlink(missing_ok=True)   # re-extract and re-score the saved reply; the model is not called
        if done.exists():
            r = json.loads(done.read_text())
            history.append(r)
            suite = (it / "test_suite.py").read_text()
            prev_cov = r["suite"]["summary"]["stmt_cov"]
            if r.get("stop"):
                break
            continue
        if mode == "basic":
            prompt = basic_prompt(source)
        elif k == 1:
            prompt = iter1_prompt(source)
        else:
            missed = history[-1]["suite"]["stmt"]["coverage"]["missing_lines"] if history[-1]["suite"]["stmt"]["coverage"] else []
            prompt = iterk_prompt(source, suite, prev_cov or 0.0, missed)
        if (it / "raw_response.md").exists() and (it / "prompt.txt").exists() and (it / "prompt.txt").read_text() == prompt:
            reply = (it / "raw_response.md").read_text()   # resume after an interrupted evaluation
        else:
            reply = generate(model, prompt, it)
        raw_tests, xlog = extract_tests(reply, sample.module, sandbox_modules(sample))
        new_tests, removed = remove_redefinitions(raw_tests, source, sample.module)
        xlog["redefinitions_removed"] = removed
        (it / "test_extracted_unrepaired.py").write_text(raw_tests)
        (it / "test_new.py").write_text(new_tests)
        write_json(it / "extract_log.json", xlog)
        suite = new_tests if k == 1 or not suite else merge_suites(suite, new_tests)
        (it / "test_suite.py").write_text(suite)
        r = {"iteration": k, "sample": sample.sample_id, "dataset": sample.dataset, "category": sample.category,
             "module_source": rel(sample.source), "extract_log": xlog,
             "suite": evaluate(sample, suite, it, "suite")}
        if k > 1:
            r["new_only"] = evaluate(sample, new_tests, it, "new")["summary"]
        if removed and k == 1:
            # transparency: score of the reply without the redefinition repair
            r["unrepaired"] = evaluate(sample, raw_tests, it, "unrepaired")["summary"]
        cov = r["suite"]["summary"]["stmt_cov"]
        r["stop"] = bool(mode == "basic" or k == MAX_ITERS or (cov is not None and cov >= 100.0)
                         or (k > 1 and prev_cov is not None and cov is not None and cov <= prev_cov))
        r["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        write_json(done, r)
        history.append(r)
        prev_cov = cov
        print(f"[{model}/{mode}] {sample.dataset}/{sample.sample_id} iter {k}: stmt={cov} branch={r['suite']['summary']['branch_cov']} "
              f"tests={r['suite']['summary']['collected']} passed={r['suite']['summary']['passed']} stop={r['stop']}", flush=True)
        if r["stop"]:
            break
    return {"sample": sample.sample_id, "iterations": len(history)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--mode", choices=["basic", "iterative"], required=True)
    ap.add_argument("--datasets", nargs="+", required=True)
    ap.add_argument("--samples", nargs="*", help="restrict to these sample ids")
    ap.add_argument("--reevaluate", action="store_true", help="basic mode: re-score saved replies without calling the model")
    args = ap.parse_args()
    ds = datasets()
    meta_path = RUNS / args.model / "model_info.json"
    if not meta_path.exists():
        write_json(meta_path, {**model_info(args.model), "options": OPTIONS})
    for name in args.datasets:
        for s in ds[name]:
            if args.samples and s.sample_id not in args.samples and f"{s.dataset}/{s.sample_id}" not in args.samples:
                continue
            try:
                run_sample(args.model, args.mode, s, reevaluate=args.reevaluate)
            except Exception as e:  # keep the queue going; the failure is recorded
                err = RUNS / args.model / args.mode / s.dataset / s.sample_id / "error.txt"
                err.parent.mkdir(parents=True, exist_ok=True)
                err.write_text(f"{type(e).__name__}: {e}\n")
                print(f"ERROR {s.dataset}/{s.sample_id}: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
