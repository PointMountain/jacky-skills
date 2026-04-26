#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  repo-study-translate.sh [--root DIR] [--json] [--force] [--group-size N]

Description:
  Build translation tasks for markdown files in a repo-study project.
  The script NEVER edits source files. Target files are always *.zh.md.

Options:
  --root DIR       Base directory to scan (default: current directory)
  --json           Print JSON output (default: text table)
  --force          Include tasks even when target *.zh.md already exists
  --group-size N   Suggested max tasks per subagent group (default: 20)
  -h, --help       Show this help

Examples:
  ./scripts/repo-study-translate.sh
  ./scripts/repo-study-translate.sh --json
  ./scripts/repo-study-translate.sh --group-size 12
  ./scripts/repo-study-translate.sh --force --json
EOF
}

ROOT_DIR="$PWD"
FORMAT="text"
FORCE=false
GROUP_SIZE=20

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      [[ $# -lt 2 ]] && { echo "Missing value for --root" >&2; exit 2; }
      ROOT_DIR="$2"
      shift 2
      ;;
    --json)
      FORMAT="json"
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --group-size)
      [[ $# -lt 2 ]] && { echo "Missing value for --group-size" >&2; exit 2; }
      GROUP_SIZE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unsupported option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$GROUP_SIZE" =~ ^[0-9]+$ ]] || [[ "$GROUP_SIZE" -le 0 ]]; then
  echo "--group-size must be a positive integer" >&2
  exit 2
fi

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "Root directory not found: $ROOT_DIR" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found in PATH" >&2
  exit 1
fi

collect_markdown_files() {
  find "$ROOT_DIR" -type f -name "*.md" \
    ! -name "*.zh.md" \
    ! -path "*/.git/*" \
    ! -path "*/node_modules/*" \
    ! -path "*/dist/*" \
    ! -path "*/build/*" \
    ! -path "*/.next/*" \
    ! -path "*/coverage/*" \
    ! -path "*/.turbo/*" \
    | sort
}

to_relpath() {
  local abs="$1"
  local rel
  rel="${abs#$ROOT_DIR/}"
  if [[ "$rel" == "$abs" ]]; then
    printf "%s\n" "$abs"
  else
    printf "%s\n" "$rel"
  fi
}

to_target_relpath() {
  local rel="$1"
  printf "%s.zh.md\n" "${rel%.md}"
}

tasks_json="[]"
total_files=0
pending_tasks=0
skipped_existing=0
group_id=1
in_group_count=0

while IFS= read -r abs_path; do
  [[ -z "$abs_path" ]] && continue
  total_files=$((total_files + 1))

  src_rel="$(to_relpath "$abs_path")"
  target_rel="$(to_target_relpath "$src_rel")"
  target_abs="$ROOT_DIR/$target_rel"

  target_exists=false
  if [[ -f "$target_abs" ]]; then
    target_exists=true
  fi

  if [[ "$target_exists" == true && "$FORCE" != true ]]; then
    skipped_existing=$((skipped_existing + 1))
    continue
  fi

  if [[ "$in_group_count" -ge "$GROUP_SIZE" ]]; then
    group_id=$((group_id + 1))
    in_group_count=0
  fi
  in_group_count=$((in_group_count + 1))

  pending_tasks=$((pending_tasks + 1))

  task_item="$(
    jq -cn \
      --arg source "$src_rel" \
      --arg target "$target_rel" \
      --arg sourceAbs "$abs_path" \
      --arg targetAbs "$target_abs" \
      --argjson targetExists "$target_exists" \
      --argjson group "$group_id" \
      '{
        source: $source,
        target: $target,
        sourceAbs: $sourceAbs,
        targetAbs: $targetAbs,
        targetExists: $targetExists,
        group: $group
      }'
  )"
  tasks_json="$(jq --argjson item "$task_item" '. + [$item]' <<<"$tasks_json")"
done < <(collect_markdown_files)

summary_json="$(
  jq -cn \
    --arg rootDir "$ROOT_DIR" \
    --argjson force "$FORCE" \
    --argjson groupSize "$GROUP_SIZE" \
    --argjson totalFiles "$total_files" \
    --argjson pendingTasks "$pending_tasks" \
    --argjson skippedExisting "$skipped_existing" \
    --argjson groupCount "$group_id" \
    --argjson tasks "$tasks_json" \
    '{
      rootDir: $rootDir,
      force: $force,
      groupSize: $groupSize,
      totalFiles: $totalFiles,
      pendingTasks: $pendingTasks,
      skippedExisting: $skippedExisting,
      groupCount: (if $pendingTasks == 0 then 0 else $groupCount end),
      tasks: $tasks
    }'
)"

if [[ "$FORMAT" == "json" ]]; then
  printf "%s\n" "$summary_json"
  exit 0
fi

echo "repo-study translate plan"
echo "root: $ROOT_DIR"
echo "total markdown files: $total_files"
echo "pending translation tasks: $pending_tasks"
echo "skipped existing zh files: $skipped_existing"
if [[ "$pending_tasks" -gt 0 ]]; then
  echo "suggested subagent groups: $(jq -r '.groupCount' <<<"$summary_json") (group-size=$GROUP_SIZE)"
fi
echo

if [[ "$pending_tasks" -eq 0 ]]; then
  echo "No pending tasks."
  exit 0
fi

printf "%-6s | %-60s | %s\n" "group" "source" "target"
printf -- "--------+--------------------------------------------------------------+------------------------------\n"
jq -r '.tasks[] | [.group, .source, .target] | @tsv' <<<"$summary_json" | \
while IFS=$'\t' read -r g s t; do
  printf "%-6s | %-60s | %s\n" "$g" "$s" "$t"
done
