import test from 'node:test';
import assert from 'node:assert/strict';
import { parseClaudeLine, extractCodexSkillNames } from '../scripts/skill-usage-audit.mjs';

test('parseClaudeLine 提取正式 Skill 调用与 cwd', () => {
  const line = JSON.stringify({
    cwd: '/tmp/demo',
    timestamp: '2026-07-18T10:00:00.000Z',
    message: {
      content: [
        { type: 'tool_use', name: 'Skill', input: { skill: 'app-flow' } },
        { type: 'text', text: 'hello' },
      ],
    },
  });
  const r = parseClaudeLine(line);
  assert.equal(r.cwd, '/tmp/demo');
  assert.deepEqual(r.calls, [{ skill: 'app-flow', ts: '2026-07-18T10:00:00.000Z' }]);
});

test('parseClaudeLine 不把 Bash 命令文本里的 skill 名误计为调用', () => {
  const line = JSON.stringify({
    message: {
      content: [
        { type: 'tool_use', name: 'Bash', input: { command: 'grep "Launching skill: app-flow" x.jsonl' } },
      ],
    },
  });
  assert.equal(parseClaudeLine(line), null);
});

test('parseClaudeLine 对非 JSON 行返回 null', () => {
  assert.equal(parseClaudeLine('not json "Skill"'), null);
});

test('extractCodexSkillNames 统计工具调用中安装路径下的 SKILL.md 读取', () => {
  const line = JSON.stringify({
    type: 'response_item',
    payload: {
      type: 'custom_tool_call',
      input: 'cat ~/.agents/skills/app-flow-delivery/SKILL.md; cat .claude/skills/git-standards/SKILL.md',
    },
  });
  assert.deepEqual(extractCodexSkillNames(line), ['app-flow-delivery', 'git-standards']);
});

test('extractCodexSkillNames 不计系统提示里的技能清单（非工具调用行）', () => {
  const line = JSON.stringify({
    type: 'session_meta',
    payload: { instructions: 'available: ~/.agents/skills/app-flow/SKILL.md' },
  });
  assert.deepEqual(extractCodexSkillNames(line), []);
});

test('extractCodexSkillNames 不计仓库开发路径（非安装根）', () => {
  const line = JSON.stringify({
    type: 'response_item',
    payload: { type: 'custom_tool_call', input: 'edit jacky-skills/labs/app-flow/app-flow/SKILL.md' },
  });
  assert.deepEqual(extractCodexSkillNames(line), []);
});

test('extractCodexSkillNames 无匹配返回空数组', () => {
  assert.deepEqual(extractCodexSkillNames('nothing here'), []);
});
