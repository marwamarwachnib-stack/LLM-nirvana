"""Shared helpers for Phase 1: config, atomic I/O, environment capture, RAPL and energy metering."""
import contextlib
import datetime as dt
import glob
import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import psutil
import yaml

PHASE1 = Path(__file__).resolve().parent.parent
REPO = PHASE1.parent
CONFIG_DIR = PHASE1 / "config"
RUNS = Path(os.environ.get("PHASE1_RUNS", PHASE1 / "runs"))           # override only for smoke tests
# results next to their runs (runs_main -> results_main), so a runs folder given alone never overwrites the pilot's results/
RESULTS = Path(os.environ.get("PHASE1_RESULTS") or RUNS.parent / RUNS.name.replace("runs", "results", 1))
VENV_PY = PHASE1 / ".venv" / "bin" / "python"              # orchestration, energy meter, analysis (Python 3.12)
RUNNER_PY = PHASE1 / ".venv-run" / "bin" / "python"        # runs the code under test: pytest, coverage (Python 3.10.12,
                                                           # pytest 7.4.0, coverage 7.3.0: the authors' versions, decision 16)
PYNGUIN_BIN = PHASE1 / ".venv-pynguin" / "bin" / "pynguin"  # Pynguin 0.34.0 on Python 3.10.12, as the authors
POWERCAP = Path("/sys/class/powercap")

log = logging.getLogger("phase1")


def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


XDG_BASE = ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")


def run_code(cmd, env=None, **kw):
    """subprocess.run for a process that runs the code under test (pytest, coverage, Pynguin): the program's import
    paths `env`, and an empty HOME of its own, removed afterwards (the XDG directories follow it). What one run writes
    there (httpie's ~/.httpie, mutpy's ~/mutpy, IPython's history) can then not change what a later run covers:
    a ~/.httpie left by Pynguin changed a ChatGPT suite's coverage of p2 sample9 (decision 16)."""
    with tempfile.TemporaryDirectory(prefix="phase1-home-", ignore_cleanup_errors=True) as home:
        base = {k: v for k, v in os.environ.items() if k not in XDG_BASE}
        return subprocess.run(cmd, env={**base, **(env or {}), "HOME": home}, **kw)


def load_config():
    with open(CONFIG_DIR / "experiment.yaml") as f:
        cfg = yaml.safe_load(f)
    if cfg["decoding"].get("num_thread") == "auto":  # resolved here so manifests record the actual value
        cfg["decoding"]["num_thread"] = psutil.cpu_count(logical=False)
    return cfg


def sha256_text(s):
    return hashlib.sha256(s.encode()).hexdigest()


def atomic_write_text(path, text):
    """Write via temp file + fsync + rename so a power cut never leaves a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path, obj):
    atomic_write_text(path, json.dumps(obj, indent=2, default=str) + "\n")


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def reset_dir(path):
    """Remove a partially written directory (no DONE marker) and recreate it empty."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def mark_done(path):
    atomic_write_text(Path(path) / "DONE", now_iso() + "\n")


def is_done(path):
    return (Path(path) / "DONE").exists()


