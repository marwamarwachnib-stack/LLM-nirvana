"""Live demo: one LLM generates tests for one program, then the tests are run with coverage.

Works in a temporary folder, so runs/ and results/ are never touched. One round only, no
cold reload and no idle subtraction, so its numbers are for showing the pipeline, not results.

    .venv/bin/python scripts/demo.py                          # dsc-1.3b on change
    .venv/bin/python scripts/demo.py --tool dsc-6.7b --program cat3_classes/bank-account
"""
import argparse
import subprocess
import tempfile
import time
from pathlib import Path

from common import CONFIG_DIR, REPO, VENV_PY, load_config, rapl_delta_wh, rapl_readable, rapl_snapshot
from evaluate import extract_blocks, normalize_imports
from run import chat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="dsc-1.3b")
    ap.add_argument("--program", default="cat2_functions/change", help="folder under '0_100 LOC'")
    args = ap.parse_args()
    cfg = load_config()
    model = cfg["llm_tools"][args.tool]["model"]
    module = (REPO / "0_100 LOC" / args.program / "example.py").read_text()
    prompts = CONFIG_DIR / "prompts"
    system = (prompts / cfg["prompts"]["system"]).read_text()
    user = (prompts / cfg["prompts"]["basic_user"]).read_text().format(code=module)

    work = Path(tempfile.mkdtemp(prefix="phase1_demo_"))
    (work / "example.py").write_text(module)
    print(f"[1/3] {args.tool} ({model}) writes tests for {args.program} ... (CPU, about 1-5 min)")
    rapl_ok, _ = rapl_readable()
    e0, t0 = rapl_snapshot() if rapl_ok else None, time.time()
    resp = chat(cfg, model, system, user)["message"]["content"]
    secs = time.time() - t0
    energy = rapl_delta_wh(e0, rapl_snapshot()) if rapl_ok else None

    tests, _, _ = extract_blocks(resp)
    tests, _ = normalize_imports(tests, module)
    (work / "test_example.py").write_text(tests)
    print(f"\n[2/3] Generated tests ({work / 'test_example.py'}):\n")
    print(tests)

    print("\n[3/3] Running the tests with coverage:\n")
    subprocess.run([str(VENV_PY), "-m", "coverage", "run", "--branch", "-m", "pytest", "-q", "test_example.py"], cwd=work)
    subprocess.run([str(VENV_PY), "-m", "coverage", "report", "-m", "--include=example.py"], cwd=work)

    print(f"\nGeneration time: {secs:.0f} s")
    if energy:
        pkg = next((v for k, v in energy.items() if k.startswith("msr:") and "package" in k), None)
        dram = next((v for k, v in energy.items() if k.startswith("msr:") and "dram" in k), None)
        print(f"Energy during generation (RAPL, gross, idle not subtracted): "
              f"package {pkg:.3f} Wh" + (f", DRAM {dram:.3f} Wh" if dram is not None else ""))
    else:
        print("Energy: RAPL not readable (run: sudo chmod a+r /sys/class/powercap/intel-rapl*:*/energy_uj)")
    print(f"\nFiles kept in {work}")


if __name__ == "__main__":
    main()
