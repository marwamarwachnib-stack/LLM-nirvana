"""p1 harness for cat3_s10 (P1_HARNESS_STATUS.md). pytest loads it before the test files; it is used only when
PHASE1_HARNESS=1 (decision 20). It does not change example.py and does not import it: a test's own `import example`
or `from example import ...` gets the prepared module, and a suite that never imports it gets nothing from here.

Why: it calls bot.run('token') at import: a login with a placeholder token (fails online, and offline).
Prepared: discord's Bot.run and Client.run patched during the import only; afterwards the real methods are back.
"""
import importlib.abc
import importlib.util
import os
import sys
from unittest import mock


EXAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "example.py")


def load():
    import discord
    from discord.ext import commands
    spec = importlib.util.spec_from_file_location("example", EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(commands.Bot, "run"), mock.patch.object(discord.Client, "run"):
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
