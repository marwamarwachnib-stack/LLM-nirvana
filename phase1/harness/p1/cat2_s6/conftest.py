"""p1 harness for cat2_s6 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: gaussian_renderer and the scene code import CUDA extensions (diff_gaussian_rasterization, simple_knn),
which need an NVIDIA GPU.
Prepared: those three extension modules replaced by stubs; torch and the project's own modules are real.
"""
import sys
from unittest import mock

for name in ("diff_gaussian_rasterization", "simple_knn", "simple_knn._C"):
    sys.modules[name] = mock.MagicMock()
