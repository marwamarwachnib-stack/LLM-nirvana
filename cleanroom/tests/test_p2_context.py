import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from cleanroom import execval, manifest, p2_context as ctx, p2_externals, p2_validate, paths
from cleanroom import provenance as pv

HAS_ENV = execval.ENV_PYTHON.exists()


def wheel(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)


class TestIndexFiltering(unittest.TestCase):
    def test_release_artifacts_cutoff_types_yanked(self):
        index = {"releases": {
            "1.0": [{"packagetype": "sdist", "upload_time_iso_8601": "2020-01-01T00:00:00Z",
                     "filename": "p-1.0.tar.gz", "url": "u", "digests": {"sha256": "a"}},
                    {"packagetype": "bdist_egg", "upload_time_iso_8601": "2020-01-01T00:00:00Z",
                     "filename": "p-1.0.egg", "url": "u", "digests": {"sha256": "b"}}],
            "2.0": [{"packagetype": "bdist_wheel", "upload_time_iso_8601": "2025-01-01T00:00:00Z",
                     "filename": "p-2.0.whl", "url": "u", "digests": {"sha256": "c"}}],
            "1.5": [{"packagetype": "bdist_wheel", "upload_time_iso_8601": "2021-01-01T00:00:00Z",
                     "filename": "p-1.5.whl", "url": "u", "digests": {"sha256": "d"}, "yanked": True}]}}
        self.assertEqual([a["filename"] for a in ctx.release_artifacts(index)], ["p-1.0.tar.gz"])

    def test_verify_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a"
            p.write_bytes(b"x")
            ctx.verify_artifact(p, pv.sha256(b"x"))
            with self.assertRaises(RuntimeError):
                ctx.verify_artifact(p, "0" * 64)


class TestClosure(unittest.TestCase):
    PKG = {
        "pkg/__init__.py": b"from pkg.core import Core\n",
        "pkg/core.py": b"from .util import helper\nimport stringcase\nclass Core: pass\n",
        "pkg/util.py": b"def helper(): pass\n",
        "pkg/types.py": b"PathType = str\n",
        "pkg/sub/__init__.py": b"",
        "pkg/sub/util.py": b"x = 1\n",
        "pkg/api.py": b"from .core import Core\n",
    }

    def test_flat_and_package_closure(self):
        target = (b"import os\nfrom core import Core\nimport sys\n"
                  b"def f():\n    from pkg.util import helper\n    import IPython\n")
        cl = ctx.import_closure(target, {k: v for k, v in self.PKG.items() if "sub/" not in k}, "pkg", {})
        self.assertEqual(cl.flat_modules, {"core": "pkg/core.py", "util": "pkg/util.py"})
        self.assertEqual(cl.pkg_files, {"pkg/__init__.py", "pkg/core.py", "pkg/util.py"})
        self.assertEqual(sorted(cl.externals), ["IPython", "stringcase"])
        at_import = {k: any(i["at_import_time"] for i in v) for k, v in cl.externals.items()}
        self.assertEqual(at_import, {"IPython": False, "stringcase": True})
        self.assertEqual(cl.problems, [])

    def test_ambiguous_flat_name_is_a_problem(self):
        cl = ctx.import_closure(b"from util import x\n", self.PKG, "pkg", {})
        self.assertTrue(any("ambiguous" in p for p in cl.problems))

    def test_optional_and_conditional_imports_not_required(self):
        target = (b"try:\n    import yaml\nexcept ImportError:\n    yaml = None\n"
                  b"import platform\nif platform.system() == 'Windows':\n    from colorama import init\n"
                  b"from sys import hexversion\nif hexversion >= 0x03080000:\n    from functools import cached_property\n"
                  b"else:\n    from .decorators import cached_property\n"
                  b"from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import attr\n")
        cl = ctx.import_closure(target, self.PKG, "pkg", {})
        self.assertEqual(cl.externals, {})
        self.assertEqual(cl.problems, [])
        self.assertEqual(len(cl.optional_unresolved), 3)  # yaml, colorama, .decorators

    def test_unguarded_relative_import_in_flat_module_is_a_problem(self):
        cl = ctx.import_closure(b"from .core import Core\n", self.PKG, "pkg", {})
        self.assertTrue(cl.problems)

    def test_target_name_never_resolved_to_release_copy(self):
        pkg = dict(self.PKG, **{"pkg/core.py": b"from .api import x\n"})
        cl = ctx.import_closure(b"from core import Core\n", pkg, "pkg", {}, target_stem="api")
        self.assertNotIn("api", cl.flat_modules)

    def test_renamed_module(self):
        cl = ctx.import_closure(b"from types_renamed import PathType\n", self.PKG, "pkg", {"types_renamed": "types"})
        self.assertEqual(cl.flat_modules, {"types_renamed": "pkg/types.py"})

    def test_benchmark_sibling_override_used(self):
        ov = {"core": {"program_id": "p2/x", "path": "x/core.py", "bytes": b"class Core: pass\n"}}
        cl = ctx.import_closure(b"from core import Core\n", self.PKG, "pkg", {}, overrides=ov)
        self.assertEqual(cl.flat_modules, {"core": "pkg/core.py"})
        self.assertEqual(cl.externals, {})  # the override (not the release file) was analysed

    def test_materialize_writes_hashes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = b"from core import Core\ndef f():\n    from pkg.util import helper\n"
            cl = ctx.import_closure(target, self.PKG, "pkg", {})
            m = ctx.materialize("sX", "mod.py", target, self.PKG, cl, "pkg", dest_root=Path(d))
            kinds = {f["path"]: f["kind"] for f in m["files"]}
            self.assertEqual(kinds["flat/mod.py"], "benchmark_module")
            self.assertEqual(kinds["flat/core.py"], "release_derived")
            self.assertEqual(kinds["pkgroot/pkg/util.py"], "release_verbatim")
            self.assertEqual(kinds["pkgroot/pkg/__init__.py"], "release_verbatim")
            for f in m["files"]:
                self.assertEqual(pv.sha256((Path(d) / "sX" / f["path"]).read_bytes()), f["sha256"])
            self.assertEqual(p2_validate.verify_context_files(m), [])
            (Path(d) / "sX/flat/core.py").write_text("tampered")
            self.assertEqual(p2_validate.verify_context_files(m), ["flat/core.py"])
            bad = ctx.Closure(flat_modules={"mod": "pkg/core.py"})
            with self.assertRaises(ValueError):
                ctx.materialize("sY", "mod.py", target, self.PKG, bad, "pkg", dest_root=Path(d))

    def test_context_modules(self):
        files = [{"path": "flat/t.py", "kind": "benchmark_module"}, {"path": "flat/core.py", "kind": "x"},
                 {"path": "pkgroot/pkg/__init__.py", "kind": "x"}, {"path": "pkgroot/pkg/sub/util.py", "kind": "x"}]
        self.assertEqual(p2_validate.context_modules(files), ["core", "pkg", "pkg.sub.util"])


