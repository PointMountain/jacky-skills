#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import os from 'node:os';

function run(cmd, args = []) {
  const r = spawnSync(cmd, args, { encoding: 'utf8' });
  return {
    ok: r.status === 0,
    status: r.status,
    stdout: (r.stdout || '').trim(),
    stderr: (r.stderr || '').trim(),
  };
}

function which(bin) {
  return run('zsh', ['-lc', `command -v ${bin}`]);
}

function version(cmd, args = ['--version']) {
  const w = which(cmd);
  if (!w.ok) return { ok: false, value: null };
  const r = run('zsh', ['-lc', `${cmd} ${args.map((arg) => `'${arg.replace(/'/g, "'\\''")}'`).join(' ')}`]);
  return { ok: r.ok, value: (r.stdout || r.stderr || '').split('\n')[0] };
}

const required = [];
const optional = [];

const platform = `${os.platform()} ${os.arch()}`;
console.log(`Platform: ${platform}`);
if (os.platform() !== 'darwin' || os.arch() !== 'arm64') {
  optional.push('Recommended environment is macOS Apple Silicon (darwin arm64). Current platform can still run non-MLX parts.');
}

const nodeMajor = Number(process.versions.node.split('.')[0]);
console.log(`Node.js: ${process.version}`);
if (nodeMajor < 20) required.push('Node.js 20+ is required. Install via: brew install node');

for (const bin of ['python3', 'ffmpeg', 'ffprobe']) {
  const v = version(bin, bin.startsWith('ff') ? ['-version'] : ['--version']);
  if (!v.ok) required.push(`${bin} not found. Suggested install: ${bin === 'python3' ? 'brew install python' : bin === 'yt-dlp' ? 'brew install yt-dlp' : 'brew install ffmpeg'}`);
  else console.log(`${bin}: ${v.value}`);
}

const ytdlpBin = version('yt-dlp');
let ytdlpModulePresent = false;

const pyCheck2 = run('bash', ['-lc', `python3 - <<'PY'
import importlib.util
import pathlib
import sys
deps = pathlib.Path(".deps").resolve()
if deps.exists():
    sys.path.insert(0, str(deps))
mods = ["yt_dlp", "mlx_whisper", "openai"]
for m in mods:
    print(f"{m}:{bool(importlib.util.find_spec(m))}")
PY`]);
if (pyCheck2.ok) {
  for (const line of pyCheck2.stdout.split('\n').filter(Boolean)) {
    const [mod, present] = line.split(':');
    if (mod === 'yt_dlp') {
      ytdlpModulePresent = present === 'True';
      if (ytdlpBin.ok) console.log(`yt-dlp: ${ytdlpBin.value}`);
      else if (ytdlpModulePresent) console.log('yt-dlp: available via python3 -m yt_dlp');
      else required.push('yt-dlp not found. Install binary, set YT_DLP_BIN, or install Python package: python3 -m pip install yt-dlp');
    }
    if (mod === 'mlx_whisper' && present !== 'True') {
      optional.push('Python package mlx-whisper not found. Needed when no subtitles exist and local audio transcription is required. Install: python3 -m pip install mlx-whisper');
    }
    if (mod === 'openai' && present !== 'True') {
      optional.push('Python package openai not found. Needed only for API-based image generation. Install: python3 -m pip install openai');
    }
    console.log(`python module ${mod}: ${present}`);
  }
} else {
  required.push('Unable to check Python modules.');
}

if (!process.env.OPENAI_API_KEY) {
  optional.push('OPENAI_API_KEY is not set. Image generation helper will be disabled, but Codex/agent can still analyze files.');
}

if (required.length) {
  console.error('\nMissing required dependencies:');
  for (const item of required) console.error(`- ${item}`);
  if (optional.length) {
    console.error('\nOptional notes:');
    for (const item of optional) console.error(`- ${item}`);
  }
  process.exit(1);
}

console.log('\nRequired dependencies OK.');
if (optional.length) {
  console.log('\nOptional notes:');
  for (const item of optional) console.log(`- ${item}`);
}
process.exit(0);
