# WebFlow Review Template

> 复制下列结构到当前版本化 review 路径；不要覆盖已登记文件。

## Binding

| Field | Value |
| --- | --- |
| Stage | `<stage>` |
| Attempt | `<positive integer>` |
| Review kind | `subjective` 或 `must_pass_recheck` |
| Round / recheck | 主观轮次 1/2，或事实复检序号 |
| Reviewer | `<reviewer identity>` |
| Independence | `independent: true`；否则写 limitation |
| Rubric ref | `web-flow-benchmark/references/rubrics.md#<stage>` |
| Rubric SHA-256 | `<raw rubric file hash>` |
| Artifact ref | `<artifact-id>@<revision>` |
| Artifact SHA-256 | `<live artifact hash>` |

## Must-pass

| Check | Result | Direct evidence |
| --- | --- | --- |
| `<check id>` | `passed` / `failed` | 文件、命令、HTTP、browser、console 或实时 hash 证据 |

任一事实门失败后停止主观评分：Weighted score 写 `null`，Decision 写 `blocked`，Top fix 只写最先需要恢复的事实条件。

## Subjective scores

| Dimension | Weight | Score (0–5) | Evidence |
| --- | ---: | ---: | --- |
| `<rubric dimension>` | `<weight>` | `<score>` | `<artifact-grounded evidence>` |

## Result

| Field | Value |
| --- | --- |
| Must-pass | `passed` / `failed` |
| Weighted score | `<0–5>` 或 `null` |
| Threshold | `3.5` |
| Decision | `pass` / `revise_once` / `proceed_with_residual` / `blocked` |
| Top fix | `<one fix only>` 或 `none` |
| Residual | `<remaining issues>` 或 `none` |

## Memory candidate

只有真实错误才填写：actual error、root cause verified、likely to recur、evidence。审美偏好或单纯低分写 `none`。

写完后计算 review 原始字节 hash，并通过 runtime `review record` 登记。主观评审路径是 `reviews/<stage>/attempt-<n>/round-<n>--<artifact-id>-r<revision>.md`；事实复检路径由运行时根据 recheck 序号生成。
