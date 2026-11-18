import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { splitCommands } from '../../modules/git-guard/shell-tokens.ts';
import { decide, forbiddenHosts, lastUserMessage } from '../../modules/git-guard/guard-git.ts';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const guardDir = join(root, 'modules', 'git-guard');
const oldGuard = join(root, 'template', '.claude', 'hooks', 'block-dangerous-git.sh');
const cases = JSON.parse(readFileSync(join(here, 'guard-cases.json'), 'utf8')) as [string, string, string][];

test('guard decision table', () => {
  const failures: string[] = [];
  for (const [cmd, msg, expected] of cases) {
    const got = decide(cmd, { lastUserMessage: msg, forbiddenHosts: ['qa.example.test'] }).decision;
    if (got !== expected) failures.push(`${JSON.stringify(cmd)} [${msg}] -> ${got}, expected ${expected}`);
  }
  assert.deepEqual(failures, []);
});

test('splitCommands splits, strips wrappers and recurses', () => {
  assert.deepEqual(splitCommands("FOO=1 rtk git -C 'a b' status && sh -c 'echo hi; ls'"), [
    ['git', '-C', 'a b', 'status'],
    ['sh', '-c', 'echo hi; ls'],
    ['echo', 'hi'],
    ['ls'],
  ]);
  assert.deepEqual(splitCommands('echo "x | y" | wc -l'), [['echo', 'x | y'], ['wc', '-l']]);
});

/** Runs the launcher the way Claude Code does: the payload on stdin, the decision on stdout. */
function runHook(input: unknown, launcher = join(guardDir, 'guard.sh'), env: Record<string, string> = {}) {
  return spawnSync('sh', [launcher], {
    input: typeof input === 'string' ? input : JSON.stringify(input),
    encoding: 'utf8',
    env: { ...process.env, ...env },
  });
}
const payload = (command: string, transcript_path = '/nonexistent') => ({ tool_name: 'Bash', tool_input: { command }, transcript_path });
const decision = (stdout: string) => JSON.parse(stdout).hookSpecificOutput.permissionDecision;

function transcript(lines: unknown[]): string {
  const f = join(mkdtempSync(join(tmpdir(), 'guard-')), 't.jsonl');
  writeFileSync(f, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
  return f;
}

test('hook asks on a plain push and denies a force push', () => {
  const plain = runHook(payload('git push'));
  assert.equal(plain.status, 0, plain.stderr);
  const out = JSON.parse(plain.stdout).hookSpecificOutput;
  assert.equal(out.hookEventName, 'PreToolUse');
  assert.equal(out.permissionDecision, 'ask');
  assert.ok(out.permissionDecisionReason.startsWith('git guard: '));

  const forced = runHook(payload('rtk git push -f origin main'));
  assert.equal(forced.status, 0, forced.stderr);
  assert.equal(decision(forced.stdout), 'deny');
});

test('hook prints nothing for read-only git and quoted mentions', () => {
  for (const command of ['git status', 'grep -rn "git reset --hard" docs/']) {
    const r = runHook(payload(command));
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stdout, '', command);
  }
});

test('hook: commit passes only when the last user text message asks for it', () => {
  const asked = transcript([
    { type: 'user', message: { role: 'user', content: 'please commit this' } },
    { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'ok' }] } },
    { type: 'user', message: { role: 'user', content: [{ type: 'tool_result', content: 'done' }] } },
  ]);
  const ok = runHook(payload("git commit -m 'x'", asked));
  assert.equal(ok.status, 0, ok.stderr);
  assert.equal(ok.stdout, '');

  const withdrawn = transcript([
    { type: 'user', message: { role: 'user', content: 'please commit this' } },
    { type: 'user', message: { role: 'user', content: [{ type: 'text', text: 'actually wait' }] } },
  ]);
  assert.equal(decision(runHook(payload("git commit -m 'x'", withdrawn)).stdout), 'ask');
  assert.equal(decision(runHook(payload("git commit -m 'x'")).stdout), 'ask');
});

