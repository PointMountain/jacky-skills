from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_RUN = SKILL_ROOT / "scripts" / "init_run.py"
VALIDATE_RUN = SKILL_ROOT / "scripts" / "validate_run.py"
AUDIT_STAGED = SKILL_ROOT / "scripts" / "audit_staged.py"
WORKFLOW_PATH = SKILL_ROOT / "references" / "workflow.json"
RUBRIC_PATH = SKILL_ROOT / "references" / "rubric.json"
DIMENSIONS = [
    item["id"]
    for item in json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))[
        "subjective_dimensions"
    ]
]
STAGES = [
    "preflight",
    "ingest",
    "transcript",
    "learn_method",
    "observe_motion",
    "plan_demo",
    "build",
    "verify",
    "review_r1",
    "revise",
    "review_r2",
    "finalize",
]


def contract_framemd5(render: Path) -> str:
    data = render.read_bytes()
    lines = [
        f"# render_sha256={hashlib.sha256(data).hexdigest()}",
        "#format: frame checksums",
        "#version: 2",
        "#hash: SHA256",
        "#tb 0: 1/6",
        "#stream#, dts, pts, duration, size, hash",
    ]
    for index in range(6):
        checksum = hashlib.sha256(data + str(index).encode()).hexdigest()
        lines.append(f"0, {index}, {index}, 1, {len(data)}, {checksum}")
    return "\n".join(lines) + "\n"


def contract_png(
    path: Path, width: int, height: int, color: tuple[int, int, int]
) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    row = bytes([0]) + bytes(color) * width
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height))
        + chunk(b"IEND", b"")
    )


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        (self.repo / "demos").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cli(
        self, script: Path, *args: str, check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(script), *map(str, args)],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=getattr(self, "cli_env", None),
        )
        if check and result.returncode != 0:
            self.fail(
                f"CLI 失败 ({result.returncode}): {result.stderr}\n{result.stdout}"
            )
        return result

    def start(self, run_id: str, source: str) -> dict:
        result = self.run_cli(
            INIT_RUN,
            "start",
            "--repo",
            str(self.repo),
            "--run-id",
            run_id,
            "--source",
            source,
            "--source-id",
            f"source-{run_id}",
            "--json",
            check=True,
        )
        return json.loads(result.stdout)

    def run_json(self, run_id: str) -> dict:
        path = self.repo / ".learning" / "runs" / run_id / "run.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def write_run_json(self, run_id: str, payload: dict) -> None:
        path = self.repo / ".learning" / "runs" / run_id / "run.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def mark_planned(self, run_id: str) -> None:
        payload = self.run_json(run_id)
        payload["completed_stages"] = [
            "preflight",
            "ingest",
            "transcript",
            "learn_method",
            "observe_motion",
            "plan_demo",
        ]
        payload["current_stage"] = "build"
        payload["next_stage"] = "verify"
        self.write_run_json(run_id, payload)


