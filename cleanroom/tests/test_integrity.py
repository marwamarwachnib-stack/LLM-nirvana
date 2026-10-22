import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from cleanroom import integrity, paths


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class FixtureRepo(unittest.TestCase):
    """Small git repository mimicking the snapshot layout (names with spaces)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        _git(self.repo, "init", "-q")
        files = {
            "0_100 LOC/cat1/example.py": b"print('hi')\n",
            "0_100 LOC/README.md": b"readme\n",
            "100_300 LOC p2/s 1/mod.py": b"x = 1\n",
            "100_300 LOC p2/s 1/__pycache__/mod.cpython-310.pyc": b"\x00\x01binary",
        }
        for rel, data in files.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "snapshot")
        self.commit = _git(self.repo, "rev-parse", "HEAD")
        (self.repo / "cleanroom").mkdir()
        (self.repo / "cleanroom" / "new.txt").write_text("not original")
        self.entries = integrity.build(self.repo, self.commit)

    def tearDown(self):
        self.tmp.cleanup()


class TestBuild(FixtureRepo):
    def test_inventory_lists_tracked_files_only(self):
        self.assertEqual([e.path for e in self.entries], sorted([
            "0_100 LOC/README.md", "0_100 LOC/cat1/example.py",
            "100_300 LOC p2/s 1/__pycache__/mod.cpython-310.pyc", "100_300 LOC p2/s 1/mod.py"]))

    def test_blob_ids_match_git(self):
        for e in self.entries:
            expected = _git(self.repo, "hash-object", e.path)
            self.assertEqual(e.git_blob, expected)

    def test_build_refuses_modified_tree(self):
        (self.repo / "0_100 LOC/README.md").write_bytes(b"changed\n")
        with self.assertRaises(integrity.IntegrityError):
            integrity.build(self.repo, self.commit)

    def test_build_refuses_untracked_original_file(self):
        (self.repo / "0_100 LOC/stray.py").write_text("")
        with self.assertRaises(integrity.IntegrityError):
            integrity.build(self.repo, self.commit)

    def test_write_is_deterministic_and_round_trips(self):
        out = self.repo / "cleanroom"
        integrity.write_inventory(self.entries, out / "a.tsv", out / "a.sums")
        integrity.write_inventory(integrity.build(self.repo, self.commit), out / "b.tsv", out / "b.sums")
        self.assertEqual((out / "a.tsv").read_bytes(), (out / "b.tsv").read_bytes())
        self.assertEqual((out / "a.sums").read_bytes(), (out / "b.sums").read_bytes())
        self.assertEqual(integrity.read_inventory(out / "a.tsv"), self.entries)

    @unittest.skipUnless(shutil.which("sha256sum"), "coreutils sha256sum not available")
    def test_sums_file_is_coreutils_compatible(self):
        out = self.repo / "cleanroom"
        integrity.write_inventory(self.entries, out / "x.tsv", out / "x.sums")
        r = subprocess.run(["sha256sum", "--strict", "-c", str(out / "x.sums")],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count(": OK"), len(self.entries))


class TestVerify(FixtureRepo):
    def test_clean_tree_passes(self):
        r = integrity.verify(self.repo, self.entries)
        self.assertTrue(r.passed)
        self.assertEqual(r.ok, 4)

    def test_cleanroom_and_git_are_ignored(self):
        (self.repo / "cleanroom" / "more.py").write_text("x")
        self.assertTrue(integrity.verify(self.repo, self.entries).passed)

    def test_same_size_modification_detected(self):
        p = self.repo / "100_300 LOC p2/s 1/mod.py"
        p.write_bytes(b"x = 2\n")
        r = integrity.verify(self.repo, self.entries)
        self.assertFalse(r.passed)
        self.assertEqual(r.modified, ["100_300 LOC p2/s 1/mod.py"])

    def test_missing_detected(self):
        (self.repo / "0_100 LOC/README.md").unlink()
        r = integrity.verify(self.repo, self.entries)
        self.assertEqual(r.missing, ["0_100 LOC/README.md"])
        self.assertFalse(r.passed)

    def test_extra_pycache_detected(self):
        p = self.repo / "0_100 LOC/cat1/__pycache__/example.cpython-313.pyc"
        p.parent.mkdir()
        p.write_bytes(b"\x00")
        r = integrity.verify(self.repo, self.entries)
        self.assertEqual(r.extra, ["0_100 LOC/cat1/__pycache__/example.cpython-313.pyc"])
        self.assertFalse(r.passed)

    def test_new_top_level_file_detected(self):
        (self.repo / "notes.txt").write_text("x")
        self.assertEqual(integrity.verify(self.repo, self.entries).extra, ["notes.txt"])

    @unittest.skipIf(os.name == "nt", "symlinks")
    def test_symlink_reported(self):
        os.symlink("README.md", self.repo / "0_100 LOC/link.md")
        r = integrity.verify(self.repo, self.entries)
        self.assertEqual(r.not_regular, ["0_100 LOC/link.md"])
        self.assertFalse(r.passed)

    def test_against_git_detects_tampered_inventory(self):
        self.assertEqual(integrity.verify_against_git(self.repo, self.entries, self.commit), [])
        tampered = list(self.entries)
        e = tampered[0]
        tampered[0] = integrity.Entry(e.path, e.size, e.sha256, "0" * 40, e.mode)
        problems = integrity.verify_against_git(self.repo, tampered, self.commit)
        self.assertEqual(problems, [f"mode/blob mismatch: {e.path}"])
        self.assertTrue(integrity.verify_against_git(self.repo, tampered[1:], self.commit))

    def test_assert_originals_intact_raises(self):
        out = self.repo / "cleanroom"
        integrity.write_inventory(self.entries, out / "i.tsv", out / "i.sums")
        integrity.assert_originals_intact(self.repo, out / "i.tsv")
        (self.repo / "0_100 LOC/README.md").write_bytes(b"x")
        with self.assertRaises(integrity.IntegrityError):
            integrity.assert_originals_intact(self.repo, out / "i.tsv")


@unittest.skipUnless(paths.INVENTORY_TSV.exists(), "inventory not built yet")
class TestRealSnapshot(unittest.TestCase):
    """Checks against the actual frozen snapshot (read-only)."""

    def test_inventory_matches_working_tree_and_commit(self):
        entries = integrity.read_inventory(paths.INVENTORY_TSV)
        self.assertEqual(len(entries), 993)
        self.assertTrue(integrity.verify(paths.REPO_ROOT, entries).passed)
        self.assertEqual(integrity.verify_against_git(paths.REPO_ROOT, entries,
                                                      paths.SNAPSHOT_COMMIT), [])

    def test_inventory_is_reproducible(self):
        rebuilt = integrity.build(paths.REPO_ROOT, paths.SNAPSHOT_COMMIT)
        self.assertEqual(rebuilt, integrity.read_inventory(paths.INVENTORY_TSV))


if __name__ == "__main__":
    unittest.main()