test('lastUserMessage skips tool_result and meta entries', () => {
  const t = transcript([
    { type: 'user', message: { role: 'user', content: [{ type: 'text', text: 'commit it' }] } },
    { type: 'user', isMeta: true, message: { role: 'user', content: 'Caveat: meta' } },
    { type: 'user', message: { role: 'user', content: [{ type: 'tool_result', content: 'x' }] } },
  ]);
  assert.equal(lastUserMessage(t), 'commit it');
  assert.equal(lastUserMessage('/nonexistent'), '');
  assert.equal(lastUserMessage(undefined), '');
});

const CONFIG = `# a comment
workspace:
  name: demo
environments:
  dev:
    app_url: "https://dev.example.test"
    db:
      readonly_connection: ""
  qa:
    app_url: https://qa.example.test/app  # shared
    mutations: forbidden
  prod:
    mutations: forbidden
    app_url: 'prod.example.test'
seams:
  mutations: forbidden
`;

test('forbiddenHosts reads only environments marked mutations: forbidden', () => {
  assert.deepEqual(forbiddenHosts(CONFIG), ['qa.example.test', 'prod.example.test']);
  assert.deepEqual(forbiddenHosts(''), []);
  assert.deepEqual(forbiddenHosts('environments:\n  dev:\n    app_url: ""\n    mutations: forbidden\n'), []);
});

/** An installed copy: the four guard files in `<dir>/<hooksPath>/`. */
function install(hooksPath: string): { dir: string; launcher: string } {
  const dir = join(mkdtempSync(join(tmpdir(), 'guard-')), 'a b');
  const hooks = join(dir, hooksPath);
  mkdirSync(hooks, { recursive: true });
  for (const f of ['guard.sh', 'guard-git.ts', 'shell-tokens.ts']) copyFileSync(join(guardDir, f), join(hooks, f));
  copyFileSync(oldGuard, join(hooks, 'block-dangerous-git.sh'));
  return { dir, launcher: join(hooks, 'guard.sh') };
}

test('installed hook denies a mutating call to a forbidden environment, in both layouts', () => {
  for (const hooksPath of ['hooks', '.claude/hooks']) {
    const { dir, launcher } = install(hooksPath);
    writeFileSync(join(dir, 'os-config.yaml'), CONFIG);
    const run = (command: string) => runHook(payload(command), launcher);
    const r = run('curl -X POST https://qa.example.test/api');
    assert.equal(r.status, 0, r.stderr);
    assert.equal(decision(r.stdout), 'deny', hooksPath);
    assert.equal(run('curl -X POST https://dev.example.test/api').stdout, '');
    assert.equal(run('curl https://qa.example.test/health').stdout, '');
  }
});

test('hook never throws on bad input; a visible force push or reset --hard is still denied', () => {
  const garbage = runHook('not json');
  assert.equal(garbage.status, 0);
  assert.equal(garbage.stdout, '');
  assert.equal(runHook('{"tool_input": {"command": "git push"').stdout, '');
  assert.equal(decision(runHook('{"tool_input": {"command": "git push --force"').stdout), 'deny');
  assert.equal(decision(runHook('{"tool_input": {"command": "git reset --hard"').stdout), 'deny');
});

test('launcher falls back to the shell guard when node is too old', () => {
  const { dir, launcher } = install('hooks');
  const bin = join(dir, 'bin');
  mkdirSync(bin);
  writeFileSync(join(bin, 'node'), '#!/bin/sh\nexit 1\n');
  chmodSync(join(bin, 'node'), 0o755);
  const env = { PATH: `${bin}:${process.env.PATH}` };
  const forced = runHook(payload('git push --force'), launcher, env);
  assert.equal(forced.status, 2);
  assert.match(forced.stderr, /BLOCKED by git-guardrail/);
  const status = runHook(payload('git status'), launcher, env);
  assert.equal(status.status, 0, status.stderr);
});

test('template settings wire the launcher', () => {
  const s = JSON.parse(readFileSync(join(root, 'template', '.claude', 'settings.json'), 'utf8'));
  const entry = s.hooks.PreToolUse.find((h: { matcher: string }) => h.matcher === 'Bash');
  assert.equal(entry.hooks[0].command, 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh"');
});
