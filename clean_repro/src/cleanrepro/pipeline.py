"""Orchestration of one sample: prompt -> local model -> extraction -> execution -> metrics.

  python -m cleanrepro.pipeline basic     --model <key> --samples <sample_id> ...
  python -m cleanrepro.pipeline iterative --model <key> --samples <sample_id> ...
  python -m cleanrepro.pipeline basic     --replay <dir> --samples ...   (pipeline validation)

`--replay <dir>` replaces the model by saved replies (<dir>/<sample_id>/iter_<k>.md); it is used
only to validate the pipeline and writes to runs_validation/, never to runs/.  Each process must be
started with the Python of the sample's test environment (exec for small, p2, p1), so that the
extraction sees the packages that the tests will see.

Output: runs/<model>/<mode>/<sample_id>/iter_<k>/... and runs/<model>/<mode>/<sample_id>/result.json
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import assertions, execute, extract, integrity, iterate, prompts, sandbox
from .paths import BENCH, CLEAN, CONFIG, REPO, RUNS, env_python

GROUP_ENV = {"small": "exec", "p2": "p2", "p1": "p1"}


def load_config() -> dict:
    return json.loads((CONFIG / "experiment.json").read_text())


def manifest() -> dict[str, dict]:
    return {r["sample_id"]: r for r in csv.DictReader(open(BENCH / "manifest.csv"))}


# ------------------------------------------------------------------ sandboxes per group
class Target:
    """A program version against which tests are run."""

    def __init__(self, label: str, build, module_file: str, python: Path, extra_env: dict | None = None):
        self.label, self.build, self.module_file = label, build, module_file
        self.python, self.extra_env = python, extra_env or {}

    @property
    def module(self) -> str:
        return self.module_file[:-3]


def targets(row: dict, rewrite_code: str | None) -> list[Target]:
    """Program versions to test.  Cat 1 small scripts: the original script AND, when the model
    rewrote it, the rewritten program (reported separately, as in the paper's Table 1)."""
    py = env_python(GROUP_ENV[row["group"]])
    if row["group"] == "p2":
        from . import p2_context
        proj = p2_context.load_projects()[row["name"]]

        def build_p2(sb: Path, row=row, proj=proj):
            log = p2_context.build_context(row, proj, sb)
            return log
        # PYTHONPATH entries are computed after building; see run_tests
        return [Target("module", build_p2, row["module_file"], py)]
    if row["group"] == "small" and row["category"] == "1":
        ts = [Target("original", lambda sb: sandbox.copy_in(row["module_path"], sb, "example.py"), "example.py", py)]
        if rewrite_code:
            ts.append(Target("rewritten", lambda sb: (sb / "example.py").write_text(rewrite_code), "example.py", py))
        return ts
    return [Target("module", lambda sb: sandbox.copy_in(row["module_path"], sb, "example.py"), "example.py", py)]


def importable_names(python: Path, sandbox_dir: Path, row: dict | None = None) -> set[str]:
    """Top-level module names importable in the test environment + files in the sandbox
    (+ for p2, every module name of the project, even if not copied into the sandbox)."""
    code = "import pkgutil,sys;print('\\n'.join(sorted({m.name for m in pkgutil.iter_modules()})))"
    out = subprocess.run([str(python), "-c", code], capture_output=True, text=True).stdout.split()
    local = {p.stem for p in sandbox_dir.glob("*.py")} | {p.name for p in sandbox_dir.iterdir() if p.is_dir()}
    names = set(out) | local
    if row is not None and row["group"] == "p2":
        from . import p2_context
        names |= p2_context.package_module_names(p2_context.load_projects()[row["name"]])
    return names


def run_tests(row: dict, target: Target, test_files: dict[str, str], out: Path, cfg: dict) -> dict:
    """Fresh sandbox for `target`, write `test_files` {name: code}, coverage run + assertion run."""
    sb = sandbox.fresh("runs", *out.relative_to(CLEAN).parts)
    ctx = target.build(sb)
    env = dict(target.extra_env)
    if isinstance(ctx, dict) and ctx.get("pythonpath"):
        env["PYTHONPATH"] = ":".join(str(sb / p) for p in ctx["pythonpath"])
    for name, code in test_files.items():
        (sb / name).write_text(code)
    names = list(test_files)
    summ = execute.run_both(sb, names, target.module_file, target.python, out / "exec",
                            timeout=cfg["test_timeout_seconds"], extra_env=env)
    asum = assertions.evaluate(sb, names, target.python, Path(str(sb) + "_assert"),
                               timeout=cfg["test_timeout_seconds"], extra_env=env)
    (out / "assertions.json").write_text(json.dumps(asum, indent=1))
    summ["assertions"] = {k: v for k, v in asum.items() if k != "records"}
    summ["stmt_cover_report"] = _report_cover(out / "exec" / "coverage_stmt.txt", target.module_file)
    return summ


def _report_cover(path: Path, module_file: str) -> int | None:
    from . import covreport
    r = covreport.read_text_report(path, module_file) if path.exists() else None
    return int(r.cover) if r else None


# ------------------------------------------------------------------ generation backends
class ModelBackend:
    def __init__(self, key: str, cfg: dict):
        from .inference import OllamaClient
        lock = json.loads((CONFIG / "models.lock.json").read_text())
        if not lock.get(key, {}).get("ollama_digest"):
            raise SystemExit(f"{key}: no recorded model digest in config/models.lock.json; "
                             "the model has not been downloaded and verified")
        self.key, self.cfg = key, cfg
        self.name = cfg["models"][key]["ollama_name"]
        self.client = OllamaClient(cfg["ollama_url"], cfg["generation_timeout_seconds"])
        self.client.check_model(self.name, lock[key]["ollama_digest"])

    def __call__(self, sample_id: str, k: int, prompt: str, out: Path) -> str:
        request, gen = self.client.chat(self.name, prompt, self.cfg["options"])
        (out / "request.json").write_text(json.dumps(request, indent=1))
        (out / "response.json").write_text(json.dumps(gen.raw, indent=1))
        return gen.content


class ReplayBackend:
    """Saved replies instead of a model (pipeline validation only)."""

    def __init__(self, directory: Path):
        self.dir = directory

    def __call__(self, sample_id: str, k: int, prompt: str, out: Path) -> str:
        p = self.dir / sample_id / f"iter_{k}.md"
        reply = p.read_text() if p.exists() else ""
        (out / "request.json").write_text(json.dumps({"replay": str(p)}, indent=1))
        (out / "response.json").write_text(json.dumps({"replay": str(p), "exists": p.exists()}))
        return reply


# ------------------------------------------------------------------ one sample
def generate_and_extract(backend, row: dict, k: int, prompt: str, out: Path, module: str,
                         module_code: str, available: set[str]) -> tuple[str, extract.Extraction, str]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "prompt.txt").write_text(prompt)
    t0 = time.monotonic()
    try:
        reply = backend(row["sample_id"], k, prompt, out)
        gen_error = ""
    except Exception as e:                       # recorded, never hidden
        reply, gen_error = "", f"{type(e).__name__}: {e}"
    (out / "reply.md").write_text(reply)
    rewrite, rlog = "", []
    if row["group"] == "small" and row["category"] == "1":
        # Category 1: imports in the tests are matched against the rewritten program when there is one
        rewrite, rlog = extract.extract_rewrite(reply)
    ex = extract.extract(reply, module, rewrite or module_code, available)
    ex.log += rlog
    ex.rewrite_code = rewrite
    if rewrite:
        (out / "rewrite.py").write_text(rewrite)
    if ex.test_code:
        (out / "test_strict.py").write_text(ex.test_code)
        (out / "test_lenient.py").write_text(ex.test_code_lenient)
    meta = {k_: v for k_, v in ex.__dict__.items() if k_ not in ("test_code", "test_code_lenient", "rewrite_code")}
    meta.update(generation_error=gen_error, generation_seconds=round(time.monotonic() - t0, 2),
                reply_chars=len(reply))
    (out / "extraction.json").write_text(json.dumps(meta, indent=1))
    return reply, ex, gen_error


