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
VALIDATE_RUN = SKILL_ROOT / "scripts" / "validate_run.py"
WORKFLOW_PATH = SKILL_ROOT / "references" / "workflow.json"
RUBRIC_PATH = SKILL_ROOT / "references" / "rubric.json"
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
FILENAMES = {
    "learn_method": "method-spec.json",
    "observe_motion": "motion-spec.json",
    "plan_demo": "asset-plan.json",
    "review_r1": "score-r1.json",
    "review_r2": "score-r2.json",
    "finalize": "final.json",
}
DIMENSIONS = [item["id"] for item in json.loads(RUBRIC_PATH.read_text())["subjective_dimensions"]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def framemd5_text(render: Path) -> str:
    data = render.read_bytes()
    lines = [
        f"# render_sha256={hashlib.sha256(data).hexdigest()}",
        "#format: frame checksums",
        "#version: 2",
        "#hash: SHA256",
        "#tb 0: 1/6",
        "#stream#, dts,        pts, duration,     size, hash",
    ]
    for index in range(6):
        checksum = hashlib.sha256(data + str(index).encode()).hexdigest()
        lines.append(f"0, {index}, {index}, 1, {len(data)}, {checksum}")
    return "\n".join(lines) + "\n"


def write_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    row = bytes([0]) + bytes(color) * width
    raw = row * height
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class TruthBoundValidatorTests(unittest.TestCase):
    """伪造 JSON 形状不能替代真实媒体、源码、证据和观看产物。"""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.run_id = "truth-run"
        self.run_dir = self.repo / ".learning" / "runs" / self.run_id
        for name in ("evidence", "frames", "logs", "snapshots", "reviews"):
            (self.run_dir / name).mkdir(parents=True, exist_ok=True)

        self.source = Path(self.tempdir.name) / "source.mp4"
        self.source.write_bytes(b"source-media-v1")
        self.media_hash = sha256(self.source)
        self.draft = self.run_dir / "draft.mp4"
        self.draft.write_bytes(b"draft-render-v1")
        self.draft_hash = sha256(self.draft)
        self.revised = self.run_dir / "revised.mp4"
        self.revised.write_bytes(b"revised-render-v2")
        self.revised_hash = sha256(self.revised)

        self.demo_dir = self.repo / "demos" / "11-truth-demo"
        (self.demo_dir / "assets" / "fixtures").mkdir(parents=True)
        self.index = self.demo_dir / "index.html"
        self.index.write_text("<main>truth demo</main>\n", encoding="utf-8")
        self.package = self.demo_dir / "package.json"
        self.package.write_text('{"scripts":{"check":"true"}}\n', encoding="utf-8")
        self.fixture = self.demo_dir / "assets" / "fixtures" / "poster.svg"
        self.fixture.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n", encoding="utf-8")

        self.evidence = self.run_dir / "evidence" / "method-frame.png"
        self.evidence.write_bytes(b"located-frame")
        self.motion_strip = self.run_dir / "frames" / "transition-strip.png"
        self.motion_strip.write_bytes(b"dense-transition-strip")
        self.transcript = self.run_dir / "transcript-cues.json"
        self.write_transcript()

        self.logs: dict[str, Path] = {}
        for log_id in ("tests", "check", "inspect", "clean_checkout", "privacy_audit"):
            stdout = self.run_dir / "logs" / f"{log_id}.stdout"
            stdout.write_text(f"{log_id}: verified\n", encoding="utf-8")
            stderr = self.run_dir / "logs" / f"{log_id}.stderr"
            stderr.write_bytes(b"")
            receipt = self.run_dir / "logs" / f"{log_id}.receipt.json"
            receipt.write_text(
                json.dumps(self.execution_receipt(log_id, stdout, stderr), ensure_ascii=False),
                encoding="utf-8",
            )
            self.logs[log_id] = receipt
        self.snapshot = self.run_dir / "snapshots" / "draft.png"
        self.snapshot.write_bytes(b"draft-snapshot")

        self.fake_bin = Path(self.tempdir.name) / "fake-bin"
        self.fake_bin.mkdir()
        fake_ffmpeg = self.fake_bin / "ffmpeg"
        fake_ffmpeg.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib, pathlib, sys\n"
            "path = pathlib.Path(sys.argv[sys.argv.index('-i') + 1])\n"
            "data = path.read_bytes()\n"
            "print('#format: frame checksums')\n"
            "print('#version: 2')\n"
            "print('#hash: SHA256')\n"
            "print('#tb 0: 1/6')\n"
            "print('#stream#, dts,        pts, duration,     size, hash')\n"
            "for index in range(6):\n"
            "    checksum = hashlib.sha256(data + str(index).encode()).hexdigest()\n"
            "    print(f'0, {index}, {index}, 1, {len(data)}, {checksum}')\n",
            encoding="utf-8",
        )
        fake_ffmpeg.chmod(0o755)
        self.cli_env = dict(os.environ)
        self.cli_env["PATH"] = f"{self.fake_bin}:{self.cli_env.get('PATH', '')}"

        self.review_files: dict[str, dict[str, Path]] = {}
        for round_name, render_hash in (("r1", self.draft_hash), ("r2", self.revised_hash)):
            framemd5 = self.run_dir / "reviews" / f"{round_name}.framemd5"
            render = self.draft if round_name == "r1" else self.revised
            framemd5.write_text(framemd5_text(render), encoding="utf-8")
            watch = self.run_dir / "reviews" / f"{round_name}-watch-sheet.png"
            dense = self.run_dir / "reviews" / f"{round_name}-dense-strip.png"
            color = (20, 120, 220) if round_name == "r1" else (220, 90, 40)
            write_png(watch, 60, 10, color)
            write_png(dense, 30, 10, tuple(reversed(color)))
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.review_files[round_name] = {
                "framemd5": framemd5,
                "watch": watch,
                "dense": dense,
                "manifest": manifest,
            }

        self.make_strict_run()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_transcript(self) -> None:
        self.transcript.write_text(
            json.dumps(
                {
                    "source_id": "source-truth-run",
                    "media_sha256": self.media_hash,
                    "cues": [
                        {
                            "cue_id": "cue-001",
                            "start_seconds": 1.0,
                            "end_seconds": 2.0,
                            "text": "这里展示关键机制。",
                        },
                        {
                            "cue_id": "cue-002",
                            "start_seconds": 2.0,
                            "end_seconds": 3.0,
                            "text": "画面进入稳定状态。",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def build_target_hash(self) -> str:
        payload = {
            "source_files": [self.repo_ref(self.index), self.repo_ref(self.package)],
            "fixture_files": [self.repo_ref(self.fixture)],
        }
        normalized = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(normalized).hexdigest()

    def execution_receipt(self, log_id: str, stdout: Path, stderr: Path) -> dict:
        commands = {
            "tests": ["npm", "test"],
            "check": ["npm", "run", "check"],
            "inspect": ["npx", "hyperframes", "inspect"],
            "clean_checkout": ["npm", "run", "clean-smoke"],
            "privacy_audit": ["python", "audit_staged.py"],
        }
        receipt = {
            "receipt_type": "execution",
            "command": commands[log_id],
            "exit_code": 0,
            "stdout": self.run_ref(stdout),
            "stderr": self.run_ref(stderr),
            "executed_at": "2026-07-11T01:02:03Z",
            "target": {
                "path": "demos/11-truth-demo",
                "sha256": self.build_target_hash(),
            },
        }
        if log_id == "privacy_audit":
            receipt.update({"ok": True, "staged_count": 3})
        return receipt

    @staticmethod
    def rel(path: Path, root: Path) -> str:
        return str(path.relative_to(root))

    def run_ref(self, path: Path) -> dict[str, str]:
        return {"path": self.rel(path, self.run_dir), "sha256": sha256(path)}

    def repo_ref(self, path: Path) -> dict[str, str]:
        return {"path": self.rel(path, self.repo), "sha256": sha256(path)}

    def claim(self, path: Path, source_type: str) -> dict:
        cue = (
            {
                "cue_id": "cue-002",
                "start_seconds": 2.0,
                "end_seconds": 3.0,
                "text": "画面进入稳定状态。",
            }
            if source_type == "visual_observation"
            else {
                "cue_id": "cue-001",
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "text": "这里展示关键机制。",
            }
        )
        return {
            "statement": "教程机制有可定位的媒体证据。",
            "source_type": source_type,
            "evidence": {
                "source_id": "source-truth-run",
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
                "artifact": self.run_ref(path),
            },
        }

    def score(self, round_name: str) -> dict:
        is_r1 = round_name == "r1"
        render = self.draft if is_r1 else self.revised
        files = self.review_files[round_name]
        return {
            "artifact_type": "score",
            "round": round_name,
            "reviewed_render_path": self.rel(render, self.run_dir),
            "reviewed_render_sha256": sha256(render),
            "full_decode": {
                "completed": True,
                "render_sha256": sha256(render),
                "framemd5_path": self.rel(files["framemd5"], self.run_dir),
                "framemd5_sha256": sha256(files["framemd5"]),
            },
            "continuous_review": {
                "completed": True,
                "render_sha256": sha256(render),
                "watch_sheet_fps": 6,
                "watch_sheet_path": self.rel(files["watch"], self.run_dir),
                "watch_sheet_sha256": sha256(files["watch"]),
                "dense_frames_path": self.rel(files["dense"], self.run_dir),
                "dense_frames_sha256": sha256(files["dense"]),
                "sampling_manifest_path": self.rel(files["manifest"], self.run_dir),
                "sampling_manifest_sha256": sha256(files["manifest"]),
            },
            "issues": [
                {
                    "time_range": {"start_seconds": 2.0, "end_seconds": 2.5},
                    "summary": "动效节奏仍有一个可定位问题。",
                }
            ],
            "top_fix": (
                {
                    "dimension": "motion_timing_fidelity",
                    "time_range": {"start_seconds": 2.0, "end_seconds": 2.5},
                    "instruction": "只修正落定节奏。",
                }
                if is_r1
                else None
            ),
            "dimensions": {dimension: 4 for dimension in DIMENSIONS},
            "score": 80,
        }

    def artifact_payload(self, stage: str) -> dict:
        required_logs = {key: self.run_ref(path) for key, path in self.logs.items()}
        payloads = {
            "preflight": {
                "artifact_type": "preflight",
                "source_readable": True,
                "source_id": "source-truth-run",
            },
            "ingest": {
                "artifact_type": "ingest",
                "media_sha256": self.media_hash,
                "fingerprint_state": "verified",
            },
            "transcript": {
                "artifact_type": "transcript",
                "media_sha256": self.media_hash,
                "transcript": self.run_ref(self.transcript),
                "text_sha256": sha256(self.transcript),
                "cue_count": 2,
            },
            "learn_method": {
                "artifact_type": "method_spec",
                "claims": [self.claim(self.evidence, "tutorial_fact")],
            },
            "observe_motion": {
                "artifact_type": "motion_spec",
                "claims": [self.claim(self.motion_strip, "visual_observation")],
                "coverage": ["start", "transition", "stable", "exit"],
            },
            "plan_demo": {
                "artifact_type": "asset_plan",
                "demo_count": 1,
                "demos": [{"slug": "truth-demo", "scope": "single-method"}],
                "private_sources_tracked": False,
            },
            "build": {
                "artifact_type": "build",
                "demo_dir": "demos/11-truth-demo",
                "candidate_render_path": "draft.mp4",
                "source_files": [self.repo_ref(self.index), self.repo_ref(self.package)],
                "fixture_files": [self.repo_ref(self.fixture)],
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
                "logs": required_logs,
                "snapshots": [self.run_ref(self.snapshot)],
                "render": self.run_ref(self.draft),
            },
            "review_r1": self.score("r1"),
            "revise": {
                "artifact_type": "revision",
                "changed_dimension": "motion_timing_fidelity",
                "frozen_dimensions": [
                    dimension for dimension in DIMENSIONS if dimension != "motion_timing_fidelity"
                ],
                "source_render_sha256": self.draft_hash,
                "output_render_path": "revised.mp4",
                "output_render_sha256": self.revised_hash,
            },
            "review_r2": self.score("r2"),
            "finalize": {
                "artifact_type": "final",
                "status": "completed",
                "render_path": "revised.mp4",
                "render_sha256": self.revised_hash,
                "video": {
                    "width": 1920,
                    "height": 1080,
                    "duration_seconds": 10.0,
                    "fps": 30,
                },
                "candidates": [
                    {
                        "path": "revised.mp4",
                        "render_sha256": self.revised_hash,
                        "selected": True,
                    }
                ],
            },
        }
        return payloads[stage]

    def make_strict_run(self) -> None:
        workflow_hash = sha256(WORKFLOW_PATH)
        descriptors: dict[str, dict] = {}
        previous_stage = None
        previous_hash = None
        for stage in STAGES:
            path = self.run_dir / FILENAMES.get(stage, f"{stage}.json")
            path.write_text(
                json.dumps(self.artifact_payload(stage), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            artifact_hash = sha256(path)
            descriptors[stage] = {
                "path": self.rel(path, self.run_dir),
                "sha256": artifact_hash,
                "schema_version": "1.0.0",
                "workflow_version": "1.0.0",
                "workflow_sha256": workflow_hash,
                "source_media_sha256": self.media_hash,
                "upstream": {previous_stage: previous_hash} if previous_stage else {},
            }
            previous_stage, previous_hash = stage, artifact_hash

        run = {
            "schema_version": "1.0.0",
            "workflow_version": "1.0.0",
            "workflow_sha256": workflow_hash,
            "run_id": self.run_id,
            "status": "completed",
            "current_stage": "finalize",
            "next_stage": None,
            "completed_stages": list(STAGES),
            "invalidated_stages": [],
            "source": {
                "kind": "local_file",
                "source_id": "source-truth-run",
                "private_locator": str(self.source.resolve()),
                "locator_sha256": hashlib.sha256(str(self.source.resolve()).encode()).hexdigest(),
                "media_sha256": self.media_hash,
                "fingerprint_state": "verified",
            },
            "artifacts": descriptors,
            "bindings": [
                {
                    "number": 11,
                    "slug": "truth-demo",
                    "relative_path": "demos/11-truth-demo",
                    "bound_at": "2026-07-11T00:00:00Z",
                }
            ],
        }
        (self.run_dir / "run.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def read_run(self) -> dict:
        return json.loads((self.run_dir / "run.json").read_text())

    def write_run(self, run: dict) -> None:
        (self.run_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")

    def refresh(self, stage: str) -> None:
        run = self.read_run()
        index = STAGES.index(stage)
        descriptor = run["artifacts"][stage]
        descriptor["sha256"] = sha256(self.run_dir / descriptor["path"])
        previous_hash = descriptor["sha256"]
        for later in STAGES[index + 1 :]:
            previous = STAGES[STAGES.index(later) - 1]
            run["artifacts"][later]["upstream"] = {previous: previous_hash}
            previous_hash = run["artifacts"][later]["sha256"]
        self.write_run(run)

    def mutate_artifact(self, stage: str, mutate) -> None:
        run = self.read_run()
        path = self.run_dir / run["artifacts"][stage]["path"]
        payload = json.loads(path.read_text())
        mutate(payload)
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.refresh(stage)

    def validate(
        self,
        run_id: str | None = None,
        *,
        ffprobe: str = "off",
        apply: bool = False,
        env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        command = [
            sys.executable,
            str(VALIDATE_RUN),
            "--repo",
            str(self.repo),
            "--run-id",
            run_id or self.run_id,
            "--ffprobe",
            ffprobe,
            "--json",
        ]
        if apply:
            command.append("--apply-invalidation")
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            env=env if env is not None else self.cli_env,
        )
        return result, json.loads(result.stdout)

    def assert_fails(self, expected: str, stage: str | None = None) -> dict:
        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, "\n".join(payload["errors"]))
        if stage is not None:
            self.assertEqual(payload["invalidated_from"], stage)
        return payload

    def test_strict_truth_bound_run_passes(self) -> None:
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(payload["ok"])

    def test_run_id_cannot_escape_or_be_modified_in_apply_mode(self) -> None:
        outside = self.repo / ".learning" / "outside"
        outside.mkdir(parents=True)
        marker = outside / "run.json"
        marker.write_text('{"sentinel":"unchanged"}\n', encoding="utf-8")

        result, payload = self.validate("../outside", apply=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run-id", "\n".join(payload["errors"]))
        self.assertEqual(marker.read_text(), '{"sentinel":"unchanged"}\n')

    def test_local_and_url_media_bytes_are_rehashed(self) -> None:
        self.source.write_bytes(b"source-media-mutated")
        self.assert_fails("本地 source", "preflight")

        self.source.write_bytes(b"source-media-v1")
        local_media = self.run_dir / "ingested.mp4"
        local_media.write_bytes(b"source-media-v1")
        run = self.read_run()
        run["source"] = {
            "kind": "url",
            "source_id": "source-truth-run",
            "locator": "https://example.test/video/1",
            "locator_sha256": hashlib.sha256(b"https://example.test/video/1").hexdigest(),
            "media_sha256": self.media_hash,
            "fingerprint_state": "verified",
        }
        self.write_run(run)
        self.mutate_artifact(
            "ingest",
            lambda value: value.update({"local_media_path": "ingested.mp4"}),
        )
        result, payload = self.validate()
        self.assertEqual(result.returncode, 0, payload)

        local_media.write_bytes(b"different-downloaded-media")
        self.assert_fails("URL ingest", "ingest")

    def test_current_contract_versions_workflow_hash_and_stage_pointer_are_facts(self) -> None:
        run = self.read_run()
        run["schema_version"] = "9.9.9"
        run["workflow_version"] = "9.9.9"
        for descriptor in run["artifacts"].values():
            descriptor["schema_version"] = "9.9.9"
            descriptor["workflow_version"] = "9.9.9"
        self.write_run(run)
        self.assert_fails("当前支持", "preflight")

        self.make_strict_run()
        run = self.read_run()
        run["workflow_sha256"] = "f" * 64
        for descriptor in run["artifacts"].values():
            descriptor["workflow_sha256"] = "f" * 64
        self.write_run(run)
        self.assert_fails("workflow.json", "preflight")

        self.make_strict_run()
        run = self.read_run()
        run["completed_stages"] = STAGES[:6]
        run["status"] = "running"
        run["current_stage"] = "finalize"
        run["next_stage"] = None
        self.write_run(run)
        self.assert_fails("completed_stages 推导", "build")

        self.make_strict_run()
        run = self.read_run()
        run["completed_stages"].append("finalize")
        self.write_run(run)
        result, payload = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("连续前缀", "\n".join(payload["errors"]))

    def test_claim_evidence_must_exist_inside_run_and_match_hash(self) -> None:
        self.evidence.write_bytes(b"tampered-frame")
        self.assert_fails("evidence.artifact", "learn_method")

        self.evidence.write_bytes(b"located-frame")
        outside = Path(self.tempdir.name) / "outside.png"
        outside.write_bytes(b"located-frame")
        self.mutate_artifact(
            "learn_method",
            lambda value: value["claims"][0]["evidence"]["artifact"].update(
                {"path": "../../../../outside.png", "sha256": sha256(outside)}
            ),
        )
        self.assert_fails("逃逸 run", "learn_method")

    def test_transcript_file_must_exist_and_match_text_hash(self) -> None:
        self.transcript.unlink()
        self.assert_fails("transcript.transcript", "transcript")

        self.write_transcript()
        self.make_strict_run()
        self.transcript.write_text("tampered\n", encoding="utf-8")
        self.assert_fails("transcript.transcript", "transcript")

    def test_transcript_cues_and_claims_are_exactly_cross_bound(self) -> None:
        transcript_payload = json.loads(self.transcript.read_text())
        transcript_payload["media_sha256"] = "f" * 64
        transcript_payload["cues"] = []
        self.transcript.write_text(json.dumps(transcript_payload), encoding="utf-8")
        self.mutate_artifact(
            "transcript",
            lambda value: value.update(
                {
                    "media_sha256": "f" * 64,
                    "transcript": self.run_ref(self.transcript),
                    "text_sha256": sha256(self.transcript),
                    "cue_count": 999,
                }
            ),
        )
        payload = self.assert_fails("实际源媒体 hash", "transcript")
        errors = "\n".join(payload["errors"])
        self.assertIn("cue_count", errors)

        self.write_transcript()
        self.make_strict_run()
        self.mutate_artifact(
            "learn_method",
            lambda value: value["claims"][0]["evidence"].update(
                {
                    "source_id": "wrong-source",
                    "cue_id": "cue-001",
                    "time_range": {"start_seconds": 2.0, "end_seconds": 1.0},
                    "cue": {
                        "start_seconds": 2.0,
                        "end_seconds": 1.0,
                        "text": "转录里不存在的句子",
                    },
                }
            ),
        )
        payload = self.assert_fails("对应 transcript cue", "learn_method")
        self.assertIn("source_id", "\n".join(payload["errors"]))

    def test_binding_demo_sources_fixtures_logs_snapshots_and_draft_are_real(self) -> None:
        run = self.read_run()
        run["bindings"] = []
        self.write_run(run)
        self.assert_fails("binding", "build")

        self.make_strict_run()
        self.index.unlink()
        self.assert_fails("source_files", "build")

        self.index.write_text("<main>truth demo</main>\n", encoding="utf-8")
        self.make_strict_run()
        self.fixture.unlink()
        self.assert_fails("fixture_files", "build")

        self.fixture.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>\n", encoding="utf-8")
        self.make_strict_run()
        self.logs["check"].unlink()
        self.assert_fails("verification.logs.check", "verify")

        self.logs["check"].write_text(
            json.dumps(
                self.execution_receipt(
                    "check",
                    self.run_dir / "logs" / "check.stdout",
                    self.run_dir / "logs" / "check.stderr",
                )
            ),
            encoding="utf-8",
        )
        self.make_strict_run()
        self.snapshot.unlink()
        self.assert_fails("verification.snapshots", "verify")

        self.snapshot.write_bytes(b"draft-snapshot")
        self.make_strict_run()
        self.draft.unlink()
        self.assert_fails("candidate_render_path", "build")

    def test_execution_receipts_cannot_turn_failed_checks_green(self) -> None:
        check_receipt = json.loads(self.logs["check"].read_text())
        check_receipt["exit_code"] = 1
        self.logs["check"].write_text(json.dumps(check_receipt), encoding="utf-8")
        self.mutate_artifact(
            "verify",
            lambda value: value["logs"]["check"].update(
                {"sha256": sha256(self.logs["check"])}
            ),
        )
        self.assert_fails("exit_code 必须为 0", "verify")

        self.make_strict_run()
        privacy = json.loads(self.logs["privacy_audit"].read_text())
        privacy.update({"ok": False, "staged_count": 0})
        self.logs["privacy_audit"].write_text(json.dumps(privacy), encoding="utf-8")
        self.mutate_artifact(
            "verify",
            lambda value: value["logs"]["privacy_audit"].update(
                {"sha256": sha256(self.logs["privacy_audit"])}
            ),
        )
        payload = self.assert_fails("privacy audit receipt", "verify")
        self.assertIn("staged_count", "\n".join(payload["errors"]))

    def test_review_evidence_paths_hashes_and_render_identity_are_bound(self) -> None:
        self.review_files["r1"]["watch"].write_bytes(b"tampered-watch-sheet")
        self.assert_fails("watch_sheet", "review_r1")

        write_png(self.review_files["r1"]["watch"], 60, 10, (20, 120, 220))
        self.make_strict_run()
        self.mutate_artifact(
            "review_r1",
            lambda value: value.update(
                {
                    "reviewed_render_path": "revised.mp4",
                    "reviewed_render_sha256": self.revised_hash,
                }
            ),
        )
        self.mutate_artifact(
            "revise",
            lambda value: value.update({"source_render_sha256": self.revised_hash}),
        )
        self.assert_fails("verification.render", "review_r1")

        self.make_strict_run()
        self.mutate_artifact(
            "review_r2",
            lambda value: value.update(
                {
                    "reviewed_render_path": "draft.mp4",
                    "reviewed_render_sha256": self.draft_hash,
                }
            ),
        )
        self.assert_fails("revision 输出", "review_r2")

    def test_framemd5_is_recomputed_and_sampling_artifacts_are_real(self) -> None:
        framemd5 = self.review_files["r1"]["framemd5"]
        framemd5.write_text("#hash: SHA256\nnot-a-real-framemd5-row\n", encoding="utf-8")
        self.make_strict_run()
        self.assert_fails("framemd5", "review_r1")

        framemd5.write_text(framemd5_text(self.draft), encoding="utf-8")
        self.make_strict_run()
        self.review_files["r1"]["dense"].write_bytes(b"not-an-image")
        self.assert_fails("真实图片", "review_r1")

        write_png(self.review_files["r1"]["dense"], 30, 10, (220, 120, 20))
        self.make_strict_run()
        manifest = json.loads(self.review_files["r1"]["manifest"].read_text())
        manifest["timestamps_seconds"] = [0.0]
        self.review_files["r1"]["manifest"].write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        self.assert_fails("覆盖全时长", "review_r1")

    def test_review_rounds_cannot_reuse_decode_or_sampling_evidence(self) -> None:
        self.mutate_artifact(
            "review_r2",
            lambda value: (
                value["full_decode"].update(
                    {
                        "framemd5_path": value["full_decode"]["framemd5_path"].replace(
                            "r2", "r1"
                        ),
                        "framemd5_sha256": sha256(self.review_files["r1"]["framemd5"]),
                    }
                ),
                value["continuous_review"].update(
                    {
                        "watch_sheet_path": self.rel(
                            self.review_files["r1"]["watch"], self.run_dir
                        ),
                        "watch_sheet_sha256": sha256(self.review_files["r1"]["watch"]),
                        "dense_frames_path": self.rel(
                            self.review_files["r1"]["dense"], self.run_dir
                        ),
                        "dense_frames_sha256": sha256(self.review_files["r1"]["dense"]),
                    }
                ),
            ),
        )
        self.assert_fails("R1/R2", "review_r2")

    def test_completed_review_requires_local_ffmpeg(self) -> None:
        empty_bin = Path(self.tempdir.name) / "empty-bin"
        empty_bin.mkdir()
        env = dict(self.cli_env)
        env["PATH"] = str(empty_bin)
        result, payload = self.validate(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ffmpeg", "\n".join(payload["errors"]))

    def test_dimensions_revision_freeze_weighted_score_and_terminal_status_are_recomputed(self) -> None:
        self.mutate_artifact(
            "revise",
            lambda value: value.update({"changed_dimension": "visual_hierarchy"}),
        )
        self.assert_fails("top_fix.dimension", "revise")

        self.make_strict_run()
        self.mutate_artifact(
            "revise", lambda value: value.update({"frozen_dimensions": []})
        )
        self.assert_fails("frozen_dimensions", "revise")

        self.make_strict_run()
        self.mutate_artifact("review_r2", lambda value: value.update({"score": 99}))
        self.assert_fails("加权重算", "review_r2")

        self.make_strict_run()
        self.mutate_artifact(
            "review_r2",
            lambda value: value.update(
                {
                    "dimensions": {dimension: 3 for dimension in DIMENSIONS},
                    "score": 60,
                }
            ),
        )
        self.assert_fails("completed_with_residuals", "finalize")

    def test_ffprobe_fps_must_match_final_video_contract(self) -> None:
        bin_dir = Path(self.tempdir.name) / "bin"
        bin_dir.mkdir()
        ffprobe = bin_dir / "ffprobe"
        ffprobe.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            "print(json.dumps({'streams':[{'width':1920,'height':1080,'r_frame_rate':'24/1'}],"
            "'format':{'duration':'10.000'}}))\n",
            encoding="utf-8",
        )
        ffprobe.chmod(0o755)
        env = dict(self.cli_env)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

        result, payload = self.validate(ffprobe="on", env=env)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fps", "\n".join(payload["errors"]))


if __name__ == "__main__":
    unittest.main()
