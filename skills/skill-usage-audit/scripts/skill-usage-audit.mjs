#!/usr/bin/env node
/**
 * skill-usage-audit —— 扫描 Claude Code / Codex 会话日志，统计各 Skill 的真实使用情况。
 *
 * 统计口径（两类信号分开呈现，不混算）：
 * 1. Claude Code 正式调用：JSONL 中 tool_use 且 name === "Skill" 的记录（精确，含 subagent 转写文件）。
 * 2. Codex 启发式：会话文本中出现 `<skill-name>/SKILL.md` 路径（只计会话数，标注为启发式）。
 *
 * 用法：
 *   node skill-usage-audit.mjs [--days N] [--skill 名称] [--json] [--no-codex]
 *                              [--claude-dir 路径] [--codex-dir 路径]
 */
import { readdir } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';
import { homedir } from 'node:os';
import { join, basename } from 'node:path';
import { parseArgs } from 'node:util';

// ---------- 纯逻辑（可测试） ----------

export function createStats() {
  return new Map(); // skill -> { invocations, sessions:Set, projects:Set, lastUsed }
}

function bump(stats, skill, session, project, ts) {
  let rec = stats.get(skill);
  if (!rec) {
    rec = { invocations: 0, sessions: new Set(), projects: new Set(), lastUsed: null };
    stats.set(skill, rec);
  }
  rec.invocations += 1;
  rec.sessions.add(session);
  if (project) rec.projects.add(project);
  if (ts && (!rec.lastUsed || ts > rec.lastUsed)) rec.lastUsed = ts;
}

/** 解析一行 Claude JSONL，返回 { cwd?, calls: [{skill, ts}] }。非 JSON 或无关行返回 null。 */
export function parseClaudeLine(line) {
  if (!line.includes('"Skill"') && !line.includes('"cwd"')) return null;
  let d;
  try { d = JSON.parse(line); } catch { return null; }
  const out = { cwd: typeof d.cwd === 'string' ? d.cwd : undefined, calls: [] };
  const content = d?.message?.content;
  if (Array.isArray(content)) {
    for (const c of content) {
      if (c && c.type === 'tool_use' && c.name === 'Skill' && c.input?.skill) {
        out.calls.push({ skill: String(c.input.skill), ts: d.timestamp || null });
      }
    }
  }
  return (out.cwd || out.calls.length) ? out : null;
}

/**
 * 从一行 Codex JSONL 中提取真实使用的 skill 名。
 * 两道门都要过，否则会把「系统提示里的技能清单」和「在仓库里开发 SKILL.md」误计为使用：
 * 1. 该行必须是工具调用（payload.type 为 custom_tool_call / function_call / local_shell_call）；
 * 2. 路径必须位于安装根（.agents/skills、.claude/skills、.codex/skills）下。
 */
const CODEX_CALL_TYPES = new Set(['custom_tool_call', 'function_call', 'local_shell_call']);
const INSTALLED_SKILL_RE = /\.(?:agents|claude|codex)\/skills\/([a-z0-9][a-z0-9-]*)\/SKILL\.md/g;

export function extractCodexSkillNames(line) {
  if (!line.includes('SKILL.md')) return [];
  let d;
  try { d = JSON.parse(line); } catch { return []; }
  if (!CODEX_CALL_TYPES.has(d?.payload?.type)) return [];
  const names = [];
  let m;
  INSTALLED_SKILL_RE.lastIndex = 0;
  while ((m = INSTALLED_SKILL_RE.exec(line)) !== null) names.push(m[1]);
  return names;
}

// ---------- 文件扫描 ----------

