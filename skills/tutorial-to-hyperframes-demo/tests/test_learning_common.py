from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import learning_common as common  # noqa: E402
from learning_common import (  # noqa: E402
    atomic_write_json,
    canonical_json_bytes,
    reject_private_payload,
    secure_run_relative,
    sha256_file,
    write_immutable_or_adopt,
)


class CanonicalJsonTests(unittest.TestCase):
    def test_normalizes_recursively_sorts_keys_and_uses_one_trailing_newline(self) -> None:
        payload = {"z": ["e\u0301"], "a": {"b": 2}}

        self.assertEqual(
            canonical_json_bytes(payload),
            '{"a":{"b":2},"z":["é"]}\n'.encode("utf-8"),
        )

    def test_rejects_non_json_nan_and_normalized_key_collision(self) -> None:
        invalid = [
            {"tuple": (1, 2)},
            {"nan": float("nan")},
            {"infinity": float("inf")},
            {1: "non-string key"},
            {"e\u0301": 1, "é": 2},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                canonical_json_bytes(value)


class HashTests(unittest.TestCase):
    def test_sha256_file_hashes_binary_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blob.bin"
            path.write_bytes(b"a\x00b" * 400_000)
            self.assertEqual(sha256_file(path), hashlib.sha256(path.read_bytes()).hexdigest())


class SecureRunRelativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_accepts_existing_and_future_contained_paths(self) -> None:
        existing = self.run_dir / "drafts" / "input.json"
        existing.parent.mkdir()
        existing.write_text("{}", encoding="utf-8")

        self.assertEqual(
            secure_run_relative(self.run_dir, "drafts/input.json", must_exist=True),
            existing.resolve(),
        )
        self.assertEqual(
            secure_run_relative(self.run_dir, "usage-events/new.json", must_exist=False),
            self.run_dir.resolve() / "usage-events" / "new.json",
        )

    def test_rejects_empty_absolute_parent_windows_and_unicode_home_paths(self) -> None:
        unsafe = [
            "",
            "/" + "Users/alice/private.json",
            "../outside.json",
            "C:" + "\\Users\\alice\\private.json",
            "\\\\server\\share\\private.json",
            "／" + "Users／alice／private.json",
            "~/.config/private.json",
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(ValueError):
                secure_run_relative(self.run_dir, value, must_exist=False)

    def test_rejects_symlink_directory_file_and_missing_required_target(self) -> None:
        outside = Path(self.tempdir.name) / "outside"
        outside.mkdir()
        (outside / "secret.json").write_text("{}", encoding="utf-8")
        (self.run_dir / "linked-dir").symlink_to(outside, target_is_directory=True)
        (self.run_dir / "linked-file.json").symlink_to(outside / "secret.json")

        for value in ("linked-dir/secret.json", "linked-file.json"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                secure_run_relative(self.run_dir, value, must_exist=True)
        with self.assertRaises(FileNotFoundError):
            secure_run_relative(self.run_dir, "missing.json", must_exist=True)

    def test_rejects_broken_symlink_symlink_root_and_compatibility_dot_components(self) -> None:
        broken = self.run_dir / "broken.json"
        broken.symlink_to(Path(self.tempdir.name) / "absent.json")
        root_link = Path(self.tempdir.name) / "run-link"
        root_link.symlink_to(self.run_dir, target_is_directory=True)

        for root, value in (
            (self.run_dir, "broken.json"),
            (root_link, "future.json"),
            (self.run_dir, "drafts/./input.json"),
            (self.run_dir, "drafts/．．/outside.json"),
            (self.run_dir, "drafts//input.json"),
        ):
            with self.subTest(root=root, value=value), self.assertRaises(ValueError):
                secure_run_relative(root, value, must_exist=False)

    def test_rejects_symlink_ancestor_and_write_cannot_escape_after_validation(self) -> None:
        real_tree = self.root / "real-tree"
        nested_run = real_tree / "run"
        nested_run.mkdir(parents=True)
        alias = self.root / "alias"
        alias.symlink_to(real_tree, target_is_directory=True)
        with self.assertRaises(ValueError):
            secure_run_relative(alias / "run", "event.json", must_exist=False)

        future_parent = self.run_dir / "future"
        future_parent.mkdir()
        candidate = secure_run_relative(
            self.run_dir, "future/event.json", must_exist=False
        )
        future_parent.rmdir()
        outside = self.root / "outside"
        outside.mkdir()
        future_parent.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(ValueError):
            atomic_write_json(candidate, {"event_id": "must-not-escape"})
        with self.assertRaises(ValueError):
            write_immutable_or_adopt(candidate, {"event_id": "must-not-escape"})
        self.assertFalse((outside / "event.json").exists())

    def test_private_run_guard_is_git_ignored(self) -> None:
        repo = Path(self.tempdir.name).resolve() / "repo"
        run_dir = repo / ".learning" / "runs" / "guarded"
        run_dir.mkdir(parents=True)
        (repo / ".gitignore").write_text("/.learning/runs/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        target = secure_run_relative(run_dir, "usage-events/one.json", must_exist=False)

        result = subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                "--",
                target.relative_to(repo.resolve()).as_posix(),
            ],
            cwd=repo,
        )
        self.assertEqual(result.returncode, 0, "私有 run 路径必须先被 Git ignore 保护")


class PrivacyTests(unittest.TestCase):
    def test_allows_hash_ids_relative_paths_and_ordinary_urls(self) -> None:
        reject_private_payload(
            {
                "sha256": "a" * 64,
                "source_id": "source-42",
                "evidence_refs": ["evidence/frame-001.json"],
                "url": "https://example.test/watch?id=42#chapter=2",
                "token_count": 128,
                "token_budget": 4096,
                "fixtures": "fixtures/Users/example.json",
                "aspect_ratio": "16/9",
                "relative_path": "relative/path",
                "tilde_text": "约等于~5，不是路径",
                "encoded_url": "https://example.test/search?q=hello%20world",
            }
        )

    def test_rejects_sensitive_keys_headers_paths_keys_and_url_parts(self) -> None:
        unsafe = [
            {"nested": {"access_token": "secret"}},
            {"note": "Authori" + "zation: Bearer " + "a" * 24},
            {"note": "Coo" + "kie: session=" + "b" * 24},
            {"note": "/" + "Users/alice/private/video.mp4"},
            {"note": "C:" + "\\Users\\alice\\private\\video.mp4"},
            {"note": "∕" + "home∕alice∕private∕video.mp4"},
            {"note": "tool=" + "/opt/homebrew/bin/ffmpeg --version"},
            {"note": "-----BEGIN " + "PRIVATE KEY-----\nsecret"},
            {"API－KEY": "secret"},
            {"url": "https://example.test/watch?id=1&api_key=secret"},
            {"url": "https://example.test/watch?%61pi_key=secret"},
            {"url": "https://example.test/watch?id=1&signature=secret"},
            {"url": "https://example.test/watch?X-Amz-Signature=secret"},
            {"url": "https://example.test/callback#access_token=secret"},
            {"url": "https://alice:secret@example.test/watch"},
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(ValueError):
                reject_private_payload(value)

    def test_nfkc_scan_rejects_disguised_headers_paths_assignments_and_urls(self) -> None:
        unsafe = [
            {"note": "中文前缀/opt/homebrew/bin/tool"},
            {"note": "中文前缀/tmp"},
            {"note": "中文前缀/private"},
            {"note": "路径：/Applications/Example.app"},
            {"note": "路径：/Library"},
            {"note": "中文前缀/mnt/data"},
            {"note": "//server/share/file.json"},
            {"note": "Ａｕｔｈｏｒｉｚａｔｉｏｎ： Ｂｅａｒｅｒ " + "a" * 24},
            {"note": "ＡＰＩ＿ＫＥＹ＝" + "b" * 24},
            {"url": "ｈｔｔｐｓ：／／example.test/watch？token＝secret"},
            {"url": "https://example.test/watch?id=1;X-Amz-Signature=secret"},
            {
                "url": "https://example.test/watch?"
                "id=1%EF%BC%86api_key%EF%BC%9Dsecret"
            },
            {
                "url": "https://example.test/watch?"
                "id=1%3BX-Amz-Signature%EF%BC%9Dsecret"
            },
            {"url": "https://example.test/watch?api_key%253Dsecret"},
            {"note": "cwd=~/.ssh/id_rsa"},
            {"note": "home=~alice/private"},
            {"note": "cwd=～／.ssh／id_rsa"},
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(ValueError):
                reject_private_payload(value)


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_uses_canonical_bytes_and_fsync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "nested" / "value.json"
            with mock.patch("learning_common.os.fsync", wraps=os.fsync) as fsync:
                atomic_write_json(path, {"z": "e\u0301", "a": 1})

            self.assertEqual(path.read_bytes(), b'{"a":1,"z":"\xc3\xa9"}\n')
            fsync.assert_called()
            self.assertEqual(list(path.parent.glob(f".{path.name}.*")), [])

    def test_atomic_write_cleans_temp_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "value.json"
            with mock.patch("learning_common.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"ok": True})

            self.assertFalse(path.exists())
            self.assertEqual(list(path.parent.glob(f".{path.name}.*")), [])

    def test_failed_replace_fsyncs_parent_after_temp_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "value.json"
            events: list[str] = []
            real_unlink = os.unlink
            real_directory_fsync = common._fsync_directory

            def tracked_unlink(*args: object, **kwargs: object) -> None:
                events.append("unlink")
                real_unlink(*args, **kwargs)

            def tracked_directory_fsync(*args: object, **kwargs: object) -> None:
                events.append("fsync-parent")
                real_directory_fsync(*args, **kwargs)

            with (
                mock.patch.object(common.os, "replace", side_effect=OSError("boom")),
                mock.patch.object(common.os, "unlink", side_effect=tracked_unlink),
                mock.patch.object(
                    common, "_fsync_directory", side_effect=tracked_directory_fsync
                ),
            ):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"ok": True})

            self.assertEqual(events[-2:], ["unlink", "fsync-parent"])

    def test_cleanup_fsync_failure_still_closes_anchored_parent_fd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "value.json"
            captured: list[int] = []

            def fail_directory_fsync(descriptor: int) -> None:
                captured.append(descriptor)
                raise OSError("fsync failed")

            with (
                mock.patch.object(common.os, "replace", side_effect=OSError("boom")),
                mock.patch.object(
                    common, "_fsync_directory", side_effect=fail_directory_fsync
                ),
            ):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"ok": True})

            self.assertTrue(captured)
            try:
                with self.assertRaises(OSError):
                    os.fstat(captured[-1])
            finally:
                try:
                    os.close(captured[-1])
                except OSError:
                    pass

    def test_atomic_write_rejects_invalid_payload_and_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            invalid = root / "nested" / "invalid.json"
            with self.assertRaises(TypeError):
                atomic_write_json(invalid, {"bad": b"bytes"})
            self.assertFalse(invalid.parent.exists())

            outside = root / "outside.json"
            outside.write_text("outside\n", encoding="utf-8")
            target = root / "target.json"
            target.symlink_to(outside)
            with self.assertRaises(ValueError):
                atomic_write_json(target, {"safe": True})
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")


class ImmutableWriteTests(unittest.TestCase):
    def test_writes_once_then_adopts_identical_canonical_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            write_immutable_or_adopt(path, {"z": "e\u0301", "a": 1})
            before = path.read_bytes()

            write_immutable_or_adopt(path, {"a": 1, "z": "é"})

            self.assertEqual(path.read_bytes(), before)

    def test_conflict_fails_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            write_immutable_or_adopt(path, {"event_id": "one"})
            before = path.read_bytes()

            with self.assertRaises(FileExistsError):
                write_immutable_or_adopt(path, {"event_id": "two"})

            self.assertEqual(path.read_bytes(), before)

    def test_semantically_equal_but_noncanonical_existing_bytes_are_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            path.write_bytes(b'{"a": 1}\n')

            with self.assertRaises(FileExistsError):
                write_immutable_or_adopt(path, {"a": 1})

            self.assertEqual(path.read_bytes(), b'{"a": 1}\n')

    def test_concurrent_distinct_writes_never_overwrite_the_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"

            def write(event_id: str) -> str:
                try:
                    write_immutable_or_adopt(path, {"event_id": event_id})
                except FileExistsError:
                    return "conflict"
                return "written"

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(write, ["one", "two"]))

            self.assertCountEqual(results, ["written", "conflict"])
            self.assertIn(
                path.read_bytes(),
                (b'{"event_id":"one"}\n', b'{"event_id":"two"}\n'),
            )
            self.assertEqual(list(path.parent.glob(f".{path.name}.*")), [])

    def test_concurrent_same_content_adopts_after_bounded_link_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            first_linked = threading.Event()
            release_first_link = threading.Event()
            multiple_links_observed = threading.Event()
            both_prechecks_complete = threading.Barrier(2)
            call_lock = threading.Lock()
            link_calls = 0
            real_link = common.os.link
            real_read = common._read_single_link_regular

            def gated_link(*args: object, **kwargs: object) -> None:
                nonlocal link_calls
                with call_lock:
                    index = link_calls
                    link_calls += 1
                real_link(*args, **kwargs)
                if index == 0:
                    first_linked.set()
                    if not release_first_link.wait(timeout=2):
                        raise TimeoutError("未观察到并发 hardlink 窗口")

            def observe_read(*args: object, **kwargs: object) -> bytes | None:
                try:
                    result = real_read(*args, **kwargs)
                except ValueError:
                    if kwargs.get("label") == "并发写入的不可变 JSON":
                        multiple_links_observed.set()
                        release_first_link.set()
                    raise
                if kwargs.get("label") == "不可变 JSON" and result is None:
                    both_prechecks_complete.wait(timeout=2)
                return result

            def write() -> BaseException | None:
                try:
                    write_immutable_or_adopt(path, {"event_id": "same"})
                except BaseException as error:
                    return error
                return None

            with (
                mock.patch.object(common.os, "link", side_effect=gated_link),
                mock.patch.object(
                    common, "_read_single_link_regular", side_effect=observe_read
                ),
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                first = executor.submit(write)
                second = executor.submit(write)
                self.assertTrue(first_linked.wait(timeout=2))
                results = [first.result(timeout=3), second.result(timeout=3)]

            self.assertTrue(multiple_links_observed.is_set())
            self.assertEqual(results, [None, None])
            self.assertEqual(path.read_bytes(), b'{"event_id":"same"}\n')

    def test_late_same_content_writer_retries_initial_nlink_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            first_linked = threading.Event()
            release_first_link = threading.Event()
            initial_multiple_links_observed = threading.Event()
            real_link = common.os.link
            real_read = common._read_single_link_regular
            call_lock = threading.Lock()
            link_calls = 0

            def gated_link(*args: object, **kwargs: object) -> None:
                nonlocal link_calls
                with call_lock:
                    index = link_calls
                    link_calls += 1
                real_link(*args, **kwargs)
                if index == 0:
                    first_linked.set()
                    if not release_first_link.wait(timeout=2):
                        raise TimeoutError("late writer 未观察到 nlink 窗口")

            def observe_read(*args: object, **kwargs: object) -> bytes | None:
                try:
                    return real_read(*args, **kwargs)
                except ValueError:
                    if kwargs.get("label") == "不可变 JSON":
                        initial_multiple_links_observed.set()
                        release_first_link.set()
                    raise

            def write() -> BaseException | None:
                try:
                    write_immutable_or_adopt(path, {"event_id": "same"})
                except BaseException as error:
                    return error
                return None

            with (
                mock.patch.object(common.os, "link", side_effect=gated_link),
                mock.patch.object(
                    common, "_read_single_link_regular", side_effect=observe_read
                ),
                ThreadPoolExecutor(max_workers=2) as executor,
            ):
                first = executor.submit(write)
                self.assertTrue(first_linked.wait(timeout=2))
                second = executor.submit(write)
                results = [first.result(timeout=3), second.result(timeout=3)]

            self.assertTrue(initial_multiple_links_observed.is_set())
            self.assertEqual(results, [None, None])

    def test_rejects_existing_external_hardlink_even_when_bytes_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            outside = root / "outside.json"
            target = root / "event.json"
            outside.write_bytes(canonical_json_bytes({"event_id": "same"}))
            os.link(outside, target)

            with self.assertRaises((ValueError, FileExistsError)):
                write_immutable_or_adopt(target, {"event_id": "same"})

    def test_immutable_success_fsyncs_parent_after_temp_unlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "event.json"
            events: list[str] = []
            real_unlink = os.unlink
            real_directory_fsync = common._fsync_directory

            def tracked_unlink(*args: object, **kwargs: object) -> None:
                events.append("unlink")
                real_unlink(*args, **kwargs)

            def tracked_directory_fsync(*args: object, **kwargs: object) -> None:
                events.append("fsync-parent")
                real_directory_fsync(*args, **kwargs)

            with (
                mock.patch.object(common.os, "unlink", side_effect=tracked_unlink),
                mock.patch.object(
                    common, "_fsync_directory", side_effect=tracked_directory_fsync
                ),
            ):
                write_immutable_or_adopt(path, {"event_id": "one"})

            self.assertEqual(events[-2:], ["unlink", "fsync-parent"])


if __name__ == "__main__":
    unittest.main()
