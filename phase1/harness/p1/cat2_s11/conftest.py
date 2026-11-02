"""p1 harness for cat2_s11 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: it imports win32api, which exists only on Windows.
Prepared: win32api replaced by a stub; nothing else.
"""
import sys
from unittest import mock

sys.modules["win32api"] = mock.MagicMock()