class TestResolveProject(unittest.TestCase):
    """Release identity rules on synthetic artifacts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.dist = root / "dist"
        (self.dist / "pkg").mkdir(parents=True)
        self.arts = []
        common = {"pkg/__init__.py": "", "pkg/base.py": "class B: pass\n"}
        for v, a_src in [("1.0", "from .base import B\nX = 1\n"), ("1.1", "from .base import B\nX = 1\n"),
                         ("2.0", "from .base import B\nX = 2\n")]:
            fn = f"pkg-{v}-py3-none-any.whl"
            wheel(self.dist / "pkg" / fn, dict(common, **{"pkg/a.py": a_src, "pkg/b.py": "from pkg.a import X\n"}))
            self.arts.append({"version": v, "filename": fn})
        rows = {}
        for s, name, text, status in [("sample1", "a.py", "from base import B\nX = 1\n", manifest.PENDING_CONTEXT),
                                      ("sample2", "b.py", "from a import X\n", manifest.PENDING_CONTEXT),
                                      ("sample3", "a.py", "from base import B\nX = 3\n", manifest.PENDING_CONTEXT)]:
            p = self.repo / s / name
            p.parent.mkdir(parents=True)
            p.write_text(text)
            rows[s] = {"program_id": f"p2/{s}", "status": status, "target": f"{s}/{name}"}
        self.rows = rows

    def tearDown(self):
        self.tmp.cleanup()

    def run_project(self, samples, **extra):
        proj = {"pypi": "pkg", "package": "pkg", "samples": samples, "evidence": "test", **extra}
        with mock.patch.object(ctx, "DIST_DIR", self.dist):
            return ctx.resolve_project("pkg", proj, self.rows, self.arts, self.repo)

    def test_intersection_and_benchmark_sibling(self):
        res = self.run_project(["sample1", "sample2"])
        self.assertEqual(res["release_set"], ["1.0", "1.1"])
        d = res["samples"]["sample2"]
        self.assertEqual(d["decision"], ctx.RESOLVED)
        self.assertEqual(d["benchmark_siblings_available"], ["a"])

    def test_no_matching_release(self):
        res = self.run_project(["sample3"])
        self.assertEqual(res["samples"]["sample3"]["decision"], ctx.UNRESOLVED_NO_MATCH)

    def test_no_common_release(self):
        self.rows["sample3"]["status"] = manifest.CANDIDATE  # cross-check sample without a match
        res = self.run_project(["sample1", "sample3"])
        self.assertEqual(res["release_set"], [])
        self.assertEqual(res["samples"]["sample1"]["decision"], ctx.UNRESOLVED_NO_COMMON)
        self.assertEqual(res["samples"]["sample3"]["decision"], "CROSS_CHECK_ONLY")

    def test_vcs_snapshot_never_resolved(self):
        res = self.run_project(["sample1"], vcs_snapshot="branch archive")
        self.assertEqual(res["samples"]["sample1"]["decision"], ctx.UNRESOLVED_VCS)

    def test_ambiguous_when_required_files_differ(self):
        wheel(self.dist / "pkg" / self.arts[1]["filename"],
              {"pkg/__init__.py": "", "pkg/base.py": "class B: x = 1\n",
               "pkg/a.py": "from .base import B\nX = 1\n", "pkg/b.py": "from pkg.a import X\n"})
        res = self.run_project(["sample1"])
        self.assertEqual(res["samples"]["sample1"]["decision"], ctx.UNRESOLVED_AMBIGUOUS)


@unittest.skipUnless(HAS_ENV, "Python 3.10.12 environment not built")
class TestExternalsPolicy(unittest.TestCase):
    def test_markers_evaluated_for_linux_py310(self):
        self.assertEqual(p2_externals.applicable(['colorama; platform_system == "Windows"',
                                                  'enum34; python_version < "3.4"', "termcolor>=1.0"]),
                         ["termcolor>=1.0"])

    def test_newest_before_cutoff(self):
        idx = {"releases": {"1.0": [{"upload_time_iso_8601": "2020-01-01T00:00:00Z"}],
                            "1.10": [{"upload_time_iso_8601": "2023-01-01T00:00:00Z"}],
                            "2.0rc1": [{"upload_time_iso_8601": "2023-06-01T00:00:00Z"}],
                            "1.9": [{"upload_time_iso_8601": "2023-02-01T00:00:00Z", "yanked": True}],
                            "3.0": [{"upload_time_iso_8601": "2025-01-01T00:00:00Z"}]}}
        self.assertEqual(p2_externals.newest_before(idx, "2024-01-26T16:51:11"), "1.10")

    def test_only_declared_and_needed_requirements(self):
        spec = {"declared": ["ipython", "psutil", "termcolor>=1.0"],
                "import_names": {"IPython": "ipython", "psutil": "psutil", "termcolor": "termcolor"}}
        with mock.patch.object(p2_externals, "resolve_lock", side_effect=AssertionError("network")), \
                mock.patch.object(p2_externals, "build_sdist_only"):
            out = p2_externals.install("x==1", spec, set(), "2024-01-26", [])
        self.assertEqual(out["status"], "NOTHING_TO_INSTALL")
        self.assertEqual(out["declared_not_needed"], ["ipython", "psutil", "termcolor"])


class TestRealResolution(unittest.TestCase):
    """Consistency of the committed resolution record with the snapshot and PyPI indexes."""

    @classmethod
    def setUpClass(cls):
        runs = sorted(p for p in ctx.OUT_DIR.glob("*/resolution.json")
                      if not (p.parent / "SUPERSEDED.txt").exists())
        cls.path = runs[-1] if runs else None

    def test_resolved_records_are_consistent(self):
        if self.path is None:
            self.skipTest("no resolution run")
        res = json.loads(self.path.read_text())
        rows = {r["program_id"]: r for r in manifest.read_manifest(paths.MANIFEST_CSV)}
        for project, pres in res.items():
            index = json.loads((self.path.parent / "pypi" / f"{pres['pypi']}.json").read_text())
            digests = {f["filename"]: f["digests"]["sha256"] for fs in index["releases"].values() for f in fs}
            for s, d in pres["samples"].items():
                if d.get("decision") != ctx.RESOLVED:
                    continue
                self.assertIn(d["artifact_used"], digests)
                self.assertTrue(set(d["release_set"]) <= set(d["matching_releases"]))
                bench = (paths.REPO_ROOT / rows[d["program_id"]]["target"]).read_bytes()
                files = {f["path"]: f for f in d["context"]["files"]}
                target = [f for f in files.values() if f["kind"] == "benchmark_module"]
                self.assertEqual(len(target), 1)
                self.assertEqual(target[0]["sha256"], pv.sha256(bench))
                for f in files.values():
                    if f["kind"] == "benchmark_sibling":
                        sib = (paths.REPO_ROOT / f["benchmark_path"]).read_bytes()
                        self.assertEqual(f["sha256"], pv.sha256(sib))


if __name__ == "__main__":
    unittest.main()