def module_info(row: dict) -> tuple[str, str]:
    code = (REPO / row["module_path"]).read_text(errors="replace")
    module = row["module_file"][:-3] if row["group"] == "p2" else "example"
    return module, code


def run_basic(backend, label: str, row: dict, cfg: dict, base: Path) -> dict:
    out_s = base / label / "basic" / row["sample_id"]
    out = out_s / "iter_1"
    module, code = module_info(row)
    probe = sandbox.fresh("probe", row["sample_id"])
    for t in targets(row, None)[:1]:
        t.build(probe)
    available = importable_names(env_python(GROUP_ENV[row["group"]]), probe, row)
    _, ex, gen_error = generate_and_extract(backend, row, 1, prompts.basic(code), out, module, code, available)
    result = {"sample_id": row["sample_id"], "group": row["group"], "category": row["category"],
              "mode": "basic", "model": label, "extraction_status": ex.status,
              "generation_error": gen_error, "truncated": ex.truncated, "variants": {}}
    if ex.status == "ok":
        for variant, code_ in (("strict", ex.test_code), ("lenient", ex.test_code_lenient)):
            for t in targets(row, ex.rewrite_code or None):
                result["variants"].setdefault(variant, {})[t.label] = run_tests(
                    row, t, {"test_generated.py": code_}, out / variant / t.label, cfg)
    (out_s / "result.json").write_text(json.dumps(result, indent=1))
    return result


