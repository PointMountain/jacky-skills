# 成品 Prompt 食谱

> 三个完整示例，演示「四层叠加公式」的实际组装效果。基底层在示例中以 `[基底层]` 代指，使用时替换为 SKILL.md 中的固定文案。

## 示例一：开篇定调图（版式 A · 单幕剧）

**文章**：《为什么你的 Code Review 总是没人看》

```
[基底层]

LAYOUT: single full-frame scene. A cozy desk corner viewed slightly
from above, lots of cream paper left empty around it.

CHARACTERS:
- A-Ma (round glasses, ginger sweater): slumped over his desk in
  despair, a tiny rain cloud doodled above his head.
- Bean (single ahoge hair strand, big eyes, off-white hoodie): peeking
  from behind the monitor, curious and slightly worried.
- An orange cat sleeping on a stack of unreviewed printouts labeled
  with tiny handwritten "PR".

PROPS: a monitor showing a long scroll with "+2048 −13" scribbled on
it; three sticky notes drifting off the desk.

HANDWRITTEN LABELS: "没人看的 PR" in large casual Chinese brush
handwriting at the top left.
```

## 示例二：方案对比图（版式 B · 左右对照）

**文章**：《从瀑布式提交到小步快跑》

```
[基底层]

LAYOUT: split comparison divided by a loose hand-drawn wavy line.

LEFT half "巨型提交" — entirely desaturated to muted gray (#ADB2BD):
- A-Ma pushing an enormous gray boulder with "1 commit / 月" chalked
  on it, sweating, completely flattened body language.
- Below: handwritten "一次全交，谁都不敢碰".

RIGHT half "小步快跑" — warm apricot and orange tones:
- A-Ma jogging lightly along a path of small stepping stones, each
  stone a tiny warm-orange card; Bot trotting behind carrying one
  more stone, chest light glowing.
- Below: handwritten "每天一小步".

No big red cross marks — the verdict is told purely by color and the
characters' moods.
```

## 示例三：收尾总结图（版式 C · 四宫格）

**文章**：《写好技术文档的四个习惯》

```
[基底层]

LAYOUT: 2x2 grid, cells separated by soft hand-drawn pencil lines,
each cell topped with a small warm-orange banner.

CELL 1 banner "先写目录": Bean sketching a tree outline on paper,
tongue out in concentration.

CELL 2 banner "一段一事": A-Ma slicing a long paragraph into three
short blocks with a pencil like cutting a cake.

CELL 3 banner "给出例子": Hui (bun hair, apricot apron top) holding up
a small framed picture, beaming.

CELL 4 banner "请人试读": Bot reading a sheet of paper, a handwritten
"看懂了!" speech bubble, orange chest light glowing happily.

The orange cat curled in the very center where the four cells meet.
```

## 组装提醒

- 基底层永远原样保留，不要为单图临时改风格描述
- 角色外观描述每次都要完整带上（生图模型没有记忆）
- 中文标注控制在每图 1~3 处，多了会被模型画崩
- 同一篇文章的系列图，生成后并排检查角色一致性
