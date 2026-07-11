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
FAULT_ENV = "TUTORIAL_TO_HYPERFRAMES_LEARNING_FAULT"
PROBE_RESULTS = {"passed", "degraded", "failed", "missing"}
BASIS_VALUES = {
    "observed",
    "reviewer_feedback",
    "user_instruction",
    "guess",
    "aesthetic_opinion",
    "residual",
}


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


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", required=True)
    common.add_argument("--run-id", required=True)
    common.add_argument("--json", action="store_true")
    parser = argparse.ArgumentParser(description="记录教程学习闭环的可审计运行事实")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("record-capability", "record-decision", "record-usage"):
        command = subparsers.add_parser(name, parents=[common])
        command.add_argument("--input", required=True)
    finalize_parser = subparsers.add_parser("finalize", parents=[common])
    finalize_parser.add_argument("--manifest-input", required=True)
    finalize_parser.add_argument("--ledger-input", required=True)
    finalize_parser.add_argument("--retrospective-input", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = Path(args.repo).expanduser().resolve()
        if not repo.is_dir():
            raise LearningError(f"仓库目录不存在：{args.repo}")
        with repository_lock(repo):
            # 锁内重新读取 run，禁止使用进程启动时的 stale snapshot。
            _, run_dir, run_path, run = resolve_context(str(repo), args.run_id)
            if args.command == "record-capability":
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
            elif args.command == "finalize":
                result = finalize(
                    run_dir,
                    run_path,
                    run,
                    read_draft(run_dir, args.manifest_input, "manifest draft"),
                    read_draft(run_dir, args.ledger_input, "ledger draft"),
                    read_draft(run_dir, args.retrospective_input, "retrospective draft"),
                )
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
