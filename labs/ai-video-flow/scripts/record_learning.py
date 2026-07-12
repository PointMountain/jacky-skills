#!/usr/bin/env python3
"""记录并冻结可由当前 run 证实的学习事实。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
import unicodedata

from learning_common import (
    atomic_write_json,
    canonical_json_bytes,
    ensure_secure_existing_directory,
    read_stable_file_bytes,
    reject_private_payload,
    secure_run_relative,
    secure_unlink_file,
    write_immutable_or_adopt,
)


SCHEMA_VERSION = "1.0.0"
WORKFLOW_VERSION = "1.1.0"
CONTRACT_VERSION = "1.0.0"
SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = SKILL_ROOT / "references" / "workflows" / "1.1.0.json"
LEGACY_WORKFLOW_PATH = SKILL_ROOT / "references" / "workflows" / "1.0.0.json"
LEGACY_CAPABILITY_REGISTRY_SHA256 = (
    "6540068ddf9971dcb5815ee3ce7561d78c0a2eb450f414391ffa4bf9289f2583"
)
CAPABILITIES_PATH = SKILL_ROOT / "references" / "capabilities.json"
CAPABILITY_REGISTRIES_ROOT = SKILL_ROOT / "references" / "capability-registries"
LEARNING_CONTRACTS_ROOT = SKILL_ROOT / "references" / "learning-contracts"
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
USAGE_KINDS = {"content", "skill", "tool"}
CAPTURE_STATES = {"captured", "missing", "degraded", "not_recorded"}
RESULTS = {"passed", "degraded", "failed", "not_recorded"}
CAPABILITY_STATUSES = {"available", "degraded", "missing"}
FINDING_TYPES = {
    "effective_pattern",
    "failure_root_cause",
    "environment_fact",
    "skill_friction",
}
DESTINATIONS = {
    "reference",
    "local_memory",
    "error_memory",
    "skill_adjustment",
    "backlog",
}
RETROSPECTIVE_RESULTS = {"success", "success_with_residuals"}
FAULT_ENV = "AI_VIDEO_FLOW_LEARNING_FAULT"
PROBE_RESULTS = {"passed", "degraded", "failed", "missing"}
BASIS_VALUES = {
    "observed",
    "reviewer_feedback",
    "user_instruction",
    "guess",
    "aesthetic_opinion",
    "residual",
}
MEMORY_STATUSES = {"active", "superseded", "archived"}
LOCAL_MEMORY_DESTINATIONS = {"local_memory", "error_memory"}
SHARED_CANDIDATE_DESTINATIONS = {"reference", "skill_adjustment"}


class LearningError(ValueError):
    """输入或 run 不满足学习事实契约。"""


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(read_stable_file_bytes(path).decode("utf-8"))
    except FileNotFoundError as error:
        raise LearningError(f"{label} 不存在：{path}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LearningError(f"{label} 不是合法 JSON：{error}") from error
    if not isinstance(value, dict):
        raise LearningError(f"{label} 顶层必须是对象")
    return value


def load_stable_object(path: Path, label: str) -> tuple[dict[str, Any], str]:
    try:
        content = read_stable_file_bytes(path)
        value = json.loads(content.decode("utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LearningError(f"{label} 不是稳定合法 JSON：{error}") from error
    if not isinstance(value, dict):
        raise LearningError(f"{label} 顶层必须是对象")
    return value, hashlib.sha256(content).hexdigest()


def stable_sha256(path: Path) -> str:
    return hashlib.sha256(read_stable_file_bytes(path)).hexdigest()


def validate_identifier(value: str, label: str) -> None:
    if not IDENTIFIER_RE.fullmatch(value) or value in {".", ".."}:
        raise LearningError(f"{label} 不安全")


def normalize_rfc3339(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
        raise LearningError(f"{label} 必须是带时区的 RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as error:
        raise LearningError(f"{label} 必须是带时区的 RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LearningError(f"{label} 必须是带时区的 RFC3339")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@contextmanager
def repository_lock(repo: Path):
    lock_path = repo / ".learning.lock"
    if lock_path.is_symlink():
        raise LearningError(".learning.lock 不能是 symlink")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        raise LearningError(f"无法安全打开 .learning.lock：{error}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise LearningError(".learning.lock 必须是普通文件")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def resolve_context(repo_value: str, run_id: str) -> tuple[Path, Path, Path, dict[str, Any]]:
    validate_identifier(run_id, "run-id")
    repo = Path(repo_value).expanduser().resolve()
    if not repo.is_dir():
        raise LearningError(f"仓库目录不存在：{repo_value}")
    runs_root = repo / ".learning" / "runs"
    run_dir = runs_root / run_id
    try:
        ensure_secure_existing_directory(runs_root)
        ensure_secure_existing_directory(run_dir)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise LearningError(".learning/runs/run 目录链不存在或包含 symlink") from error
    run_path = secure_run_relative(run_dir, "run.json", must_exist=True)
    run = load_object(run_path, "run.json")
    if run.get("run_id") != run_id:
        raise LearningError("run.json 的 run_id 与目录不一致")
    if run.get("workflow_version") != WORKFLOW_VERSION:
        raise LearningError("运行事实记录只支持 workflow 1.1.0")
    workflow, workflow_hash = load_stable_object(WORKFLOW_PATH, "workflow 1.1.0")
    if run.get("workflow_sha256") != workflow_hash:
        raise LearningError("run.workflow_sha256 与稳定 workflow 字节不一致")
    extension = learning_extension(run)
    if extension.get("contract_version") != CONTRACT_VERSION:
        raise LearningError("learning contract version 不受支持")
    workflow_extension = workflow.get("learning_extension")
    if not isinstance(workflow_extension, dict):
        raise LearningError("workflow learning_extension 缺失")
    contract, contract_hash = load_stable_object(
        LEARNING_CONTRACTS_ROOT / f"{CONTRACT_VERSION}.json",
        "frozen learning contract",
    )
    if (
        contract.get("contract_version") != CONTRACT_VERSION
        or workflow_extension.get("contract_sha256") != contract_hash
    ):
        raise LearningError("frozen learning contract 与 workflow pin 不一致")
    pinned_capability_registry()
    return repo, run_dir, run_path, run


def learning_extension(run: dict[str, Any]) -> dict[str, Any]:
    extensions = run.get("extensions")
    extension = extensions.get("learning_loop") if isinstance(extensions, dict) else None
    if not isinstance(extension, dict):
        raise LearningError("run.extensions.learning_loop 缺失")
    if extension.get("required") is not True or not isinstance(
        extension.get("sidecars"), dict
    ):
        raise LearningError("run.extensions.learning_loop 结构非法")
    return extension


def require_collecting(run: dict[str, Any]) -> dict[str, Any]:
    extension = learning_extension(run)
    if extension.get("state") != "collecting":
        raise LearningError("学习事实只能在 collecting 状态记录")
    return extension


def read_draft(run_dir: Path, relative: str, label: str) -> dict[str, Any]:
    path = secure_run_relative(run_dir, relative, must_exist=True)
    if path.is_symlink() or not path.is_file():
        raise LearningError(f"{label} 必须是 run 内普通 JSON 文件")
    payload = load_object(path, label)
    reject_private_payload(payload)
    return payload


def require_string(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LearningError(f"{label} 必须是非空字符串")
    return value


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise LearningError(f"{label} 必须是字符串数组")
    return value


def descriptor(run_dir: Path, relative: str, label: str) -> dict[str, str]:
    path = secure_run_relative(run_dir, relative, must_exist=True)
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise LearningError(f"{label} 指向的证据不存在或为空：{relative}")
    content = read_stable_file_bytes(path)
    if not content:
        raise LearningError(f"{label} 指向的证据为空：{relative}")
    return {"path": relative, "sha256": hashlib.sha256(content).hexdigest()}


def evidence_descriptors(
    run_dir: Path, value: Any, label: str
) -> list[dict[str, str]]:
    refs = require_string_list(value, label)
    if len(refs) != len(set(refs)):
        raise LearningError(f"{label} 不得重复")
    return [descriptor(run_dir, ref, f"{label}[{index}]") for index, ref in enumerate(refs)]


def load_workflow() -> dict[str, Any]:
    workflow, _ = load_stable_object(WORKFLOW_PATH, "workflow 1.1.0")
    return workflow


def pinned_capability_registry() -> tuple[dict[str, Any], str, str]:
    workflow = load_workflow()
    extension = workflow.get("learning_extension")
    if not isinstance(extension, dict):
        raise LearningError("workflow 缺少 learning_extension")
    version = extension.get("capability_registry_version")
    expected_hash = extension.get("capability_registry_sha256")
    if not isinstance(version, str) or not HASH_RE.fullmatch(str(expected_hash)):
        raise LearningError("workflow capability registry pin 非法")
    path = CAPABILITY_REGISTRIES_ROOT / f"{version}.json"
    registry, actual_hash = load_stable_object(path, "frozen capability registry")
    if actual_hash != expected_hash or registry.get("registry_version") != version:
        raise LearningError("frozen capability registry 与 workflow pin 不一致")
    return registry, version, actual_hash


def capability_registry_details() -> dict[str, dict[str, Any]]:
    registry, _, _ = pinned_capability_registry()
    policy = registry.get("policy")
    default_mode = (
        policy.get("default_candidate_mode") if isinstance(policy, dict) else None
    )
    output: dict[str, dict[str, Any]] = {}
    for entry in registry.get("capabilities", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise LearningError("capabilities registry 结构非法")
        candidates = entry.get("candidates")
        if not isinstance(candidates, list):
            raise LearningError("capabilities registry candidates 非法")
        normalized_candidates = sorted(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, dict)
                and isinstance(candidate.get("id"), str)
                and isinstance(candidate.get("priority"), int)
            ),
            key=lambda candidate: candidate["priority"],
        )
        if len(normalized_candidates) != len(candidates):
            raise LearningError("capabilities registry candidate 结构非法")
        output[entry["id"]] = {
            "candidate_mode": entry.get("candidate_mode", default_mode),
            "candidates": normalized_candidates,
        }
    return output


def capability_registry() -> dict[str, set[str]]:
    return {
        capability_id: {item["id"] for item in entry["candidates"]}
        for capability_id, entry in capability_registry_details().items()
    }


def stage_index(stage: str) -> int:
    stages = [item["id"] for item in load_workflow().get("stages", [])]
    try:
        return stages.index(stage)
    except ValueError:
        return len(stages)


def applicable_capabilities(run: dict[str, Any]) -> dict[str, set[str]]:
    source = run.get("source")
    source_kind = source.get("kind") if isinstance(source, dict) else None
    matrix: dict[str, set[str]] = {}
    for stage in load_workflow().get("stages", []):
        if not isinstance(stage, dict) or not isinstance(stage.get("id"), str):
            raise LearningError("workflow stages 结构非法")
        values = set(require_string_list(stage.get("capability_ids"), "workflow capability_ids"))
        conditional = stage.get("conditional_capabilities", [])
        if not isinstance(conditional, list):
            raise LearningError("workflow conditional_capabilities 非法")
        for item in conditional:
            if not isinstance(item, dict):
                raise LearningError("workflow conditional capability 非法")
            condition = item.get("when")
            capability_id = item.get("capability_id")
            if condition == "source.kind == 'url'" and source_kind == "url":
                values.add(require_string(capability_id, "conditional capability_id"))
        matrix[stage["id"]] = values
    return matrix


def ensure_stage_capability(
    run: dict[str, Any],
    stage: Any,
    capability_id: Any,
    *,
    require_completed: bool,
) -> tuple[str, str]:
    stage_value = require_string(stage, "stage")
    capability_value = require_string(capability_id, "capability_id")
    matrix = applicable_capabilities(run)
    if stage_value not in matrix:
        raise LearningError(f"stage 不在 workflow：{stage_value}")
    completed = run.get("completed_stages")
    is_completed = isinstance(completed, list) and stage_value in completed
    is_active = stage_value == run.get("current_stage")
    if require_completed and not is_completed:
        raise LearningError(f"stage 尚未完成：{stage_value}")
    if not require_completed and not (is_completed or is_active):
        raise LearningError(f"stage 既未完成也不是当前活动阶段：{stage_value}")
    if capability_value not in matrix[stage_value]:
        raise LearningError(
            f"capability {capability_value!r} 不适用于阶段 {stage_value!r}"
        )
    return stage_value, capability_value


def update_sidecar_descriptor(
    run_path: Path,
    run: dict[str, Any],
    relative: str,
    path: Path,
    *,
    allow_replace: bool,
) -> None:
    updated = deepcopy(run)
    extension = learning_extension(updated)
    sidecars = extension["sidecars"]
    new_descriptor = {"path": relative, "sha256": stable_sha256(path)}
    current = sidecars.get(relative)
    if current is not None and current != new_descriptor and not allow_replace:
        raise LearningError(f"sidecar descriptor 已存在且内容不同：{relative}")
    sidecars[relative] = new_descriptor
    atomic_write_json(run_path, updated)


def record_capability(
    run_dir: Path, run_path: Path, run: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    require_collecting(run)
    capability_id = require_string(payload.get("capability_id"), "capability_id")
    registry = capability_registry_details()
    if capability_id not in registry:
        raise LearningError(f"capability 不在 registry：{capability_id}")
    entry = registry[capability_id]
    candidate_defs = entry["candidates"]
    candidate_ids = [candidate["id"] for candidate in candidate_defs]
    probes = payload.get("probes")
    if not isinstance(probes, list) or not probes:
        raise LearningError("probes 必须是非空数组")
    normalized_probes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, probe in enumerate(probes):
        if not isinstance(probe, dict):
            raise LearningError(f"probes[{index}] 必须是对象")
        candidate_id = probe.get("candidate_id")
        if candidate_id not in candidate_ids or candidate_id in seen:
            raise LearningError("probe candidate 不在 registry 或重复")
        result = probe.get("result")
        if result not in PROBE_RESULTS:
            raise LearningError(f"probe result 非法：{result!r}")
        refs = evidence_descriptors(
            run_dir, probe.get("evidence_refs"), f"probes[{index}].evidence_refs"
        )
        if not refs:
            raise LearningError("每个 capability probe 必须绑定真实 evidence")
        normalized_probes.append(
            {"candidate_id": candidate_id, "result": result, "evidence_refs": refs}
        )
        seen.add(candidate_id)
    mode = entry.get("candidate_mode")
    probe_ids = [probe["candidate_id"] for probe in normalized_probes]
    if mode == "all":
        if probe_ids != candidate_ids:
            raise LearningError("all capability 必须按 registry 顺序 probe 全部候选")
        passed = [
            probe["candidate_id"]
            for probe in normalized_probes
            if probe["result"] == "passed"
        ]
        if len(passed) == len(candidate_ids):
            expected_status, expected_selected, expected_fallback = (
                "available",
                passed,
                None,
            )
        elif passed or any(
            probe["result"] == "degraded" for probe in normalized_probes
        ):
            expected_status, expected_selected, expected_fallback = (
                "degraded",
                passed,
                candidate_defs[-1]["fallback"],
            )
        else:
            expected_status, expected_selected, expected_fallback = (
                "missing",
                [],
                candidate_defs[-1]["fallback"],
            )
    elif mode == "ordered_fallback":
        if probe_ids != candidate_ids[: len(probe_ids)]:
            raise LearningError("ordered_fallback probes 必须是 registry 有序前缀")
        passed_probe = next(
            (probe for probe in normalized_probes if probe["result"] == "passed"),
            None,
        )
        if passed_probe is not None:
            if normalized_probes[-1] is not passed_probe:
                raise LearningError("ordered_fallback 在 passed 后不得继续 probe")
            expected_status = "available"
            expected_selected = passed_probe["candidate_id"]
            expected_fallback = None
        else:
            degraded_probe = next(
                (
                    probe
                    for probe in normalized_probes
                    if probe["result"] == "degraded"
                ),
                None,
            )
            if degraded_probe is not None:
                expected_status = "degraded"
                expected_selected = degraded_probe["candidate_id"]
                expected_fallback = next(
                    candidate["fallback"]
                    for candidate in candidate_defs
                    if candidate["id"] == expected_selected
                )
            else:
                if len(normalized_probes) != len(candidate_defs):
                    raise LearningError(
                        "ordered_fallback missing requires all candidates probed"
                    )
                expected_status = "missing"
                expected_selected = None
                expected_fallback = candidate_defs[len(normalized_probes) - 1]["fallback"]
    else:
        raise LearningError(f"capability candidate_mode 非法：{mode!r}")
    if payload.get("status") != expected_status:
        raise LearningError("status 与 probes 推导结果不一致")
    if payload.get("selected") != expected_selected:
        raise LearningError("selected 与 probes/candidate_mode 推导结果不一致")
    if payload.get("fallback") != expected_fallback:
        raise LearningError("fallback 与 registry/probes 推导结果不一致")
    checked_at = normalize_rfc3339(payload.get("checked_at"), "checked_at")
    normalized = {
        "candidate_mode": mode,
        "status": expected_status,
        "selected": expected_selected,
        "fallback": expected_fallback,
        "probes": normalized_probes,
        "checked_at": checked_at,
    }
    target = run_dir / "runtime-capabilities.json"
    _, registry_version, registry_hash = pinned_capability_registry()
    if target.exists():
        value = load_object(target, "runtime-capabilities.json")
    else:
        value = {
            "schema_version": SCHEMA_VERSION,
            "workflow_version": WORKFLOW_VERSION,
            "run_id": run.get("run_id"),
            "registry_version": registry_version,
            "registry_sha256": registry_hash,
            "probed_at": checked_at,
            "capabilities": {},
        }
    if (
        value.get("registry_version") not in {None, registry_version}
        or value.get("registry_sha256") not in {None, registry_hash}
    ):
        raise LearningError("runtime-capabilities registry pin 漂移")
    value["registry_version"] = registry_version
    value["registry_sha256"] = registry_hash
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict):
        raise LearningError("runtime-capabilities.json.capabilities 非法")
    existing = capabilities.get(capability_id)
    if existing is not None and existing != normalized:
        raise LearningError("capability 事实已存在且内容不同")
    capabilities[capability_id] = normalized
    times = [
        item.get("checked_at")
        for item in capabilities.values()
        if isinstance(item, dict) and isinstance(item.get("checked_at"), str)
    ]
    value["probed_at"] = max(times) if times else checked_at
    atomic_write_json(target, value)
    update_sidecar_descriptor(
        run_path, run, "runtime-capabilities.json", target, allow_replace=True
    )
    return {"ok": True, "path": "runtime-capabilities.json", "reused": existing == normalized}


def record_decision(
    run_dir: Path, run_path: Path, run: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    require_collecting(run)
    decision_id = require_string(payload.get("decision_id"), "decision_id")
    validate_identifier(decision_id, "decision_id")
    stage = require_string(payload.get("stage"), "stage")
    if stage not in applicable_capabilities(run):
        raise LearningError("decision stage 不在 workflow")
    completed = run.get("completed_stages", [])
    if stage not in completed and stage != run.get("current_stage"):
        raise LearningError("decision stage 既未完成也不是当前活动阶段")
    refs = evidence_descriptors(run_dir, payload.get("evidence_refs"), "evidence_refs")
    required_chain = [
        "observation",
        "decision",
        "action",
        "validation",
        "error",
        "root_cause",
        "next_rule",
    ]
    missing = [field for field in required_chain if field not in payload]
    if missing:
        raise LearningError("decision fact chain 缺少：" + ", ".join(missing))
    for field in ("observation", "decision", "action", "validation", "next_rule"):
        require_string(payload.get(field), field)
    for field in ("error", "root_cause"):
        value = payload.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise LearningError(f"{field} 只能是 null 或非空字符串")
    if payload.get("root_cause") is not None and not refs:
        raise LearningError("无 evidence 的 root_cause 必须为 null")
    required_core_stages: tuple[str, ...] = ()
    if stage in {"transcript", "learn_method"}:
        required_core_stages = ("transcript", "learn_method")
    elif stage == "plan_demo":
        required_core_stages = ("learn_method", "observe_motion", "plan_demo")
    elif stage == "revise":
        required_core_stages = ("review_r1",)
    if required_core_stages:
        artifacts = run.get("artifacts")
        allowed = {
            (item.get("path"), item.get("sha256"))
            for core_stage in required_core_stages
            for item in [
                artifacts.get(core_stage) if isinstance(artifacts, dict) else None
            ]
            if isinstance(item, dict)
        }
        actual = {(item["path"], item["sha256"]) for item in refs}
        if not (actual & allowed):
            raise LearningError(
                f"decision {stage} evidence 未绑定合理 core artifact"
            )
    normalized = {
        "decision_id": decision_id,
        "stage": stage,
        "observation": payload["observation"],
        "evidence_refs": refs,
        "decision": payload["decision"],
        "action": payload["action"],
        "validation": payload["validation"],
        "error": payload["error"],
        "root_cause": payload["root_cause"],
        "next_rule": payload["next_rule"],
        "recorded_at": normalize_rfc3339(payload.get("recorded_at"), "recorded_at"),
    }
    target = run_dir / "decision-trace.json"
    if target.exists():
        value = load_object(target, "decision-trace.json")
    else:
        value = {
            "schema_version": SCHEMA_VERSION,
            "workflow_version": WORKFLOW_VERSION,
            "run_id": run.get("run_id"),
            "decisions": [],
        }
    decisions = value.get("decisions")
    if not isinstance(decisions, list):
        raise LearningError("decision-trace.json.decisions 非法")
    existing = next(
        (
            item
            for item in decisions
            if isinstance(item, dict) and item.get("decision_id") == decision_id
        ),
        None,
    )
    if existing is not None and existing != normalized:
        raise LearningError("decision_id 已存在且事实链不同")
    if existing is None:
        decisions.append(normalized)
        decisions.sort(
            key=lambda item: (
                stage_index(item["stage"]),
                item["recorded_at"],
                item["decision_id"],
            )
        )
    atomic_write_json(target, value)
    update_sidecar_descriptor(run_path, run, "decision-trace.json", target, allow_replace=True)
    return {"ok": True, "path": "decision-trace.json", "reused": existing is not None}


def normalize_usage(
    run_dir: Path, run: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    event_id = require_string(payload.get("event_id"), "event_id")
    validate_identifier(event_id, "event_id")
    kind = payload.get("kind")
    if kind not in USAGE_KINDS:
        raise LearningError(f"kind 非法：{kind!r}")
    stage, capability_id = ensure_stage_capability(
        run,
        payload.get("stage"),
        payload.get("capability_id"),
        require_completed=False,
    )
    result = payload.get("result")
    capture_state = payload.get("capture_state")
    if result not in RESULTS:
        raise LearningError(f"result 非法：{result!r}")
    if capture_state not in CAPTURE_STATES:
        raise LearningError(f"capture_state 非法：{capture_state!r}")
    if capture_state != "captured" and result == "passed":
        raise LearningError("missing/degraded/not_recorded coverage 不能声明 passed")
    if capture_state == "captured" and result == "not_recorded":
        raise LearningError("captured usage 不能声明 not_recorded result")
    refs = evidence_descriptors(run_dir, payload.get("evidence_refs"), "evidence_refs")
    if result == "passed" and not refs:
        raise LearningError("passed usage 必须有真实 evidence")
    actual_id = require_string(payload.get("actual_id"), "actual_id")
    normalized: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "event_id": event_id,
        "kind": kind,
        "stage": stage,
        "capability_id": capability_id,
        "actual_id": actual_id,
        "purpose": require_string(payload.get("purpose"), "purpose"),
        "result": result,
        "capture_state": capture_state,
        "evidence_refs": refs,
        "recorded_at": normalize_rfc3339(payload.get("recorded_at"), "recorded_at"),
    }
    if kind == "content":
        if "execution_receipt" in payload and payload.get("execution_receipt") is not None:
            raise LearningError("content usage 禁止 execution_receipt")
        content_ref = require_string(payload.get("content_ref"), "content_ref")
        content_path = secure_run_relative(run_dir, content_ref, must_exist=True)
        if content_path.is_symlink() or not content_path.is_file():
            raise LearningError("content_ref 必须指向真实普通文件")
        normalized.update(
            {
                "content_ref": content_ref,
                "content_sha256": hashlib.sha256(
                    read_stable_file_bytes(content_path)
                ).hexdigest(),
            }
        )
    else:
        registry = capability_registry()
        if actual_id not in registry.get(capability_id, set()):
            raise LearningError("skill/tool actual_id 不在 capability registry")
        if "version" not in payload or "execution_receipt" not in payload:
            raise LearningError("skill/tool 必须显式包含 version 与 execution_receipt")
        version = payload.get("version")
        if version is not None and (not isinstance(version, str) or not version.strip()):
            raise LearningError("version 必须为非空字符串或 null")
        if version is None and not (
            result == "not_recorded" or capture_state in {"missing", "not_recorded"}
        ):
            raise LearningError("version 仅可在 not_recorded/missing 时为 null")
        receipt_value = payload.get("execution_receipt")
        receipt = None
        if receipt_value is not None:
            receipt_ref = require_string(receipt_value, "execution_receipt")
            receipt_path = secure_run_relative(run_dir, receipt_ref, must_exist=True)
            receipt_bytes = read_stable_file_bytes(receipt_path)
            try:
                receipt_payload = json.loads(receipt_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise LearningError(f"execution receipt 不是合法 JSON：{error}") from error
            if not isinstance(receipt_payload, dict):
                raise LearningError("execution receipt 顶层必须是对象")
            receipt = {
                "path": receipt_ref,
                "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            }
            try:
                reject_private_payload(receipt_payload)
            except (TypeError, ValueError) as error:
                raise LearningError(f"execution receipt 包含私有或敏感数据：{error}") from error
            required_receipt = {"receipt_type", "command", "exit_code", "executed_at"}
            missing_receipt = sorted(required_receipt - receipt_payload.keys())
            if missing_receipt:
                raise LearningError(
                    "execution receipt 缺少：" + ", ".join(missing_receipt)
                )
            if receipt_payload.get("receipt_type") != "execution":
                raise LearningError("execution receipt.receipt_type 必须为 execution")
            command = receipt_payload.get("command")
            if not isinstance(command, list) or not command or any(
                not isinstance(item, str) or not item.strip() for item in command
            ):
                raise LearningError("execution receipt.command 必须是非空字符串数组")
            exit_code = receipt_payload.get("exit_code")
            if type(exit_code) is not int:
                raise LearningError("execution receipt.exit_code 必须是非布尔整数")
            normalize_rfc3339(receipt_payload.get("executed_at"), "execution receipt.executed_at")
            for optional in ("stdout", "stderr", "target"):
                if optional not in receipt_payload:
                    continue
                reference = receipt_payload[optional]
                if not isinstance(reference, dict):
                    raise LearningError(f"execution receipt.{optional} 必须是 path/sha256 引用")
                actual_ref = descriptor(
                    run_dir,
                    require_string(reference.get("path"), f"execution receipt.{optional}.path"),
                    f"execution receipt.{optional}",
                )
                if reference != actual_ref:
                    raise LearningError(f"execution receipt.{optional} hash 不一致")
            if result == "passed" and exit_code != 0:
                raise LearningError("passed usage 的 execution receipt.exit_code 必须为 0")
            if result == "failed" and exit_code == 0:
                raise LearningError("failed usage 的 execution receipt.exit_code 必须非零")
        if capture_state == "captured" and receipt is None:
            raise LearningError("captured skill/tool 必须有 execution receipt")
        normalized.update({"version": version, "execution_receipt": receipt})
    return normalized


def record_usage(
    run_dir: Path, run_path: Path, run: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    require_collecting(run)
    event = normalize_usage(run_dir, run, payload)
    relative = f"usage-events/{event['event_id']}.json"
    target = secure_run_relative(run_dir, relative, must_exist=False)
    created = write_immutable_or_adopt(target, event)
    try:
        update_sidecar_descriptor(run_path, run, relative, target, allow_replace=False)
    except BaseException:
        if created:
            secure_unlink_file(target)
        raise
    return {"ok": True, "path": relative, "reused": not created}


def scan_usage_event_paths(run_dir: Path) -> set[str]:
    directory = run_dir / "usage-events"
    if not directory.exists():
        return set()
    if directory.is_symlink() or not directory.is_dir():
        raise LearningError("usage-events 必须是无 symlink 的普通目录")
    paths: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise LearningError("usage-events 只允许单层普通 JSON 文件")
        if path.suffix != ".json" or not path.stem:
            continue
        paths.add(f"usage-events/{path.name}")
    return paths


def load_usage_events(
    run_dir: Path, run: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    sidecars = learning_extension(run).get("sidecars")
    if not isinstance(sidecars, dict):
        raise LearningError("learning sidecars 非法")
    descriptor_paths = {
        relative
        for relative in sidecars
        if isinstance(relative, str) and relative.startswith("usage-events/")
    }
    actual_paths = scan_usage_event_paths(run_dir)
    if descriptor_paths != actual_paths:
        orphaned = sorted(actual_paths - descriptor_paths)
        dangling = sorted(descriptor_paths - actual_paths)
        raise LearningError(
            "usage-events 与 descriptors 必须 exact-set；"
            f"orphan={orphaned} dangling={dangling}"
        )
    events: list[tuple[str, dict[str, Any]]] = []
    for relative in sorted(actual_paths):
        sidecar = sidecars[relative]
        expected = sidecar if isinstance(sidecar, dict) else {}
        if expected.get("path") != relative:
            raise LearningError(f"usage event descriptor path 不一致：{relative}")
        path = secure_run_relative(run_dir, relative, must_exist=True)
        content = read_stable_file_bytes(path)
        if expected.get("sha256") != hashlib.sha256(content).hexdigest():
            raise LearningError(f"usage event descriptor hash 不一致：{relative}")
        try:
            event = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LearningError(f"usage event 非法 JSON：{relative}: {error}") from error
        if not isinstance(event, dict):
            raise LearningError(f"usage event 顶层必须是对象：{relative}")
        events.append((relative, event))
    return sorted(
        events,
        key=lambda item: (
            stage_index(str(item[1].get("stage"))),
            str(item[1].get("recorded_at")),
            str(item[1].get("event_id")),
        ),
    )


def validate_coverage(
    run: dict[str, Any], events: list[tuple[str, dict[str, Any]]]
) -> None:
    matrix = applicable_capabilities(run)
    completed = run.get("completed_stages")
    if not isinstance(completed, list):
        raise LearningError("completed_stages 非法")
    covered = {
        (event.get("stage"), event.get("capability_id"))
        for _, event in events
        if event.get("capture_state") in CAPTURE_STATES
        and (
            event.get("capture_state") == "captured"
            or event.get("capture_state") in {"missing", "degraded", "not_recorded"}
        )
    }
    required = {
        (stage, capability)
        for stage in completed
        for capability in matrix.get(stage, set())
    }
    missing = sorted(required - covered)
    if missing:
        details = ", ".join(f"{stage}:{capability}" for stage, capability in missing)
        raise LearningError(f"coverage 缺少 completed stage/capability：{details}")


def normalize_manifest(
    run_dir: Path,
    run: dict[str, Any],
    payload: dict[str, Any],
    events: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise LearningError("manifest.entries 必须是数组")
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
    registry = capability_registry()
    normalized_entries: list[dict[str, Any]] = []
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise LearningError(f"manifest.entries[{index}] 必须是对象")
        missing = sorted(required - raw.keys())
        if missing:
            raise LearningError(f"manifest.entries[{index}] 缺少：{', '.join(missing)}")
        stage, capability = ensure_stage_capability(
            run,
            raw.get("phase"),
            raw.get("capability"),
            require_completed=True,
        )
        candidates = require_string_list(
            raw.get("candidates_checked"), f"manifest.entries[{index}].candidates_checked"
        )
        if any(candidate not in registry[capability] for candidate in candidates):
            raise LearningError("manifest candidates_checked 不在 registry")
        selected = raw.get("selected")
        if selected is not None and selected not in registry[capability]:
            raise LearningError("manifest selected 不在 registry")
        if selected is not None and selected not in candidates:
            raise LearningError("manifest selected 必须属于 candidates_checked")
        require_string(raw.get("source"), "manifest source")
        require_string(raw.get("mode"), "manifest mode")
        result = raw.get("result")
        if result not in RESULTS:
            raise LearningError("manifest result 非法")
        inputs = require_string_list(raw.get("inputs"), "manifest inputs")
        outputs = require_string_list(raw.get("outputs"), "manifest outputs")
        refs = evidence_descriptors(
            run_dir, raw.get("evidence_refs"), f"manifest.entries[{index}].evidence_refs"
        )
        output_descriptors = [descriptor(run_dir, item, "manifest output") for item in outputs]
        matching_events = [
            event
            for _, event in events
            if event.get("stage") == stage
            and event.get("capability_id") == capability
            and event.get("capture_state") == "captured"
            and event.get("result") == "passed"
            and event.get("actual_id") == selected
            and event.get("execution_receipt") is not None
        ]
        if result == "passed" and not matching_events:
            raise LearningError(
                "passed manifest selected 缺少同阶段/capability 的 captured+passed usage"
            )
        revision = raw.get("revision")
        if result == "passed" and (
            not isinstance(revision, str)
            or not revision.strip()
            or any(event.get("version") != revision for event in matching_events)
        ):
            raise LearningError("passed manifest revision 必须匹配 usage version")
        if result == "passed" and not output_descriptors:
            raise LearningError("passed manifest entry 缺少真实 output")
        if result == "passed" and not refs:
            raise LearningError("passed manifest entry 缺少真实 evidence")
        normalized_entries.append(
            {
                **raw,
                "capability": capability,
                "phase": stage,
                "inputs": inputs,
                "outputs": output_descriptors,
                "evidence_refs": refs,
            }
        )
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
            entry.get("phase"),
            entry.get("capability"),
            entry.get("selected"),
            entry.get("revision"),
        )
        for entry in normalized_entries
        if entry.get("result") == "passed"
    ]
    if len(passed_manifest_keys) != len(set(passed_manifest_keys)):
        raise LearningError("duplicate passed manifest projection entry")
    if set(passed_manifest_keys) != passed_usage_keys:
        raise LearningError(
            "passed manifest projection must exactly equal captured passed usage keys"
        )
    normalized_entries.sort(
        key=lambda item: (
            stage_index(item["phase"]),
            item["capability"],
            str(item.get("selected")),
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "entries": normalized_entries,
        "bindings": core_bindings(run_dir, run),
    }


def core_bindings(run_dir: Path, run: dict[str, Any]) -> dict[str, Any]:
    source = run.get("source")
    artifacts = run.get("artifacts")
    media_hash = source.get("media_sha256") if isinstance(source, dict) else None
    if not isinstance(media_hash, str) or not HASH_RE.fullmatch(media_hash):
        raise LearningError("core binding 缺少真实 source media hash")
    if isinstance(source, dict) and source.get("kind") == "local_file":
        locator = source.get("private_locator")
        if not isinstance(locator, str) or not Path(locator).is_file():
            raise LearningError("core binding 的本地 source 不存在")
        if stable_sha256(Path(locator).resolve()) != media_hash:
            raise LearningError("core binding 的 source media hash 已漂移")
    elif isinstance(source, dict) and source.get("kind") == "url":
        ingest_descriptor = artifacts.get("ingest") if isinstance(artifacts, dict) else None
        if not isinstance(ingest_descriptor, dict):
            raise LearningError("URL core binding 缺少 ingest descriptor")
        ingest_path = secure_run_relative(
            run_dir,
            require_string(ingest_descriptor.get("path"), "ingest descriptor.path"),
            must_exist=True,
        )
        if stable_sha256(ingest_path) != ingest_descriptor.get("sha256"):
            raise LearningError("URL core binding ingest artifact hash 已漂移")
        ingest = load_object(ingest_path, "ingest artifact")
        media_path = secure_run_relative(
            run_dir,
            require_string(ingest.get("local_media_path"), "ingest.local_media_path"),
            must_exist=True,
        )
        if stable_sha256(media_path) != media_hash:
            raise LearningError("URL core binding 的实际下载媒体 hash 已漂移")
    if not isinstance(artifacts, dict):
        raise LearningError("core binding 缺少 artifacts")
    bound: dict[str, Any] = {"source_media_sha256": media_hash}
    for stage in ("build", "review_r1", "review_r2", "finalize"):
        item = artifacts.get(stage)
        if not isinstance(item, dict):
            raise LearningError(f"core binding 缺少 {stage} descriptor")
        relative = item.get("path")
        declared_hash = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(
            declared_hash, str
        ) or not HASH_RE.fullmatch(declared_hash):
            raise LearningError(f"core binding 的 {stage} descriptor 非法")
        path = secure_run_relative(run_dir, relative, must_exist=True)
        if not path.is_file() or stable_sha256(path) != declared_hash:
            raise LearningError(f"core binding 的 {stage} artifact hash 已漂移")
        bound[stage] = {"path": relative, "sha256": declared_hash}
    return bound


def normalize_retrospective(
    run_dir: Path, run: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    objective = require_string(payload.get("objective"), "retrospective.objective")
    result = payload.get("result")
    if result not in RETROSPECTIVE_RESULTS:
        raise LearningError("retrospective.result 非法")
    if payload.get("skills_manifest_ref") != "skill-usage-manifest.json":
        raise LearningError("skills_manifest_ref 必须指向 skill-usage-manifest.json")
    evidence = evidence_descriptors(
        run_dir, payload.get("evidence"), "retrospective.evidence"
    )
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise LearningError("retrospective.findings 必须是数组")
    normalized_findings: list[dict[str, Any]] = []
    required = {
        "type",
        "claim",
        "evidence_refs",
        "applies_to",
        "destination_candidate",
        "status",
    }
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise LearningError("retrospective finding 必须是对象")
        missing = sorted(required - finding.keys())
        if missing:
            raise LearningError(f"retrospective finding 缺少：{', '.join(missing)}")
        if finding.get("type") not in FINDING_TYPES:
            raise LearningError("retrospective finding type 非法")
        require_string(finding.get("claim"), "retrospective finding.claim")
        applies_to = require_string_list(
            finding.get("applies_to"), "retrospective finding.applies_to"
        )
        if not applies_to:
            raise LearningError("retrospective finding.applies_to 不能为空")
        destination = finding.get("destination_candidate")
        if destination not in DESTINATIONS:
            raise LearningError("retrospective destination 非法")
        if finding.get("status") != "candidate":
            raise LearningError("retrospective status 必须为 candidate")
        refs = evidence_descriptors(
            run_dir,
            finding.get("evidence_refs"),
            f"retrospective.findings[{index}].evidence_refs",
        )
        basis = finding.get("basis")
        if basis is not None and basis not in BASIS_VALUES:
            raise LearningError("retrospective finding.basis 非法")
        if (not refs or basis in {"guess", "aesthetic_opinion", "residual"}) and destination != "backlog":
            raise LearningError("无证据、猜测、审美或 residual finding 只能进入 backlog")
        normalized_findings.append(
            {**finding, "applies_to": applies_to, "evidence_refs": refs}
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "objective": objective,
        "result": result,
        "skills_manifest_ref": "skill-usage-manifest.json",
        "evidence": evidence,
        "findings": normalized_findings,
        "bindings": core_bindings(run_dir, run),
    }


def normalize_ledger(
    run_dir: Path,
    run: dict[str, Any],
    payload: dict[str, Any],
    events: list[tuple[str, dict[str, Any]]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    event_refs = [
        {"path": relative, "sha256": stable_sha256(Path(path))}
        for relative, _ in events
        for path in [secure_run_relative(run_dir, relative, must_exist=True)]
    ]
    grouped = {kind: [] for kind in sorted(USAGE_KINDS)}
    for relative, event in events:
        grouped[event["kind"]].append(
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
    output = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "event_refs": event_refs,
        "manifest": {
            "path": "skill-usage-manifest.json",
            "sha256": hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
        },
        "entries": grouped,
        "bindings": core_bindings(run_dir, run),
    }
    if "objective" in payload:
        output["objective"] = require_string(payload.get("objective"), "ledger.objective")
    return output


def validate_fixed_descriptor(run_dir: Path, run: dict[str, Any], relative: str) -> None:
    sidecars = learning_extension(run).get("sidecars", {})
    item = sidecars.get(relative) if isinstance(sidecars, dict) else None
    if not isinstance(item, dict) or item.get("path") != relative:
        raise LearningError(f"finalize 前缺少 {relative} descriptor")
    path = secure_run_relative(run_dir, relative, must_exist=True)
    if item.get("sha256") != stable_sha256(path):
        raise LearningError(f"{relative} descriptor hash 不一致")


def validate_required_decisions(run_dir: Path, run: dict[str, Any]) -> None:
    value = load_object(run_dir / "decision-trace.json", "decision-trace.json")
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("workflow_version") != WORKFLOW_VERSION
        or value.get("run_id") != run.get("run_id")
    ):
        raise LearningError("decision-trace identity 与 run 不一致")
    decisions = value.get("decisions")
    if not isinstance(decisions, list):
        raise LearningError("decision-trace.decisions 必须是数组")
    stages = {
        item.get("stage")
        for item in decisions
        if isinstance(item, dict) and isinstance(item.get("stage"), str)
    }
    missing: list[str] = []
    if not ({"transcript", "learn_method"} & stages):
        missing.append("extraction")
    if "plan_demo" not in stages:
        missing.append("plan_demo")
    if "revise" not in stages:
        missing.append("R1-to-revise")
    if missing:
        raise LearningError("decision trace 缺少审计判断点：" + ", ".join(missing))


def finalize(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    manifest_payload: dict[str, Any],
    ledger_payload: dict[str, Any],
    retrospective_payload: dict[str, Any],
) -> dict[str, Any]:
    extension = learning_extension(run)
    state = extension.get("state")
    if state not in {"collecting", "frozen"}:
        raise LearningError("finalize 只支持 collecting 或同字节 frozen 重试")
    if run.get("completed_stages") != [
        stage["id"] for stage in load_workflow().get("stages", [])
    ]:
        raise LearningError("finalize 前必须完成全部核心阶段")
    for relative in (
        "runtime-capabilities.json",
        "decision-trace.json",
    ):
        validate_fixed_descriptor(run_dir, run, relative)
    selection = extension.get("selection")
    if not isinstance(selection, dict) or selection.get("path") != "memory-selection.json":
        raise LearningError("finalize 前缺少 memory-selection descriptor")
    selection_path = secure_run_relative(run_dir, "memory-selection.json", must_exist=True)
    if selection.get("sha256") != stable_sha256(selection_path):
        raise LearningError("memory-selection descriptor hash 不一致")

    events = load_usage_events(run_dir, run)
    validate_coverage(run, events)
    validate_required_decisions(run_dir, run)
    manifest = normalize_manifest(run_dir, run, manifest_payload, events)
    ledger = normalize_ledger(run_dir, run, ledger_payload, events, manifest)
    retrospective = normalize_retrospective(run_dir, run, retrospective_payload)

    outputs = [
        ("skill-usage-manifest.json", manifest),
        ("usage-ledger.json", ledger),
        ("retrospective.json", retrospective),
    ]
    expected_descriptors = {
        relative: {
            "path": relative,
            "sha256": hashlib.sha256(canonical_json_bytes(value)).hexdigest(),
        }
        for relative, value in outputs
    }
    updated = deepcopy(run)
    updated_extension = learning_extension(updated)
    updated_sidecars = updated_extension["sidecars"]
    for relative, expected in expected_descriptors.items():
        existing = updated_sidecars.get(relative)
        if existing is not None and existing != expected:
            raise LearningError(f"finalize sidecar descriptor 冲突：{relative}")
        updated_sidecars[relative] = expected
    updated_extension["state"] = "frozen"

    if state == "frozen":
        for relative, value in outputs:
            path = secure_run_relative(run_dir, relative, must_exist=True)
            if path.read_bytes() != canonical_json_bytes(value):
                raise LearningError(f"frozen finalize 重试内容不同：{relative}")
        if canonical_json_bytes(updated) != canonical_json_bytes(run):
            raise LearningError("frozen run descriptors 与 finalize 输入不一致")
        return {"ok": True, "state": "frozen", "reused": True}

    created: list[Path] = []
    try:
        for index, (relative, value) in enumerate(outputs):
            path = secure_run_relative(run_dir, relative, must_exist=False)
            owned = write_immutable_or_adopt(path, value)
            if owned:
                created.append(path)
            if os.environ.get(FAULT_ENV) == f"after-output-{index + 1}":
                raise OSError("fault injection after learning output")
        atomic_write_json(run_path, updated)
    except BaseException:
        for path in reversed(created):
            try:
                secure_unlink_file(path)
            except FileNotFoundError:
                pass
        raise
    return {"ok": True, "state": "frozen", "reused": False}


def local_memory_root() -> Path:
    return SKILL_ROOT / "local"


def validate_scope(value: Any, label: str) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise LearningError(f"{label} 必须是对象")
    expected = {"task_intents", "mechanisms", "capability_ids"}
    if set(value) != expected:
        raise LearningError(f"{label} 必须只包含 task_intents/mechanisms/capability_ids")
    return {
        key: require_string_list(value.get(key), f"{label}.{key}")
        for key in sorted(expected)
    }


def load_local_index(*, allow_missing: bool) -> tuple[Path, dict[str, Any] | None]:
    root = local_memory_root()
    if not root.exists():
        if allow_missing:
            return root, None
        raise LearningError("local memory 不存在")
    try:
        ensure_secure_existing_directory(root)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise LearningError("local memory 目录链非法或包含 symlink") from error
    index_path = secure_run_relative(root, "index.json", must_exist=True)
    index = load_object(index_path, "local/index.json")
    reject_private_payload(index)
    if index.get("schema_version") != SCHEMA_VERSION:
        raise LearningError("local index schema_version 不受支持")
    if not isinstance(index.get("memories"), dict) or not isinstance(
        index.get("maps"), dict
    ):
        raise LearningError("local index memories/maps 必须是对象")
    return root, index


def load_indexed_memory(
    root: Path, memory_id: str, entry: Any
) -> tuple[dict[str, Any], str]:
    validate_identifier(memory_id, "memory_id")
    if not isinstance(entry, dict):
        raise LearningError(f"memory index entry 非法：{memory_id}")
    expected_path = f"memories/{memory_id}.json"
    if entry.get("path") != expected_path or not HASH_RE.fullmatch(
        str(entry.get("sha256"))
    ):
        raise LearningError(f"memory index descriptor 非法：{memory_id}")
    path = secure_run_relative(root, expected_path, must_exist=True)
    content = read_stable_file_bytes(path)
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != entry.get("sha256"):
        raise LearningError(f"memory index hash 漂移：{memory_id}")
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LearningError(f"memory 非法 JSON：{memory_id}") from error
    if not isinstance(value, dict) or value.get("memory_id") != memory_id:
        raise LearningError(f"memory identity 非法：{memory_id}")
    reject_private_payload(value)
    for field in ("revision", "status", "destination", "scope", "problem_model"):
        if entry.get(field) != value.get(field):
            raise LearningError(f"memory index 与 memory.{field} 不一致：{memory_id}")
    if value.get("status") not in MEMORY_STATUSES:
        raise LearningError(f"memory status 非法：{memory_id}")
    if type(value.get("revision")) is not int or value["revision"] < 1:
        raise LearningError(f"memory revision 非法：{memory_id}")
    if value.get("destination") not in LOCAL_MEMORY_DESTINATIONS:
        raise LearningError(f"memory destination 非法：{memory_id}")
    validate_scope(value.get("scope"), f"memory {memory_id}.scope")
    require_string(value.get("problem_model"), f"memory {memory_id}.problem_model")
    return value, actual_hash


def scope_match_score(query: dict[str, list[str]], scope: dict[str, list[str]]) -> int:
    score = 0
    constrained = False
    for key in ("task_intents", "mechanisms", "capability_ids"):
        values = set(scope[key])
        if not values:
            continue
        constrained = True
        overlap = values & set(query[key])
        if not overlap:
            return -1
        score += len(overlap)
    return score if constrained else -1


def select_memory(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    extension = require_collecting(run)
    if "preflight" not in run.get("completed_stages", []):
        raise LearningError("select-memory 只能在 preflight 完成后执行")
    query = {
        "task_intents": require_string_list(payload.get("task_intents"), "task_intents"),
        "mechanisms": require_string_list(payload.get("mechanisms"), "mechanisms"),
        "capability_ids": require_string_list(
            payload.get("capability_ids"), "capability_ids"
        ),
        "conflicting_evidence_refs": evidence_descriptors(
            run_dir,
            payload.get("conflicting_evidence_refs"),
            "conflicting_evidence_refs",
        ),
    }
    if not query["task_intents"]:
        raise LearningError("task_intents 不能为空")
    created_at = normalize_rfc3339(payload.get("created_at"), "created_at")
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    root, index = load_local_index(allow_missing=True)
    matches: list[tuple[int, str, dict[str, Any], str]] = []
    if index is not None:
        for memory_id, entry in index["memories"].items():
            memory, memory_hash = load_indexed_memory(root, memory_id, entry)
            if memory.get("status") != "active":
                continue
            scope = validate_scope(memory.get("scope"), f"memory {memory_id}.scope")
            score = scope_match_score(query, scope)
            if score < 0:
                continue
            matches.append((score, memory_id, memory, memory_hash))
    matches.sort(key=lambda item: (-item[0], item[1]))
    has_conflict = bool(query["conflicting_evidence_refs"])
    for _, memory_id, memory, memory_hash in matches:
        base = {
            "memory_id": memory_id,
            "revision": memory.get("revision"),
            "snapshot_sha256": memory_hash,
        }
        if has_conflict:
            rejected.append({**base, "reason": "conflicting_evidence"})
        elif len(selected) < 3:
            selected.append({**base, "reason": "scope_match", "snapshot": memory})
        else:
            rejected.append({**base, "reason": "selection_limit"})
    snapshot = {
        "selected": [
            {
                "memory_id": item["memory_id"],
                "revision": item["revision"],
                "snapshot_sha256": item["snapshot_sha256"],
            }
            for item in selected
        ],
        "rejected": rejected,
    }
    value = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "query": query,
        "selected": selected,
        "rejected": rejected,
        "selection_snapshot": snapshot,
        "selection_snapshot_sha256": hashlib.sha256(
            canonical_json_bytes(snapshot)
        ).hexdigest(),
        "created_at": created_at,
    }
    target = secure_run_relative(run_dir, "memory-selection.json", must_exist=False)
    created = write_immutable_or_adopt(target, value)
    updated = deepcopy(run)
    updated_extension = learning_extension(updated)
    descriptor_value = {"path": "memory-selection.json", "sha256": stable_sha256(target)}
    current = updated_extension.get("selection")
    if current is not None and current != descriptor_value:
        if created:
            secure_unlink_file(target)
        raise LearningError("memory selection 已冻结且内容不同")
    updated_extension["selection"] = descriptor_value
    try:
        atomic_write_json(run_path, updated)
    except BaseException:
        if created:
            secure_unlink_file(target)
        raise
    return {"ok": True, "path": "memory-selection.json", "reused": not created}


def require_post_run(run: dict[str, Any]) -> dict[str, Any]:
    extension = learning_extension(run)
    if extension.get("state") not in {"frozen", "backfilled"}:
        raise LearningError("post-run 操作只支持 frozen/backfilled run")
    return extension


def load_bound_core_artifact(
    run_dir: Path, run: dict[str, Any], stage: str
) -> tuple[dict[str, Any], dict[str, str]]:
    artifacts = run.get("artifacts")
    item = artifacts.get(stage) if isinstance(artifacts, dict) else None
    if not isinstance(item, dict):
        raise LearningError(f"run 缺少 {stage} artifact")
    relative = require_string(item.get("path"), f"{stage}.path")
    actual = descriptor(run_dir, relative, stage)
    if item != actual:
        raise LearningError(f"{stage} artifact descriptor hash 漂移")
    return load_object(run_dir / relative, stage), actual


def core_review_hashes(run_dir: Path, run: dict[str, Any]) -> tuple[str, str]:
    r2, _ = load_bound_core_artifact(run_dir, run, "review_r2")
    final, _ = load_bound_core_artifact(run_dir, run, "finalize")
    r2_hash = r2.get("reviewed_render_sha256")
    final_hash = final.get("render_sha256")
    if not HASH_RE.fullmatch(str(r2_hash)) or not HASH_RE.fullmatch(str(final_hash)):
        raise LearningError("final/R2 缺少真实 render hash")
    if r2_hash != final_hash:
        raise LearningError("final hash 与 R2 reviewed hash 不一致")
    return final_hash, r2_hash


def trusted_feedback_evidence(
    run_dir: Path, run: dict[str, Any]
) -> dict[tuple[str, str], str]:
    """只接受 run 已绑定的核心工件或受信执行回执/日志。"""

    trusted: dict[tuple[str, str], str] = {}
    artifacts = run.get("artifacts")
    if not isinstance(artifacts, dict):
        raise LearningError("run.artifacts 非法")
    for stage, item in artifacts.items():
        if not isinstance(item, dict):
            raise LearningError(f"core artifact descriptor 非法：{stage}")
        relative = require_string(item.get("path"), f"artifacts.{stage}.path")
        actual = descriptor(run_dir, relative, f"core artifact {stage}")
        if item != actual:
            raise LearningError(f"core artifact descriptor 漂移：{stage}")
        trusted[(actual["path"], actual["sha256"])] = f"core_artifact:{stage}"

    sidecars = learning_extension(run).get("sidecars")
    if not isinstance(sidecars, dict):
        raise LearningError("learning sidecars 非法")
    for relative, item in sidecars.items():
        if not relative.startswith("usage-events/"):
            continue
        actual_event = descriptor(run_dir, relative, "usage event")
        if item != actual_event:
            raise LearningError(f"usage event descriptor 漂移：{relative}")
        event = load_object(run_dir / relative, "usage event")
        if (
            event.get("kind") not in {"skill", "tool"}
            or event.get("capture_state") != "captured"
            or event.get("result") not in {"passed", "degraded", "failed"}
        ):
            continue
        receipt = event.get("execution_receipt")
        if not isinstance(receipt, dict):
            continue
        receipt_path = require_string(receipt.get("path"), "execution_receipt.path")
        actual_receipt = descriptor(run_dir, receipt_path, "execution receipt")
        if receipt != actual_receipt:
            raise LearningError("execution receipt descriptor 漂移")
        trusted[(actual_receipt["path"], actual_receipt["sha256"])] = "execution_receipt"
        receipt_value = load_object(run_dir / receipt_path, "execution receipt")
        for category in ("stdout", "stderr", "target"):
            reference = receipt_value.get(category)
            if not isinstance(reference, dict):
                continue
            actual_log = descriptor(
                run_dir,
                require_string(reference.get("path"), f"receipt.{category}.path"),
                f"receipt.{category}",
            )
            if reference != actual_log:
                raise LearningError(f"receipt.{category} descriptor 漂移")
            trusted[(actual_log["path"], actual_log["sha256"])] = f"receipt:{category}"
    return trusted


def reject_untrusted_feedback_evidence(
    run_dir: Path,
    run: dict[str, Any],
    refs: list[dict[str, str]],
) -> None:
    trusted = trusted_feedback_evidence(run_dir, run)
    untrusted = [item["path"] for item in refs if (item["path"], item["sha256"]) not in trusted]
    if untrusted:
        raise LearningError(
            "feedback evidence 不是 trusted core artifact/receipt/test/verification log："
            + ", ".join(sorted(untrusted))
        )


def append_post_run_sidecar(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    relative: str,
    value: dict[str, Any],
) -> bool:
    target = secure_run_relative(run_dir, relative, must_exist=False)
    created = write_immutable_or_adopt(target, value)
    try:
        update_sidecar_descriptor(
            run_path, run, relative, target, allow_replace=False
        )
    except BaseException:
        if created:
            secure_unlink_file(target)
        raise
    return created


def record_feedback(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    require_post_run(run)
    candidate_id = require_string(payload.get("candidate_id"), "candidate_id")
    validate_identifier(candidate_id, "candidate_id")
    final_hash, r2_hash = core_review_hashes(run_dir, run)
    if payload.get("final_hash") != final_hash or payload.get("r2_hash") != r2_hash:
        raise LearningError("candidate final_hash/r2_hash 与冻结 run 不一致")
    refs = evidence_descriptors(run_dir, payload.get("evidence_refs"), "evidence_refs")
    applies_to = require_string_list(payload.get("applies_to"), "applies_to")
    if not applies_to:
        raise LearningError("applies_to 不能为空")
    destination = payload.get("destination")
    if destination not in DESTINATIONS:
        raise LearningError("candidate destination 非法")
    source = require_string(payload.get("source"), "source")
    if source == "reviewer_feedback" and not refs:
        raise LearningError("reviewer feedback 必须绑定 R2、测试或验证证据")
    if source == "reviewer_feedback":
        reject_untrusted_feedback_evidence(run_dir, run, refs)
    if not refs and destination != "backlog":
        raise LearningError("无可复验证据的反馈只能进入 backlog")
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "candidate_id": candidate_id,
        "final_hash": final_hash,
        "r2_hash": r2_hash,
        "evidence_refs": refs,
        "applies_to": applies_to,
        "destination": destination,
        "received_at": normalize_rfc3339(payload.get("received_at"), "received_at"),
        "source": source,
        "claim": require_string(payload.get("claim"), "claim"),
        "next_validation": require_string(
            payload.get("next_validation"), "next_validation"
        ),
    }
    for field in (
        "finding_type",
        "symptom",
        "root_cause",
        "future_recurrence",
        "verified_at",
        "problem_model",
    ):
        if field in payload:
            item = payload.get(field)
            if item is not None:
                item = require_string(item, field)
                if field == "verified_at":
                    item = normalize_rfc3339(item, field)
            value[field] = item
    if value.get("finding_type") is not None and value["finding_type"] not in FINDING_TYPES:
        raise LearningError("candidate finding_type 非法")
    if "not_applies_to" in payload:
        value["not_applies_to"] = require_string_list(
            payload.get("not_applies_to"), "not_applies_to"
        )
    if "scope" in payload:
        value["scope"] = validate_scope(payload.get("scope"), "scope")
    relative = f"feedback-candidates/{candidate_id}.json"
    created = append_post_run_sidecar(run_dir, run_path, run, relative, value)
    return {"ok": True, "path": relative, "reused": not created}


def validate_candidate_evidence(
    run_dir: Path, candidate: dict[str, Any]
) -> list[dict[str, str]]:
    refs = candidate.get("evidence_refs")
    if not isinstance(refs, list):
        raise LearningError("candidate evidence_refs 非法")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(refs):
        if not isinstance(item, dict):
            raise LearningError("candidate evidence descriptor 非法")
        actual = descriptor(
            run_dir,
            require_string(item.get("path"), f"evidence_refs[{index}].path"),
            f"evidence_refs[{index}]",
        )
        if item != actual:
            raise LearningError("candidate evidence hash 漂移")
        normalized.append(actual)
    return normalized


def normalized_root_key(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFC", value).casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def default_local_index() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "memories": {}, "maps": {}}


def reconcile_problem_maps_and_index(
    root: Path, index: dict[str, Any], updated_at: str
) -> None:
    groups: dict[str, list[str]] = {}
    for memory_id, entry in index["memories"].items():
        memory, _ = load_indexed_memory(root, memory_id, entry)
        if memory.get("status") == "active":
            groups.setdefault(memory["problem_model"], []).append(memory_id)
    groups = {
        model: sorted(memory_ids)
        for model, memory_ids in groups.items()
        if len(memory_ids) >= 3
    }
    desired: dict[str, tuple[str, dict[str, Any]]] = {}
    for problem_model, memory_ids in sorted(groups.items()):
        map_id = "map-" + hashlib.sha256(problem_model.encode("utf-8")).hexdigest()[:20]
        relative = f"maps/{map_id}.json"
        desired[map_id] = (
            relative,
            {
                "schema_version": SCHEMA_VERSION,
                "map_id": map_id,
                "problem_model": problem_model,
                "memory_ids": memory_ids,
                "updated_at": updated_at,
            },
        )

    touched_paths = {
        item.get("path")
        for item in index["maps"].values()
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    } | {relative for relative, _ in desired.values()}
    backups: dict[str, dict[str, Any] | None] = {}
    for relative in touched_paths:
        path = secure_run_relative(root, relative, must_exist=False)
        backups[relative] = load_object(path, f"map backup {relative}") if path.exists() else None

    try:
        next_maps: dict[str, dict[str, Any]] = {}
        for map_id, (relative, value) in desired.items():
            path = secure_run_relative(root, relative, must_exist=False)
            atomic_write_json(path, value)
            next_maps[map_id] = {
                "path": relative,
                "sha256": stable_sha256(path),
                "problem_model": value["problem_model"],
                "memory_ids": value["memory_ids"],
                "reason": "three_active_memories_share_problem_model",
            }
        desired_paths = {relative for relative, _ in desired.values()}
        for relative in touched_paths - desired_paths:
            secure_unlink_file(secure_run_relative(root, relative, must_exist=True))
        index["maps"] = next_maps
        atomic_write_json(root / "index.json", index)
    except BaseException:
        for relative, value in backups.items():
            path = secure_run_relative(root, relative, must_exist=False)
            if value is None:
                if path.exists():
                    secure_unlink_file(path)
            else:
                atomic_write_json(path, value)
        raise


def promote_memory(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    candidate_relative: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    extension = require_post_run(run)
    match = re.fullmatch(r"feedback-candidates/([A-Za-z0-9][A-Za-z0-9._-]{0,127})\.json", candidate_relative)
    if match is None or candidate.get("candidate_id") != match.group(1):
        raise LearningError("promote-memory input 必须是匹配 candidate_id 的 feedback candidate")
    candidate_descriptor = extension["sidecars"].get(candidate_relative)
    actual_candidate = descriptor(run_dir, candidate_relative, "source candidate")
    if candidate_descriptor != actual_candidate:
        raise LearningError("source candidate descriptor 缺失或漂移")
    final_hash, r2_hash = core_review_hashes(run_dir, run)
    if candidate.get("final_hash") != final_hash or candidate.get("r2_hash") != r2_hash:
        raise LearningError("source candidate 已与 final/R2 脱钩")
    refs = validate_candidate_evidence(run_dir, candidate)
    reject_untrusted_feedback_evidence(run_dir, run, refs)
    destination = candidate.get("destination")
    if destination in SHARED_CANDIDATE_DESTINATIONS:
        raise LearningError("共享规则只能保留 candidate 并走正常 Skill Review")
    if destination == "backlog":
        raise LearningError("backlog candidate 不可晋升")
    if destination not in LOCAL_MEMORY_DESTINATIONS:
        raise LearningError("candidate destination 不可晋升为本地 memory")
    if not refs:
        raise LearningError("promotion 必须有可复验证据")
    root_cause = require_string(candidate.get("root_cause"), "root_cause")
    symptom = require_string(candidate.get("symptom"), "symptom")
    problem_model = require_string(candidate.get("problem_model"), "problem_model")
    scope = validate_scope(candidate.get("scope"), "scope")
    if not any(scope.values()):
        raise LearningError("promotion scope 不能为空")
    applies_to = require_string_list(candidate.get("applies_to"), "applies_to")
    if not applies_to:
        raise LearningError("promotion applies_to 不能为空")
    if destination == "error_memory":
        if candidate.get("finding_type") != "failure_root_cause":
            raise LearningError("error_memory 必须来自 failure_root_cause")
        require_string(candidate.get("future_recurrence"), "future_recurrence")
        verified_at = candidate.get("verified_at") or candidate.get("received_at")
    else:
        if candidate.get("finding_type") != "environment_fact":
            raise LearningError("local_memory 必须来自 environment_fact")
        verified_at = normalize_rfc3339(candidate.get("verified_at"), "verified_at")

    candidate_id = candidate["candidate_id"]
    promotion_id = f"promotion-{candidate_id}"
    receipt_relative = f"promotion-receipts/{candidate_id}.json"
    receipt_path = secure_run_relative(run_dir, receipt_relative, must_exist=False)
    if receipt_path.exists():
        receipt = load_object(receipt_path, "promotion receipt")
        if (
            receipt.get("promotion_id") != promotion_id
            or receipt.get("source_candidate") != actual_candidate
        ):
            raise LearningError("既有 promotion receipt 与 candidate 不一致")
        if extension["sidecars"].get(receipt_relative) != descriptor(
            run_dir, receipt_relative, "promotion receipt"
        ):
            update_sidecar_descriptor(
                run_path, run, receipt_relative, receipt_path, allow_replace=False
            )
        return {"ok": True, "path": receipt_relative, "reused": True}

    root_key = normalized_root_key(root_cause)
    memory_id = "memory-" + root_key[:20]
    root, index = load_local_index(allow_missing=True)
    if index is None:
        index = default_local_index()
    relative = f"memories/{memory_id}.json"
    memory_path = secure_run_relative(root, relative, must_exist=False) if root.exists() else root / relative
    existing: dict[str, Any] | None = None
    if memory_id in index["memories"]:
        existing, _ = load_indexed_memory(root, memory_id, index["memories"][memory_id])
        if existing.get("root_cause_key") != root_key:
            raise LearningError("同 stable memory ID 的 root cause 不一致")
    revision = int(existing.get("revision", 0)) + 1 if existing else 1
    created_at = existing.get("created_at") if existing else candidate.get("received_at")
    memory = {
        "schema_version": SCHEMA_VERSION,
        "memory_id": memory_id,
        "revision": revision,
        "status": "active",
        "destination": destination,
        "finding_type": candidate.get("finding_type"),
        "symptom": symptom,
        "root_cause": root_cause,
        "root_cause_key": root_key,
        "next_rule": candidate.get("next_validation"),
        "applies_to": applies_to,
        "not_applies_to": require_string_list(
            candidate.get("not_applies_to", []), "not_applies_to"
        ),
        "scope": scope,
        "problem_model": problem_model,
        "evidence_refs": [{"run_id": run.get("run_id"), **item} for item in refs],
        "verified_at": normalize_rfc3339(verified_at, "verified_at"),
        "created_at": created_at,
        "updated_at": candidate.get("received_at"),
        "source_candidate": {
            "run_id": run.get("run_id"),
            "candidate_id": candidate_id,
            **actual_candidate,
        },
    }
    reject_private_payload(memory)
    atomic_write_json(memory_path, memory)
    index["memories"][memory_id] = {
        "path": relative,
        "sha256": stable_sha256(memory_path),
        "revision": revision,
        "status": "active",
        "destination": destination,
        "scope": scope,
        "problem_model": problem_model,
        "entered_at": memory["verified_at"],
        "reason": "evidence_gated_promotion",
    }
    reconcile_problem_maps_and_index(root, index, candidate.get("received_at"))

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "run_id": run.get("run_id"),
        "promotion_id": promotion_id,
        "candidate_id": candidate_id,
        "destination": destination,
        "evidence_refs": refs,
        "source_candidate": actual_candidate,
        "promoted_revision": revision,
        "memory_id": memory_id,
        "memory_ref": {"path": relative, "sha256": stable_sha256(memory_path)},
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    created = append_post_run_sidecar(
        run_dir, run_path, run, receipt_relative, receipt
    )
    return {"ok": True, "path": receipt_relative, "reused": not created}


def scan_json_directory(root: Path, name: str) -> set[str]:
    directory = root / name
    if not directory.exists():
        return set()
    if directory.is_symlink() or not directory.is_dir():
        raise LearningError(f"{name} 必须是普通目录")
    output: set[str] = set()
    for item in directory.iterdir():
        if item.is_symlink() or not item.is_file() or item.suffix != ".json":
            raise LearningError(f"{name} 只允许普通 JSON 文件")
        output.add(f"{name}/{item.name}")
    return output


def lint_learning_memory(run_dir: Path, run: dict[str, Any]) -> dict[str, Any]:
    extension = learning_extension(run)
    for name in ("feedback-candidates", "promotion-receipts"):
        actual = scan_json_directory(run_dir, name)
        declared = {
            relative
            for relative in extension["sidecars"]
            if relative.startswith(f"{name}/")
        }
        if actual != declared:
            raise LearningError(f"orphan {name}: actual={sorted(actual)} declared={sorted(declared)}")
        for relative in actual:
            if extension["sidecars"].get(relative) != descriptor(
                run_dir, relative, relative
            ):
                raise LearningError(f"{relative} descriptor hash 漂移")
            reject_private_payload(load_object(run_dir / relative, relative))

    root, index = load_local_index(allow_missing=True)
    if index is None:
        return {"ok": True, "memory_count": 0, "map_count": 0}
    actual_memories = scan_json_directory(root, "memories")
    declared_memories = {
        item.get("path")
        for item in index["memories"].values()
        if isinstance(item, dict)
    }
    if actual_memories != declared_memories:
        raise LearningError(
            f"orphan memory: actual={sorted(actual_memories)} declared={sorted(declared_memories)}"
        )
    root_keys: set[str] = set()
    for memory_id, entry in index["memories"].items():
        memory, _ = load_indexed_memory(root, memory_id, entry)
        if memory.get("status") not in MEMORY_STATUSES or entry.get("status") != memory.get("status"):
            raise LearningError(f"memory status 非法：{memory_id}")
        key = memory.get("root_cause_key")
        if not HASH_RE.fullmatch(str(key)) or key in root_keys:
            raise LearningError("memory root_cause_key 缺失或重复")
        root_keys.add(key)
    actual_maps = scan_json_directory(root, "maps")
    declared_maps = {
        item.get("path") for item in index["maps"].values() if isinstance(item, dict)
    }
    if actual_maps != declared_maps:
        raise LearningError(
            f"orphan map: actual={sorted(actual_maps)} declared={sorted(declared_maps)}"
        )
    for map_id, entry in index["maps"].items():
        if not isinstance(entry, dict) or entry.get("path") != f"maps/{map_id}.json":
            raise LearningError(f"map index entry 非法：{map_id}")
        path = secure_run_relative(root, entry["path"], must_exist=True)
        if entry.get("sha256") != stable_sha256(path):
            raise LearningError(f"map hash 漂移：{map_id}")
        value = load_object(path, f"map {map_id}")
        reject_private_payload(value)
        members = value.get("memory_ids")
        if not isinstance(members, list) or len(set(members)) < 3 or any(
            memory_id not in index["memories"] for memory_id in members
        ):
            raise LearningError(f"map 至少需要三个有效 memory：{map_id}")
        problem_model = value.get("problem_model")
        expected_members = sorted(
            memory_id
            for memory_id, memory_entry in index["memories"].items()
            if isinstance(memory_entry, dict)
            and memory_entry.get("status") == "active"
            and memory_entry.get("problem_model") == problem_model
        )
        if sorted(members) != expected_members or len(expected_members) < 3:
            raise LearningError(f"map 成员必须全部 active 且属于同一 problem_model：{map_id}")
        if (
            entry.get("problem_model") != problem_model
            or entry.get("memory_ids") != members
        ):
            raise LearningError(f"map index 与 map 内容不一致：{map_id}")
    return {
        "ok": True,
        "memory_count": len(index["memories"]),
        "map_count": len(index["maps"]),
    }


def legacy_context(
    repo: Path, run_id: str
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    """只解析已完成的 workflow 1.0 run，不把当前环境冒充历史事实。"""

    validate_identifier(run_id, "run-id")
    runs_root = repo / ".learning" / "runs"
    run_dir = runs_root / run_id
    try:
        ensure_secure_existing_directory(runs_root)
        ensure_secure_existing_directory(run_dir)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise LearningError(".learning/runs/run 目录链不存在或包含 symlink") from error
    run_path = secure_run_relative(run_dir, "run.json", must_exist=True)
    run = load_object(run_path, "run.json")
    if run.get("run_id") != run_id:
        raise LearningError("run.json 的 run_id 与目录不一致")
    if run.get("workflow_version") != "1.0.0":
        raise LearningError("backfill 只支持 workflow 1.0.0")
    workflow, workflow_hash = load_stable_object(LEGACY_WORKFLOW_PATH, "workflow 1.0.0")
    if run.get("workflow_sha256") != workflow_hash:
        raise LearningError("run.workflow_sha256 与稳定 workflow 1.0.0 字节不一致")
    if run.get("status") not in {"completed", "completed_with_residuals"}:
        raise LearningError("backfill 只支持 completed legacy run")
    stages = [item.get("id") for item in workflow.get("stages", []) if isinstance(item, dict)]
    if run.get("completed_stages") != stages:
        raise LearningError("backfill 要求 legacy 核心阶段全部 completed")
    extensions = run.get("extensions")
    existing = extensions.get("learning_loop") if isinstance(extensions, dict) else None
    if existing is not None and (
        not isinstance(existing, dict) or existing.get("state") != "backfilled"
    ):
        raise LearningError("legacy run 已有非 backfilled learning extension")

    # 只把已经通过旧核心契约的 run 纳入回填，扩展错误不参与这一步。
    from validate_run import Validator

    result = Validator(repo, run_id, "off", core_only=True).validate()
    if not result.get("ok"):
        raise LearningError("legacy core validation failed: " + "; ".join(result["errors"]))
    return run_dir, run_path, run, workflow


def historical_timestamp(run: dict[str, Any]) -> str:
    for key in ("updated_at", "created_at"):
        try:
            return normalize_rfc3339(run.get(key), f"run.{key}")
        except LearningError:
            continue
    return "1970-01-01T00:00:00Z"


def backfill_core_ref(
    run_dir: Path, run: dict[str, Any], stage: str
) -> dict[str, str]:
    artifacts = run.get("artifacts")
    item = artifacts.get(stage) if isinstance(artifacts, dict) else None
    if not isinstance(item, dict):
        raise LearningError(f"legacy run 缺少 {stage} artifact")
    relative = require_string(item.get("path"), f"artifacts.{stage}.path")
    actual = descriptor(run_dir, relative, f"artifact {stage}")
    if item.get("sha256") != actual["sha256"]:
        raise LearningError(f"legacy {stage} artifact hash 漂移")
    return actual


def backfill_learning(
    run_dir: Path,
    run_path: Path,
    run: dict[str, Any],
    workflow: dict[str, Any],
) -> dict[str, Any]:
    """从冻结核心工件生成 best-effort 历史账本；不推断工具、Skill 或版本。"""

    timestamp = historical_timestamp(run)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": "1.0.0",
        "run_id": run.get("run_id"),
    }
    artifacts = {
        stage: backfill_core_ref(run_dir, run, stage)
        for stage in run.get("completed_stages", [])
    }
    registry_path = CAPABILITY_REGISTRIES_ROOT / "1.0.0.json"
    registry, registry_hash = load_stable_object(
        registry_path, "capability registry 1.0.0"
    )
    if (
        registry.get("registry_version") != "1.0.0"
        or registry_hash != LEGACY_CAPABILITY_REGISTRY_SHA256
    ):
        raise LearningError("legacy frozen capability registry 漂移")

    snapshot = {"selected": [], "rejected": []}
    selection = {
        **identity,
        "query": {
            "task_intents": ["historical_backfill"],
            "mechanisms": [],
            "capability_ids": [],
            "conflicting_evidence_refs": [],
        },
        "selected": [],
        "rejected": [],
        "selection_snapshot": snapshot,
        "selection_snapshot_sha256": hashlib.sha256(
            canonical_json_bytes(snapshot)
        ).hexdigest(),
        "created_at": timestamp,
    }
    runtime = {
        **identity,
        "registry_version": "1.0.0",
        "registry_sha256": registry_hash,
        "probed_at": timestamp,
        "capabilities": {},
    }
    decision_specs = (
        ("historical-extraction", "transcript", "transcript"),
        ("historical-plan", "plan_demo", "plan_demo"),
        ("historical-r1-revision", "revise", "review_r1"),
    )
    decisions = {
        **identity,
        "decisions": [
            {
                "decision_id": decision_id,
                "stage": stage,
                "observation": "已有 legacy 核心工件，可确认该阶段曾完成。",
                "evidence_refs": [artifacts[evidence_stage]],
                "decision": "仅回填可由冻结工件证明的历史事实。",
                "action": "记录 best-effort 历史账本，不推断当时工具。",
                "validation": "证据 hash 与 legacy run artifact descriptor 一致。",
                "error": None,
                "root_cause": None,
                "next_rule": "缺失的 Skill、工具与版本统一记为 not_recorded。",
                "recorded_at": timestamp,
            }
            for decision_id, stage, evidence_stage in decision_specs
        ],
    }

    source_kind = (
        run.get("source", {}).get("kind")
        if isinstance(run.get("source"), dict)
        else None
    )
    usage_payloads: dict[str, dict[str, Any]] = {}
    manifest_entries: list[dict[str, Any]] = []
    for stage_item in workflow.get("stages", []):
        if not isinstance(stage_item, dict):
            continue
        stage = stage_item.get("id")
        capabilities = list(stage_item.get("capability_ids", []))
        for condition in stage_item.get("conditional_capabilities", []):
            if (
                isinstance(condition, dict)
                and condition.get("when") == "source.kind == 'url'"
                and source_kind == "url"
                and isinstance(condition.get("capability_id"), str)
            ):
                capabilities.append(condition["capability_id"])
        for capability_id in capabilities:
            event_id = f"historical-{stage}-{capability_id}"
            relative = f"usage-events/{event_id}.json"
            evidence = [artifacts[stage]]
            usage_payloads[relative] = {
                **identity,
                "event_id": event_id,
                "kind": "tool",
                "stage": stage,
                "capability_id": capability_id,
                "actual_id": "unknown_historical_usage",
                "purpose": "覆盖 legacy 已完成阶段；原始使用记录不存在。",
                "result": "not_recorded",
                "capture_state": "not_recorded",
                "evidence_refs": evidence,
                "recorded_at": timestamp,
                "version": None,
                "execution_receipt": None,
            }
            manifest_entries.append(
                {
                    "capability": capability_id,
                    "phase": stage,
                    "candidates_checked": [],
                    "selected": None,
                    "source": "historical_best_effort",
                    "revision": None,
                    "mode": "historical_best_effort",
                    "inputs": [],
                    "outputs": evidence,
                    "result": "not_recorded",
                    "evidence_refs": evidence,
                    "friction": "历史 run 未记录使用的 Skill、工具和版本。",
                    "adjustment_candidate": None,
                }
            )

    bindings = {
        "source_media_sha256": (
            run.get("source", {}).get("media_sha256")
            if isinstance(run.get("source"), dict)
            else None
        ),
        **{stage: artifacts[stage] for stage in ("build", "review_r1", "review_r2", "finalize")},
    }
    manifest = {
        **identity,
        "entries": manifest_entries,
        "bindings": bindings,
    }
    payloads: dict[str, dict[str, Any]] = {
        "memory-selection.json": selection,
        "runtime-capabilities.json": runtime,
        "decision-trace.json": decisions,
        **usage_payloads,
        "skill-usage-manifest.json": manifest,
    }

    event_refs = [
        {"path": relative, "sha256": hashlib.sha256(canonical_json_bytes(value)).hexdigest()}
        for relative, value in usage_payloads.items()
    ]
    ledger_entries = {kind: [] for kind in ("content", "skill", "tool")}
    ledger_entries["tool"] = [
        {
            "event_id": value["event_id"],
            "event_ref": relative,
            "stage": value["stage"],
            "capability_id": value["capability_id"],
            "actual_id": value["actual_id"],
            "result": value["result"],
            "capture_state": value["capture_state"],
            "evidence_refs": value["evidence_refs"],
        }
        for relative, value in sorted(usage_payloads.items())
    ]
    manifest_ref = {
        "path": "skill-usage-manifest.json",
        "sha256": hashlib.sha256(canonical_json_bytes(manifest)).hexdigest(),
    }
    payloads["usage-ledger.json"] = {
        **identity,
        "event_refs": event_refs,
        "manifest": manifest_ref,
        "entries": ledger_entries,
        "bindings": bindings,
    }
    payloads["retrospective.json"] = {
        **identity,
        "objective": "从已完成 workflow 1.0 核心工件回填可审计历史事实。",
        "result": (
            "success_with_residuals"
            if run.get("status") == "completed_with_residuals"
            else "success"
        ),
        "skills_manifest_ref": "skill-usage-manifest.json",
        "evidence": [
            artifacts["review_r1"],
            artifacts["review_r2"],
            artifacts["finalize"],
        ],
        "findings": [],
        "bindings": bindings,
    }
    reject_private_payload(payloads)

    created_paths: list[Path] = []
    try:
        for relative, value in payloads.items():
            target = secure_run_relative(run_dir, relative, must_exist=False)
            if write_immutable_or_adopt(target, value):
                created_paths.append(target)
        sidecars = {
            relative: {"path": relative, "sha256": stable_sha256(run_dir / relative)}
            for relative in payloads
            if relative != "memory-selection.json"
        }
        extension = {
            "required": True,
            "state": "backfilled",
            "contract_version": CONTRACT_VERSION,
            "selection": {
                "path": "memory-selection.json",
                "sha256": stable_sha256(run_dir / "memory-selection.json"),
            },
            "sidecars": sidecars,
        }
        updated = deepcopy(run)
        existing_extensions = updated.get("extensions")
        if existing_extensions is None:
            updated["extensions"] = {"learning_loop": extension}
        elif isinstance(existing_extensions, dict):
            existing = existing_extensions.get("learning_loop")
            if existing is not None and existing != extension:
                raise LearningError("既有 backfilled extension 与确定性回填结果不同")
            existing_extensions["learning_loop"] = extension
        else:
            raise LearningError("run.extensions 必须是对象")
        reused = not created_paths and updated == run
        if updated != run:
            atomic_write_json(run_path, updated)
        return {"ok": True, "state": "backfilled", "reused": reused}
    except BaseException:
        for path in reversed(created_paths):
            secure_unlink_file(path)
        raise


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True)
    common.add_argument("--run-id", required=True)
    common.add_argument("--json", action="store_true")
    parser = argparse.ArgumentParser(description="记录教程学习闭环的可审计运行事实")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in (
        "record-capability",
        "record-decision",
        "record-usage",
        "select-memory",
        "record-feedback",
        "promote-memory",
    ):
        command = subparsers.add_parser(name, parents=[common])
        command.add_argument("--input", required=True)
    finalize_parser = subparsers.add_parser("finalize", parents=[common])
    finalize_parser.add_argument("--manifest-input", required=True)
    finalize_parser.add_argument("--ledger-input", required=True)
    finalize_parser.add_argument("--retrospective-input", required=True)
    subparsers.add_parser("backfill", parents=[common])
    subparsers.add_parser("lint", parents=[common])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = Path(args.repo).expanduser().resolve()
        if not repo.is_dir():
            raise LearningError(f"仓库目录不存在：{args.repo}")
        with repository_lock(repo):
            if args.command == "backfill":
                run_dir, run_path, run, workflow = legacy_context(repo, args.run_id)
                result = backfill_learning(
                    run_dir, run_path, run, workflow
                )
            else:
                # 锁内重新读取 run，禁止使用进程启动时的 stale snapshot。
                _, run_dir, run_path, run = resolve_context(str(repo), args.run_id)
            if args.command == "backfill":
                pass
            elif args.command == "record-capability":
                result = record_capability(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.input, "capability draft"),
                )
            elif args.command == "record-decision":
                result = record_decision(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.input, "decision draft"),
                )
            elif args.command == "record-usage":
                result = record_usage(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.input, "usage draft"),
                )
            elif args.command == "select-memory":
                result = select_memory(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.input, "memory query"),
                )
            elif args.command == "record-feedback":
                result = record_feedback(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.input, "feedback candidate draft"),
                )
            elif args.command == "promote-memory":
                result = promote_memory(
                    run_dir,
                    run_path,
                    run,
                    args.input,
                    read_draft(run_dir, args.input, "feedback candidate"),
                )
            elif args.command == "finalize":
                result = finalize(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.manifest_input, "manifest draft"),
                    read_draft(run_dir, args.ledger_input, "ledger draft"),
                    read_draft(run_dir, args.retrospective_input, "retrospective draft"),
                )
            elif args.command == "lint":
                result = lint_learning_memory(run_dir, run)
            else:
                raise AssertionError("不可达 command")
    except (LearningError, FileExistsError, FileNotFoundError, OSError, TypeError, ValueError) as error:
        result = {"ok": False, "error": str(error)}
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            print(f"错误：{error}", file=sys.stderr)
        # 即使 --json，也保留 stderr 供无人值守日志直接定位。
        if getattr(args, "json", False):
            print(f"错误：{error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("学习事实已记录")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
