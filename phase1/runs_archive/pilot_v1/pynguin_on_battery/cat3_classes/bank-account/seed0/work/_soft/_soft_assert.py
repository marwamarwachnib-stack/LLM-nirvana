"""Soft-assertion recorder injected by phase1/scripts/evaluate.py (instrumented copy only)."""
import json, os
_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soft_results.jsonl")

def record(site, outcome, detail=""):
    with open(_OUT, "a") as f:
        f.write(json.dumps({"site": site, "outcome": outcome, "detail": str(detail)[:300]}) + "\n")

class raises:
    """Wraps pytest.raises / assertRaises: records the outcome and never propagates."""
    def __init__(self, site, cm):
        self.site, self.cm = site, cm
    def __enter__(self):
        return self.cm.__enter__()
    def __exit__(self, et, ev, tb):
        try:
            suppressed = self.cm.__exit__(et, ev, tb)
        except AssertionError as e:      # unittest assertRaises: not raised
            record(self.site, "try_except", e)
        except BaseException as e:       # pytest "DID NOT RAISE" (Failed) or a different exception type
            name = type(e).__name__
            if name == "Failed" and "DID NOT RAISE" in str(e):
                record(self.site, "try_except", e)
            elif name in ("KeyboardInterrupt", "SystemExit"):
                raise
            else:
                record(self.site, "runtime", f"{name}: {e}")
        else:
            if et is not None and not suppressed:  # a different exception type: the manager lets it propagate
                record(self.site, "runtime", f"{et.__name__}: {ev}")
            else:
                record(self.site, "pass")
        return True
