# Skill 使用清单、外部能力探测与批量可插拔

> 工作流应复用已经存在且真实可用的能力，并记录本轮究竟用了什么。Skill 通过能力槽位接入，才能在事实发生变化后被批量启用、停用、替换或重排。

## 两类信息分开

### 稳定能力注册表

进入版本控制，描述能力需求、候选 Skill、探测方法和降级路径，但不声称它们此刻一定可用：

```yaml
capabilities:
  prototype_design:
    candidates: [external-prototype-skill, browser-prototype]
    probe: "检查 Skill 是否可调用，并执行最小样例"
    fallback: html-prototype
```

### 运行时状态

写入本轮目录或 `*.local.yaml`，不作为长期事实提交：

```yaml
checked_at: "<current timestamp>"
capabilities:
  prototype_design:
    status: available   # available | degraded | missing
    selected: external-prototype-skill
    evidence: "最小原型已生成并可打开"
    fallback: html-prototype
```

状态必须带证据和检查时间；“目录存在”不等于“能力可用”。

## Skills 使用清单：记录实际发生的组合

稳定注册表只描述候选，运行时状态只描述探测结果；任务结束时还需要一份 `skill_usage_manifest`，记录内部 Skill、外部 Skill 和 fallback 在本轮实际承担了什么职责。

```yaml
skill_usage_manifest:
  run_id: "<run-id>"
  skills:
    - capability: prototype_design
      phase: prototype
      candidates_checked: [external-prototype-skill, browser-prototype]
      selected: browser-prototype
      source: "<插件、仓库或本地路径>"
      revision: "<版本、commit 或校验值；不可得时为 null>"
      mode: primary # primary | fallback
      inputs: [research-spec]
      outputs: [prototype]
      result: passed # passed | degraded | failed
      evidence: "<可复核产物、测试或日志>"
      friction: null
      adjustment_candidate: null
```

清单记录的是运行事实：

- `capability` 说明为什么需要它，避免只统计工具名；
- `candidates_checked`、`selected` 和 `mode` 还原选择与降级过程；
- `source` 和 `revision` 在可获得时锁定实际使用的 Skill 身份，避免同名不同版本混淆；
- `inputs`、`outputs`、`result` 和 `evidence` 证明它是否完成契约；
- `friction` 记录能力摩擦；证据足够时才填写 `adjustment_candidate`，其中必须包含 `operation`、`reason` 和 `status: candidate`，它不直接修改稳定注册表。

“被调用过”不等于“有效”，“调用次数多”也不等于“应该保留”。判断依据始终是产物契约与验收证据。

## 选择流程

1. 从当前 SOP 提取所需能力，而不是先选工具名。
2. 读取稳定注册表，获得候选和 fallback。
3. 在当前环境做最小探测：能否触发、输入输出是否匹配、产物能否复核。
4. 记录 `available`、`degraded` 或 `missing`，以及证据和 `last_checked`。
5. 选择第一个满足当前质量与约束的候选；不是永远选择功能最多的。
6. 候选失败时按注册表降级，不能静默跳过整个阶段。
7. 只有所有候选与合理 fallback 都无法满足真实 SOP 时，才确认能力缺口并考虑新建 Skill。

## 以能力槽位实现可插拔

工作流阶段依赖的是 `prototype_design`、`web_deploy` 之类的能力，不应硬编码某个 Skill 名。稳定注册表为每个能力槽位维护有序候选：

```yaml
capabilities:
  prototype_design:
    enabled: true
    candidates:
      - id: external-prototype-skill
        enabled: true
        priority: 10
      - id: browser-prototype
        enabled: true
        priority: 20
    fallback: html-prototype
```

四种最小插拔操作是：

- **启用**：把已验证的新候选加入能力槽位；
- **停用**：保留候选定义但设为 `enabled: false`，便于审计和回滚；
- **替换**：加入替代候选并调整优先级，验证通过后再停用旧候选；
- **重排**：根据质量、约束和稳定性调整候选顺序。

阶段输入输出契约保持不变，候选 Skill 才能被替换而不牵连整个流程。薄适配 Skill 负责把不同候选的产物统一到该契约。

## 批量调整：用一个可审计变更集处理重复摩擦

多个复盘里的 `skill_adjustment_candidate` 可以聚类成一个批量变更集，但必须先通过证据门槛：

1. 按“能力槽位 + 同类根因”聚类，不能只按 Skill 名或调用次数聚类；
2. 确认问题可复现，或确认现有候选与阶段契约存在稳定缺口；
3. 为每项变更附上复盘与验收证据，并写明 `enable`、`disable`、`replace` 或 `reorder`；
4. 先对新组合执行最小探测和关键流程回归；
5. 验证通过后一次性更新稳定注册表，保留可回滚的旧组合；
6. 下一次真实运行继续验证，失败则回退并更新候选状态。

```yaml
skill_change_set:
  id: "<change-set-id>"
  changes:
    - operation: replace
      capability: prototype_design
      target: external-prototype-skill
      replacement: browser-prototype
      evidence_refs: ["<retrospective-ref>", "<probe-result>"]
  validation:
    probe: passed
    regression: passed
  rollback: "<previous-registry-version>"
```

“批量”表示多项调整在同一个证据化变更集中被审查和验证，不表示无条件自动执行。调整对象是声明式能力注册表；只有确证为通用规则时才另行修改 Skill 或 reference。

## 薄适配 Skill

当一个阶段需要在多个外部能力间选择时，可以创建薄适配 Skill。它只负责：

- 描述阶段输入输出；
- 执行运行时探测；
- 选择候选或 fallback；
- 统一产物契约；
- 记录决策证据。

它不应复制外部 Skill 的完整说明，也不重新实现已有工具。

## 可用状态如何自进化

- 新候选跑通：更新稳定注册表的候选与探测方法；
- 候选失效：本轮状态标记 `degraded/missing`，先走 fallback；
- 失效被证明是稳定变化：再更新注册表或对应 Skill；
- 多次复盘暴露同类能力摩擦：生成批量变更集，回归通过后再调整组合；
- 只在当前机器成立的状态留在本地，不写进公开规范；
- 外部 Skill 自报成功但产物不可用：记录为错误候选，验证根因后再进入 memory。

## 反模式

- 把安装清单当可用性证明；
- 在公开 YAML 中提交会漂移的“当前在线”状态；
- 没有 fallback，外部 Skill 一失败整个工作流就消失；
- 只记调用次数，不记录输入、输出、结果和证据；
- 一次失败就自动停用 Skill，或直接批量重写 Skill 内容；
- 阶段硬编码具体 Skill 名，导致替换候选时必须改完整流程；
- 为每个供应者创建一个重复流程；
- 未观察真实 SOP 就凭想象补 `background`、`feature` 等模块；
- 把外部 Skill 的偶发故障直接写成永久规则。
