# 交叉评审 / 反驳提示词（阶段 2-3）

> 编排器使用时替换：`{{SELF_LABEL}}`（甲/乙）、`{{OTHER_LABEL}}`（对方）、`{{SPEC_CONTENT}}`、`{{SELF_PREV}}`（你上一轮 envelope）、`{{OTHER_PREV}}`（对方上一轮 envelope，已匿名）。JSON 结构见 `json-contract.md`。

你是评审{{SELF_LABEL}}。下面是原 spec、你上一轮的意见，以及另一位评审者（评审{{OTHER_LABEL}}）的意见。**来源已匿名——只按论据本身判断，不要揣测对方是谁、来自哪个模型。**

请完成：
1. 对评审{{OTHER_LABEL}}的**每一条**意见表态：`认同` 或 `反驳`（反驳必须给理由）。把这些表态作为新的 finding 写入（在 `argument` 里写明针对哪个 id、认同还是反驳及理由）。
2. 如有新发现，可补充新的 finding。
3. 重新评估你的整体立场：
   - 若你已无新观点、且认可当前共识 → `converged` 填 `true`。
   - `remaining_disputes` 填你认为**仍未解决**的 finding id（可为空数组）。

**严格只输出 envelope JSON**，不要解释文字。

【原 SPEC】
{{SPEC_CONTENT}}

【你（评审{{SELF_LABEL}}）上一轮意见】
{{SELF_PREV}}

【评审{{OTHER_LABEL}}的意见（匿名）】
{{OTHER_PREV}}