async function* walkJsonl(dir) {
  let entries;
  try { entries = await readdir(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* walkJsonl(p);
    else if (e.isFile() && e.name.endsWith('.jsonl')) yield p;
  }
}

async function scanClaude(dir, stats, { since, skillFilter }) {
  for await (const file of walkJsonl(dir)) {
    const session = basename(file, '.jsonl');
    let cwd = null;
    const rl = createInterface({ input: createReadStream(file), crlfDelay: Infinity });
    for await (const line of rl) {
      const parsed = parseClaudeLine(line);
      if (!parsed) continue;
      if (!cwd && parsed.cwd) cwd = parsed.cwd;
      for (const { skill, ts } of parsed.calls) {
        if (skillFilter && skill !== skillFilter) continue;
        if (since && ts && new Date(ts) < since) continue;
        bump(stats, skill, session, cwd, ts);
      }
    }
  }
}

async function scanCodex(dir, stats, { since, skillFilter }) {
  for await (const file of walkJsonl(dir)) {
    // 路径形如 .../sessions/YYYY/MM/DD/rollout-*.jsonl，用日期段做过滤
    const m = file.match(/(\d{4})\/(\d{2})\/(\d{2})/);
    const day = m ? `${m[1]}-${m[2]}-${m[3]}` : null;
    if (since && day && new Date(day) < since) continue;
    const session = basename(file, '.jsonl');
    const seen = new Set();
    const rl = createInterface({ input: createReadStream(file), crlfDelay: Infinity });
    for await (const line of rl) {
      for (const name of extractCodexSkillNames(line)) {
        if (skillFilter && name !== skillFilter) continue;
        if (seen.has(name)) continue;
        seen.add(name);
        bump(stats, name, session, null, day ? `${day}T00:00:00Z` : null);
      }
    }
  }
}

// ---------- 输出 ----------

function toRows(stats) {
  return [...stats.entries()]
    .map(([skill, r]) => ({
      skill,
      invocations: r.invocations,
      sessions: r.sessions.size,
      projects: [...r.projects].map((p) => p.replace(homedir(), '~')),
      lastUsed: r.lastUsed ? r.lastUsed.slice(0, 10) : '-',
    }))
    .sort((a, b) => b.invocations - a.invocations || a.skill.localeCompare(b.skill));
}

function printTable(title, rows, note) {
  console.log(`\n== ${title} ==`);
  if (note) console.log(`(${note})`);
  if (!rows.length) { console.log('  （无记录）'); return; }
  const w = Math.max(12, ...rows.map((r) => r.skill.length));
  console.log(`  ${'Skill'.padEnd(w)}  调用  会话  最近使用    项目`);
  for (const r of rows) {
    console.log(
      `  ${r.skill.padEnd(w)}  ${String(r.invocations).padStart(4)}  ${String(r.sessions).padStart(4)}  ${r.lastUsed.padEnd(10)}  ${r.projects.join(', ')}`,
    );
  }
}

// ---------- 主入口 ----------

const isMain = process.argv[1] && import.meta.url.endsWith(basename(process.argv[1]));
if (isMain) {
  const { values } = parseArgs({
    options: {
      days: { type: 'string' },
      skill: { type: 'string' },
      json: { type: 'boolean', default: false },
      'no-codex': { type: 'boolean', default: false },
      'claude-dir': { type: 'string', default: join(homedir(), '.claude', 'projects') },
      'codex-dir': { type: 'string', default: join(homedir(), '.codex', 'sessions') },
    },
  });
  const since = values.days ? new Date(Date.now() - Number(values.days) * 86400_000) : null;
  const opts = { since, skillFilter: values.skill };

  const claudeStats = createStats();
  await scanClaude(values['claude-dir'], claudeStats, opts);
  const codexStats = createStats();
  if (!values['no-codex']) await scanCodex(values['codex-dir'], codexStats, opts);

  const claudeRows = toRows(claudeStats);
  const codexRows = toRows(codexStats);
  if (values.json) {
    console.log(JSON.stringify({ claude: claudeRows, codex: codexRows }, null, 2));
  } else {
    printTable('Claude Code · 正式 Skill 调用', claudeRows);
    printTable('Codex · 工具调用读取安装的 SKILL.md（启发式，仅计会话数）', codexRows,
      '内联/间接使用不产生正式记录，实际使用量可能高于此表');
  }
}
