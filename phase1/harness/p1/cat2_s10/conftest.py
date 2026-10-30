"""p1 harness for cat2_s10 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: its dependency vbench.benchmark (wesm/vbench) is Python 2 code (exec statement, line 52).
Prepared: vbench.benchmark replaced by a stub; the module itself and the rest of vbench are real.
"""
import sys
from unittest import mock

sys.modules["vbench.benchmark"] = mock.MagicMock()
