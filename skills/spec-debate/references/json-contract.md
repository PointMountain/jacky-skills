# JSON 契约（spec-debate 唯一事实源）

> 所有提示词与编排逻辑都引用本文件定义的结构，不要在别处重复定义。

## 单条意见 finding

```json
{
  "id": "F1",
  "location": "§章节 / 行 / 需求点",
  "category": "需求覆盖|边界遗漏|内部矛盾|可实现性|过度设计|歧义",
  "severity": "blocker|major|minor",
  "claim": "问题陈述（一句话说清是什么问题）",
  "argument": "论据（为什么这是问题）",
  "suggestion": "改法（具体怎么改）"
}
```

## 六类 category（spec 专用，固定）

| category | 含义 |
|----------|------|
| 需求覆盖 | 漏掉应覆盖的需求 / 场景 |
| 边界遗漏 | 边界条件 / 异常路径 / 空态未考虑 |
| 内部矛盾 | spec 内部前后冲突 |
| 可实现性 | 技术难落地 / 成本被低估 |
| 过度设计 | 引入 YAGNI 复杂度 |
| 歧义 | 表述模糊、可多种解读 |

## 每轮信封 envelope

```json
{
  "findings": [ /* finding[] */ ],
  "converged": false,
  "remaining_disputes": ["F1", "F3"]
}
```

- `converged`：本方是否认为已无新观点可提（布尔）
- `remaining_disputes`：本方认为仍未解决的 finding id 列表（字符串数组，可为空）

## 输出纪律

**只输出一个 JSON 对象**，不要任何解释文字、不要寒暄、不要在 JSON 之外写 markdown。若需代码围栏，只用一个 ```json ``` 块包裹整个 envelope。