class InitRunTests(CliTestCase):
    def test_start_local_source_hashes_media_and_creates_private_run_only(self) -> None:
        source = Path(self.tempdir.name) / "私有 教程.mp4"
        source.write_bytes(b"tutorial-media")

        output = self.start("local-run", str(source))
        payload = self.run_json("local-run")

        expected = hashlib.sha256(b"tutorial-media").hexdigest()
        self.assertEqual(output["run_dir"], ".learning/runs/local-run")
        self.assertEqual(payload["status"], "running")
        self.assertEqual(
            payload["workflow_sha256"],
            hashlib.sha256(WORKFLOW_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(payload["current_stage"], "preflight")
        self.assertEqual(payload["next_stage"], "ingest")
        self.assertEqual(payload["source"]["kind"], "local_file")
        self.assertEqual(payload["source"]["media_sha256"], expected)
        self.assertEqual(payload["source"]["fingerprint_state"], "verified")
        self.assertEqual(payload["source"]["private_locator"], str(source.resolve()))
        self.assertFalse((self.repo / "demos" / "local-run").exists())
        for directory in ("evidence", "frames", "logs"):
            self.assertTrue(
                (self.repo / ".learning" / "runs" / "local-run" / directory).is_dir()
            )

    def test_start_url_uses_provisional_locator_hash_not_media_hash(self) -> None:
        url = "https://example.test/tutorial?id=42"
        self.start("url-run", url)
        source = self.run_json("url-run")["source"]

        self.assertEqual(source["kind"], "url")
        self.assertEqual(
            source["locator_sha256"], hashlib.sha256(url.encode()).hexdigest()
        )
        self.assertIsNone(source["media_sha256"])
        self.assertEqual(source["fingerprint_state"], "provisional")
        self.assertNotIn("private_locator", source)

    def test_start_rejects_duplicate_run_id_without_overwrite(self) -> None:
        source = Path(self.tempdir.name) / "source.mp4"
        source.write_bytes(b"first")
        self.start("duplicate", str(source))
        before = self.run_json("duplicate")
        source.write_bytes(b"second")

        result = self.run_cli(
            INIT_RUN,
            "start",
            "--repo",
            str(self.repo),
            "--run-id",
            "duplicate",
            "--source",
            str(source),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已存在", result.stderr)
        self.assertEqual(self.run_json("duplicate"), before)

    def test_bind_demo_requires_plan_then_allocates_next_number(self) -> None:
        source = Path(self.tempdir.name) / "source.mp4"
        source.write_bytes(b"media")
        (self.repo / "demos" / "06-existing").mkdir()
        (self.repo / "demos" / "10-latest").mkdir()
        self.start("bind-run", str(source))

        early = self.run_cli(
            INIT_RUN,
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "bind-run",
            "--slug",
            "learned-scene",
        )
        self.assertNotEqual(early.returncode, 0)
        self.assertIn("plan_demo", early.stderr)

        self.mark_planned("bind-run")
        result = self.run_cli(
            INIT_RUN,
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "bind-run",
            "--slug",
            "learned-scene",
            "--json",
            check=True,
        )
        output = json.loads(result.stdout)

        self.assertEqual(output["number"], 11)
        self.assertEqual(output["demo_dir"], "demos/11-learned-scene")
        self.assertTrue((self.repo / "demos" / "11-learned-scene").is_dir())
        self.assertEqual(
            self.run_json("bind-run")["bindings"][0]["relative_path"],
            "demos/11-learned-scene",
        )
        self.assertTrue((self.repo / ".learning.lock").exists())

    def test_concurrent_bindings_receive_unique_numbers(self) -> None:
        source = Path(self.tempdir.name) / "source.mp4"
        source.write_bytes(b"media")
        for run_id in ("run-a", "run-b"):
            self.start(run_id, str(source))
            self.mark_planned(run_id)

        processes = []
        for run_id, slug in (("run-a", "alpha"), ("run-b", "beta")):
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        str(INIT_RUN),
                        "bind-demo",
                        "--repo",
                        str(self.repo),
                        "--run-id",
                        run_id,
                        "--slug",
                        slug,
                        "--json",
                    ],
                    cwd=self.repo,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )

        outputs = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            outputs.append(json.loads(stdout))

        self.assertEqual(len({item["number"] for item in outputs}), 2)
        self.assertEqual(
            sorted(item["number"] for item in outputs),
            [1, 2],
        )

    def test_kernel_releases_lock_after_holder_exits(self) -> None:
        source = Path(self.tempdir.name) / "source.mp4"
        source.write_bytes(b"media")
        self.start("recovery", str(source))
        self.mark_planned("recovery")
        lock_path = self.repo / ".learning.lock"
        lock_path.touch()

        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import fcntl, os, sys; "
                    "f=open(sys.argv[1], 'a+'); "
                    "fcntl.flock(f.fileno(), fcntl.LOCK_EX); "
                    "print('locked', flush=True); os._exit(17)"
                ),
                str(lock_path),
            ],
            text=True,
            stdout=subprocess.PIPE,
        )
        self.assertEqual(holder.stdout.readline().strip(), "locked")
        self.assertEqual(holder.wait(timeout=5), 17)
        holder.stdout.close()

        result = self.run_cli(
            INIT_RUN,
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "recovery",
            "--slug",
            "after-crash",
            "--json",
            check=True,
        )
        self.assertEqual(json.loads(result.stdout)["number"], 1)

    def test_rejects_unsafe_identifiers_and_duplicate_binding(self) -> None:
        source = Path(self.tempdir.name) / "source.mp4"
        source.write_bytes(b"media")
        bad = self.run_cli(
            INIT_RUN,
            "start",
            "--repo",
            str(self.repo),
            "--run-id",
            "../escape",
            "--source",
            str(source),
        )
        self.assertNotEqual(bad.returncode, 0)

        self.start("once", str(source))
        self.mark_planned("once")
        first = self.run_cli(
            INIT_RUN,
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "once",
            "--slug",
            "safe-slug",
            check=True,
        )
        self.assertEqual(first.returncode, 0)
        second = self.run_cli(
            INIT_RUN,
            "bind-demo",
            "--repo",
            str(self.repo),
            "--run-id",
            "once",
            "--slug",
            "another",
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("已绑定", second.stderr)


class ValidateRunTests(CliTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.source = Path(self.tempdir.name) / "source.mp4"
        self.source.write_bytes(b"source-media")
        self.start("valid-run", str(self.source))
        self.run_dir = self.repo / ".learning" / "runs" / "valid-run"
        self.media_hash = hashlib.sha256(b"source-media").hexdigest()
        self.draft_path = self.run_dir / "draft.mp4"
        self.draft_path.write_bytes(b"draft-render-for-contract-test")
        self.draft_hash = hashlib.sha256(self.draft_path.read_bytes()).hexdigest()
        self.render_path = self.run_dir / "candidate.mp4"
        self.render_path.write_bytes(b"synthetic-render-for-contract-test")
        self.render_hash = hashlib.sha256(self.render_path.read_bytes()).hexdigest()

        self.demo_dir = self.repo / "demos" / "11-contract-fixture"
        (self.demo_dir / "assets" / "fixtures").mkdir(parents=True)
        self.demo_index = self.demo_dir / "index.html"
        self.demo_index.write_text("<main>contract fixture</main>\n", encoding="utf-8")
        self.demo_package = self.demo_dir / "package.json"
        self.demo_package.write_text('{"scripts":{"check":"true"}}\n', encoding="utf-8")
        self.demo_fixture = self.demo_dir / "assets" / "fixtures" / "poster.svg"
        self.demo_fixture.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n", encoding="utf-8")

        self.evidence_frame = self.run_dir / "evidence" / "frame-001.png"
        self.evidence_frame.write_bytes(b"method-evidence")
        self.motion_frame = self.run_dir / "frames" / "transition-strip.png"
        self.motion_frame.write_bytes(b"motion-evidence")
        self.transcript_path = self.run_dir / "transcript-cues.json"
        self.write_transcript()
        self.verification_logs = {}
        for log_id in ("tests", "check", "inspect", "clean_checkout", "privacy_audit"):
            stdout = self.run_dir / "logs" / f"{log_id}.stdout"
            stdout.write_text(f"{log_id}: verified\n", encoding="utf-8")
            stderr = self.run_dir / "logs" / f"{log_id}.stderr"
            stderr.write_bytes(b"")
            receipt = self.run_dir / "logs" / f"{log_id}.receipt.json"
            receipt.write_text(
                json.dumps(self.execution_receipt(log_id, stdout, stderr)),
                encoding="utf-8",
            )
            self.verification_logs[log_id] = receipt
        (self.run_dir / "snapshots").mkdir()
        self.snapshot = self.run_dir / "snapshots" / "draft.png"
        self.snapshot.write_bytes(b"snapshot")
        (self.run_dir / "reviews").mkdir()
        fake_bin = Path(self.tempdir.name) / "fake-bin"
        fake_bin.mkdir()
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib, pathlib, sys\n"
            "data = pathlib.Path(sys.argv[sys.argv.index('-i') + 1]).read_bytes()\n"
            "print('#format: frame checksums')\nprint('#version: 2')\n"
            "print('#hash: SHA256')\nprint('#tb 0: 1/6')\n"
            "print('#stream#, dts, pts, duration, size, hash')\n"
            "for index in range(6):\n"
            " print(f'0, {index}, {index}, 1, {len(data)}, {hashlib.sha256(data + str(index).encode()).hexdigest()}')\n",
            encoding="utf-8",
        )
        fake_ffmpeg.chmod(0o755)
        self.cli_env = dict(os.environ)
        self.cli_env["PATH"] = f"{fake_bin}:{self.cli_env.get('PATH', '')}"
        self.review_files = {}
        for round_name, render_hash in (("r1", self.draft_hash), ("r2", self.render_hash)):
            framemd5 = self.run_dir / "reviews" / f"{round_name}.framemd5"
            render = self.draft_path if round_name == "r1" else self.render_path
            framemd5.write_text(contract_framemd5(render), encoding="utf-8")
            watch = self.run_dir / "reviews" / f"{round_name}-watch.png"
            dense = self.run_dir / "reviews" / f"{round_name}-dense.png"
            color = (30, 110, 210) if round_name == "r1" else (210, 80, 30)
            contract_png(watch, 60, 10, color)
            contract_png(dense, 30, 10, tuple(reversed(color)))
            manifest = self.run_dir / "reviews" / f"{round_name}-sampling.json"
            manifest.write_text(
                json.dumps(
                    {
                        "render_sha256": render_hash,
                        "duration_seconds": 1.0,
                        "sample_fps": 6,
                        "timestamps_seconds": [index / 6 for index in range(6)],
                        "watch_sheet": {"width": 60, "height": 10, "frame_count": 6},
                        "dense_frames": {
                            "width": 30,
                            "height": 10,
                            "timestamps_seconds": [1 / 3, 1 / 2, 2 / 3],
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.review_files[round_name] = {
                "framemd5": framemd5,
                "watch": watch,
                "dense": dense,
                "manifest": manifest,
            }
        self.make_valid_run()

    def write_transcript(self) -> None:
        self.transcript_path.write_text(
            json.dumps(
                {
                    "source_id": "source-valid-run",
                    "media_sha256": self.media_hash,
                    "cues": [
                        {
                            "cue_id": "cue-001",
                            "start_seconds": 1.0,
                            "end_seconds": 2.0,
                            "text": "背景移动得更慢。",
                        },
                        {
                            "cue_id": "cue-002",
                            "start_seconds": 2.0,
                            "end_seconds": 3.0,
                            "text": "前景随后稳定落定。",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def build_target_hash(self) -> str:
        payload = {
            "source_files": [
                self.repo_ref(self.demo_index),
                self.repo_ref(self.demo_package),
            ],
            "fixture_files": [self.repo_ref(self.demo_fixture)],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def execution_receipt(self, log_id: str, stdout: Path, stderr: Path) -> dict:
        receipt = {
            "receipt_type": "execution",
            "command": ["test-tool", log_id],
            "exit_code": 0,
            "stdout": self.run_ref(stdout),
            "stderr": self.run_ref(stderr),
            "executed_at": "2026-07-11T01:02:03Z",
            "target": {
                "path": "demos/11-contract-fixture",
                "sha256": self.build_target_hash(),
            },
        }
        if log_id == "privacy_audit":
            receipt.update({"ok": True, "staged_count": 2})
        return receipt

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_ref(self, path: Path) -> dict:
        return {
            "path": str(path.relative_to(self.run_dir)),
            "sha256": self.digest(path),
        }

    def repo_ref(self, path: Path) -> dict:
        return {
            "path": str(path.relative_to(self.repo)),
            "sha256": self.digest(path),
        }

    def claim(self, source_type: str = "tutorial_fact") -> dict:
        artifact_path = (
            self.motion_frame
            if source_type == "visual_observation"
            else self.evidence_frame
        )
        cue = (
            {
                "cue_id": "cue-002",
                "start_seconds": 2.0,
                "end_seconds": 3.0,
                "text": "前景随后稳定落定。",
            }
            if source_type == "visual_observation"
            else {
                "cue_id": "cue-001",
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "text": "背景移动得更慢。",
            }
        )
        return {
            "statement": "背景层移动速度低于前景层，形成视差。",
            "source_type": source_type,
            "evidence": {
                "source_id": "source-valid-run",
                "media_sha256": self.media_hash,
                "cue_id": cue["cue_id"],
                "time_range": {
                    "start_seconds": cue["start_seconds"],
                    "end_seconds": cue["end_seconds"],
                },
                "cue": {
                    "start_seconds": cue["start_seconds"],
                    "end_seconds": cue["end_seconds"],
                    "text": cue["text"],
                },
                "artifact": self.run_ref(artifact_path),
            },
        }

    def artifact_payload(self, stage: str) -> dict:
        payloads = {
            "preflight": {
                "artifact_type": "preflight",
                "source_readable": True,
                "source_id": "source-valid-run",
            },
            "ingest": {
                "artifact_type": "ingest",
                "media_sha256": self.media_hash,
                "fingerprint_state": "verified",
            },
            "transcript": {
                "artifact_type": "transcript",
                "media_sha256": self.media_hash,
                "transcript": self.run_ref(self.transcript_path),
                "text_sha256": self.digest(self.transcript_path),
                "cue_count": 2,
            },
            "learn_method": {
                "artifact_type": "method_spec",
                "claims": [self.claim()],
            },
            "observe_motion": {
                "artifact_type": "motion_spec",
                "claims": [self.claim("visual_observation")],
                "coverage": ["start", "transition", "stable", "exit"],
            },
            "plan_demo": {
                "artifact_type": "asset_plan",
                "demo_count": 1,
                "demos": [{"slug": "contract-fixture", "scope": "single-method"}],
                "private_sources_tracked": False,
            },
            "build": {
                "artifact_type": "build",
                "demo_dir": "demos/11-contract-fixture",
                "candidate_render_path": "draft.mp4",
                "source_files": [
                    self.repo_ref(self.demo_index),
                    self.repo_ref(self.demo_package),
                ],
                "fixture_files": [self.repo_ref(self.demo_fixture)],
            },
            "verify": {
                "artifact_type": "verification",
                "must_pass": {
                    "source_readable": True,
                    "transcript_nonempty": True,
                    "keyframes_covered": True,
                    "demo_complete": True,
                    "tests_passed": True,
                    "check_passed": True,
                    "render_verified": True,
                    "clean_checkout_smoke": True,
                    "private_assets_untracked": True,
                    "single_final_pointer": True,
                },
                "logs": {
                    key: self.run_ref(path)
                    for key, path in self.verification_logs.items()
                },
                "snapshots": [self.run_ref(self.snapshot)],
                "render": {
                    "path": "draft.mp4",
                    "sha256": self.draft_hash,
                },
            },
            "review_r1": self.score_payload(
                "r1", top_fix=True, render_hash=self.draft_hash
            ),
            "revise": {
                "artifact_type": "revision",
                "changed_dimension": "motion_timing_fidelity",
                "frozen_dimensions": [
                    dimension
                    for dimension in DIMENSIONS
                    if dimension != "motion_timing_fidelity"
                ],
                "source_render_sha256": self.draft_hash,
                "output_render_path": "candidate.mp4",
                "output_render_sha256": self.render_hash,
            },
            "review_r2": self.score_payload(
                "r2", top_fix=False, render_hash=self.render_hash
            ),
            "finalize": {
                "artifact_type": "final",
                "status": "completed",
                "render_path": "candidate.mp4",
                "render_sha256": self.render_hash,
                "video": {
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 10.0,
                    "fps": 30,
                },
                "candidates": [
                    {
                        "path": "candidate.mp4",
                        "render_sha256": self.render_hash,
                        "selected": True,
                    }
                ],
            },
        }
        return payloads[stage]

    def score_payload(self, round_name: str, top_fix: bool, render_hash: str) -> dict:
        render_path = "draft.mp4" if round_name == "r1" else "candidate.mp4"
        files = self.review_files[round_name]
        return {
            "artifact_type": "score",
            "round": round_name,
            "reviewed_render_path": render_path,
            "reviewed_render_sha256": render_hash,
            "full_decode": {
                "completed": True,
                "render_sha256": render_hash,
                "framemd5_path": str(files["framemd5"].relative_to(self.run_dir)),
                "framemd5_sha256": self.digest(files["framemd5"]),
            },
            "continuous_review": {
                "completed": True,
                "render_sha256": render_hash,
                "watch_sheet_fps": 6,
                "watch_sheet_path": str(files["watch"].relative_to(self.run_dir)),
                "watch_sheet_sha256": self.digest(files["watch"]),
                "dense_frames_path": str(files["dense"].relative_to(self.run_dir)),
                "dense_frames_sha256": self.digest(files["dense"]),
                "sampling_manifest_path": str(
                    files["manifest"].relative_to(self.run_dir)
                ),
                "sampling_manifest_sha256": self.digest(files["manifest"]),
            },
            "issues": [
                {
                    "time_range": {"start_seconds": 2.0, "end_seconds": 2.5},
                    "summary": "入场略快",
                }
            ],
            "top_fix": (
                {
                    "dimension": "motion_timing_fidelity",
                    "time_range": {"start_seconds": 2.0, "end_seconds": 2.5},
                    "instruction": "仅延长落定时间。",
                }
                if top_fix
                else None
            ),
            "dimensions": {dimension: 4 for dimension in DIMENSIONS},
            "score": 80,
        }

    def make_valid_run(self) -> None:
        run = self.run_json("valid-run")
        workflow_hash = self.digest(WORKFLOW_PATH)
        descriptors = {}
        previous_stage = None
        previous_hash = None
        for stage in STAGES:
            filename = {
                "learn_method": "method-spec.json",
                "observe_motion": "motion-spec.json",
                "plan_demo": "asset-plan.json",
                "review_r1": "score-r1.json",
                "review_r2": "score-r2.json",
                "finalize": "final.json",
            }.get(stage, f"{stage}.json")
            path = self.run_dir / filename
            path.write_text(
                json.dumps(self.artifact_payload(stage), ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            output_hash = self.digest(path)
            upstream = (
                {previous_stage: previous_hash} if previous_stage is not None else {}
            )
            descriptors[stage] = {
                "path": filename,
                "sha256": output_hash,
                "schema_version": run["schema_version"],
                "workflow_version": run["workflow_version"],
                "workflow_sha256": workflow_hash,
                "source_media_sha256": self.media_hash,
                "upstream": upstream,
            }
            previous_stage, previous_hash = stage, output_hash

        run.update(
            {
                "status": "completed",
                "current_stage": "finalize",
                "next_stage": None,
                "completed_stages": list(STAGES),
                "artifacts": descriptors,
                "workflow_sha256": workflow_hash,
                "bindings": [
                    {
                        "number": 11,
                        "slug": "contract-fixture",
                        "relative_path": "demos/11-contract-fixture",
                        "bound_at": "2026-07-11T00:00:00Z",
                    }
                ],
            }
        )
        self.write_run_json("valid-run", run)

    def validate(self, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = self.run_cli(
            VALIDATE_RUN,
            "--repo",
            str(self.repo),
            "--run-id",
            "valid-run",
            "--ffprobe",
            "off",
            "--json",
            *extra,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        return result, payload

    def test_complete_semantic_run_passes(self) -> None:
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])
        self.assertIsNone(payload["invalidated_from"])

    def test_url_run_can_resume_at_ingest_while_media_hash_is_provisional(self) -> None:
        self.start("url-partial", "https://example.test/tutorial/partial")
        run_dir = self.repo / ".learning" / "runs" / "url-partial"
        artifact_path = run_dir / "preflight.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "artifact_type": "preflight",
                    "source_readable": True,
                    "source_id": "source-url-partial",
                }
            ),
            encoding="utf-8",
        )
        run_path = run_dir / "run.json"
        run = json.loads(run_path.read_text())
        workflow_hash = self.digest(WORKFLOW_PATH)
        run.update(
            {
                "completed_stages": ["preflight"],
                "current_stage": "ingest",
                "next_stage": "transcript",
                "workflow_sha256": workflow_hash,
                "artifacts": {
                    "preflight": {
                        "path": "preflight.json",
                        "sha256": self.digest(artifact_path),
                        "schema_version": run["schema_version"],
                        "workflow_version": run["workflow_version"],
                        "workflow_sha256": workflow_hash,
                        "source_media_sha256": None,
                        "upstream": {},
                    }
                },
            }
        )
        run_path.write_text(json.dumps(run), encoding="utf-8")

        result = self.run_cli(
            VALIDATE_RUN,
            "--repo",
            str(self.repo),
            "--run-id",
            "url-partial",
            "--ffprobe",
            "off",
            "--json",
        )
        output = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, output)
        self.assertTrue(output["ok"])

    def test_invalid_status_and_stage_fail(self) -> None:
        run = self.run_json("valid-run")
        run["status"] = "pretend-done"
        run["current_stage"] = "invented"
        self.write_run_json("valid-run", run)

        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("status" in item for item in payload["errors"]))
        self.assertTrue(any("current_stage" in item for item in payload["errors"]))

    def test_completed_stages_must_be_ordered_prefix(self) -> None:
        run = self.run_json("valid-run")
        run["completed_stages"] = ["preflight", "transcript"]
        self.write_run_json("valid-run", run)

        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("连续前缀" in item for item in payload["errors"]))

    def test_missing_or_empty_completed_artifact_fails(self) -> None:
        (self.run_dir / "method-spec.json").unlink()
        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["invalidated_from"], "learn_method")

        (self.run_dir / "method-spec.json").write_bytes(b"")
        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("为空" in item for item in payload["errors"]))

    def test_artifact_missing_field_wrong_type_and_enum_fail(self) -> None:
        path = self.run_dir / "transcript.json"
        payload = json.loads(path.read_text())
        payload.pop("text_sha256")
        payload["cue_count"] = "three"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.refresh_descriptor_hash("transcript")

        score = self.run_dir / "score-r1.json"
        score_payload = json.loads(score.read_text())
        score_payload["round"] = "third"
        score.write_text(json.dumps(score_payload), encoding="utf-8")
        self.refresh_descriptor_hash("review_r1", cascade=False)

        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        errors = "\n".join(output["errors"])
        self.assertIn("text_sha256", errors)
        self.assertIn("cue_count", errors)
        self.assertIn("round", errors)

    def refresh_descriptor_hash(self, stage: str, cascade: bool = True) -> None:
        run = self.run_json("valid-run")
        index = STAGES.index(stage)
        descriptor = run["artifacts"][stage]
        descriptor["sha256"] = self.digest(self.run_dir / descriptor["path"])
        if cascade:
            previous_hash = descriptor["sha256"]
            for later in STAGES[index + 1 :]:
                run["artifacts"][later]["upstream"] = {
                    STAGES[STAGES.index(later) - 1]: previous_hash
                }
                previous_hash = run["artifacts"][later]["sha256"]
        self.write_run_json("valid-run", run)

    def test_method_and_motion_claims_require_locatable_evidence(self) -> None:
        path = self.run_dir / "method-spec.json"
        payload = json.loads(path.read_text())
        payload["claims"][0]["evidence"].pop("source_id")
        payload["claims"][0]["source_type"] = "unverified_guess"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.refresh_descriptor_hash("learn_method")

        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        errors = "\n".join(output["errors"])
        self.assertIn("source_id", errors)
        self.assertIn("source_type", errors)

    def test_score_requires_render_hash_and_continuous_decode_evidence(self) -> None:
        path = self.run_dir / "score-r2.json"
        payload = json.loads(path.read_text())
        payload.pop("reviewed_render_sha256")
        payload["full_decode"]["completed"] = False
        payload["continuous_review"].pop("watch_sheet_sha256")
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.refresh_descriptor_hash("review_r2")

        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        errors = "\n".join(output["errors"])
        self.assertIn("reviewed_render_sha256", errors)
        self.assertIn("full_decode.completed", errors)
        self.assertIn("watch_sheet_sha256", errors)

    def test_final_requires_exactly_one_candidate_and_matching_r2_hash(self) -> None:
        final_path = self.run_dir / "final.json"
        final = json.loads(final_path.read_text())
        final["candidates"] = []
        final_path.write_text(json.dumps(final), encoding="utf-8")
        self.refresh_descriptor_hash("finalize")
        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("一个最终候选" in item for item in output["errors"]))

        final["candidates"] = [
            {"path": "candidate.mp4", "render_sha256": self.render_hash, "selected": True},
            {"path": "other.mp4", "render_sha256": "f" * 64, "selected": True},
        ]
        final_path.write_text(json.dumps(final), encoding="utf-8")
        self.refresh_descriptor_hash("finalize")
        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("一个最终候选" in item for item in output["errors"]))

        final["candidates"] = [
            {"path": "candidate.mp4", "render_sha256": "f" * 64, "selected": True}
        ]
        final["render_sha256"] = "f" * 64
        final_path.write_text(json.dumps(final), encoding="utf-8")
        self.refresh_descriptor_hash("finalize")
        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any("R2" in item for item in output["errors"]))

    def test_detects_source_upstream_schema_and_output_drift(self) -> None:
        cases = []

        run = self.run_json("valid-run")
        run["source"]["media_sha256"] = "f" * 64
        cases.append((run, None, "preflight"))

        self.make_valid_run()
        run = self.run_json("valid-run")
        run["artifacts"]["transcript"]["upstream"]["ingest"] = "f" * 64
        cases.append((run, None, "transcript"))

        self.make_valid_run()
        run = self.run_json("valid-run")
        run["artifacts"]["learn_method"]["schema_version"] = "9.9.9"
        cases.append((run, None, "learn_method"))

        for run_payload, _, expected_stage in cases:
            with self.subTest(stage=expected_stage):
                self.make_valid_run()
                self.write_run_json("valid-run", run_payload)
                result, output = self.validate()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output["invalidated_from"], expected_stage)

        self.make_valid_run()
        path = self.run_dir / "method-spec.json"
        path.write_text(path.read_text() + " ", encoding="utf-8")
        result, output = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output["invalidated_from"], "learn_method")

    def test_apply_invalidation_trims_first_drift_and_downstream(self) -> None:
        run = self.run_json("valid-run")
        run["artifacts"]["observe_motion"]["workflow_version"] = "old"
        self.write_run_json("valid-run", run)

        result, output = self.validate("--apply-invalidation")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output["invalidated_from"], "observe_motion")
        updated = self.run_json("valid-run")
        self.assertEqual(updated["completed_stages"], STAGES[:4])
        self.assertEqual(updated["current_stage"], "observe_motion")
        self.assertEqual(updated["next_stage"], "plan_demo")
        self.assertEqual(updated["status"], "running")
        self.assertEqual(updated["invalidated_stages"], STAGES[4:])


