#!/usr/bin/env python3
"""确定性校验教程学习 run，并报告或应用从首个漂移点向下失效。"""

from __future__ import annotations

import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable

from init_run import atomic_write_json
from learning_common import (
    ensure_secure_existing_directory,
    read_stable_file_bytes,
    reject_private_payload,
)


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
STATUSES = {
    "running",
    "blocked",
    "failed",
    "completed",
    "completed_with_residuals",
}
SOURCE_TYPES = {
    "tutorial_fact",
    "visual_observation",
    "code_fact",
    "implementation_inference",
    "local_project_decision",
    "verified_result",
}
EXPECTED_TYPES = {
    "preflight": "preflight",
    "ingest": "ingest",
    "transcript": "transcript",
    "learn_method": "method_spec",
    "observe_motion": "motion_spec",
    "plan_demo": "asset_plan",
    "build": "build",
    "verify": "verification",
    "review_r1": "score",
    "revise": "revision",
    "review_r2": "score",
    "finalize": "final",
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEMO_RE = re.compile(r"^(\d+)-([a-z0-9][a-z0-9-]*)$")
CURRENT_SCHEMA_VERSION = "1.0.0"
SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_ROOT = SKILL_ROOT / "references" / "workflows"
SUPPORTED_WORKFLOWS = {
    "1.0.0": WORKFLOWS_ROOT / "1.0.0.json",
    "1.1.0": WORKFLOWS_ROOT / "1.1.0.json",
}
SUPPORTED_LEARNING_CONTRACTS = {
    "1.0.0": {
        "path": SKILL_ROOT / "references" / "learning-contracts" / "1.0.0.json",
        "sha256": "1d7e76d5a74c1afbea83cee933a16bfbc301ba51d481fe991c66e5ec542b9c50",
    },
}
CAPABILITY_REGISTRIES_ROOT = SKILL_ROOT / "references" / "capability-registries"
LEGACY_CAPABILITY_REGISTRY_SHA256 = (
    "6540068ddf9971dcb5815ee3ce7561d78c0a2eb450f414391ffa4bf9289f2583"
)
RUBRIC_PATH = SKILL_ROOT / "references" / "rubric.json"
REQUIRED_VERIFICATION_LOGS = {
    "tests",
    "check",
    "inspect",
    "clean_checkout",
    "privacy_audit",
}
FRAMEMD5_ROW_RE = re.compile(
    r"^\s*(\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9a-fA-F]{64})\s*$"
)
FRAMEMD5_TIMEBASE_RE = re.compile(r"^#tb\s+(\d+):\s*(\d+)/(\d+)\s*$")


class ValidationFailure(ValueError):
    """表示无法开始校验的顶层错误。"""


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_file_hash(path: Path) -> str:
    return hashlib.sha256(read_stable_file_bytes(path)).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValidationFailure(f"文件不存在：{path}") from error
    except json.JSONDecodeError as error:
        raise ValidationFailure(f"JSON 解析失败：{path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"JSON 顶层必须是对象：{path}")
    return value


def load_stable_object(path: Path) -> tuple[dict[str, Any], str]:
    try:
        content = read_stable_file_bytes(path)
        value = json.loads(content.decode("utf-8"))
    except FileNotFoundError as error:
        raise ValidationFailure(f"文件不存在：{path}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"JSON 稳定读取失败：{path}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"JSON 顶层必须是对象：{path}")
    return value, hashlib.sha256(content).hexdigest()


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and bool(HASH_RE.fullmatch(value))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def valid_rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
        return False
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_identifier(value: str, label: str) -> None:
    if not IDENTIFIER_RE.fullmatch(value) or value in {".", ".."}:
        raise ValidationFailure(
            f"{label} 不安全：只允许字母、数字、点、下划线和连字符"
        )


class Validator:
    def __init__(
        self,
        repo: Path,
        run_id: str,
        ffprobe_mode: str,
        *,
        core_only: bool = False,
        require_learning_memory: bool = False,
    ) -> None:
        validate_identifier(run_id, "run-id")
        self.repo = repo.resolve()
        self.run_id = run_id
        self.runs_root = self.repo / ".learning" / "runs"
        self.run_dir = self.runs_root / run_id
        try:
            ensure_secure_existing_directory(self.runs_root)
            ensure_secure_existing_directory(self.run_dir)
        except (FileNotFoundError, OSError, ValueError) as error:
            raise ValidationFailure(
                ".learning/runs/run 目录链不存在或包含 symlink"
            ) from error
        self.run_path = self.run_dir / "run.json"
        self.ffprobe_mode = ffprobe_mode
        self.core_only = core_only
        self.require_learning_memory = require_learning_memory
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.invalid_index: int | None = None
        self.contents: dict[str, dict[str, Any]] = {}
        # run 本身决定要解析哪一份冻结契约；未知版本绝不能回退到 current。
        self.run, _ = load_stable_object(self.run_path)
        raw_workflow_version = self.run.get("workflow_version")
        self.workflow_version = (
            raw_workflow_version if isinstance(raw_workflow_version, str) else None
        )
        self.workflow_path = SUPPORTED_WORKFLOWS.get(self.workflow_version or "")
        self.workflow_resolution_error: str | None = None
        if self.workflow_path is None:
            self.workflow = {}
            self.workflow_hash: str | None = None
            self.workflow_resolution_error = (
                f"run.workflow_version 不受支持：{raw_workflow_version!r}"
            )
        else:
            self.workflow, self.workflow_hash = load_stable_object(self.workflow_path)
        self.rubric = load_object(RUBRIC_PATH)
        self.dimension_weights = self.load_dimension_weights()
        self.threshold = self.rubric.get("threshold")
        if not is_number(self.threshold):
            raise ValidationFailure("rubric.json.threshold 必须是数字")
        self.actual_media_hash: str | None = None
        self.binding_dir: Path | None = None
        self.binding_relative: str | None = None
        self.build_candidate_path: Path | None = None
        self.verification_render_path: Path | None = None
        self.verification_render_hash: str | None = None
        self.revision_output_path: Path | None = None
        self.review_paths: dict[str, Path] = {}
        self.review_evidence: dict[str, dict[str, tuple[str, str]]] = {}
        self.transcript_source_id: str | None = None
        self.transcript_cues: dict[str, dict[str, Any]] = {}
        self.build_target_hash: str | None = None
        self.learning_contents: dict[str, dict[str, Any]] = {}
        self.learning_file_bytes: dict[Path, bytes] = {}
        self.learning_registry: dict[str, Any] | None = None
        self.learning_registry_version: str | None = None
        self.learning_registry_hash: str | None = None

    def load_dimension_weights(self) -> dict[str, float]:
        dimensions = self.rubric.get("subjective_dimensions")
        if not isinstance(dimensions, list) or not dimensions:
            raise ValidationFailure("rubric.json.subjective_dimensions 必须是非空数组")
        weights: dict[str, float] = {}
        for index, item in enumerate(dimensions):
            if not isinstance(item, dict):
                raise ValidationFailure(
                    f"rubric subjective_dimensions[{index}] 必须是对象"
                )
            identifier = item.get("id")
            weight = item.get("weight")
            if (
                not isinstance(identifier, str)
                or not identifier
                or not is_number(weight)
                or float(weight) <= 0
                or identifier in weights
            ):
                raise ValidationFailure("rubric subjective dimension id/weight 非法")
            weights[identifier] = float(weight)
        if abs(sum(weights.values()) - 100.0) > 1e-6:
            raise ValidationFailure("rubric subjective dimension 权重之和必须为 100")
        return weights

    def error(self, message: str, stage: str | None = None) -> None:
        self.errors.append(message)
        if stage in STAGES:
            index = STAGES.index(stage)
            if self.invalid_index is None or index < self.invalid_index:
                self.invalid_index = index

    def require(
        self,
        obj: dict[str, Any],
        key: str,
        predicate: Callable[[Any], bool],
        context: str,
        stage: str,
        expectation: str,
    ) -> Any:
        value = obj.get(key)
        if not predicate(value):
            self.error(f"{context}.{key} {expectation}", stage)
        return value

    def secure_relative_path(
        self, value: Any, context: str, stage: str
    ) -> Path | None:
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            self.error(f"{context} 必须是 run 内的非空相对路径", stage)
            return None
        resolved = (self.run_dir / value).resolve()
        try:
            resolved.relative_to(self.run_dir.resolve())
        except ValueError:
            self.error(f"{context} 逃逸 run 目录", stage)
            return None
        return resolved

    def secure_repo_relative_path(
        self, value: Any, context: str, stage: str
    ) -> Path | None:
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            self.error(f"{context} 必须是仓库内的非空相对路径", stage)
            return None
        resolved = (self.repo / value).resolve()
        try:
            resolved.relative_to(self.repo)
        except ValueError:
            self.error(f"{context} 逃逸目标仓库", stage)
            return None
        return resolved

    def validate_file_reference(
        self,
        reference: Any,
        context: str,
        stage: str,
        *,
        root: str = "run",
        within: Path | None = None,
        allow_empty: bool = False,
    ) -> Path | None:
        if not isinstance(reference, dict):
            self.error(f"{context} 必须是包含 path/sha256 的对象", stage)
            return None
        path_value = reference.get("path")
        path = (
            self.secure_relative_path(path_value, f"{context}.path", stage)
            if root == "run"
            else self.secure_repo_relative_path(path_value, f"{context}.path", stage)
        )
        declared_hash = reference.get("sha256")
        if not is_hash(declared_hash):
            self.error(f"{context}.sha256 必须是 SHA-256", stage)
        if path is None:
            return None
        if within is not None:
            try:
                path.relative_to(within.resolve())
            except ValueError:
                self.error(f"{context}.path 必须位于 {within.name} 内", stage)
                return None
        if not path.is_file() or (not allow_empty and path.stat().st_size == 0):
            self.error(f"{context} 指向的文件不存在或为空：{path_value}", stage)
            return path
        actual_hash = file_hash(path)
        if is_hash(declared_hash) and actual_hash != declared_hash:
            self.error(f"{context} 内容 hash 与 sha256 不一致", stage)
        return path

    def validate_state(self) -> list[str]:
        status = self.run.get("status")
        if status not in STATUSES:
            self.error(f"run.status 非法：{status!r}", "preflight")
        current = self.run.get("current_stage")
        if current not in STAGES:
            self.error(f"run.current_stage 非法：{current!r}", "preflight")
        next_stage = self.run.get("next_stage")
        if next_stage is not None and next_stage not in STAGES:
            self.error(f"run.next_stage 非法：{next_stage!r}", "preflight")
        if self.run.get("run_id") != self.run_id:
            self.error("run.run_id 与目录名不一致", "preflight")

        raw_completed = self.run.get("completed_stages")
        if not isinstance(raw_completed, list) or any(
            not isinstance(stage, str) for stage in raw_completed
        ):
            self.error("run.completed_stages 必须是字符串数组", "preflight")
            return []
        prefix_length = 0
        for index, stage in enumerate(raw_completed[: len(STAGES)]):
            if stage != STAGES[index]:
                break
            prefix_length += 1
        prefix_is_valid = (
            len(raw_completed) <= len(STAGES)
            and raw_completed == STAGES[: len(raw_completed)]
        )
        if not prefix_is_valid:
            self.error(
                "run.completed_stages 必须是工作流的无重复连续前缀",
                "preflight",
            )
        completed = STAGES[:prefix_length]

        first_incomplete_index = min(len(completed), len(STAGES) - 1)
        pointer_stage = STAGES[first_incomplete_index]
        if len(completed) == len(STAGES):
            expected_current = STAGES[-1]
            expected_next = None
        else:
            expected_current = STAGES[len(completed)]
            expected_next = (
                STAGES[len(completed) + 1]
                if len(completed) + 1 < len(STAGES)
                else None
            )
        if current != expected_current:
            self.error(
                "run.current_stage 必须由 completed_stages 推导为 "
                f"{expected_current!r}",
                pointer_stage,
            )
        if next_stage != expected_next:
            self.error(
                "run.next_stage 必须由 completed_stages 推导为 "
                f"{expected_next!r}",
                pointer_stage,
            )

        if status in {"completed", "completed_with_residuals"}:
            if raw_completed != STAGES:
                self.error("完成状态必须完成全部阶段", pointer_stage)
            if next_stage is not None:
                self.error("完成状态的 run.next_stage 必须为 null", pointer_stage)
        elif completed == STAGES:
            self.error("完成全部阶段后 run.status 必须是完成状态", "finalize")

        if self.run.get("schema_version") != CURRENT_SCHEMA_VERSION:
            self.error(
                f"run.schema_version 必须是当前支持的 {CURRENT_SCHEMA_VERSION}",
                "preflight",
            )
        if self.workflow_resolution_error is not None:
            self.error(self.workflow_resolution_error, "preflight")
        workflow_stages = self.workflow.get("stages")
        workflow_ids = (
            [item.get("id") for item in workflow_stages if isinstance(item, dict)]
            if isinstance(workflow_stages, list)
            else []
        )
        if (
            self.workflow.get("schema_version") != CURRENT_SCHEMA_VERSION
            or self.workflow.get("workflow_version") != self.workflow_version
            or workflow_ids != STAGES
        ):
            self.error("所选 workflow 与校验器阶段契约不一致", "preflight")
        if self.workflow_hash is not None and self.run.get("workflow_sha256") != self.workflow_hash:
            self.error("run.workflow_sha256 与所选 workflow.json 实际 hash 不一致", "preflight")
        return [stage for stage in completed if stage in STAGES]

    def validate_source_truth(self, completed: list[str]) -> None:
        source = self.run.get("source")
        if not isinstance(source, dict):
            self.error("run.source 必须是对象", "preflight")
            return
        declared_hash = source.get("media_sha256")
        kind = source.get("kind")
        if kind == "local_file":
            locator = source.get("private_locator")
            if not isinstance(locator, str) or not locator:
                self.error("本地 source.private_locator 必须是非空路径", "preflight")
                return
            path = Path(locator).expanduser().resolve()
            if not path.is_file():
                self.error("本地 source.private_locator 不存在或不是文件", "preflight")
                return
            actual_hash = file_hash(path)
            self.actual_media_hash = actual_hash
            if actual_hash != declared_hash:
                self.error("本地 source 媒体字节已变化，media_sha256 失效", "preflight")
            if source.get("fingerprint_state") != "verified":
                self.error("本地 source.fingerprint_state 必须为 'verified'", "preflight")
            return

        if kind == "url":
            if "ingest" not in completed:
                if declared_hash is not None or source.get("fingerprint_state") != "provisional":
                    self.error("URL ingest 前必须保持 provisional 且 media_sha256 为 null", "ingest")
                return
            artifacts = self.run.get("artifacts")
            descriptor = artifacts.get("ingest") if isinstance(artifacts, dict) else None
            if not isinstance(descriptor, dict):
                self.error("URL ingest 缺少 ingest descriptor", "ingest")
                return
            artifact_path = self.secure_relative_path(
                descriptor.get("path"), "run.artifacts.ingest.path", "ingest"
            )
            if artifact_path is None or not artifact_path.is_file():
                self.error("URL ingest artifact 不存在", "ingest")
                return
            try:
                ingest = load_object(artifact_path)
            except ValidationFailure as error:
                self.error(str(error), "ingest")
                return
            local_media = self.secure_relative_path(
                ingest.get("local_media_path"), "ingest.local_media_path", "ingest"
            )
            if local_media is None or not local_media.is_file() or local_media.stat().st_size == 0:
                self.error("URL ingest.local_media_path 不存在或为空", "ingest")
                return
            actual_hash = file_hash(local_media)
            self.actual_media_hash = actual_hash
            if actual_hash != declared_hash or actual_hash != ingest.get("media_sha256"):
                self.error("URL ingest 本地媒体字节 hash 与 media_sha256 不一致", "ingest")
            if source.get("fingerprint_state") != "verified":
                self.error("URL ingest 完成后 fingerprint_state 必须为 'verified'", "ingest")
            return

        self.error("run.source.kind 必须是 local_file 或 url", "preflight")

    def validate_bindings(self, completed: list[str]) -> None:
        bindings = self.run.get("bindings")
        if not isinstance(bindings, list):
            self.error("run.bindings 必须是数组", "build")
            return
        if "build" in completed and len(bindings) != 1:
            self.error("build 完成时 run.bindings 必须恰好有一个 binding", "build")
            return
        if len(bindings) > 1:
            self.error("run.bindings 最多只能有一个 binding", "build")
            return
        if not bindings:
            return
        binding = bindings[0]
        if not isinstance(binding, dict):
            self.error("run.bindings[0] 必须是对象", "build")
            return
        number = binding.get("number")
        slug = binding.get("slug")
        relative = binding.get("relative_path")
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            self.error("binding.number 必须是非负整数", "build")
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            self.error("binding.slug 非法", "build")
        directory = self.secure_repo_relative_path(relative, "binding.relative_path", "build")
        if directory is None:
            return
        match = DEMO_RE.fullmatch(directory.name)
        if (
            match is None
            or not isinstance(number, int)
            or int(match.group(1)) != number
            or match.group(2) != slug
        ):
            self.error("binding 的 number/slug/relative_path 不一致", "build")
        if "build" in completed and not directory.is_dir():
            self.error("binding 指向的 Demo 目录不存在", "build")
        self.binding_dir = directory
        self.binding_relative = relative if isinstance(relative, str) else None

    def validate_descriptor(
        self,
        stage: str,
        descriptor: Any,
        previous_stage: str | None,
        previous_hash: str | None,
    ) -> str | None:
        if not isinstance(descriptor, dict):
            self.error(f"run.artifacts.{stage} 必须是对象", stage)
            return None
        path_value = descriptor.get("path")
        artifact_path = self.secure_relative_path(
            path_value, f"run.artifacts.{stage}.path", stage
        )
        declared_hash = descriptor.get("sha256")
        if not is_hash(declared_hash):
            self.error(f"run.artifacts.{stage}.sha256 必须是 SHA-256", stage)
        if descriptor.get("schema_version") != CURRENT_SCHEMA_VERSION:
            self.error(f"{stage} schema_version 与当前支持版本漂移", stage)
        if descriptor.get("workflow_version") != self.workflow_version:
            self.error(f"{stage} workflow_version 与 run 选择版本漂移", stage)
        descriptor_workflow_hash = descriptor.get(
            "workflow_sha256", descriptor.get("workflow_file_sha256")
        )
        if descriptor_workflow_hash != self.workflow_hash:
            self.error(f"{stage} 所选 workflow.json 实际 hash 漂移", stage)

        source = self.run.get("source")
        media_hash = (
            source.get("media_sha256")
            if isinstance(source, dict) and source.get("kind") == "url"
            else self.actual_media_hash
        )
        if media_hash is None and isinstance(source, dict):
            media_hash = source.get("media_sha256")
        if not is_hash(media_hash):
            provisional_url = (
                isinstance(source, dict)
                and source.get("kind") == "url"
                and source.get("fingerprint_state") == "provisional"
                and media_hash is None
            )
            if not provisional_url or "ingest" in getattr(self, "completed", set()):
                self.error("run.source.media_sha256 尚未成为实际媒体指纹", "ingest")
        preflight_url_without_media = (
            stage == "preflight"
            and isinstance(source, dict)
            and source.get("kind") == "url"
            and "ingest" not in getattr(self, "completed", set())
            and descriptor.get("source_media_sha256") is None
        )
        if not preflight_url_without_media and descriptor.get("source_media_sha256") != media_hash:
            self.error(f"{stage} source/media 指纹漂移", stage)

        upstream = descriptor.get("upstream")
        if not isinstance(upstream, dict):
            self.error(f"run.artifacts.{stage}.upstream 必须是对象", stage)
        elif previous_stage is None:
            if upstream:
                self.error("preflight.upstream 必须为空", stage)
        elif upstream.get(previous_stage) != previous_hash:
            self.error(f"{stage} 上游 {previous_stage} hash 漂移", stage)

        if artifact_path is None:
            return declared_hash if is_hash(declared_hash) else None
        if not artifact_path.exists():
            self.error(f"{stage} 已完成但 artifact 不存在：{path_value}", stage)
            return declared_hash if is_hash(declared_hash) else None
        if not artifact_path.is_file():
            self.error(f"{stage} artifact 不是文件：{path_value}", stage)
            return declared_hash if is_hash(declared_hash) else None
        if artifact_path.stat().st_size == 0:
            self.error(f"{stage} artifact 为空：{path_value}", stage)
            return declared_hash if is_hash(declared_hash) else None

        actual_hash = file_hash(artifact_path)
        if actual_hash != declared_hash:
            self.error(f"{stage} 输出 hash 漂移", stage)
        try:
            content = load_object(artifact_path)
        except ValidationFailure as error:
            self.error(str(error), stage)
            return actual_hash
        self.contents[stage] = content
        expected_type = EXPECTED_TYPES[stage]
        if content.get("artifact_type") != expected_type:
            self.error(
                f"{stage}.artifact_type 必须是 {expected_type!r}", stage
            )
        self.validate_semantics(stage, content)
        return actual_hash

    def validate_semantics(self, stage: str, value: dict[str, Any]) -> None:
        nonempty = lambda item: isinstance(item, str) and bool(item.strip())
        boolean = lambda item: isinstance(item, bool)
        object_value = lambda item: isinstance(item, dict)
        list_value = lambda item: isinstance(item, list)

        if stage == "preflight":
            self.require(value, "source_readable", lambda item: item is True, stage, stage, "必须为 true")
            self.require(value, "source_id", nonempty, stage, stage, "必须是非空字符串")
        elif stage == "ingest":
            self.require(value, "media_sha256", is_hash, stage, stage, "必须是 SHA-256")
            if value.get("media_sha256") != self.actual_media_hash:
                self.error("ingest.media_sha256 与 run source 不一致", stage)
            if value.get("fingerprint_state") != "verified":
                self.error("ingest.fingerprint_state 必须是 'verified'", stage)
        elif stage == "transcript":
            transcript_media_hash = self.require(
                value, "media_sha256", is_hash, stage, stage, "必须是 SHA-256"
            )
            if transcript_media_hash != self.actual_media_hash:
                self.error("transcript.media_sha256 必须等于实际源媒体 hash", stage)
            text_hash = self.require(
                value, "text_sha256", is_hash, stage, stage, "必须是 SHA-256"
            )
            transcript_path = self.validate_file_reference(
                value.get("transcript"), "transcript.transcript", stage
            )
            if (
                transcript_path is not None
                and transcript_path.is_file()
                and is_hash(text_hash)
                and file_hash(transcript_path) != text_hash
            ):
                self.error(
                    "transcript.text_sha256 必须等于真实转录文件 hash", stage
                )
            cues: list[Any] = []
            if transcript_path is not None and transcript_path.is_file():
                try:
                    transcript_document = load_object(transcript_path)
                except ValidationFailure as error:
                    self.error(str(error), stage)
                else:
                    source_id = transcript_document.get("source_id")
                    if source_id != self.run.get("source", {}).get("source_id"):
                        self.error(
                            "transcript source_id 必须等于 run.source.source_id", stage
                        )
                    else:
                        self.transcript_source_id = source_id
                    if transcript_document.get("media_sha256") != self.actual_media_hash:
                        self.error(
                            "transcript 文件 media_sha256 必须等于实际源媒体 hash",
                            stage,
                        )
                    raw_cues = transcript_document.get("cues")
                    if not isinstance(raw_cues, list) or not raw_cues:
                        self.error("transcript.cues 必须是非空数组", stage)
                    else:
                        cues = raw_cues
                        for index, cue in enumerate(cues):
                            context = f"transcript.cues[{index}]"
                            if not isinstance(cue, dict):
                                self.error(f"{context} 必须是对象", stage)
                                continue
                            cue_id = cue.get("cue_id")
                            start = cue.get("start_seconds")
                            end = cue.get("end_seconds")
                            text = cue.get("text")
                            if not isinstance(cue_id, str) or not cue_id.strip():
                                self.error(f"{context}.cue_id 必须非空", stage)
                                continue
                            if cue_id in self.transcript_cues:
                                self.error(f"{context}.cue_id 不得重复", stage)
                            if (
                                not is_number(start)
                                or not is_number(end)
                                or float(start) < 0
                                or float(end) <= float(start)
                            ):
                                self.error(f"{context} 时间范围非法", stage)
                            if not isinstance(text, str) or not text.strip():
                                self.error(f"{context}.text 必须非空", stage)
                            self.transcript_cues[cue_id] = cue
            cue_count = value.get("cue_count")
            if (
                not isinstance(cue_count, int)
                or isinstance(cue_count, bool)
                or cue_count != len(cues)
                or cue_count <= 0
            ):
                self.error(
                    "transcript.cue_count 必须等于机器可解析 cues 的实际数量",
                    stage,
                )
        elif stage in {"learn_method", "observe_motion"}:
            claims = self.require(value, "claims", list_value, stage, stage, "必须是数组")
            if isinstance(claims, list):
                if not claims:
                    self.error(f"{stage}.claims 不能为空", stage)
                for index, claim in enumerate(claims):
                    self.validate_claim(stage, index, claim)
            if stage == "observe_motion":
                coverage = self.require(value, "coverage", list_value, stage, stage, "必须是数组")
                required = {"start", "transition", "stable", "exit"}
                if isinstance(coverage, list) and not required.issubset(set(coverage)):
                    self.error("observe_motion.coverage 必须覆盖 start/transition/stable/exit", stage)
        elif stage == "plan_demo":
            count = self.require(
                value,
                "demo_count",
                lambda item: isinstance(item, int) and not isinstance(item, bool) and item > 0,
                stage,
                stage,
                "必须是正整数",
            )
            demos = self.require(value, "demos", list_value, stage, stage, "必须是数组")
            if isinstance(demos, list):
                if isinstance(count, int) and len(demos) != count:
                    self.error("asset_plan.demo_count 与 demos 数量不一致", stage)
                for index, demo in enumerate(demos):
                    if not isinstance(demo, dict):
                        self.error(f"asset_plan.demos[{index}] 必须是对象", stage)
                        continue
                    self.require(demo, "slug", nonempty, f"asset_plan.demos[{index}]", stage, "必须是非空字符串")
                    self.require(demo, "scope", nonempty, f"asset_plan.demos[{index}]", stage, "必须是非空字符串")
            self.require(
                value,
                "private_sources_tracked",
                lambda item: item is False,
                stage,
                stage,
                "必须为 false",
            )
        elif stage == "build":
            demo_dir_value = self.require(
                value, "demo_dir", nonempty, stage, stage, "必须是非空字符串"
            )
            demo_dir = self.secure_repo_relative_path(
                demo_dir_value, "build.demo_dir", stage
            )
            if demo_dir is not None:
                if demo_dir != self.binding_dir or demo_dir_value != self.binding_relative:
                    self.error("build.demo_dir 必须与 run binding 完全一致", stage)
                if not demo_dir.is_dir():
                    self.error("build.demo_dir 不存在", stage)

            candidate_value = self.require(
                value,
                "candidate_render_path",
                nonempty,
                stage,
                stage,
                "必须是非空字符串",
            )
            candidate = self.secure_relative_path(
                candidate_value, "build.candidate_render_path", stage
            )
            if candidate is not None:
                if not candidate.is_file() or candidate.stat().st_size == 0:
                    self.error("build.candidate_render_path 不存在或为空", stage)
                self.build_candidate_path = candidate

            source_files = value.get("source_files", value.get("demo_files"))
            if not isinstance(source_files, list) or not source_files:
                self.error("build.source_files 必须是非空数组", stage)
            else:
                source_paths = [
                    self.validate_file_reference(
                        reference,
                        f"build.source_files[{index}]",
                        stage,
                        root="repo",
                        within=demo_dir,
                    )
                    for index, reference in enumerate(source_files)
                ]
                basenames = {path.name for path in source_paths if path is not None}
                if not {"index.html", "package.json"}.issubset(basenames):
                    self.error(
                        "build.source_files 必须实际包含 index.html 与 package.json",
                        stage,
                    )

            fixture_files = value.get("fixture_files")
            if not isinstance(fixture_files, list) or not fixture_files:
                self.error("build.fixture_files 必须是非空数组", stage)
            else:
                for index, reference in enumerate(fixture_files):
                    self.validate_file_reference(
                        reference,
                        f"build.fixture_files[{index}]",
                        stage,
                        root="repo",
                        within=demo_dir,
                    )
            if isinstance(source_files, list) and isinstance(fixture_files, list):
                normalized_manifest = json.dumps(
                    {
                        "source_files": source_files,
                        "fixture_files": fixture_files,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.build_target_hash = hashlib.sha256(normalized_manifest).hexdigest()
        elif stage == "verify":
            must_pass = self.require(value, "must_pass", object_value, stage, stage, "必须是对象")
            rubric_checks = self.rubric.get("must_pass")
            required_checks = {
                item.get("id")
                for item in rubric_checks
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            } if isinstance(rubric_checks, list) else set()
            if isinstance(must_pass, dict):
                for check in sorted(required_checks):
                    if must_pass.get(check) is not True:
                        self.error(f"verification.must_pass.{check} 必须为 true", stage)

            logs = value.get("logs")
            if not isinstance(logs, dict):
                self.error("verification.logs 必须是对象", stage)
            else:
                for log_id in sorted(REQUIRED_VERIFICATION_LOGS):
                    receipt_path = self.validate_file_reference(
                        logs.get(log_id), f"verification.logs.{log_id}", stage
                    )
                    self.validate_execution_receipt(log_id, receipt_path, stage)

            snapshots = value.get("snapshots")
            if not isinstance(snapshots, list) or not snapshots:
                self.error("verification.snapshots 必须是非空数组", stage)
            else:
                for index, reference in enumerate(snapshots):
                    self.validate_file_reference(
                        reference, f"verification.snapshots[{index}]", stage
                    )

            render = self.require(value, "render", object_value, stage, stage, "必须是对象")
            if isinstance(render, dict):
                render_path = self.validate_file_reference(
                    render, "verification.render", stage
                )
                if (
                    render_path is not None
                    and self.build_candidate_path is not None
                    and render_path != self.build_candidate_path
                ):
                    self.error(
                        "verification.render.path 必须等于 build.candidate_render_path",
                        stage,
                    )
                self.verification_render_path = render_path
                if render_path is not None and render_path.is_file():
                    self.verification_render_hash = file_hash(render_path)
        elif stage in {"review_r1", "review_r2"}:
            self.validate_score(stage, value)
        elif stage == "revise":
            dimension = self.require(
                value, "changed_dimension", nonempty, stage, stage, "必须是非空字符串"
            )
            if dimension not in self.dimension_weights:
                self.error("revision.changed_dimension 不在 rubric 维度枚举中", stage)
            self.require(value, "source_render_sha256", is_hash, stage, stage, "必须是 SHA-256")
            self.require(value, "output_render_sha256", is_hash, stage, stage, "必须是 SHA-256")
            output_path = self.secure_relative_path(
                value.get("output_render_path"), "revision.output_render_path", stage
            )
            if output_path is not None:
                if not output_path.is_file() or output_path.stat().st_size == 0:
                    self.error("revision.output_render_path 不存在或为空", stage)
                elif file_hash(output_path) != value.get("output_render_sha256"):
                    self.error("revision 输出文件实际 hash 不一致", stage)
                self.revision_output_path = output_path
            frozen = value.get("frozen_dimensions")
            expected_frozen = set(self.dimension_weights) - ({dimension} if dimension in self.dimension_weights else set())
            if (
                not isinstance(frozen, list)
                or any(not isinstance(item, str) for item in frozen)
                or len(frozen) != len(set(frozen))
                or set(frozen) != expected_frozen
            ):
                self.error(
                    "revision.frozen_dimensions 必须无重复地包含除 changed_dimension 外的全部 rubric 维度",
                    stage,
                )
        elif stage == "finalize":
            self.validate_final(value)

    def validate_execution_receipt(
        self, log_id: str, receipt_path: Path | None, stage: str
    ) -> None:
        context = f"verification.logs.{log_id}.receipt"
        if receipt_path is None or not receipt_path.is_file():
            return
        try:
            receipt = load_object(receipt_path)
        except ValidationFailure as error:
            self.error(str(error), stage)
            return
        if receipt.get("receipt_type") != "execution":
            self.error(f"{context}.receipt_type 必须是 'execution'", stage)
        command = receipt.get("command")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(part, str) or not part.strip() for part in command)
        ):
            self.error(f"{context}.command 必须是规范化的非空字符串数组", stage)
        exit_code = receipt.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
            self.error(f"{context}.exit_code 必须为 0", stage)
        for stream in ("stdout", "stderr"):
            self.validate_file_reference(
                receipt.get(stream),
                f"{context}.{stream}",
                stage,
                allow_empty=True,
            )
        executed_at = receipt.get("executed_at")
        try:
            parsed_time = datetime.fromisoformat(
                executed_at.replace("Z", "+00:00")
                if isinstance(executed_at, str)
                else ""
            )
        except ValueError:
            parsed_time = None
        if parsed_time is None or parsed_time.tzinfo is None:
            self.error(f"{context}.executed_at 必须是带时区的 ISO-8601", stage)
        target = receipt.get("target")
        if not isinstance(target, dict):
            self.error(f"{context}.target 必须是对象", stage)
        else:
            if target.get("path") != self.binding_relative:
                self.error(f"{context}.target.path 必须等于绑定 Demo", stage)
            if (
                not is_hash(target.get("sha256"))
                or target.get("sha256") != self.build_target_hash
            ):
                self.error(f"{context}.target.sha256 必须绑定 build source manifest", stage)
        if log_id == "privacy_audit":
            if receipt.get("ok") is not True:
                self.error("privacy audit receipt.ok 必须为 true", stage)
            staged_count = receipt.get("staged_count")
            if (
                not isinstance(staged_count, int)
                or isinstance(staged_count, bool)
                or staged_count <= 0
            ):
                self.error("privacy audit receipt.staged_count 必须大于 0", stage)

    def validate_claim(self, stage: str, index: int, claim: Any) -> None:
        context = f"{stage}.claims[{index}]"
        if not isinstance(claim, dict):
            self.error(f"{context} 必须是对象", stage)
            return
        if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
            self.error(f"{context}.statement 必须是非空字符串", stage)
        if claim.get("source_type") not in SOURCE_TYPES:
            self.error(f"{context}.source_type 非法", stage)
        evidence = claim.get("evidence")
        if not isinstance(evidence, dict):
            self.error(f"{context}.evidence 必须是对象", stage)
            return
        if not isinstance(evidence.get("source_id"), str) or not evidence["source_id"].strip():
            self.error(f"{context}.evidence.source_id 必须是非空字符串", stage)
        elif evidence.get("source_id") != self.transcript_source_id:
            self.error(
                f"{context}.evidence.source_id 必须等于对应 transcript source_id",
                stage,
            )
        media_hash = evidence.get("media_sha256")
        if not is_hash(media_hash):
            self.error(f"{context}.evidence.media_sha256 必须是 SHA-256", stage)
        elif media_hash != self.actual_media_hash:
            self.error(
                f"{context}.evidence.media_sha256 必须等于对应 transcript 媒体 hash",
                stage,
            )
        self.validate_time_range(evidence.get("time_range"), f"{context}.evidence.time_range", stage)
        cue_id = evidence.get("cue_id")
        transcript_cue = self.transcript_cues.get(cue_id) if isinstance(cue_id, str) else None
        if transcript_cue is None:
            self.error(f"{context}.evidence.cue_id 必须定位对应 transcript cue", stage)
        cue = evidence.get("cue")
        if not isinstance(cue, dict):
            self.error(f"{context}.evidence.cue 必须是对象", stage)
        else:
            if not is_number(cue.get("start_seconds")) or not is_number(cue.get("end_seconds")):
                self.error(f"{context}.evidence.cue 必须有数字时间码", stage)
            if not isinstance(cue.get("text"), str) or not cue["text"].strip():
                self.error(f"{context}.evidence.cue.text 必须非空", stage)
        if transcript_cue is not None and isinstance(cue, dict):
            expected_range = {
                "start_seconds": transcript_cue.get("start_seconds"),
                "end_seconds": transcript_cue.get("end_seconds"),
            }
            expected_cue = {
                **expected_range,
                "text": transcript_cue.get("text"),
            }
            if evidence.get("time_range") != expected_range or cue != expected_cue:
                self.error(
                    f"{context}.evidence 时间、文本必须与对应 transcript cue 精确一致",
                    stage,
                )
        artifact = evidence.get("artifact")
        self.validate_file_reference(
            artifact, f"{context}.evidence.artifact", stage
        )

    def validate_time_range(self, value: Any, context: str, stage: str) -> None:
        if not isinstance(value, dict):
            self.error(f"{context} 必须是对象", stage)
            return
        start = value.get("start_seconds")
        end = value.get("end_seconds")
        if (
            not isinstance(start, (int, float))
            or isinstance(start, bool)
            or not isinstance(end, (int, float))
            or isinstance(end, bool)
            or start < 0
            or end < start
        ):
            self.error(f"{context} 必须是合法的非负时间范围", stage)

    def parse_framemd5(
        self, text: str, context: str, stage: str
    ) -> tuple[list[tuple[int, int, int, int, int, str]], float | None]:
        timebases: dict[int, Fraction] = {}
        rows: list[tuple[int, int, int, int, int, str]] = []
        has_sha256_header = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower() == "#hash: sha256":
                has_sha256_header = True
                continue
            timebase_match = FRAMEMD5_TIMEBASE_RE.fullmatch(stripped)
            if timebase_match:
                stream = int(timebase_match.group(1))
                numerator = int(timebase_match.group(2))
                denominator = int(timebase_match.group(3))
                if numerator <= 0 or denominator <= 0:
                    self.error(f"{context} 第 {line_number} 行 timebase 非法", stage)
                else:
                    timebases[stream] = Fraction(numerator, denominator)
                continue
            if stripped.startswith("#"):
                continue
            match = FRAMEMD5_ROW_RE.fullmatch(line)
            if match is None:
                self.error(f"{context} 第 {line_number} 行不是标准 FFmpeg framemd5", stage)
                continue
            row = (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                int(match.group(5)),
                match.group(6).lower(),
            )
            if row[3] <= 0 or row[4] < 0:
                self.error(f"{context} 第 {line_number} 行 duration/size 非法", stage)
            rows.append(row)
        if not has_sha256_header:
            self.error(f"{context} 必须声明 #hash: SHA256", stage)
        if not rows:
            self.error(f"{context} 缺少标准逐帧校验行", stage)
            return rows, None
        for stream in {row[0] for row in rows}:
            if stream not in timebases:
                self.error(f"{context} 缺少 stream {stream} timebase", stage)
        video_rows = [row for row in rows if row[0] == 0]
        if not video_rows:
            self.error(f"{context} 缺少视频 stream 0", stage)
            return rows, None
        pts = [row[2] for row in video_rows]
        if pts != sorted(pts) or len(pts) != len(set(pts)):
            self.error(f"{context} 视频 PTS 必须严格递增", stage)
        timebase = timebases.get(0)
        duration = (
            max(float((row[2] + row[3]) * timebase) for row in video_rows)
            if timebase is not None
            else None
        )
        return rows, duration

    def verify_framemd5(
        self, render_path: Path | None, saved_path: Path | None, context: str, stage: str
    ) -> float | None:
        executable = shutil.which("ffmpeg")
        if executable is None:
            self.error(f"{context} 需要本地 ffmpeg 重算逐帧 hash", stage)
            return None
        if render_path is None or not render_path.is_file() or saved_path is None or not saved_path.is_file():
            return None
        try:
            saved_text = saved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self.error(f"{context} 必须是 UTF-8 文本", stage)
            return None
        saved_rows, _ = self.parse_framemd5(saved_text, context, stage)
        result = subprocess.run(
            [
                executable,
                "-v",
                "error",
                "-i",
                str(render_path),
                "-map",
                "0:v:0",
                "-f",
                "framemd5",
                "-hash",
                "sha256",
                "-",
            ],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            self.error(f"{context} 无法用 ffmpeg 完整解码：{result.stderr.strip()}", stage)
            return None
        actual_rows, duration = self.parse_framemd5(
            result.stdout, f"{context}.recomputed", stage
        )
        if saved_rows != actual_rows:
            self.error(f"{context} 与 ffmpeg 对 reviewed render 的重算结果不一致", stage)
        return duration

    def image_dimensions(
        self, path: Path | None, context: str, stage: str
    ) -> tuple[int, int] | None:
        if path is None or not path.is_file():
            return None
        data = path.read_bytes()
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            if width > 0 and height > 0:
                return width, height
        if data.startswith(b"\xff\xd8"):
            offset = 2
            while offset + 4 <= len(data):
                if data[offset] != 0xFF:
                    offset += 1
                    continue
                marker = data[offset + 1]
                offset += 2
                if marker in {0xD8, 0xD9}:
                    continue
                if offset + 2 > len(data):
                    break
                segment_length = int.from_bytes(data[offset : offset + 2], "big")
                if segment_length < 2 or offset + segment_length > len(data):
                    break
                if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and segment_length >= 7:
                    height = int.from_bytes(data[offset + 3 : offset + 5], "big")
                    width = int.from_bytes(data[offset + 5 : offset + 7], "big")
                    if width > 0 and height > 0:
                        return width, height
                offset += segment_length
        self.error(f"{context} 必须是带有效尺寸的真实图片", stage)
        return None

    def validate_sampling_manifest(
        self,
        manifest_path: Path | None,
        render_hash: Any,
        decoded_duration: float | None,
        watch_dimensions: tuple[int, int] | None,
        dense_dimensions: tuple[int, int] | None,
        stage: str,
    ) -> None:
        context = f"{stage}.continuous_review.sampling_manifest"
        if manifest_path is None or not manifest_path.is_file():
            return
        try:
            manifest = load_object(manifest_path)
        except ValidationFailure as error:
            self.error(str(error), stage)
            return
        if manifest.get("render_sha256") != render_hash:
            self.error(f"{context}.render_sha256 与 reviewed render 不一致", stage)
        duration = manifest.get("duration_seconds")
        if (
            not is_number(duration)
            or float(duration) <= 0
            or decoded_duration is None
            or abs(float(duration) - decoded_duration) > 1e-6
        ):
            self.error(f"{context}.duration_seconds 与完整解码时长不一致", stage)
            duration_value = decoded_duration
        else:
            duration_value = float(duration)
        if manifest.get("sample_fps") != 6:
            self.error(f"{context}.sample_fps 必须为 6", stage)
        timestamps = manifest.get("timestamps_seconds")
        valid_timestamps = (
            isinstance(timestamps, list)
            and timestamps
            and all(is_number(item) for item in timestamps)
        )
        if not valid_timestamps or duration_value is None:
            self.error(f"{context}.timestamps_seconds 必须覆盖全时长", stage)
        else:
            numeric = [float(item) for item in timestamps]
            expected_count = math.ceil(duration_value * 6 - 1e-9)
            gap_limit = 1 / 6 + 1e-6
            if (
                len(numeric) != expected_count
                or abs(numeric[0]) > 1e-6
                or any(b <= a or b - a > gap_limit for a, b in zip(numeric, numeric[1:]))
                or numeric[-1] < max(0.0, duration_value - 1 / 6) - 1e-6
                or numeric[-1] >= duration_value + 1e-6
            ):
                self.error(f"{context}.timestamps_seconds 未以 6fps 覆盖全时长", stage)
        watch = manifest.get("watch_sheet")
        if (
            not isinstance(watch, dict)
            or watch_dimensions is None
            or (watch.get("width"), watch.get("height")) != watch_dimensions
            or watch.get("frame_count") != (len(timestamps) if isinstance(timestamps, list) else None)
        ):
            self.error(f"{context}.watch_sheet 与真实图片/采样数不一致", stage)
        dense = manifest.get("dense_frames")
        dense_times = dense.get("timestamps_seconds") if isinstance(dense, dict) else None
        if (
            not isinstance(dense, dict)
            or dense_dimensions is None
            or (dense.get("width"), dense.get("height")) != dense_dimensions
            or not isinstance(dense_times, list)
            or not dense_times
            or any(not is_number(item) for item in dense_times)
            or duration_value is None
            or any(float(item) < 0 or float(item) > duration_value for item in dense_times)
        ):
            self.error(f"{context}.dense_frames 与真实图片/时长不一致", stage)

    def validate_score(self, stage: str, value: dict[str, Any]) -> None:
        if shutil.which("ffmpeg") is None:
            self.error(f"{stage} 完成审阅必须有本地 ffmpeg", stage)
        expected_round = "r1" if stage == "review_r1" else "r2"
        if value.get("round") != expected_round:
            self.error(f"{stage}.round 必须是 {expected_round!r}", stage)
        reviewed_hash = self.require(
            value,
            "reviewed_render_sha256",
            is_hash,
            stage,
            stage,
            "必须是 SHA-256",
        )
        reviewed_path = self.secure_relative_path(
            value.get("reviewed_render_path"), f"{stage}.reviewed_render_path", stage
        )
        if reviewed_path is not None:
            if not reviewed_path.is_file() or reviewed_path.stat().st_size == 0:
                self.error(f"{stage}.reviewed_render_path 不存在或为空", stage)
            elif is_hash(reviewed_hash) and file_hash(reviewed_path) != reviewed_hash:
                self.error(f"{stage} reviewed render 文件实际 hash 不一致", stage)
            self.review_paths[stage] = reviewed_path

        decoded_duration: float | None = None
        evidence_refs: dict[str, tuple[str, str]] = {}
        decode = value.get("full_decode")
        if not isinstance(decode, dict):
            self.error(f"{stage}.full_decode 必须是对象", stage)
        else:
            if decode.get("completed") is not True:
                self.error(f"{stage}.full_decode.completed 必须为 true", stage)
            if decode.get("render_sha256") != reviewed_hash:
                self.error(
                    f"{stage}.full_decode.render_sha256 必须等于 reviewed render",
                    stage,
                )
            framemd5_path = self.validate_file_reference(
                {
                    "path": decode.get("framemd5_path"),
                    "sha256": decode.get("framemd5_sha256"),
                },
                f"{stage}.full_decode.framemd5",
                stage,
            )
            decoded_duration = self.verify_framemd5(
                reviewed_path,
                framemd5_path,
                f"{stage}.full_decode.framemd5",
                stage,
            )
            if isinstance(decode.get("framemd5_path"), str) and is_hash(
                decode.get("framemd5_sha256")
            ):
                evidence_refs["framemd5"] = (
                    decode["framemd5_path"],
                    decode["framemd5_sha256"],
                )

        review = value.get("continuous_review")
        if not isinstance(review, dict):
            self.error(f"{stage}.continuous_review 必须是对象", stage)
        else:
            if review.get("completed") is not True:
                self.error(f"{stage}.continuous_review.completed 必须为 true", stage)
            if review.get("render_sha256") != reviewed_hash:
                self.error(
                    f"{stage}.continuous_review.render_sha256 必须等于 reviewed render",
                    stage,
                )
            if review.get("watch_sheet_fps") != 6:
                self.error(f"{stage}.continuous_review.watch_sheet_fps 必须为 6", stage)
            if not is_hash(review.get("watch_sheet_sha256")):
                self.error(
                    f"{stage}.continuous_review.watch_sheet_sha256 必须是 SHA-256",
                    stage,
                )
            watch_path = self.validate_file_reference(
                {
                    "path": review.get("watch_sheet_path"),
                    "sha256": review.get("watch_sheet_sha256"),
                },
                f"{stage}.continuous_review.watch_sheet",
                stage,
            )
            dense_path = self.validate_file_reference(
                {
                    "path": review.get("dense_frames_path"),
                    "sha256": review.get("dense_frames_sha256"),
                },
                f"{stage}.continuous_review.dense_frames",
                stage,
            )
            manifest_path = self.validate_file_reference(
                {
                    "path": review.get("sampling_manifest_path"),
                    "sha256": review.get("sampling_manifest_sha256"),
                },
                f"{stage}.continuous_review.sampling_manifest",
                stage,
            )
            watch_dimensions = self.image_dimensions(
                watch_path, f"{stage}.continuous_review.watch_sheet", stage
            )
            dense_dimensions = self.image_dimensions(
                dense_path, f"{stage}.continuous_review.dense_frames", stage
            )
            self.validate_sampling_manifest(
                manifest_path,
                reviewed_hash,
                decoded_duration,
                watch_dimensions,
                dense_dimensions,
                stage,
            )
            for name, path_key, hash_key in (
                ("watch_sheet", "watch_sheet_path", "watch_sheet_sha256"),
                ("dense_frames", "dense_frames_path", "dense_frames_sha256"),
                (
                    "sampling_manifest",
                    "sampling_manifest_path",
                    "sampling_manifest_sha256",
                ),
            ):
                if isinstance(review.get(path_key), str) and is_hash(review.get(hash_key)):
                    evidence_refs[name] = (review[path_key], review[hash_key])

        self.review_evidence[stage] = evidence_refs

        issues = value.get("issues")
        if not isinstance(issues, list):
            self.error(f"{stage}.issues 必须是数组", stage)
        else:
            for index, issue in enumerate(issues):
                if not isinstance(issue, dict):
                    self.error(f"{stage}.issues[{index}] 必须是对象", stage)
                    continue
                self.validate_time_range(issue.get("time_range"), f"{stage}.issues[{index}].time_range", stage)
                if not isinstance(issue.get("summary"), str) or not issue["summary"].strip():
                    self.error(f"{stage}.issues[{index}].summary 必须非空", stage)
        top_fix = value.get("top_fix")
        if stage == "review_r1":
            if not isinstance(top_fix, dict):
                self.error("review_r1.top_fix 必须恰好有一个对象", stage)
            else:
                dimension = top_fix.get("dimension")
                if dimension not in self.dimension_weights:
                    self.error(
                        "review_r1.top_fix.dimension 必须属于 rubric 维度枚举",
                        stage,
                    )
                if not isinstance(top_fix.get("instruction"), str) or not top_fix["instruction"].strip():
                    self.error("review_r1.top_fix.instruction 必须非空", stage)
                self.validate_time_range(top_fix.get("time_range"), "review_r1.top_fix.time_range", stage)
        elif top_fix is not None:
            self.error("review_r2.top_fix 必须为 null，R2 后停止", stage)

        dimensions = value.get("dimensions", value.get("dimension_scores"))
        if not isinstance(dimensions, dict):
            self.error(f"{stage}.dimensions 必须是 rubric 逐维度评分对象", stage)
            calculated_score = None
        else:
            actual_ids = set(dimensions)
            expected_ids = set(self.dimension_weights)
            if actual_ids != expected_ids:
                self.error(
                    f"{stage}.dimensions 必须恰好覆盖全部 rubric 维度",
                    stage,
                )
            calculated_score = 0.0
            for identifier, weight in self.dimension_weights.items():
                dimension_score = dimensions.get(identifier)
                if (
                    not is_number(dimension_score)
                    or float(dimension_score) < 1
                    or float(dimension_score) > 5
                ):
                    self.error(
                        f"{stage}.dimensions.{identifier} 必须在 1..5",
                        stage,
                    )
                    calculated_score = None
                    continue
                if calculated_score is not None:
                    calculated_score += float(dimension_score) / 5.0 * weight

        score = value.get("score")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or score < 0
            or score > 100
        ):
            self.error(f"{stage}.score 必须在 0..100", stage)
        elif calculated_score is not None and abs(float(score) - calculated_score) > 0.01:
            self.error(
                f"{stage}.score 必须按 rubric 权重加权重算为 {calculated_score:.2f}",
                stage,
            )

    def validate_final(self, value: dict[str, Any]) -> None:
        stage = "finalize"
        final_status = value.get("status")
        if final_status not in {"completed", "completed_with_residuals"}:
            self.error("final.status 非法", stage)
        if final_status != self.run.get("status"):
            self.error("final.status 必须与 run.status 一致", stage)
        r2_score = self.contents.get("review_r2", {}).get("score")
        if is_number(r2_score):
            expected_status = (
                "completed"
                if float(r2_score) >= float(self.threshold)
                else "completed_with_residuals"
            )
            if final_status != expected_status:
                self.error(
                    f"R2 分数对应的完成状态必须是 {expected_status}", stage
                )
        render_path_value = value.get("render_path")
        render_path = self.secure_relative_path(render_path_value, "final.render_path", stage)
        render_hash = value.get("render_sha256")
        if not is_hash(render_hash):
            self.error("final.render_sha256 必须是 SHA-256", stage)
        video = value.get("video")
        if not isinstance(video, dict):
            self.error("final.video 必须是对象", stage)
        else:
            for key in ("width", "height"):
                if (
                    not isinstance(video.get(key), int)
                    or isinstance(video.get(key), bool)
                    or video[key] <= 0
                ):
                    self.error(f"final.video.{key} 必须是正整数", stage)
            for key in ("duration_seconds", "fps"):
                if not is_number(video.get(key)) or float(video[key]) <= 0:
                    self.error(f"final.video.{key} 必须是正数", stage)
        candidates = value.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1:
            self.error("final.candidates 必须恰好包含一个最终候选", stage)
        else:
            candidate = candidates[0]
            if not isinstance(candidate, dict):
                self.error("final.candidates[0] 必须是对象", stage)
            else:
                if candidate.get("selected") is not True:
                    self.error("final.candidates[0].selected 必须为 true", stage)
                if candidate.get("path") != render_path_value:
                    self.error("final 候选 path 与 render_path 不一致", stage)
                if candidate.get("render_sha256") != render_hash:
                    self.error("final 候选 hash 与 render_sha256 不一致", stage)
        if render_path is not None:
            if not render_path.is_file() or render_path.stat().st_size == 0:
                self.error("final 指向的 MP4 不存在或为空", stage)
            elif is_hash(render_hash) and file_hash(render_path) != render_hash:
                self.error("final MP4 内容 hash 与 render_sha256 不一致", stage)
            else:
                self.probe_video(render_path, video)

    def probe_video(self, path: Path, expected: Any) -> None:
        if self.ffprobe_mode == "off":
            return
        executable = shutil.which("ffprobe")
        if executable is None:
            message = "未找到 ffprobe，未验证最终 MP4 流信息"
            if self.ffprobe_mode == "on":
                self.error(message, "finalize")
            else:
                self.warnings.append(message)
            return
        result = subprocess.run(
            [
                executable,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate:format=duration",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            self.error(f"ffprobe 无法读取最终 MP4：{result.stderr.strip()}", "finalize")
            return
        try:
            probe = json.loads(result.stdout)
            stream = probe["streams"][0]
            duration = float(probe["format"]["duration"])
            frame_rate = float(Fraction(stream["r_frame_rate"]))
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            ZeroDivisionError,
            json.JSONDecodeError,
        ):
            self.error("ffprobe 未返回可用的视频流、尺寸或时长", "finalize")
            return
        if (
            stream.get("width", 0) <= 0
            or stream.get("height", 0) <= 0
            or duration <= 0
            or frame_rate <= 0
        ):
            self.error("最终 MP4 的尺寸、时长或 fps 无效", "finalize")
        if isinstance(expected, dict):
            for key in ("width", "height"):
                if key in expected:
                    if (
                        not isinstance(expected[key], int)
                        or isinstance(expected[key], bool)
                        or expected[key] <= 0
                    ):
                        self.error(f"final.video.{key} 必须是正整数", "finalize")
                    elif stream.get(key) != expected[key]:
                        self.error(f"最终 MP4 {key} 与 final.video 不一致", "finalize")
            if "duration_seconds" in expected:
                if (
                    not is_number(expected["duration_seconds"])
                    or float(expected["duration_seconds"]) <= 0
                ):
                    self.error("final.video.duration_seconds 必须是正数", "finalize")
                elif abs(duration - float(expected["duration_seconds"])) > 0.05:
                    self.error("最终 MP4 时长与 final.video 不一致", "finalize")
            expected_fps = expected.get("fps", expected.get("frame_rate"))
            if expected_fps is not None:
                if not is_number(expected_fps) or float(expected_fps) <= 0:
                    self.error("final.video.fps 必须是正数", "finalize")
                elif abs(frame_rate - float(expected_fps)) > 0.001:
                    self.error("最终 MP4 fps 与 final.video 不一致", "finalize")

    def cross_validate_rounds(self, completed: list[str]) -> None:
        if "verify" in completed and "review_r1" in completed:
            first = self.contents.get("review_r1", {})
            first_hash = first.get("reviewed_render_sha256")
            first_path = self.review_paths.get("review_r1")
            if (
                first_hash != self.verification_render_hash
                or (
                    first_path is not None
                    and self.verification_render_path is not None
                    and first_path != self.verification_render_path
                )
            ):
                self.error(
                    "R1 reviewed render 必须与 verification.render 是同一文件和 hash",
                    "review_r1",
                )
        if "review_r1" in completed and "review_r2" in completed:
            first = self.contents.get("review_r1", {}).get("reviewed_render_sha256")
            second = self.contents.get("review_r2", {}).get("reviewed_render_sha256")
            if is_hash(first) and first == second:
                self.error("R2 必须审阅修正后生成的新 MP4 hash", "review_r2")
            first_evidence = self.review_evidence.get("review_r1", {})
            second_evidence = self.review_evidence.get("review_r2", {})
            for evidence_name in ("framemd5", "watch_sheet", "dense_frames"):
                first_ref = first_evidence.get(evidence_name)
                second_ref = second_evidence.get(evidence_name)
                if (
                    first_ref is not None
                    and second_ref is not None
                    and (first_ref[0] == second_ref[0] or first_ref[1] == second_ref[1])
                ):
                    self.error(
                        f"R1/R2 的 {evidence_name} 路径与 hash 都必须不同",
                        "review_r2",
                    )
        if "review_r1" in completed and "revise" in completed:
            first = self.contents.get("review_r1", {}).get("reviewed_render_sha256")
            top_fix = self.contents.get("review_r1", {}).get("top_fix")
            revision = self.contents.get("revise", {})
            if is_hash(first) and revision.get("source_render_sha256") != first:
                self.error("revision.source_render_sha256 必须等于 R1 审阅 hash", "revise")
            if (
                isinstance(top_fix, dict)
                and revision.get("changed_dimension") != top_fix.get("dimension")
            ):
                self.error(
                    "revision.changed_dimension 必须等于 R1 top_fix.dimension",
                    "revise",
                )
        if "revise" in completed and "review_r2" in completed:
            output_hash = self.contents.get("revise", {}).get("output_render_sha256")
            second = self.contents.get("review_r2", {}).get("reviewed_render_sha256")
            second_path = self.review_paths.get("review_r2")
            if (
                is_hash(output_hash)
                and (
                    second != output_hash
                    or (
                        second_path is not None
                        and self.revision_output_path is not None
                        and second_path != self.revision_output_path
                    )
                )
            ):
                self.error("R2 必须审阅 revision 输出文件和 hash", "review_r2")
        if "review_r2" in completed and "finalize" in completed:
            second = self.contents.get("review_r2", {}).get("reviewed_render_sha256")
            final_hash = self.contents.get("finalize", {}).get("render_sha256")
            if is_hash(second) and final_hash != second:
                self.error("final render hash 必须与 R2 reviewed_render_sha256 相同", "finalize")

    def learning_path(self, value: Any, context: str) -> Path | None:
        """解析私有 sidecar；学习扩展错误永远不绑定核心阶段。"""

        if not isinstance(value, str) or not value:
            self.error(f"{context} 必须是 run 内的非空相对路径")
            return None
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            self.error(f"{context} 禁止绝对路径或 ..")
            return None
        cursor = self.run_dir
        for part in candidate.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                self.error(f"{context} 任一路径组件都不得是 symlink")
                return None
        resolved = (self.run_dir / candidate).resolve()
        try:
            resolved.relative_to(self.run_dir.resolve())
        except ValueError:
            self.error(f"{context} 逃逸 run 目录")
            return None
        return resolved

    def validate_learning_descriptor(
        self,
        descriptor: Any,
        context: str,
        *,
        expected_path: str | None = None,
    ) -> Path | None:
        if not isinstance(descriptor, dict):
            self.error(f"{context} 必须是包含 path/sha256 的对象")
            return None
        path_value = descriptor.get("path")
        if expected_path is not None and path_value != expected_path:
            self.error(f"{context}.path 必须是 {expected_path!r}")
        path = self.learning_path(path_value, f"{context}.path")
        declared_hash = descriptor.get("sha256")
        if not is_hash(declared_hash):
            self.error(f"{context}.sha256 必须是 SHA-256")
        if path is None:
            return None
        if not path.is_file() or path.stat().st_size == 0:
            self.error(f"{context} 指向的文件不存在或为空：{path_value}")
            return path
        try:
            content = self.learning_file_bytes.setdefault(
                path, read_stable_file_bytes(path)
            )
        except (FileNotFoundError, OSError, ValueError) as error:
            self.error(f"{context} 无法稳定读取：{error}")
            return path
        if is_hash(declared_hash) and hashlib.sha256(content).hexdigest() != declared_hash:
            self.error(f"{context} 内容 hash 与 sha256 不一致")
        return path

    def load_learning_object(
        self, path: Path | None, context: str
    ) -> dict[str, Any] | None:
        if path is None or not path.is_file() or path.stat().st_size == 0:
            return None
        try:
            content = self.learning_file_bytes.get(path)
            if content is None:
                content = read_stable_file_bytes(path)
                self.learning_file_bytes[path] = content
            value = json.loads(content.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValidationFailure(f"JSON 顶层必须是对象：{path}")
            return value
        except (ValidationFailure, UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as error:
            self.error(f"{context} 必须是 JSON 对象：{error}")
            return None

    def validate_learning_identity(
        self,
        value: dict[str, Any],
        required_fields: Any,
        contract: dict[str, Any],
        context: str,
    ) -> None:
        if not isinstance(required_fields, list) or any(
            not isinstance(field, str) or not field for field in required_fields
        ):
            self.error(f"{context} 对应 contract required fields 非法")
            return
        missing = [field for field in required_fields if field not in value]
        if missing:
            self.error(f"{context} 缺少 required fields：{', '.join(missing)}")
        if value.get("schema_version") != contract.get("schema_version"):
            self.error(f"{context}.schema_version 与 learning contract 不一致")
        if value.get("workflow_version") != self.workflow_version:
            self.error(f"{context}.workflow_version 与 run 不一致")
        if value.get("run_id") != self.run_id:
            self.error(f"{context}.run_id 与目录名不一致")

    def classify_learning_sidecar(
        self, path_value: str, contract: dict[str, Any]
    ) -> tuple[str, Any] | None:
        artifacts = contract.get("artifacts")
        required = artifacts.get("required") if isinstance(artifacts, dict) else None
        fixed = (
            {
                key: fields
                for key, fields in required.items()
                if key != "memory-selection.json"
            }
            if isinstance(required, dict)
            else {}
        )
        if path_value in fixed:
            return "fixed", fixed[path_value]

        logical_path = Path(path_value)
        if logical_path.as_posix() != path_value:
            return None
        parts = logical_path.parts
        if len(parts) != 2:
            return None
        directory, filename = parts
        if not filename.endswith(".json") or not filename[:-5]:
            return None
        if directory == "usage-events":
            return "usage_event", None

        optional = (
            artifacts.get("post_run_optional")
            if isinstance(artifacts, dict)
            else None
        )
        if isinstance(optional, dict):
            pattern = f"{directory}/*.json"
            if pattern in optional and directory in {
                "feedback-candidates",
                "promotion-receipts",
            }:
                return "post_run", optional[pattern]
        return None

    def validate_learning_json(
        self,
        path: Path | None,
        kind: str,
        required_fields: Any,
        contract: dict[str, Any],
        context: str,
    ) -> None:
        value = self.load_learning_object(path, context)
        if value is None:
            return
        try:
            reject_private_payload(value)
        except (TypeError, ValueError) as error:
            self.error(f"{context} 包含私有或敏感 payload：{error}")
        if path is not None:
            try:
                relative = path.relative_to(self.run_dir).as_posix()
            except ValueError:
                relative = context
            self.learning_contents[relative] = value
        if kind != "usage_event":
            self.validate_learning_identity(
                value, required_fields, contract, context
            )
            return

        usage = contract.get("usage_event")
        if not isinstance(usage, dict):
            self.error("learning contract usage_event 必须是对象")
            return
        self.validate_learning_identity(
            value, usage.get("common_required_fields"), contract, context
        )
        kind_value = value.get("kind")
        if kind_value not in usage.get("kind_enum", []):
            self.error(f"{context}.kind 非法：{kind_value!r}")
        capture_state = value.get("capture_state")
        if capture_state not in usage.get("capture_state_enum", []):
            self.error(f"{context}.capture_state 非法：{capture_state!r}")
        result = value.get("result")
        if result not in usage.get("result_enum", []):
            self.error(f"{context}.result 非法：{result!r}")
        branches = usage.get("branches")
        branch = branches.get(kind_value) if isinstance(branches, dict) else None
        if isinstance(branch, dict):
            branch_fields = branch.get("required_fields")
            if not isinstance(branch_fields, list):
                self.error(f"{context} kind branch required fields 非法")
            else:
                missing = [field for field in branch_fields if field not in value]
                if missing:
                    self.error(
                        f"{context} 缺少 kind required fields：{', '.join(missing)}"
                    )

    def learning_capability_matrix(self) -> dict[str, set[str]]:
        source = self.run.get("source")
        source_kind = source.get("kind") if isinstance(source, dict) else None
        matrix: dict[str, set[str]] = {}
        stages = self.workflow.get("stages")
        if not isinstance(stages, list):
            self.error("learning workflow stages 必须是数组")
            return matrix
        for item in stages:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                self.error("learning workflow stage 结构非法")
                continue
            raw_capabilities = item.get("capability_ids")
            if not isinstance(raw_capabilities, list) or any(
                not isinstance(value, str) for value in raw_capabilities
            ):
                self.error(f"learning workflow {item.get('id')} capability_ids 非法")
                continue
            capabilities = set(raw_capabilities)
            conditional = item.get("conditional_capabilities", [])
            if not isinstance(conditional, list):
                self.error(
                    f"learning workflow {item.get('id')} conditional_capabilities 非法"
                )
                conditional = []
            for condition in conditional:
                if not isinstance(condition, dict):
                    self.error("learning conditional capability 必须是对象")
                    continue
                if (
                    condition.get("when") == "source.kind == 'url'"
                    and source_kind == "url"
                    and isinstance(condition.get("capability_id"), str)
                ):
                    capabilities.add(condition["capability_id"])
            matrix[item["id"]] = capabilities
        return matrix

    def load_pinned_capability_registry(self) -> dict[str, Any] | None:
        if self.learning_registry is not None:
            return self.learning_registry
        extension = self.workflow.get("learning_extension")
        if self.workflow_version == "1.0.0" and not isinstance(extension, dict):
            path = CAPABILITY_REGISTRIES_ROOT / "1.0.0.json"
            try:
                registry, actual_hash = load_stable_object(path)
            except ValidationFailure as error:
                self.error(str(error))
                return None
            if (
                registry.get("registry_version") != "1.0.0"
                or actual_hash != LEGACY_CAPABILITY_REGISTRY_SHA256
            ):
                self.error("legacy frozen capability registry 漂移")
                return None
            self.learning_registry = registry
            self.learning_registry_version = "1.0.0"
            self.learning_registry_hash = actual_hash
            return registry
        if not isinstance(extension, dict):
            self.error("workflow learning_extension 缺失 capability registry pin")
            return None
        version = extension.get("capability_registry_version")
        expected_hash = extension.get("capability_registry_sha256")
        if not isinstance(version, str) or not is_hash(expected_hash):
            self.error("workflow capability registry pin 非法")
            return None
        path = CAPABILITY_REGISTRIES_ROOT / f"{version}.json"
        try:
            registry, actual_hash = load_stable_object(path)
        except ValidationFailure as error:
            self.error(str(error))
            return None
        if actual_hash != expected_hash or registry.get("registry_version") != version:
            self.error("frozen capability registry 与 workflow pin 不一致")
            return None
        self.learning_registry = registry
        self.learning_registry_version = version
        self.learning_registry_hash = actual_hash
        return registry

    def validate_nested_learning_ref(
        self, reference: Any, context: str
    ) -> Path | None:
        if not isinstance(reference, dict):
            self.error(f"{context} 必须是包含 path/sha256 的证据对象")
            return None
        path_value = reference.get("path")
        path = self.learning_path(path_value, f"{context}.path")
        declared_hash = reference.get("sha256")
        if not is_hash(declared_hash):
            self.error(f"{context}.sha256 必须是 SHA-256")
        if path is None:
            return None
        if not path.is_file() or path.stat().st_size == 0:
            self.error(f"{context} 指向的 evidence 不存在或为空：{path_value}")
            return path
        try:
            content = self.learning_file_bytes.setdefault(
                path, read_stable_file_bytes(path)
            )
        except (FileNotFoundError, OSError, ValueError) as error:
            self.error(f"{context} 无法稳定读取：{error}")
            return path
        if is_hash(declared_hash) and hashlib.sha256(content).hexdigest() != declared_hash:
            self.error(f"{context} evidence hash 不一致")
        return path

    def validate_learning_refs(self, value: Any, context: str) -> list[Path]:
        if not isinstance(value, list):
            self.error(f"{context} 必须是 evidence descriptor 数组")
            return []
        paths: list[Path] = []
        seen: set[str] = set()
        for index, item in enumerate(value):
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                if item["path"] in seen:
                    self.error(f"{context} 不得重复引用 {item['path']!r}")
                seen.add(item["path"])
            path = self.validate_nested_learning_ref(item, f"{context}[{index}]")
            if path is not None:
                paths.append(path)
        return paths

    def validate_learning_bindings(self, value: Any, context: str) -> None:
        if not isinstance(value, dict):
            self.error(f"{context}.bindings 必须是对象")
            return
        source = self.run.get("source")
        expected_media = source.get("media_sha256") if isinstance(source, dict) else None
        if value.get("source_media_sha256") != expected_media:
            self.error(f"{context}.bindings source hash 与当前 run 不一致")
        artifacts = self.run.get("artifacts")
        for stage in ("build", "review_r1", "review_r2", "finalize"):
            descriptor = artifacts.get(stage) if isinstance(artifacts, dict) else None
            actual = value.get(stage)
            if not isinstance(descriptor, dict):
                # 核心校验已报告该问题；这里仍保持学习错误不绑定核心失效阶段。
                continue
            expected = {
                "path": descriptor.get("path"),
                "sha256": descriptor.get("sha256"),
            }
            if actual != expected:
                self.error(f"{context}.bindings 未绑定当前 {stage} descriptor")

    def validate_runtime_capabilities_deep(self) -> None:
        value = self.learning_contents.get("runtime-capabilities.json")
        if not isinstance(value, dict):
            return
        capabilities = value.get("capabilities")
        if not isinstance(capabilities, dict):
            self.error("runtime-capabilities.capabilities 必须是对象")
            return
        registry_payload = self.load_pinned_capability_registry()
        if not isinstance(registry_payload, dict):
            return
        policy = registry_payload.get("policy")
        default_mode = policy.get("default_candidate_mode") if isinstance(policy, dict) else None
        registry = {
            item.get("id"): {
                "mode": item.get("candidate_mode", default_mode),
                "candidates": sorted(
                    item.get("candidates", []), key=lambda candidate: candidate.get("priority", 0)
                ),
            }
            for item in registry_payload.get("capabilities", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if (
            value.get("registry_version") != self.learning_registry_version
            or value.get("registry_sha256") != self.learning_registry_hash
        ):
            self.error("runtime-capabilities registry pin 与 workflow 不一致")
        for capability_id, item in capabilities.items():
            context = f"runtime-capabilities.capabilities[{capability_id!r}]"
            if capability_id not in registry or not isinstance(item, dict):
                self.error(f"{context} 不在 capability registry 或不是对象")
                continue
            registry_entry = registry[capability_id]
            candidates = registry_entry["candidates"]
            candidate_ids = [candidate.get("id") for candidate in candidates]
            probes = item.get("probes")
            if not isinstance(probes, list) or not probes:
                self.error(f"{context}.probes 必须是非空数组")
                continue
            probe_ids: list[Any] = []
            for index, probe in enumerate(probes):
                probe_context = f"{context}.probes[{index}]"
                if not isinstance(probe, dict):
                    self.error(f"{probe_context} 必须是对象")
                    continue
                probe_ids.append(probe.get("candidate_id"))
                if probe.get("candidate_id") not in candidate_ids:
                    self.error(f"{probe_context}.candidate_id 不在 registry")
                if probe.get("result") not in {"passed", "degraded", "failed", "missing"}:
                    self.error(f"{probe_context}.result 非法")
                if not self.validate_learning_refs(
                    probe.get("evidence_refs"), f"{probe_context}.evidence_refs"
                ):
                    self.error(f"{probe_context} 缺少真实 evidence")
            mode = registry_entry["mode"]
            if item.get("candidate_mode") != mode:
                self.error(f"{context}.candidate_mode 与 registry 不一致")
            passed = [
                probe.get("candidate_id")
                for probe in probes
                if isinstance(probe, dict) and probe.get("result") == "passed"
            ]
            if mode == "all":
                if probe_ids != candidate_ids:
                    self.error(f"{context} all 模式必须覆盖全部候选")
                if len(passed) == len(candidate_ids):
                    expected = ("available", passed, None)
                elif passed or any(
                    isinstance(probe, dict) and probe.get("result") == "degraded"
                    for probe in probes
                ):
                    expected = ("degraded", passed, candidates[-1].get("fallback"))
                else:
                    expected = ("missing", [], candidates[-1].get("fallback"))
            else:
                if probe_ids != candidate_ids[: len(probe_ids)]:
                    self.error(f"{context} ordered_fallback 必须是有序前缀")
                passed_probe = next(
                    (probe for probe in probes if isinstance(probe, dict) and probe.get("result") == "passed"),
                    None,
                )
                if passed_probe is not None:
                    expected = ("available", passed_probe.get("candidate_id"), None)
                else:
                    degraded = next(
                        (probe for probe in probes if isinstance(probe, dict) and probe.get("result") == "degraded"),
                        None,
                    )
                    if degraded is not None:
                        selected = degraded.get("candidate_id")
                        fallback = next(
                            candidate.get("fallback")
                            for candidate in candidates
                            if candidate.get("id") == selected
                        )
                        expected = ("degraded", selected, fallback)
                    else:
                        if len(probes) != len(candidates):
                            self.error(
                                f"{context} ordered_fallback missing requires all candidates probed"
                            )
                        expected = ("missing", None, candidates[len(probes) - 1].get("fallback"))
            if (item.get("status"), item.get("selected"), item.get("fallback")) != expected:
                self.error(f"{context} status/selected/fallback 与 probes 不一致")
            if not valid_rfc3339(item.get("checked_at")):
                self.error(f"{context}.checked_at 不是带时区 RFC3339")

    def validate_decision_trace_deep(self, completed_all: bool) -> None:
        value = self.learning_contents.get("decision-trace.json")
        if not isinstance(value, dict):
            return
        decisions = value.get("decisions")
        if not isinstance(decisions, list):
            self.error("decision-trace.decisions 必须是数组")
            return
        matrix = self.learning_capability_matrix()
        seen: set[str] = set()
        decision_stages: set[str] = set()
        required = {
            "decision_id",
            "stage",
            "observation",
            "evidence_refs",
            "decision",
            "action",
            "validation",
            "error",
            "root_cause",
            "next_rule",
            "recorded_at",
        }
        for index, item in enumerate(decisions):
            context = f"decision-trace.decisions[{index}]"
            if not isinstance(item, dict):
                self.error(f"{context} 必须是对象")
                continue
            missing = sorted(required - item.keys())
            if missing:
                self.error(f"{context} 事实链缺少：{', '.join(missing)}")
            decision_id = item.get("decision_id")
            if not isinstance(decision_id, str) or decision_id in seen:
                self.error(f"{context}.decision_id 非法或重复")
            else:
                seen.add(decision_id)
            stage = item.get("stage")
            if stage not in matrix:
                self.error(f"{context}.stage 不在 workflow")
            elif isinstance(stage, str):
                decision_stages.add(stage)
            refs = self.validate_learning_refs(
                item.get("evidence_refs"), f"{context}.evidence_refs"
            )
            for field in ("observation", "decision", "action", "validation", "next_rule"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    self.error(f"{context}.{field} 必须是非空字符串")
            for field in ("error", "root_cause"):
                field_value = item.get(field)
                if field_value is not None and (
                    not isinstance(field_value, str) or not field_value.strip()
                ):
                    self.error(f"{context}.{field} 只能是 null 或非空字符串")
            if item.get("root_cause") is not None and not refs:
                self.error(f"{context} 无 evidence 的 root_cause 必须为 null")
            if not valid_rfc3339(item.get("recorded_at")):
                self.error(f"{context}.recorded_at 不是带时区 RFC3339")
            core_stages: tuple[str, ...] = ()
            if stage in {"transcript", "learn_method"}:
                core_stages = ("transcript", "learn_method")
            elif stage == "plan_demo":
                core_stages = ("learn_method", "observe_motion", "plan_demo")
            elif stage == "revise":
                core_stages = ("review_r1",)
            artifacts = self.run.get("artifacts")
            allowed = {
                (descriptor.get("path"), descriptor.get("sha256"))
                for core_stage in core_stages
                for descriptor in [
                    artifacts.get(core_stage) if isinstance(artifacts, dict) else None
                ]
                if isinstance(descriptor, dict)
            }
            raw_refs = item.get("evidence_refs")
            actual = {
                (reference.get("path"), reference.get("sha256"))
                for reference in (raw_refs if isinstance(raw_refs, list) else [])
                if isinstance(reference, dict)
            }
            if core_stages and not (allowed & actual):
                self.error(f"{context} evidence 未绑定合理 core artifact")
        ordered = sorted(
            (
                item
                for item in decisions
                if isinstance(item, dict)
            ),
            key=lambda item: (
                STAGES.index(item.get("stage")) if item.get("stage") in STAGES else len(STAGES),
                str(item.get("recorded_at")),
                str(item.get("decision_id")),
            ),
        )
        if ordered != decisions:
            self.error("decision-trace.decisions 必须按 stage/time/id 稳定排序")
        if completed_all:
            missing_points: list[str] = []
            if not ({"transcript", "learn_method"} & decision_stages):
                missing_points.append("extraction")
            if "plan_demo" not in decision_stages:
                missing_points.append("plan_demo")
            if "revise" not in decision_stages:
                missing_points.append("R1-to-revise")
            if missing_points:
                self.error(
                    "decision trace 缺少审计判断点：" + ", ".join(missing_points)
                )

    def validate_usage_event_deep(
        self,
        relative: str,
        value: dict[str, Any],
        matrix: dict[str, set[str]],
    ) -> None:
        context = f"usage event {relative}"
        event_id = value.get("event_id")
        if not isinstance(event_id, str) or relative != f"usage-events/{event_id}.json":
            self.error(f"{context}.event_id 与文件名不一致")
        stage = value.get("stage")
        capability_id = value.get("capability_id")
        if stage not in matrix or capability_id not in matrix.get(stage, set()):
            self.error(f"{context} stage/capability 不适用于当前 workflow")
        if stage not in self.completed:
            self.error(f"{context}.stage 尚未完成")
        refs = self.validate_learning_refs(
            value.get("evidence_refs"), f"{context}.evidence_refs"
        )
        capture_state = value.get("capture_state")
        result = value.get("result")
        if value.get("kind") not in {"content", "skill", "tool"}:
            self.error(f"{context}.kind 非法")
        if capture_state not in {"captured", "missing", "degraded", "not_recorded"}:
            self.error(f"{context}.capture_state 非法")
        if result not in {"passed", "degraded", "failed", "not_recorded"}:
            self.error(f"{context}.result 非法")
        for field in ("actual_id", "purpose"):
            if not isinstance(value.get(field), str) or not value[field].strip():
                self.error(f"{context}.{field} 必须是非空字符串")
        if capture_state != "captured" and result == "passed":
            self.error(f"{context} coverage event 不能声明 passed")
        if capture_state == "captured" and result == "not_recorded":
            self.error(f"{context} captured 不能声明 not_recorded")
        if result == "passed" and not refs:
            self.error(f"{context} passed 缺少真实 evidence")
        kind = value.get("kind")
        if kind == "content":
            content_ref = value.get("content_ref")
            content_path = self.learning_path(content_ref, f"{context}.content_ref")
            if content_path is None or not content_path.is_file():
                self.error(f"{context}.content_ref 不存在")
            elif value.get("content_sha256") != stable_file_hash(content_path):
                self.error(f"{context}.content_sha256 与真实内容不一致")
            if value.get("execution_receipt") is not None:
                self.error(f"{context} content 禁止 execution_receipt")
        elif kind in {"skill", "tool"}:
            if "version" not in value or "execution_receipt" not in value:
                self.error(f"{context} 缺少显式 version/execution_receipt")
            registry_payload = self.load_pinned_capability_registry()
            registry_entries = (
                registry_payload.get("capabilities", [])
                if isinstance(registry_payload, dict)
                else []
            )
            candidates = {
                candidate.get("id")
                for entry in registry_entries
                if isinstance(entry, dict) and entry.get("id") == capability_id
                for candidate in entry.get("candidates", [])
                if isinstance(candidate, dict)
            }
            historical_unknown = (
                self.workflow_version == "1.0.0"
                and value.get("actual_id") == "unknown_historical_usage"
                and capture_state == "not_recorded"
                and result == "not_recorded"
            )
            if value.get("actual_id") not in candidates and not historical_unknown:
                self.error(f"{context}.actual_id 不在 capability registry")
            version = value.get("version")
            if version is None and not (
                result == "not_recorded"
                or capture_state in {"missing", "not_recorded"}
            ):
                self.error(f"{context}.version 仅可在 not_recorded/missing 时为 null")
            elif version is not None and (
                not isinstance(version, str) or not version.strip()
            ):
                self.error(f"{context}.version 必须是非空字符串或 null")
            receipt = value.get("execution_receipt")
            if capture_state == "captured" and receipt is None:
                self.error(f"{context} captured skill/tool 缺少 execution receipt")
            if receipt is not None:
                self.validate_execution_receipt_deep(
                    receipt, result, f"{context}.execution_receipt"
                )
        if not valid_rfc3339(value.get("recorded_at")):
            self.error(f"{context}.recorded_at 不是带时区 RFC3339")

    def validate_execution_receipt_deep(
        self, reference: Any, result: Any, context: str
    ) -> None:
        path = self.validate_nested_learning_ref(reference, context)
        if path is None or not path.is_file():
            return
        try:
            content = self.learning_file_bytes.get(path)
            if content is None:
                content = read_stable_file_bytes(path)
                self.learning_file_bytes[path] = content
            receipt = json.loads(content.decode("utf-8"))
            if not isinstance(receipt, dict):
                raise ValidationFailure(f"JSON 顶层必须是对象：{path}")
        except (ValidationFailure, UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as error:
            self.error(f"{context} 不是合法 execution receipt：{error}")
            return
        try:
            reject_private_payload(receipt)
        except (TypeError, ValueError) as error:
            self.error(f"{context} 包含私有或敏感数据：{error}")
        required = {"receipt_type", "command", "exit_code", "executed_at"}
        missing = sorted(required - receipt.keys())
        if missing:
            self.error(f"{context} 缺少：{', '.join(missing)}")
        if receipt.get("receipt_type") != "execution":
            self.error(f"{context}.receipt_type 必须为 execution")
        command = receipt.get("command")
        if not isinstance(command, list) or not command or any(
            not isinstance(item, str) or not item.strip() for item in command
        ):
            self.error(f"{context}.command 必须是非空字符串数组")
        exit_code = receipt.get("exit_code")
        if type(exit_code) is not int:
            self.error(f"{context}.exit_code 必须是非布尔整数")
        if not valid_rfc3339(receipt.get("executed_at")):
            self.error(f"{context}.executed_at 不是带时区 RFC3339")
        if result == "passed" and exit_code != 0:
            self.error(f"{context}.exit_code 必须为 0 才能支撑 passed")
        if result == "failed" and exit_code == 0:
            self.error(f"{context}.exit_code 必须非零才能支撑 failed")
        for optional in ("stdout", "stderr", "target"):
            if optional in receipt:
                self.validate_nested_learning_ref(
                    receipt[optional], f"{context}.{optional}"
                )

    def validate_manifest_deep(
        self,
        value: dict[str, Any],
        events: list[tuple[str, dict[str, Any]]],
        matrix: dict[str, set[str]],
    ) -> None:
        entries = value.get("entries")
        if not isinstance(entries, list):
            self.error("skill usage manifest.entries 必须是数组")
            return
        required = {
            "capability",
            "phase",
            "candidates_checked",
            "selected",
            "source",
            "revision",
            "mode",
            "inputs",
            "outputs",
            "result",
            "evidence_refs",
            "friction",
            "adjustment_candidate",
        }
        registry_payload = self.load_pinned_capability_registry()
        if not isinstance(registry_payload, dict):
            return
        registry = {
            entry.get("id"): {
                candidate.get("id")
                for candidate in entry.get("candidates", [])
                if isinstance(candidate, dict) and isinstance(candidate.get("id"), str)
            }
            for entry in registry_payload.get("capabilities", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        for index, item in enumerate(entries):
            context = f"skill usage manifest.entries[{index}]"
            if not isinstance(item, dict):
                self.error(f"{context} 必须是对象")
                continue
            missing = sorted(required - item.keys())
            if missing:
                self.error(f"{context} 缺少 contract 字段：{', '.join(missing)}")
            phase = item.get("phase")
            capability = item.get("capability")
            if phase not in matrix or capability not in matrix.get(phase, set()):
                self.error(f"{context} phase/capability 不适用于 workflow")
            candidates = item.get("candidates_checked")
            if not isinstance(candidates, list) or any(
                candidate not in registry.get(capability, set())
                for candidate in candidates
            ):
                self.error(f"{context}.candidates_checked 不在 capability registry")
            selected = item.get("selected")
            if selected is not None and selected not in registry.get(capability, set()):
                self.error(f"{context}.selected 不在 capability registry")
            historical_best_effort = (
                self.workflow_version == "1.0.0"
                and item.get("source") == "historical_best_effort"
                and item.get("mode") == "historical_best_effort"
                and item.get("result") == "not_recorded"
                and candidates == []
                and selected is None
            )
            if (
                isinstance(candidates, list)
                and selected not in candidates
                and not historical_best_effort
            ):
                self.error(f"{context}.selected 必须属于 candidates_checked")
            if item.get("result") not in {"passed", "degraded", "failed", "not_recorded"}:
                self.error(f"{context}.result 非法")
            for field in ("source", "mode"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    self.error(f"{context}.{field} 必须是非空字符串")
            refs = self.validate_learning_refs(
                item.get("evidence_refs"), f"{context}.evidence_refs"
            )
            outputs = self.validate_learning_refs(
                item.get("outputs"), f"{context}.outputs"
            )
            matching_events = [
                event
                for _, event in events
                if event.get("stage") == phase
                and event.get("capability_id") == capability
                and event.get("capture_state") == "captured"
                and event.get("result") == "passed"
                and event.get("actual_id") == selected
                and event.get("execution_receipt") is not None
            ]
            matching_receipt = bool(matching_events)
            if item.get("result") == "passed" and not refs:
                self.error(f"{context} passed 缺少 evidence")
            if item.get("result") == "passed" and not matching_receipt:
                self.error(f"{context} passed selected 缺少匹配 captured+passed usage")
            if item.get("result") == "passed" and not outputs:
                self.error(f"{context} passed 缺少真实 output")
            revision = item.get("revision")
            if item.get("result") == "passed" and (
                not isinstance(revision, str)
                or not revision.strip()
                or any(event.get("version") != revision for event in matching_events)
            ):
                self.error(f"{context}.revision 未匹配 usage version")
        passed_usage_keys = {
            (
                event.get("stage"),
                event.get("capability_id"),
                event.get("actual_id"),
                event.get("version"),
            )
            for _, event in events
            if event.get("kind") in {"skill", "tool"}
            and event.get("capture_state") == "captured"
            and event.get("result") == "passed"
        }
        passed_manifest_keys = [
            (
                item.get("phase"),
                item.get("capability"),
                item.get("selected"),
                item.get("revision"),
            )
            for item in entries
            if isinstance(item, dict) and item.get("result") == "passed"
        ]
        try:
            unique_manifest_keys = set(passed_manifest_keys)
        except TypeError:
            unique_manifest_keys = set()
            self.error("passed manifest projection keys 必须是字符串字段")
        if len(passed_manifest_keys) != len(unique_manifest_keys):
            self.error("duplicate passed manifest projection entry")
        if unique_manifest_keys != passed_usage_keys:
            self.error(
                "passed manifest projection must exactly equal captured passed usage keys"
            )
        self.validate_learning_bindings(value.get("bindings"), "skill usage manifest")

    def validate_ledger_deep(
        self,
        value: dict[str, Any],
        events: list[tuple[str, dict[str, Any]]],
        manifest_path: Path | None,
    ) -> None:
        refs = value.get("event_refs")
        if not isinstance(refs, list):
            self.error("usage ledger.event_refs 必须是 descriptor 数组")
            refs = []
        ref_paths: set[str] = set()
        for index, item in enumerate(refs):
            path = self.validate_nested_learning_ref(
                item, f"usage ledger.event_refs[{index}]"
            )
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                ref_paths.add(item["path"])
            if path is not None and path.parent.name != "usage-events":
                self.error("usage ledger.event_refs 只能指向 usage-events")
        event_paths = {relative for relative, _ in events}
        if ref_paths != event_paths:
            self.error("usage ledger.event_refs 与 immutable usage events 不一致")
        manifest = value.get("manifest")
        resolved_manifest = self.validate_nested_learning_ref(
            manifest, "usage ledger.manifest"
        )
        if (
            resolved_manifest is not None
            and manifest_path is not None
            and resolved_manifest != manifest_path
        ):
            self.error("usage ledger.manifest 未绑定 skill usage manifest")
        entries = value.get("entries")
        if not isinstance(entries, dict):
            self.error("usage ledger.entries 必须从实际 events 分组")
        else:
            listed = {
                item.get("event_ref")
                for group in entries.values()
                if isinstance(group, list)
                for item in group
                if isinstance(item, dict)
            }
            if listed != event_paths:
                self.error("usage ledger.entries 与实际 immutable events 不一致")
            expected_entries = {kind: [] for kind in ("content", "skill", "tool")}
            for relative, event in events:
                kind = event.get("kind")
                if kind not in expected_entries:
                    continue
                expected_entries[kind].append(
                    {
                        "event_id": event.get("event_id"),
                        "event_ref": relative,
                        "stage": event.get("stage"),
                        "capability_id": event.get("capability_id"),
                        "actual_id": event.get("actual_id"),
                        "result": event.get("result"),
                        "capture_state": event.get("capture_state"),
                        "evidence_refs": event.get("evidence_refs"),
                    }
                )
            if entries != expected_entries:
                self.error("usage ledger.entries 不是实际 immutable events 的确定性聚合")
        self.validate_learning_bindings(value.get("bindings"), "usage ledger")

    def validate_retrospective_deep(self, value: dict[str, Any]) -> None:
        if not isinstance(value.get("objective"), str) or not value["objective"].strip():
            self.error("retrospective.objective 必须是非空字符串")
        if value.get("result") not in {"success", "success_with_residuals"}:
            self.error("retrospective.result 非法")
        if value.get("skills_manifest_ref") != "skill-usage-manifest.json":
            self.error("retrospective.skills_manifest_ref 非法")
        self.validate_learning_refs(value.get("evidence"), "retrospective.evidence")
        findings = value.get("findings")
        if not isinstance(findings, list):
            self.error("retrospective.findings 必须是数组")
            findings = []
        for index, item in enumerate(findings):
            context = f"retrospective.findings[{index}]"
            if not isinstance(item, dict):
                self.error(f"{context} 必须是对象")
                continue
            refs = self.validate_learning_refs(
                item.get("evidence_refs"), f"{context}.evidence_refs"
            )
            if item.get("type") not in {
                "effective_pattern",
                "failure_root_cause",
                "environment_fact",
                "skill_friction",
            }:
                self.error(f"{context}.type 非法")
            if not isinstance(item.get("claim"), str) or not item["claim"].strip():
                self.error(f"{context}.claim 必须是非空字符串")
            applies_to = item.get("applies_to")
            if not isinstance(applies_to, list) or not applies_to or any(
                not isinstance(scope, str) or not scope.strip() for scope in applies_to
            ):
                self.error(f"{context}.applies_to 必须是非空字符串数组")
            basis = item.get("basis")
            if basis is not None and basis not in {
                "observed",
                "reviewer_feedback",
                "user_instruction",
                "guess",
                "aesthetic_opinion",
                "residual",
            }:
                self.error(f"{context}.basis 非法")
            destination = item.get("destination_candidate")
            if destination not in {
                "reference",
                "local_memory",
                "error_memory",
                "skill_adjustment",
                "backlog",
            }:
                self.error(f"{context}.destination_candidate 非法")
            if item.get("status") != "candidate":
                self.error(f"{context}.status 必须为 candidate")
            if (
                not refs
                or basis in {"guess", "aesthetic_opinion", "residual"}
            ) and destination != "backlog":
                self.error(f"{context} 无证据、猜测、审美或 residual 只能 backlog")
        self.validate_learning_bindings(value.get("bindings"), "retrospective")

    def validate_learning_semantics_deep(self, completed_all: bool) -> None:
        matrix = self.learning_capability_matrix()
        self.validate_runtime_capabilities_deep()
        self.validate_decision_trace_deep(completed_all)
        events = sorted(
            (
                (relative, value)
                for relative, value in self.learning_contents.items()
                if relative.startswith("usage-events/")
            ),
            key=lambda item: item[0],
        )
        for relative, event in events:
            self.validate_usage_event_deep(relative, event, matrix)
        if completed_all:
            required = {
                (stage, capability)
                for stage in self.completed
                for capability in matrix.get(stage, set())
            }
            covered = {
                (event.get("stage"), event.get("capability_id"))
                for _, event in events
                if event.get("capture_state")
                in {"captured", "missing", "degraded", "not_recorded"}
            }
            missing = sorted(required - covered)
            if missing:
                self.error(
                    "learning usage coverage 缺少："
                    + ", ".join(f"{stage}:{capability}" for stage, capability in missing)
                )
        manifest = self.learning_contents.get("skill-usage-manifest.json")
        manifest_path = (
            self.run_dir / "skill-usage-manifest.json"
            if isinstance(manifest, dict)
            else None
        )
        if isinstance(manifest, dict):
            self.validate_manifest_deep(manifest, events, matrix)
        ledger = self.learning_contents.get("usage-ledger.json")
        if isinstance(ledger, dict):
            self.validate_ledger_deep(ledger, events, manifest_path)
        retrospective = self.learning_contents.get("retrospective.json")
        if isinstance(retrospective, dict):
            self.validate_retrospective_deep(retrospective)

    def validate_learning_extension(self, completed: list[str]) -> None:
        if self.core_only:
            return

        extensions = self.run.get("extensions")
        extension = (
            extensions.get("learning_loop") if isinstance(extensions, dict) else None
        )
        workflow_extension = self.workflow.get("learning_extension")
        workflow_requires = (
            isinstance(workflow_extension, dict)
            and workflow_extension.get("required") is True
        )

        # legacy 1.0 默认保持原样；只有显式 require 或已有 extension 才进入校验。
        if extension is None and not workflow_requires and not self.require_learning_memory:
            return
        if extension is None:
            self.error("run.extensions.learning_loop 缺失")
            return
        if not isinstance(extension, dict):
            self.error("run.extensions.learning_loop 必须是对象")
            return

        required_fields = {"required", "state", "contract_version", "selection", "sidecars"}
        missing = sorted(required_fields - extension.keys())
        if missing:
            self.error(
                "run.extensions.learning_loop 缺少字段：" + ", ".join(missing)
            )
        if extension.get("required") is not True:
            self.error("run.extensions.learning_loop.required 必须为 true")

        contract_version = extension.get("contract_version")
        contract_spec = (
            SUPPORTED_LEARNING_CONTRACTS.get(contract_version)
            if isinstance(contract_version, str)
            else None
        )
        if not isinstance(contract_spec, dict):
            self.error(f"learning_loop contract_version 不受支持：{contract_version!r}")
            contract = None
            contract_path = None
            pinned_contract_hash = None
        else:
            contract_path = contract_spec.get("path")
            pinned_contract_hash = contract_spec.get("sha256")
            if not isinstance(contract_path, Path) or not is_hash(pinned_contract_hash):
                self.error("learning contract resolver 配置非法")
                contract = None
                contract_path = None
            else:
                contract, actual_contract_hash = load_stable_object(contract_path)
                if actual_contract_hash != pinned_contract_hash:
                    self.error("learning contract 实际 hash 与固定 allowlist 不一致")
        if isinstance(contract, dict):
            if contract.get("contract_version") != contract_version:
                self.error("learning contract 文件版本与 extension 不一致")

        if isinstance(workflow_extension, dict):
            allowlist = workflow_extension.get("contract_allowlist")
            if not isinstance(allowlist, list) or contract_version not in allowlist:
                self.error("learning_loop contract_version 不在 workflow allowlist")
            expected_contract_hash = workflow_extension.get("contract_sha256")
            if pinned_contract_hash is not None and (
                not is_hash(expected_contract_hash)
                or expected_contract_hash != pinned_contract_hash
            ):
                self.error("learning contract 实际 hash 与 workflow pin 不一致")
            if workflow_extension.get("contract_version") != contract_version:
                self.error("workflow learning contract version 与 run extension 不一致")

        states = (
            contract.get("extension", {}).get("state_enum")
            if isinstance(contract, dict)
            else None
        )
        state = extension.get("state")
        if not isinstance(states, list) or state not in states:
            self.error(f"run.extensions.learning_loop.state 非法：{state!r}")

        selection = extension.get("selection")
        selection_required = "preflight" in completed
        if selection is None:
            if selection_required:
                self.error("preflight 完成后 learning_loop.selection 必须存在")
        else:
            expected_selection = (
                workflow_extension.get("selection", {}).get("path")
                if isinstance(workflow_extension, dict)
                else "memory-selection.json"
            )
            selection_path = self.validate_learning_descriptor(
                selection,
                "run.extensions.learning_loop.selection",
                expected_path=expected_selection,
            )
            if isinstance(contract, dict):
                required_artifacts = contract.get("artifacts", {}).get("required", {})
                required_fields = (
                    required_artifacts.get(expected_selection)
                    if isinstance(required_artifacts, dict)
                    else None
                )
                self.validate_learning_json(
                    selection_path,
                    "selection",
                    required_fields,
                    contract,
                    "run.extensions.learning_loop.selection",
                )

        sidecars = extension.get("sidecars")
        if not isinstance(sidecars, dict):
            self.error("run.extensions.learning_loop.sidecars 必须是对象")
            return
        recognized_usage_events: list[str] = []
        for key, descriptor in sidecars.items():
            if not isinstance(key, str) or not key:
                self.error("learning_loop.sidecars key 必须是非空相对路径")
                continue
            membership = (
                self.classify_learning_sidecar(key, contract)
                if isinstance(contract, dict)
                else None
            )
            if membership is None:
                self.error(f"learning_loop.sidecars 不允许该 sidecar：{key!r}")
            sidecar_path = self.validate_learning_descriptor(
                descriptor,
                f"run.extensions.learning_loop.sidecars[{key!r}]",
                expected_path=key,
            )
            if membership is None or not isinstance(contract, dict):
                continue
            kind, artifact_required_fields = membership
            if kind == "usage_event":
                recognized_usage_events.append(key)
            if kind == "post_run" and state not in {"frozen", "backfilled"}:
                self.error(
                    "post-run sidecar 只允许 learning_loop.state 为 frozen/backfilled"
                )
            self.validate_learning_json(
                sidecar_path,
                kind,
                artifact_required_fields,
                contract,
                f"run.extensions.learning_loop.sidecars[{key!r}]",
            )

        usage_directory = self.run_dir / "usage-events"
        actual_usage_events: set[str] = set()
        if usage_directory.exists():
            if usage_directory.is_symlink() or not usage_directory.is_dir():
                self.error("usage-events 必须是无 symlink 的普通目录")
            else:
                for path in usage_directory.iterdir():
                    if path.is_symlink() or not path.is_file():
                        self.error("usage-events 只允许单层普通 JSON 文件")
                    elif path.suffix == ".json" and path.stem:
                        actual_usage_events.add(f"usage-events/{path.name}")
        descriptor_usage_events = set(recognized_usage_events)
        if actual_usage_events != descriptor_usage_events:
            self.error(
                "usage-events 与 descriptors 必须 exact-set；"
                f"orphan={sorted(actual_usage_events - descriptor_usage_events)} "
                f"dangling={sorted(descriptor_usage_events - actual_usage_events)}"
            )

        completed_all = completed == STAGES
        if not completed_all:
            if self.workflow_version == "1.0.0":
                self.error("legacy 1.0 learning extension/backfill 只允许核心阶段全部完成后存在")
            if self.workflow_version == "1.1.0" and state != "collecting":
                self.error("workflow 1.1 未完成时 learning_loop.state 必须是 collecting")
            return

        expected_terminal_state = (
            "frozen" if self.workflow_version == "1.1.0" else "backfilled"
        )
        if state != expected_terminal_state:
            self.error(
                "核心阶段完成后 learning_loop.state 必须是 "
                f"{expected_terminal_state}"
            )

        required_sidecars = (
            workflow_extension.get("required_sidecars", [])
            if isinstance(workflow_extension, dict)
            else [
                {"path": "runtime-capabilities.json"},
                {"path": "decision-trace.json"},
                {"path": "skill-usage-manifest.json"},
                {"path": "usage-ledger.json"},
                {"path": "retrospective.json"},
            ]
        )
        required_paths = {
            item.get("path")
            for item in required_sidecars
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        for path_value in sorted(required_paths):
            if path_value not in sidecars:
                self.error(f"完成态 learning_loop.sidecars 缺少 {path_value}")

        if not recognized_usage_events:
            self.error("完成态 learning_loop.sidecars 缺少 usage-events/*.json coverage")
        self.validate_learning_semantics_deep(completed_all)

    def validate(self) -> dict[str, Any]:
        completed = self.validate_state()
        self.completed = set(completed)
        self.validate_source_truth(completed)
        self.validate_bindings(completed)
        artifacts = self.run.get("artifacts")
        if not isinstance(artifacts, dict):
            self.error("run.artifacts 必须是对象", "preflight")
            artifacts = {}
        previous_stage = None
        previous_hash = None
        for stage in completed:
            previous_hash = self.validate_descriptor(
                stage, artifacts.get(stage), previous_stage, previous_hash
            )
            previous_stage = stage
        self.cross_validate_rounds(completed)
        self.validate_learning_extension(completed)

        invalidated_from = (
            STAGES[self.invalid_index] if self.invalid_index is not None else None
        )
        invalidated_stages = (
            STAGES[self.invalid_index :] if self.invalid_index is not None else []
        )
        return {
            "ok": not self.errors,
            "run_id": self.run_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "invalidated_from": invalidated_from,
            "invalidated_stages": invalidated_stages,
        }

    def apply_invalidation(self) -> None:
        if self.invalid_index is None:
            return
        self.run["completed_stages"] = STAGES[: self.invalid_index]
        self.run["current_stage"] = STAGES[self.invalid_index]
        self.run["next_stage"] = (
            STAGES[self.invalid_index + 1]
            if self.invalid_index + 1 < len(STAGES)
            else None
        )
        self.run["invalidated_stages"] = STAGES[self.invalid_index :]
        self.run["status"] = "running"
        atomic_write_json(self.run_path, self.run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验教程学习 run 的状态、artifact 语义、hash 链和最终 MP4。"
    )
    parser.add_argument("--repo", required=True, help="目标仓库根目录")
    parser.add_argument("--run-id", required=True, help="run ID")
    parser.add_argument(
        "--ffprobe",
        choices=("auto", "on", "off"),
        default="auto",
        help="auto=可用时校验；on=必须校验；off=跳过",
    )
    parser.add_argument(
        "--apply-invalidation",
        action="store_true",
        help="把首个失效阶段及下游写回 run.json",
    )
    learning_mode = parser.add_mutually_exclusive_group()
    learning_mode.add_argument(
        "--core-only",
        action="store_true",
        help="只校验原 12 阶段、final 与 ffprobe，跳过 learning sidecar",
    )
    learning_mode.add_argument(
        "--require-learning-memory",
        action="store_true",
        help="legacy run 也必须具备并通过 learning extension",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).expanduser().resolve()
    try:
        validator = Validator(
            repo,
            args.run_id,
            args.ffprobe,
            core_only=args.core_only,
            require_learning_memory=args.require_learning_memory,
        )
        result = validator.validate()
        if args.apply_invalidation and result["invalidated_from"] is not None:
            validator.apply_invalidation()
            result["invalidation_applied"] = True
        else:
            result["invalidation_applied"] = False
    except (ValidationFailure, OSError) as error:
        result = {
            "ok": False,
            "run_id": args.run_id,
            "errors": [str(error)],
            "warnings": [],
            "invalidated_from": None,
            "invalidated_stages": [],
            "invalidation_applied": False,
        }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        if result["ok"]:
            print(f"run {args.run_id} 校验通过")
        else:
            for message in result["errors"]:
                print(f"错误：{message}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
