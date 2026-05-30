# slugify-cli 设计文档（样例 / 故意留缺陷，供 spec-debate dry-run）

> 一个把剪贴板里的文本转成 URL slug 的命令行小工具。

## 目标

用户复制一段标题文本后，运行 `slugify`，工具读取剪贴板内容，转成小写连字符 slug（如 `My First Post!` → `my-first-post`），并把结果写回剪贴板。

## 功能

1. 读取系统剪贴板的纯文本。
2. 转换规则：
   - 转小写
   - 空格转连字符 `-`
   - 去除特殊字符
   - 连续连字符合并为一个
3. 把 slug 写回剪贴板，并在终端打印结果。

## 技术选型

- Node.js + `clipboardy` 读写剪贴板。
- 提供一个插件机制：允许用户注册自定义转换插件，按顺序对文本做额外处理；插件用独立配置文件 `~/.slugify/plugins.json` 声明，支持远程 URL 加载插件包。

## 使用

```bash
slugify
# 剪贴板: "Hello World" → 输出并写回: hello-world
```

## 完成标准

运行后剪贴板内容变成合法 slug，终端打印出来即可。
