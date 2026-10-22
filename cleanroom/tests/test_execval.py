import json
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from cleanroom import execval, paths

PY = execval.ENV_PYTHON if execval.ENV_PYTHON.exists() else Path(sys.executable)
HAS_ENV = execval.ENV_PYTHON.exists()
HAS_UNSHARE = shutil.which("unshare") is not None


def _write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def sandbox_with(self, files):
        sb = self.tmp / "sb"
        sb.mkdir(exist_ok=True)
        for name, text in files.items():
            _write(sb, name, text)
        return sb


@unittest.skipUnless(HAS_UNSHARE, "unshare not available")
class TestRunSandboxed(Tmp):
    def run_code(self, code, timeout=20):
        sb = self.sandbox_with({})
        return execval.run_sandboxed([str(PY), "-I", "-B", "-c", textwrap.dedent(code)], sb, timeout, PY)

    def test_network_is_disabled(self):
        rec, out = self.run_code("""
            import socket
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=3); print("CONNECTED")
            except OSError as e:
                print("BLOCKED", type(e).__name__)
        """)
        self.assertIn(b"BLOCKED", out)

    def test_stdin_is_closed(self):
        rec, out = self.run_code("""
            try:
                input(); print("READ")
            except EOFError:
                print("EOF")
        """)
        self.assertEqual(out.strip(), b"EOF")

    def test_minimal_environment(self):
        rec, out = self.run_code("import os, json; print(json.dumps(sorted(os.environ)))")
        keys = set(json.loads(out))
        self.assertTrue({"PATH", "HOME", "PYTHONHASHSEED", "TZ", "LC_ALL"} <= keys)
        self.assertFalse({"HTTPS_PROXY", "HTTP_PROXY", "PYTHONPATH"} & keys)

    def test_timeout_kills(self):
        rec, _ = self.run_code("while True: pass", timeout=1)
        self.assertTrue(rec.timed_out)
        self.assertLess(rec.duration_s, 10)

    def test_crash_signal_recorded(self):
        rec, _ = self.run_code("import os, signal; os.kill(os.getpid(), signal.SIGSEGV)")
        self.assertEqual(rec.signal, "SIGSEGV")

    def test_file_side_effects(self):
        rec, _ = self.run_code("open('new.txt', 'w').write('x')")
        self.assertEqual(rec.files_created, ["new.txt"])


@unittest.skipUnless(HAS_UNSHARE, "unshare not available")
class TestValidateImport(Tmp):
    def check(self, source, expected, **kw):
        sb = self.sandbox_with({"target.py": source})
        res = execval.validate_import({}, sb, PY, "target")
        self.assertEqual(res["outcome"], expected, res["first_result"])
        return res

    def test_ok_and_consistent(self):
        res = self.check("X = 1\n", "IMPORT_OK")
        self.assertTrue(res["consistent"])
        self.assertEqual(len(res["runs"]), execval.REPETITIONS)

    def test_missing_module(self):
        res = self.check("import no_such_module_xyz\n", "MISSING_MODULE")
        self.assertEqual(res["first_result"]["module"], "no_such_module_xyz")

    def test_exception(self):
        self.assertEqual(self.check("1/0\n", "IMPORT_ERROR")["first_result"]["exc_type"],
                         "ZeroDivisionError")

    def test_stdin_at_import_fails(self):
        self.assertEqual(self.check("n = input()\n", "IMPORT_ERROR")["first_result"]["exc_type"],
                         "EOFError")

    def test_system_exit(self):
        self.check("raise SystemExit(3)\n", "SYSTEM_EXIT")

    def test_timeout(self):
        with mock.patch.object(execval, "IMPORT_TIMEOUT_S", 1):
            self.check("while True: pass\n", "TIMEOUT")

    def test_nondeterministic_output_is_inconsistent(self):
        res = self.check("import os; print(os.urandom(8).hex())\n", "IMPORT_OK")
        self.assertFalse(res["consistent"])

    def test_side_effects_reported(self):
        res = self.check("open('out.log', 'a').write('x')\n", "IMPORT_OK")
        self.assertEqual(res["side_effect_files"], ["out.log"])
        self.assertFalse(res["consistent"])  # file content grows across repetitions


