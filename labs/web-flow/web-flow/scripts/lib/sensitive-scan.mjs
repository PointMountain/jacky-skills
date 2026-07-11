import { lstat, readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

const SENSITIVE_PATTERNS = Object.freeze([
  {
    kind: 'Authorization Bearer 凭证',
    pattern: /authorization\s*:\s*bearer\s+[^\s"']+/iu,
  },
  {
    kind: 'token/api-key/secret/password 赋值',
    pattern:
      /(?:^|[\s`{,:"'])["']?(?:token|api[-_]?key|secret|password)["']?\s*[:=]\s*["']?[^\s,"'}]+/imu,
  },
  {
    kind: 'macOS/Linux 用户绝对路径',
    pattern: /(?:^|[\s"'`=(])\/(?:Users|home)\/[^\s"'`]+/imu,
  },
  {
    kind: 'Windows 用户绝对路径',
    pattern: /(?:^|[\s"'`=(])[a-z]:\\+Users\\+[^\s"'`]+/imu,
  },
  {
    kind: 'private URL',
    pattern:
      /https?:\/\/(?:localhost|127(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|[a-z0-9.-]+\.local)(?=[:/\s?#]|$)/iu,
  },
]);

export function assertNoSensitiveContent(contents, label = 'content') {
  if (typeof contents !== 'string') {
    throw new TypeError(`${label} sensitive scan 只接受文本`);
  }
  for (const { kind, pattern } of SENSITIVE_PATTERNS) {
    if (pattern.test(contents)) {
      throw new Error(`${label} 命中 sensitive ${kind}`);
    }
  }
  return true;
}

async function collectMarkdownFiles(directory, relativeParent = '') {
  const files = [];
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const relativePath = relativeParent
      ? `${relativeParent}/${entry.name}`
      : entry.name;
    const absolutePath = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error(`sensitive scan 拒绝符号链接：${relativePath}`);
    }
    if (entry.isDirectory()) {
      files.push(...(await collectMarkdownFiles(absolutePath, relativePath)));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      files.push({ relativePath, absolutePath });
    }
  }
  return files;
}

export async function scanRunSensitiveFiles(runDir) {
  const absoluteRunDir = path.resolve(runDir);
  const runtimeFiles = ['run.json', 'events.jsonl', 'artifacts.jsonl'].map(
    (relativePath) => ({
      relativePath,
      absolutePath: path.join(absoluteRunDir, relativePath),
    }),
  );
  const files = [
    ...runtimeFiles,
    ...(await collectMarkdownFiles(absoluteRunDir)),
  ];

  for (const file of files) {
    const stats = await lstat(file.absolutePath);
    if (stats.isSymbolicLink() || !stats.isFile()) {
      throw new Error(`sensitive scan 目标必须是普通文件：${file.relativePath}`);
    }
    assertNoSensitiveContent(
      await readFile(file.absolutePath, 'utf8'),
      file.relativePath,
    );
  }
  return { scanned: files.length, files: files.map((file) => file.relativePath) };
}
