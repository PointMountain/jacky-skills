#!/bin/bash
# hooks/topic-awareness.sh
# SessionStart Hook：注入知识收集意识
# skill: ob-topic

cat << 'EOF'
<system-reminder>
## 知识收集提醒 (ob-topic)

你在对话中识别到以下类型的**通用知识点**时，主动询问用户是否收藏到 Obsidian 知识库：
- 技术原理/概念解释（如"XX 的工作原理是..."）
- 最佳实践/经验总结（如"建议用 XX 方式处理..."）
- 非项目绑定的有价值知识

判断标准：如果这个知识点对未来的其他对话也有参考价值，就值得收藏。

不要提醒：临时调试命令、代码修改细节、项目特定配置。

用户说 /save、/collect、收藏 时立即执行收藏，不再询问确认。
</system-reminder>
EOF