class TestParsing(unittest.TestCase):
    def rec(self, **kw):
        base = dict(argv=[], returncode=0)
        base.update(kw)
        return execval.RunRecord(**base)

    def test_parse_import_result(self):
        out = b"noise\n" + execval.RESULT_MARKER.encode() + b'{"outcome": "IMPORT_OK"}\n'
        self.assertEqual(execval.parse_import_result(self.rec(), out)["outcome"], "IMPORT_OK")
        self.assertEqual(execval.parse_import_result(self.rec(timed_out=True), b"")["outcome"], "TIMEOUT")
        self.assertEqual(execval.parse_import_result(self.rec(returncode=-11, signal="SIGSEGV"), b"")
                         ["outcome"], "CRASH")
        self.assertEqual(execval.parse_import_result(self.rec(returncode=1), b"x")["outcome"], "CRASH")

    def test_parse_junit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "j.xml"
            p.write_text("""<testsuites><testsuite>
              <testcase classname="m.T" name="a"/>
              <testcase classname="m.T" name="b"><failure message="x"/></testcase>
              <testcase classname="m.T" name="c"><error message="x"/></testcase>
              <testcase classname="m.T" name="d"><skipped/></testcase>
            </testsuite></testsuites>""")
            r = execval.parse_junit(p)
        self.assertEqual((r["tests"], r["passed"], r["failed"], r["error"], r["skipped"]), (4, 1, 1, 1, 1))
        self.assertEqual(r["outcomes"]["m.T::b"], "failed")
        self.assertFalse(execval.parse_junit(Path("/nonexistent.xml"))["parsed"])

    def test_consistent(self):
        self.assertTrue(execval.consistent([1, 1, 1]))
        self.assertFalse(execval.consistent([1, 2, 1]))
        self.assertFalse(execval.consistent([]))


class TestDecide(unittest.TestCase):
    def v1(self, outcome="IMPORT_OK", consistent=True, side=()):
        return {"outcome": outcome, "consistent": consistent, "side_effect_files": list(side),
                "first_result": {"outcome": outcome, "module": "x"}}

    def test_branches(self):
        d = execval.decide({"v1_import": self.v1("MISSING_MODULE")})
        self.assertEqual((d["execution_verified"], d["outcome"]), (False, "FAIL_IMPORT_MISSING_MODULE"))
        d = execval.decide({"v1_import": self.v1(consistent=False)})
        self.assertEqual(d["outcome"], "FAIL_IMPORT_INCONSISTENT")
        d = execval.decide({"v1_import": self.v1()})
        self.assertEqual((d["execution_verified"], d["outcome"]), (True, "VERIFIED_IMPORT"))
        v2 = {"status": "RAN", "consistent": True, "tests": 3, "passed": 2, "failed": 1, "error": 0}
        d = execval.decide({"v1_import": self.v1(), "v2b_reference": v2})
        self.assertEqual(d["outcome"], "VERIFIED_IMPORT_AND_DEVTESTS")
        self.assertIn("2/3 passed", d["outcome_reason"])
        d = execval.decide({"v1_import": self.v1(), "v2b_reference": dict(v2, consistent=False)})
        self.assertEqual((d["execution_verified"], d["outcome"]), (False, "FAIL_DEVTEST_INCONSISTENT"))
        d = execval.decide({"v1_import": self.v1(), "v2b_reference": dict(v2, status="TIMEOUT")})
        self.assertEqual(d["outcome"], "FAIL_DEVTEST_TIMEOUT")


