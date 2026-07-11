# 图片风格预设

每个预设由 `style_prefix` 和 `style_suffix` 组成。所有配图共用，保证视觉一致性。

提示词最终格式：`{style_prefix}, {段落概念描述}, {style_suffix}`

---

## tech-illustration（默认）

扁平化技术插画，深色背景，霓虹点缀。

```
style_prefix: "flat design digital illustration, dark navy background, neon green and cyan accent lighting"
style_suffix: "clean vector lines, minimalist composition, high contrast, no text, no letters, no words"
```

**适合**：技术、编程、AI、系统设计

---

## minimal-line

极简线条画，大量留白，单色点缀。

```
style_prefix: "minimalist line art illustration, white background, single accent color"
style_suffix: "simple elegant composition, negative space, thin precise lines, no text, no letters"
```

**适合**：概念讲解、方法论、思维模型

---

## watercolor

水彩手绘风格，柔和渐变。

```
style_prefix: "soft watercolor painting, dreamy gradient background, artistic brush strokes"
style_suffix: "gentle pastel colors, ethereal atmosphere, hand-painted texture, no text, no letters"
```

**适合**：人文、创意、随笔、生活感悟

---

## isometric

等距视角 3D 插画。

```
style_prefix: "isometric 3D illustration, clean geometric shapes, soft ambient lighting"
style_suffix: "modern design, precise perspective, subtle shadows, no text, no letters, no words"
```

**适合**：系统架构、流程图解、数据管道

---

## pixel-art

像素复古风格。

```
style_prefix: "16-bit pixel art illustration, retro video game aesthetic, limited color palette"
style_suffix: "sharp clean pixels, nostalgic CRT feel, no text, no letters"
```

**适合**：趣味、游戏开发、怀旧主题

---

## dark-cyberpunk

暗黑赛博朋克，霓虹灯光。

```
style_prefix: "cyberpunk illustration, dark moody atmosphere, neon pink and blue lighting, rain reflections"
style_suffix: "holographic effects, dramatic cinematic composition, sci-fi aesthetic, no text, no letters"
```

**适合**：科幻、前沿技术、未来感

---

## 自定义风格

提供 `style_prefix` 和 `style_suffix` 即可创建自定义风格。

**提示词工程技巧**（针对 Flux 模型优化）：

1. **结尾加否定提示**：`no text, no letters, no words` 防止图片中出现乱码文字
2. **描述具体画面**：不要写"表达创新"，而是写"a glowing lightbulb hovering over a circuit board"
3. **限定色彩范围**：如 `limited to neon green and dark blue` 保持一致性
4. **封面图额外修饰**：加 `cinematic composition, wide angle, epic scale` 增强视觉冲击