def run_iterative(backend, label: str, row: dict, cfg: dict, base: Path) -> dict:
    out_s = base / label / "iterative" / row["sample_id"]
    module, code = module_info(row)
    variant = cfg["primary_extraction"]
    t = targets(row, None)[0]
    probe = sandbox.fresh("probe", row["sample_id"])
    t.build(probe)
    available = importable_names(t.python, probe, row)
    files: dict[str, str] = {}
    state: dict = {}

    def generate(k: int, prompt: str) -> str:
        reply, ex, err = generate_and_extract(backend, row, k, prompt, out_s / f"iter_{k}", module, code, available)
        state[k] = ex
        return reply

    def extract_and_write(k: int, reply: str):
        ex = state[k]
        if ex.status != "ok":
            return ex.status, None
        name = f"test_iter{k}.py"
        files[name] = ex.test_code if variant == "strict" else ex.test_code_lenient
        return ex.status, name

    def evaluate(names: list[str]) -> dict:
        k = len(state)
        return run_tests(row, t, {n: files[n] for n in names}, out_s / f"iter_{k}" / "suite", cfg)

    def suite_text(names: list[str]) -> str:
        return "\n\n".join(files[n].strip() for n in names) if cfg["iterative_feedback_suite"] == "cumulative" \
            else files[names[-1]].strip()

    r = iterate.run(code, generate, extract_and_write, evaluate, cfg["max_iterations"], suite_text)
    result = {"sample_id": row["sample_id"], "group": row["group"], "category": row["category"],
              "mode": "iterative", "model": label, "variant": variant, "stop_reason": r.stop_reason,
              "iterations": [{k_: v for k_, v in rec.__dict__.items() if k_ not in ("prompt", "reply")}
                             for rec in r.records],
              "coverage_by_iteration": r.coverage_by_iteration(cfg["max_iterations"])}
    (out_s / "result.json").write_text(json.dumps(result, indent=1))
    return result


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["basic", "iterative"])
    ap.add_argument("--model")
    ap.add_argument("--replay", type=Path)
    ap.add_argument("--label")
    ap.add_argument("--samples", nargs="+", required=True)
    a = ap.parse_args(argv)
    cfg = load_config()
    if bool(a.model) == bool(a.replay):
        raise SystemExit("exactly one of --model / --replay")
    if a.replay:
        backend, label, base = ReplayBackend(a.replay), a.label or f"replay-{a.replay.name}", CLEAN / "runs_validation"
    else:
        backend, label, base = ModelBackend(a.model, cfg), a.model, RUNS
    rows = manifest()
    integrity.verify("(start)")
    for sid in a.samples:
        row = rows[sid]
        expected = env_python(GROUP_ENV[row["group"]])
        if Path(sys.executable).resolve() != expected.resolve():
            raise SystemExit(f"{sid}: run with {expected} (test environment of group {row['group']})")
        res = (run_basic if a.mode == "basic" else run_iterative)(backend, label, row, cfg, base)
        print(sid, json.dumps({k: res.get(k) for k in ("extraction_status", "stop_reason", "coverage_by_iteration")}), flush=True)
    integrity.verify("(end)")


if __name__ == "__main__":
    main()