class AuditStagedTests(CliTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.test")
        self.git("config", "user.name", "Contract Tests")
        (self.repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "baseline.txt")
        self.git("commit", "-qm", "baseline")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} 失败：{result.stderr}")
        return result

    def audit(self, *paths: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = self.run_cli(
            AUDIT_STAGED,
            "--repo",
            str(self.repo),
            "--paths",
            *paths,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        return result, payload

    def test_fails_when_no_target_file_is_staged(self) -> None:
        (self.repo / "target.txt").write_text("safe\n", encoding="utf-8")

        result, payload = self.audit("target.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["staged_files"], [])
        self.assertTrue(any("未暂存" in item for item in payload["errors"]))

    def test_only_scans_requested_paths(self) -> None:
        (self.repo / "target.txt").write_text("public fixture\n", encoding="utf-8")
        outside_secret = "Authori" + "zation: Bearer " + "z" * 32
        (self.repo / "unrelated.txt").write_text(outside_secret + "\n", encoding="utf-8")
        self.git("add", "target.txt", "unrelated.txt")

        result, payload = self.audit("target.txt")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["staged_files"], ["target.txt"])
        self.assertEqual(payload["findings"], [])

    def test_detects_exact_private_and_secret_patterns(self) -> None:
        unsafe_values = {
            "home_path": "/" + "Users/alice/Private/photos.jpg",
            "authorization": "Authori" + "zation: Bearer " + "a" * 32,
            "secret_assignment": "API" + "_KEY = \"live_" + "b" * 28 + "\"",
            "sensitive_query": (
                "https://media.example.test/watch?id=1&" + "token=" + "c" * 32
            ),
        }

        for expected_rule, unsafe in unsafe_values.items():
            with self.subTest(rule=expected_rule):
                self.git("reset", "-q")
                path = self.repo / "target.txt"
                path.write_text(unsafe + "\n", encoding="utf-8")
                self.git("add", "target.txt")
                result, payload = self.audit("target.txt")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(payload["ok"])
                self.assertIn(expected_rule, {item["rule"] for item in payload["findings"]})

    def test_policy_examples_and_split_rule_source_do_not_self_match(self) -> None:
        safe = "\n".join(
            [
                "不要提交用户主目录绝对路径。",
                "Authorization: Bearer <redacted>",
                'API_KEY = "<redacted>"',
                "https://example.test/watch?token=<redacted>",
                'HOME_RULE = "/" + r"Users/[A-Za-z0-9._-]+"',
                'AUTH_RULE = r"authori" + r"zation\\s*:\\s*bearer"',
            ]
        )
        (self.repo / "target.txt").write_text(safe + "\n", encoding="utf-8")
        self.git("add", "target.txt")

        result, payload = self.audit("target.txt")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["scanned_added_lines"], 0)


if __name__ == "__main__":
    unittest.main()
