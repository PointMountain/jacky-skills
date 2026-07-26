# Todo CLI 安装与启动

## 前置条件

- Node.js 22 或更高版本
- npm

Apple Silicon 设备应使用原生 `arm64` Node：

```bash
node -p "process.arch"
```

期望输出：

```text
arm64
```

## 安装依赖

进入 Todo Skill 目录：

```bash
npm install
```

## 注册全局命令

```bash
npm link
```

验证：

```bash
todo --version
todo doctor
```

Agent 不依赖全局命令，可以直接运行：

```bash
node /path/to/todo-skill/bin/todo.mjs list
```

## 启动 Web

全局任务：

```bash
todo web
```

当前项目：

```bash
todo web --current-project
```

默认地址：

```text
http://127.0.0.1:4187
```

端口被占用时：

```bash
todo web --port 4190
```

## 常见问题

### 缺少依赖

如果提示找不到 `yaml`、`cac` 或 `@clack/prompts`，在 Skill 目录重新运行：

```bash
npm install
```

### 当前项目无法识别

`--current-project` 只能在 Git 仓库内使用。检查：

```bash
git rev-parse --show-toplevel
```

### 数据异常

```bash
todo doctor
todo index
```

`doctor` 负责发现问题，`index` 负责重建生成视图。