def git_commit():
    try:
        rev = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip() != ""
        return {"commit": rev, "dirty": dirty}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def _read(path, default=None):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def system_state():
    """Power/thermal settings that influence time and energy; stored in every manifest."""
    return {
        "governor": _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "no_turbo": _read("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "ac_online": [_read(p) for p in glob.glob("/sys/class/power_supply/*/online")],
        "energy_performance_preference": _read("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference"),
        "pkg_temp_c": pkg_temp(),
        "load_avg": os.getloadavg(),
        "mem_available_gb": round(psutil.virtual_memory().available / 2**30, 2),
    }


def on_ac():
    """True if a mains adapter reports online (None if the machine exposes no adapter)."""
    vals = [_read(p) for p in glob.glob("/sys/class/power_supply/AC*/online") + glob.glob("/sys/class/power_supply/ADP*/online")]
    return None if not vals else any(v == "1" for v in vals)


def wait_for_ac(allow_battery=False, poll_s=30):
    """Block until the laptop is on mains power: on battery the CPU runs a different energy/performance
    preference, so time and energy are not comparable (the pilot's Pynguin bank-account runs, PLAN.md §13.11)."""
    if allow_battery or on_ac() is not False:
        return 0
    t0 = time.time()
    print("  ON BATTERY: waiting for the charger before the next job (plug it in; Ctrl+C to stop)...", flush=True)
    while on_ac() is False:
        time.sleep(poll_s)
    print(f"  AC back after {time.time() - t0:.0f}s, continuing", flush=True)
    return time.time() - t0


def environment_info():
    return {
        "captured_at": now_iso(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "cpu": _cpu_model(),
        "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 2),
        "python": platform.python_version(),
        "git": git_commit(),
        "system_state": system_state(),
        "rapl_domains": rapl_domains_info(),
    }


def machine_id():
    return {"hostname": platform.node(), "cpu": _cpu_model()}


def _cpu_model():
    for line in _read("/proc/cpuinfo", "").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


# ----------------------------------------------------------------------------- thermal

def pkg_temp():
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        if _read(f"{z}/type") == "x86_pkg_temp":
            t = _read(f"{z}/temp")
            return int(t) / 1000 if t else None
    return None


def cooldown(cfg):
    """Wait (bounded) until the package is below the threshold, to limit throttling carry-over."""
    e = cfg["energy"]
    t0 = time.time()
    while time.time() - t0 < e["cooldown_max_s"]:
        t = pkg_temp()
        if t is None or t < e["cooldown_temp_c"]:
            break
        time.sleep(2)
    return round(time.time() - t0, 1)


# ----------------------------------------------------------------------------- RAPL

def _rapl_dirs():
    """All RAPL domains, both MSR (intel-rapl:*) and MMIO (intel-rapl-mmio:*) interfaces."""
    return sorted(p for p in POWERCAP.glob("intel-rapl*:*") if (p / "energy_uj").exists())


def _domain_key(p):
    iface = "mmio" if "mmio" in p.name else "msr"
    return f"{iface}:{p.name}:{_read(p / 'name')}"


def rapl_domains_info():
    out = {}
    for p in _rapl_dirs():
        out[_domain_key(p)] = {"path": str(p / "energy_uj"),
                               "readable": os.access(p / "energy_uj", os.R_OK),
                               "max_energy_range_uj": _read(p / "max_energy_range_uj")}
    return out


def rapl_readable():
    info = rapl_domains_info()
    pkg = [k for k, v in info.items() if "package" in k]
    return bool(pkg) and all(info[k]["readable"] for k in pkg), info


def rapl_snapshot():
    snap = {}
    for p in _rapl_dirs():
        v = _read(p / "energy_uj")
        if v is not None:
            snap[_domain_key(p)] = (int(v), int(_read(p / "max_energy_range_uj") or 0))
    return snap


def rapl_delta_wh(a, b):
    """Energy per domain between two snapshots, handling counter wrap-around."""
    out = {}
    for k, (v0, vmax) in a.items():
        if k not in b:
            continue
        v1 = b[k][0]
        d = v1 - v0 if v1 >= v0 else v1 + vmax - v0
        out[k] = d / 3.6e9  # uJ -> Wh
    return out


# ----------------------------------------------------------------------------- energy meter

class _Sampler(threading.Thread):
    """Samples temperature, CPU frequency and utilisation every second during a phase."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_evt = threading.Event()
        self.temps, self.freqs, self.utils = [], [], []

    def run(self):
        psutil.cpu_percent(None)
        while not self.stop_evt.wait(1.0):
            t = pkg_temp()
            if t is not None:
                self.temps.append(t)
            f = psutil.cpu_freq()
            if f:
                self.freqs.append(f.current)
            self.utils.append(psutil.cpu_percent(None))

    def summary(self):
        def stats(xs):
            return {"mean": round(sum(xs) / len(xs), 1), "max": round(max(xs), 1)} if xs else None
        return {"pkg_temp_c": stats(self.temps), "cpu_mhz": stats(self.freqs), "cpu_util_pct": stats(self.utils)}


@contextlib.contextmanager
def measure(phase, out_dir, cfg, record):
    """Measure one phase with CodeCarbon (RAPL) + an independent raw RAPL reading.

    Fills ``record`` (a dict) with wall time, CodeCarbon energy, raw RAPL energy per domain
    and thermal/frequency statistics. Energy is in Wh.

    With ``cfg["_energy"] == "none"`` only the wall time is recorded: an external meter (e.g. the
    energy tool of the supervisors) wraps the whole command and must not see CodeCarbon's sampling.
    """
    if cfg.get("_energy") == "none":
        started, t0 = now_iso(), time.perf_counter()
        try:
            yield record
        finally:
            record.update({"phase": phase, "started": started, "wall_s": round(time.perf_counter() - t0, 3),
                           "energy_meter": "external"})
        return
    from codecarbon import OfflineEmissionsTracker
    logging.getLogger("codecarbon").setLevel(logging.ERROR)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tracker = OfflineEmissionsTracker(
        project_name=phase, output_dir=str(out_dir), output_file="emissions.csv",
        measure_power_secs=cfg["energy"]["measure_power_secs"], tracking_mode="machine",
        country_iso_code=cfg["energy"]["country_iso_code"], save_to_file=True,
        log_level="error", allow_multiple_runs=True, gpu_ids=[],
    )
    sampler = _Sampler()
    tracker.start()
    sampler.start()
    r0 = rapl_snapshot()
    t0 = time.perf_counter()
    started = now_iso()
    try:
        yield record
    finally:
        wall = time.perf_counter() - t0
        r1 = rapl_snapshot()
        sampler.stop_evt.set()
        tracker.stop()
        sampler.join(timeout=3)
        fe = tracker.final_emissions_data
        cc = None
        if fe is not None:
            cc = {
                "cpu_wh": fe.cpu_energy * 1000, "ram_wh": fe.ram_energy * 1000,
                "gpu_wh": fe.gpu_energy * 1000, "total_wh": fe.energy_consumed * 1000,
                "cpu_power_w": fe.cpu_power, "ram_power_w": fe.ram_power,
                "emissions_kgco2eq": fe.emissions, "duration_s": fe.duration,
                "cpu_model": fe.cpu_model, "tracking_mode": fe.tracking_mode,
                "codecarbon_version": fe.codecarbon_version, "country_iso_code": fe.country_iso_code,
            }
        record.update({
            "phase": phase, "started": started, "wall_s": round(wall, 3),
            "codecarbon": cc, "rapl_raw_wh": rapl_delta_wh(r0, r1), **sampler.summary(),
        })