class TestSandboxConstruction(Tmp):
    def prog(self, **kw):
        base = {"program_id": "small/cat2_functions/two-fer", "name": "two-fer",
                "directory": "0_100 LOC/cat2_functions/two-fer",
                "target": "0_100 LOC/cat2_functions/two-fer/example.py",
                "saved_suites": "pynguin:0_100 LOC/cat2_functions/two-fer/test_example.py",
                "dev_test_files": "0_100 LOC/cat2_functions/two-fer/two_fer_test.py",
                "dev_test_imports": "two_fer"}
        base.update(kw)
        return base

    def layout(self, with_config=True):
        d = "0_100 LOC/cat2_functions/two-fer"
        _write(self.tmp, f"{d}/example.py", "def two_fer(name='you'):\n    return f'One for {name}, one for me.'\n")
        _write(self.tmp, f"{d}/two_fer.py", "def two_fer(name):\n    pass\n")
        _write(self.tmp, f"{d}/two_fer_test.py", """
            import unittest
            from two_fer import two_fer
            class T(unittest.TestCase):
                def test_a(self):
                    self.assertEqual(two_fer("Bob"), "One for Bob, one for me.")
                def test_b(self):
                    self.assertEqual(two_fer(), "One for you, one for me.")
        """)
        _write(self.tmp, f"{d}/test_example.py", "# authors' saved suite\n")
        _write(self.tmp, f"{d}/notes.txt", "not copied")
        if with_config:
            _write(self.tmp, f"{d}/config.json",
                   '{"files": {"solution": ["two_fer.py"], "test": ["two_fer_test.py"], '
                   '"example": [".meta/example.py"]}}')

    def test_sandbox_files_exclude_saved_suites_and_non_python(self):
        self.layout()
        files = execval.sandbox_files(self.prog(), self.tmp)
        self.assertEqual([Path(f).name for f in files], ["example.py", "two_fer.py", "two_fer_test.py"])

    def test_make_sandbox_refuses_existing_dir_and_copies_bytes(self):
        self.layout()
        files = execval.sandbox_files(self.prog(), self.tmp)
        copied = execval.make_sandbox(self.tmp / "sb", files, self.tmp)
        self.assertEqual(set(copied), {"example.py", "two_fer.py", "two_fer_test.py"})
        with self.assertRaises(FileExistsError):
            execval.make_sandbox(self.tmp / "sb", files, self.tmp)

    def test_solution_module_evidence(self):
        self.layout(with_config=True)
        self.assertEqual(execval.solution_module(self.prog(), self.tmp),
                         ("two_fer.py", "config.json files.solution"))
        (self.tmp / "0_100 LOC/cat2_functions/two-fer/config.json").unlink()
        self.assertEqual(execval.solution_module(self.prog(), self.tmp)[0], "two_fer.py")
        self.assertIn("inferred", execval.solution_module(self.prog(), self.tmp)[1])

    @unittest.skipUnless(HAS_ENV and HAS_UNSHARE, "Python 3.10.12 environment not built")
    def test_validate_program_end_to_end(self):
        self.layout()
        run_dir = self.tmp / "run"
        res = execval.validate_program(self.prog(), run_dir, self.tmp / "sandboxes", PY, self.tmp)
        self.assertEqual(res["v2a_as_shipped"]["failed"], 2)  # stub returns None
        self.assertEqual(res["v2b_reference"]["passed"], 2)
        self.assertTrue(res["v2b_resolution"]["test_files_unmodified"])
        self.assertTrue(res["execution_verified"])
        self.assertEqual(res["outcome"], "VERIFIED_IMPORT_AND_DEVTESTS")
        self.assertFalse((self.tmp / "sandboxes" / "small__cat2_functions__two-fer").exists())
        self.assertTrue((run_dir / "programs/small__cat2_functions__two-fer/result.json").is_file())
        # the repository-side files were not touched
        self.assertIn("pass", (self.tmp / "0_100 LOC/cat2_functions/two-fer/two_fer.py").read_text())


class TestSealedRuns(unittest.TestCase):
    def test_every_sealed_run_still_matches(self):
        for seal in sorted(execval.RUNS_DIR.glob("*/SEALED.sha256")):
            run_dir = seal.parent
            expected = dict(reversed(line.split("  ", 1)) for line in seal.read_text().splitlines() if line)
            actual = {p: h for p, h in execval.tree_hashes(run_dir).items() if p != "SEALED.sha256"}
            self.assertEqual(actual, expected, f"sealed run changed: {run_dir.name}")


if __name__ == "__main__":
    unittest.main()
