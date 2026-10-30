"""p1 harness for cat3_s8 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: `from .image_utils import ...` is a relative import, and no version of its CoDeF repository matches
the authors' file, so its sibling image_utils is not available.
Prepared: example.py loaded as a member of a stub package whose image_utils is a stub, then registered as
`example`. Its other imports (skvideo, numpy, ...) are real.
"""
import importlib.abc
import importlib.util
import os
import sys
import types
from unittest import mock


EXAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example.py")


def load():
    package = types.ModuleType("codef_utils")
    package.__path__ = []
    sys.modules["codef_utils"] = package
    sys.modules["codef_utils.image_utils"] = mock.MagicMock()
    spec = importlib.util.spec_from_file_location("codef_utils.example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PreparedImport(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """A test's `import example` runs load() in place of the plain import."""

    def find_spec(self, name, path=None, target=None):
        return importlib.util.spec_from_loader(name, self, origin=EXAMPLE) if name == "example" else None

    def create_module(self, spec):
        self.module = load()
        self.spec = self.module.__spec__
        return self.module

    def exec_module(self, module):
        module.__spec__ = self.spec  # load() ran it already; keep the spec it was loaded with


sys.meta_path.insert(0, PreparedImport())
