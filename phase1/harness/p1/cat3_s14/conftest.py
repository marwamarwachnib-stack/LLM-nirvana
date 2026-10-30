"""p1 harness for cat3_s14 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: it is Python 2 code (`import cPickle`) and imports vbench.git (needs pandas.Panel, removed in pandas 1.0)
and, through vbench, vbench.benchmark (Python 2).
Prepared: cPickle aliased to the standard pickle (its Python 3 name); vbench.git and vbench.benchmark replaced
by stubs; vbench.db and vbench.utils are real.
"""
import pickle
import sys
from unittest import mock

sys.modules["cPickle"] = pickle
sys.modules["vbench.git"] = mock.MagicMock()
sys.modules["vbench.benchmark"] = mock.MagicMock()
