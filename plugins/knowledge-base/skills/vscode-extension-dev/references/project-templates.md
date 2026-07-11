# VSCode 插件项目模板

> 初始化项目或生成新功能模块时读取。这里保留核心配置、基础入口、状态栏模板和 contributes 配置的完整示例。

## 目录

- [核心配置文件](#phase-2-核心配置文件)
- [功能模块生成](#phase-3-功能模块生成)

## Phase 2: 核心配置文件

**目标**: 生成开发环境所需的配置文件

**步骤**:

### 2.1 package.json

```json
{
  "name": "<extension-name>",
  "displayName": "<Display Name>",
  "description": "<Extension description>",
  "version": "0.0.1",
  "publisher": "<your-publisher-id>",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/<username>/<extension-name>.git"
  },
  "engines": { "vscode": "^1.85.0" },
  "categories": ["Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./dist/extension.js",
  "contributes": {
    "commands": [],
    "keybindings": [],
    "configuration": {}
  },
  "scripts": {
    "vscode:prepublish": "pnpm run package",
    "compile": "webpack",
    "watch": "webpack --watch",
    "package": "webpack --mode production --devtool hidden-source-map",
    "lint": "eslint src --ext ts",
    "test": "vscode-test",
    "build": "pnpm run package",
    "package:vsix": "vsce package",
    "publish:vsce": "vsce publish",
    "publish:ovsx": "ovsx publish --no-dependencies",
    "publish:all": "pnpm run publish:vsce && pnpm run publish:ovsx",
    "deploy": "pnpm run build && pnpm run publish:all"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "@types/node": "18.x",
    "typescript": "^5.3.3",
    "ts-loader": "^9.5.1",
    "webpack": "^5.90.3",
    "webpack-cli": "^5.1.4",
    "@vscode/vsce": "^3.2.1",
    "ovsx": "^0.10.9"
  },
  "vsce": { "dependencies": false },
  "ovsx": { "dependencies": false }
}
```

### 2.2 tsconfig.json

```json
{
  "compilerOptions": {
    "module": "Node16",
    "target": "ES2022",
    "lib": ["ES2022"],
    "sourceMap": true,
    "rootDir": "src",
    "strict": true,
    "outDir": "out"
  }
}
```

### 2.3 webpack.config.js

```javascript
//@ts-check
'use strict';
const path = require('path');

const extensionConfig = {
  target: 'node',
  mode: 'none',
  entry: './src/extension.ts',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'extension.js',
    libraryTarget: 'commonjs2'
  },
  externals: { vscode: 'commonjs vscode' },
  resolve: { extensions: ['.ts', '.js'] },
  module: {
    rules: [{ test: /\.ts$/, exclude: /node_modules/, use: [{ loader: 'ts-loader' }] }]
  },
  devtool: 'nosources-source-map'
};

module.exports = [extensionConfig];
```

### 2.4 .vscode/launch.json

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Extension",
      "type": "extensionHost",
      "request": "launch",
      "args": ["--extensionDevelopmentPath=${workspaceFolder}"],
      "outFiles": ["${workspaceFolder}/dist/**/*.js"],
      "preLaunchTask": "webpack: watch"
    }
  ]
}
```

### 2.5 .vscodeignore

```
.vscode/**
.vscode-test/**
src/**
**/*.ts
**/*.map
.gitignore
node_modules/**
*.vsix
.git/**
docs/**
*.md
!README.md
!CHANGELOG.md
```

**Checkpoint**: 所有配置文件就位，`pnpm install && pnpm run compile` 无错误

---

## Phase 3: 功能模块生成

**目标**: 根据项目类型生成核心代码

**步骤**:

### 3.1 基础 extension.ts

```typescript
import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('Extension is now active!');

    const helloCommand = vscode.commands.registerCommand(
        '<extension-name>.hello',
        () => vscode.window.showInformationMessage('Hello World!')
    );
    context.subscriptions.push(helloCommand);
}

export function deactivate() {}
```

### 3.2 状态栏插件模板

```typescript
import * as vscode from 'vscode';

let statusBarItem: vscode.StatusBarItem | undefined;

export function activate(context: vscode.ExtensionContext) {
    // 创建状态栏图标
    statusBarItem = vscode.window.createStatusBarItem(
        '<extension-name>.statusBar',
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(robot) Action';
    statusBarItem.tooltip = 'Quick Action';
    statusBarItem.command = '<extension-name>.quickAction';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // 注册命令
    context.subscriptions.push(
        vscode.commands.registerCommand('<extension-name>.quickAction', async () => {
            const config = vscode.workspace.getConfiguration('<extension-name>');
            const command = config.get<string>('command', 'echo "Hello"');
            const terminal = vscode.window.createTerminal({ name: 'Quick Action' });
            terminal.sendText(command + '\n');
            terminal.show();
        })
    );
}

export function deactivate() { statusBarItem?.dispose(); }
```

### 3.3 package.json contributes

```json
{
  "contributes": {
    "commands": [{
      "command": "<extension-name>.quickAction",
      "title": "Quick Action",
      "category": "<Category>"
    }],
    "keybindings": [{
      "command": "<extension-name>.quickAction",
      "key": "cmd+shift+a",
      "when": "editorTextFocus"
    }],
    "configuration": {
      "title": "<Extension Name>",
      "properties": {
        "<extension-name>.command": {
          "type": "string",
          "default": "echo 'Hello'",
          "description": "执行的命令"
        }
      }
    }
  }
}
```

**Checkpoint**: `pnpm run watch` 成功，F5 调试可激活插件

---


