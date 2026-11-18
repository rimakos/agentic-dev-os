// PreToolUse(Bash) hook: denies destructive git, asks before git writes (push, add, commit, stash,
// new branch) and denies mutating HTTP calls to environments marked `mutations: forbidden`.
// Never throws; on internal error it stays silent, except that a command that visibly contains a
// force push or `reset --hard` is still denied.
// Adapted from the AutopilotOS kit with its author's permission.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { basename, gitSubcommand, OPAQUE, splitCommands } from './shell-tokens.ts';

export type Decision = { decision: 'allow' | 'deny' | 'ask'; reason: string };
export type Ctx = { lastUserMessage: string; forbiddenHosts: string[] };

const deny = (reason: string): Decision => ({ decision: 'deny', reason });
const ask = (reason: string): Decision => ({ decision: 'ask', reason });

/** True when `arg` is `--full` or an abbreviation of it at least `min` characters long. */
function longOpt(arg: string, full: string, min: number): boolean {
  const name = arg.split('=')[0];
  return name.length >= min && full.startsWith(name);
}
/** True when `arg` is a short-option cluster (e.g. `-xdf`) containing `letter`. */
function shortHas(arg: string, letter: string): boolean {
  return /^-[A-Za-z]+$/.test(arg) && arg.includes(letter);
}

const ALL_PATHS = new Set(['.', './', ':/', ':/.', ':(top)', '*']);

const COMMIT_REQUEST = [
  /^commit\b(?!\s*(messages?|msgs?|hooks?|format|history|logs?)\b|-msg)/,
  /\b(please|pls|go ahead( and)?|can you|could you|would you|will you|now)\s+commit\b/,
  /\bcommit\s+(it|this|that|these|those|them|both|all|now|the changes|pls|please)\b/,
];
const NEGATION =
  /\b(don'?t|do not|not|no|never|shouldn'?t|should not|can'?t|cannot|can not|hold off|wait|not yet|without|i'?ll|i will|i'?m going to|let me|we'?ll)\b/;

/** True only for a request-shaped commit instruction with no negation before `commit` in any sentence. */
export function userAskedToCommit(msg: string): boolean {
  const text = msg.toLowerCase().replace(/[‘’]/g, "'").trim();
  const sentences = (text.match(/[^.!?;\n]+[.!?;\n]*/g) ?? []).map((s) => s.trim()).filter(Boolean);
  let requested = false;
  for (const raw of sentences) {
    const s = raw.replace(/[.!?;\s]+$/, '');
    for (const m of s.matchAll(/\bcommit/g)) {
      if (NEGATION.test(s.slice(0, m.index))) return false;
    }
    if (!COMMIT_REQUEST.some((re) => re.test(s))) continue;
    // A question is only a request when phrased as one ("can you commit it?").
    if (raw.endsWith('?') && !/^(can|could|would|will) you\b/.test(s)) continue;
    requested = true;
  }
  return requested;
}

/** `-c` keys that cannot make git run anything; every other key needs review. */
const SAFE_KEY =
  /^(user\..+|color\..+|core\.(quotepath|autocrlf|safecrlf)|init\..+|log\..+|format\..+|advice\..+|i18n\..+|safe\.directory|column\..+|status\..+|push\..+)$/;
/** `-c` keys whose value is a program, shell command or included config that git will act on. */
const COMMAND_KEY =
  /^(core\.(pager|editor|sshcommand|fsmonitor|askpass|hookspath)|sequence\.editor|diff\.external|diff\..+\.(textconv|command)|filter\..+\.(clean|smudge|process)|merge\..+\.driver|credential\.helper|credential\..+\.helper|gpg\.program|gpg\..+\.program|remote\..+\.(uploadpack|receivepack)|include\.path|includeif\..+\.path|uploadpack\.packobjectshook)$/;

/** `-c key=value` / `--config-env key=VAR`: safe keys pass, command-valued keys recurse, the rest ask. */
function configRule(configs: string[], configEnv: string[], ctx: Ctx): Decision | null {
  let result: Decision | null = null;
  const entries = [
    ...configs.map((c) => ({ c, fromEnv: false })),
    ...configEnv.map((c) => ({ c, fromEnv: true })),
  ];
  for (const { c, fromEnv } of entries) {
    const eq = c.indexOf('=');
    const key = (eq < 0 ? c : c.slice(0, eq)).toLowerCase();
    const value = eq < 0 ? 'true' : c.slice(eq + 1);
    if (SAFE_KEY.test(key)) continue;
    if (/^pager\..+$/.test(key) && !fromEnv && /^(true|false)$/i.test(value)) continue;
    let nested: string | null = null;
    if (!fromEnv) {
      if (key.startsWith('alias.')) nested = value.startsWith('!') ? value.slice(1) : `git ${value}`;
      else if (COMMAND_KEY.test(key)) nested = value.replace(/^!/, '');
    }
    if (nested !== null && decide(nested, ctx).decision === 'deny') {
      return deny(`git config ${key} would run a blocked command`);
    }
    result ??= ask(`git config ${key} set on the command line needs review`);
  }
  return result;
}

function gitRule(argv: string[], ctx: Ctx): Decision | 'gate' | null {
  const { sub, args, configs, configEnv } = gitSubcommand(argv);
  const cfg = configRule(configs, configEnv, ctx);
  if (cfg?.decision === 'deny') return cfg;
  const r = subRule(sub, args);
  if (cfg && (r === null || r === 'gate')) return cfg;
  return r;
}

/** `git push` options that take a separate value, so the value is not read as a refspec. */
const PUSH_VALUE_OPTS = new Set(['-o', '--push-option', '--repo', '--receive-pack', '--exec']);

/** A push that overwrites or deletes remote refs is denied; every other push asks. */
function pushRule(args: string[]): Decision {
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (PUSH_VALUE_OPTS.has(a)) i++;
    else if (/^--for/.test(a) || shortHas(a, 'f')) return deny('git push --force overwrites remote history');
    else if (longOpt(a, '--mirror', 3)) return deny('git push --mirror overwrites every remote ref');
    else if (longOpt(a, '--delete', 3) || shortHas(a, 'd') || longOpt(a, '--prune', 4) || a.startsWith(':')) {
      return deny('this git push deletes remote branches');
    } else if (a.startsWith('+')) return deny('git push +refspec is a force push');
  }
  return ask('git push publishes work; the user confirms it');
}

function subRule(sub: string | undefined, args: string[]): Decision | 'gate' | null {
  switch (sub) {
    case 'push':
    case 'send-pack':
      return pushRule(args);
    case 'subtree':
    case 'lfs':
      return args.includes('push') ? ask(`git ${sub} push publishes work; the user confirms it`) : null;
    case 'reset':
      return args.some((a) => longOpt(a, '--hard', 3)) ? deny('git reset --hard discards work') : null;
    case 'clean':
      return args.some((a) => longOpt(a, '--force', 3) || shortHas(a, 'f'))
        ? deny('git clean --force deletes untracked files')
        : null;
    case 'checkout': {
      if (args.some((a) => longOpt(a, '--force', 3) || shortHas(a, 'f'))) return deny('git checkout --force discards local changes');
      if (args.some((a) => ALL_PATHS.has(a))) return deny('git checkout . discards working-tree changes');
      const dd = args.indexOf('--');
      if (dd >= 0 && dd < args.length - 1) return ask('git checkout -- <path> discards changes to that path; the user confirms it');
      return args.some((a) => shortHas(a, 'b') || shortHas(a, 'B') || longOpt(a, '--orphan', 4))
        ? ask('git checkout -b creates a branch')
        : null;
    }
    case 'switch':
      if (args.some((a) => longOpt(a, '--force', 3) || longOpt(a, '--discard-changes', 4) || shortHas(a, 'f'))) {
        return deny('git switch --force/--discard-changes discards local changes');
      }
      return args.some((a) => shortHas(a, 'c') || shortHas(a, 'C') || /^--(cr|force-c|or)/.test(a))
        ? ask('git switch -c creates a branch')
        : null;
    case 'restore': {
      if (!args.some((a) => ALL_PATHS.has(a))) return null;
      const staged = args.some((a) => longOpt(a, '--staged', 4) || shortHas(a, 'S'));
      const worktree = args.some((a) => longOpt(a, '--worktree', 3) || shortHas(a, 'W'));
      return !staged || worktree ? deny('git restore . discards working-tree changes') : null;
    }
    case 'branch': {
      const del = args.some((a) => longOpt(a, '--delete', 4) || shortHas(a, 'd'));
      const force = args.some((a) => longOpt(a, '--force', 4) || shortHas(a, 'f'));
      if (args.some((a) => shortHas(a, 'D')) || (del && force)) return deny('git branch -D force-deletes a branch');
      // A name with no listing, delete, rename, copy or upstream option creates a branch.
      const other = /^(-[A-Za-z]*[dlmMcCu]|--(list|delete|move|copy|contains|no-contains|merged|no-merged|points-at|set-upstream-to|unset-upstream|edit-description))/;
      return !args.some((a) => other.test(a)) && args.some((a) => !a.startsWith('-')) ? ask('git branch <name> creates a branch') : null;
    }
    case 'rebase':
      return ask('git rebase rewrites local history; the user confirms it');
    case 'filter-branch':
    case 'filter-repo':
      return deny(`git ${sub} rewrites history`);
    case 'update-ref':
      return args.some((a) => a === '-d' || shortHas(a, 'd')) ? deny('git update-ref -d deletes refs') : null;
    case 'stash': {
      const op = args.find((a) => !a.startsWith('-'));
      if (op === 'drop' || op === 'clear') return deny(`git stash ${op} discards stashed work`);
      return op === 'list' || op === 'show' ? null : ask('git stash moves uncommitted work; the user confirms it');
    }
    case 'config': {
      const read = args.some((a) => /^(--get|--get-all|--get-regexp|--list|-l|get|list)$/.test(a));
      return !read && args.some((a) => /^alias\./i.test(a)) ? deny('defining git aliases is blocked') : null;
    }
    case 'commit':
      return args.some((a) => longOpt(a, '--amend', 4)) ? ask('git commit --amend rewrites the last commit; the user confirms it') : 'gate';
    case 'add':
      return 'gate';
    default:
      return null;
  }
}

function hostOf(arg: string, forbidden: string[]): string | null {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(arg)) {
    try {
      return new URL(arg).hostname.toLowerCase();
    } catch {
      return null;
    }
  }
  const a = arg.toLowerCase();
  return forbidden.find((h) => a === h || /^[/:?#]/.test(a.slice(h.length)) && a.startsWith(h)) ?? null;
}

const MUTATING = /^(POST|PUT|PATCH|DELETE)$/i;
const CURL_VALUE_SHORT = 'AbcCdDeEFHKmorTuUwxXyYz';

function isMutatingHttp(prog: string, args: string[]): boolean {
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const [name, inline] = a.split(/=(.*)/s, 2);
    const value = () => (inline !== undefined ? inline : args[i + 1] ?? '');
    if (prog === 'curl') {
      if (name === '--request') {
        if (MUTATING.test(value())) return true;
      } else if (name.startsWith('--data') || name === '--json' || name.startsWith('--form') || name === '--upload-file') {
        return true;
      } else if (/^-[A-Za-z]/.test(a)) {
        for (let j = 1; j < a.length; j++) {
          const c = a[j];
          if (!CURL_VALUE_SHORT.includes(c)) continue;
          if (c === 'X') {
            if (MUTATING.test(a.slice(j + 1) || (args[i + 1] ?? ''))) return true;
          } else if ('dFT'.includes(c)) return true;
          break;
        }
      }
    } else if (name === '--method') {
      if (MUTATING.test(value())) return true;
    } else if (/^--(post|body)-(data|file)$/.test(name)) return true;
  }
  return false;
}

/** Programs that never execute their arguments; exempt from the wrapped-git catch-all. */
const INERT = new Set([
  'echo', 'printf', 'grep', 'egrep', 'fgrep', 'rg', 'ag', 'ack', 'cat', 'less', 'more', 'head', 'tail', 'wc',
  'ls', 'true', 'false', 'test', '[', 'cd', 'pwd', 'which', 'type', 'man', 'sort', 'uniq', 'cut', 'tr', 'diff',
  'jq', 'yq', 'tee', 'touch', 'mkdir',
]);

function rank(d: Decision['decision']): number {
  return d === 'deny' ? 2 : d === 'ask' ? 1 : 0;
}

export function decide(command: string, ctx: Ctx): Decision {
  let result: Decision = { decision: 'allow', reason: '' };
  const raise = (d: Decision) => {
    if (rank(d.decision) > rank(result.decision)) result = d;
  };
  const gate = (r: Decision | 'gate' | null) => {
    if (r === 'gate') {
      if (!userAskedToCommit(ctx.lastUserMessage)) raise(ask('commit/add needs an explicit commit request from the user'));
    } else if (r) raise(r);
  };
  const forbidden = ctx.forbiddenHosts.map((h) => h.toLowerCase());
  // A construct that cannot be read statically only matters here when git is involved.
  const mentionsGit = /\bgit\b|GIT_/.test(command);
  for (const argv of splitCommands(command)) {
    const prog = basename(argv[0]);
    if (argv[0] === OPAQUE) {
      if (mentionsGit) raise(ask(argv[1]));
    } else if (argv[0].includes('$') || argv[0].includes('`')) {
      if (mentionsGit) raise(ask('command name comes from an expansion and cannot be checked'));
    } else if (prog === 'git') gate(gitRule(argv, ctx));
    else {
      if ((prog === 'curl' || prog === 'wget') && forbidden.length && isMutatingHttp(prog, argv.slice(1))) {
        const host = argv.slice(1).map((a) => hostOf(a, forbidden)).find((h) => h !== null && forbidden.includes(h));
        if (host) {
          raise(deny(`mutating request to ${host}, an environment with mutations: forbidden`));
          continue;
        }
      }
      // Catch-all for a program this guard does not know: `git …` in its arguments is judged as a
      // git command, and `git … push` inside one (quoted) argument asks. Programs that only print
      // or search text are exempt.
      if (!INERT.has(prog)) {
        const g = argv.findIndex((a, i) => i > 0 && basename(a) === 'git');
        if (g > 0) gate(gitRule(argv.slice(g), ctx));
        if (argv.slice(1).some((a) => /\bgit\b[^;]*\bpush\b/.test(a))) {
          raise(ask(`${prog} appears to run git push via a wrapper that cannot be checked`));
        }
      }
    }
  }
  return result;
}

/** Text of the last real user message in a Claude Code JSONL transcript; '' when unavailable. */
export function lastUserMessage(path: string | undefined): string {
  if (!path) return '';
  let raw: string;
  try {
    raw = readFileSync(path, 'utf8');
  } catch {
    return '';
  }
  const lines = raw.split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    if (!lines[i].trim()) continue;
    let e: { type?: string; isMeta?: boolean; message?: { content?: unknown } };
    try {
      e = JSON.parse(lines[i]);
    } catch {
      continue;
    }
    if (e?.type !== 'user' || e.isMeta) continue;
    const c = e.message?.content;
    if (typeof c === 'string') return c;
    if (!Array.isArray(c) || c.some((b) => b?.type === 'tool_result')) continue;
    const text = c.filter((b) => b?.type === 'text' && typeof b.text === 'string').map((b) => b.text);
    if (text.length) return text.join('\n');
  }
  return '';
}

/**
 * Hosts of the `environments.<name>.app_url` entries marked `mutations: forbidden` in os-config.yaml
 * text. Reads only those keys, by line, and expects the template's two-space indentation.
 */
export function forbiddenHosts(yaml: string): string[] {
  const hosts: string[] = [];
  let inEnvironments = false;
  let url = '';
  let forbidden = false;
  const endEnvironment = () => {
    try {
      if (forbidden && url) hosts.push(new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(url) ? url : `http://${url}`).hostname.toLowerCase());
    } catch {
      /* skip malformed url */
    }
    url = '';
    forbidden = false;
  };
  for (const line of yaml.split('\n')) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    if (/^\S/.test(line)) {
      endEnvironment();
      inEnvironments = /^environments:/.test(line);
    } else if (inEnvironments) {
      if (/^ {2}\S/.test(line)) endEnvironment();
      const value = line.match(/^ {4}(app_url|mutations):\s*["']?([^"'#\s]*)/);
      if (value?.[1] === 'app_url') url = value[2];
      if (value?.[1] === 'mutations') forbidden = value[2] === 'forbidden';
    }
  }
  endEnvironment();
  return hosts;
}

/** os-config.yaml sits one level above the hook (data folder) or two (workspace root). */
function configText(): string {
  for (const up of ['..', '../..']) {
    try {
      return readFileSync(join(import.meta.dirname, up, 'os-config.yaml'), 'utf8');
    } catch {
      /* try the next place */
    }
  }
  return '';
}

function emit(d: Decision): void {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: d.decision,
        permissionDecisionReason: `git guard: ${d.reason}`,
      },
    }),
  );
}

const VISIBLY_DESTRUCTIVE =
  /\bgit\b[^;|&]*\b(push\b[^;|&]*(\s--for|\s-[A-Za-z]*f\b|\s\+)|reset\b[^;|&]*\s--hard)/;

export function main(): void {
  let raw = '';
  try {
    raw = readFileSync(0, 'utf8');
    const input = JSON.parse(raw);
    const command = input?.tool_input?.command;
    if (typeof command !== 'string') return;
    const d = decide(command, {
      lastUserMessage: lastUserMessage(input.transcript_path),
      forbiddenHosts: forbiddenHosts(configText()),
    });
    if (d.decision !== 'allow') emit(d);
  } catch {
    try {
      if (VISIBLY_DESTRUCTIVE.test(raw)) emit(deny('force push or reset --hard seen in a command that could not be checked'));
    } catch {
      /* stay silent */
    }
  }
}

if (import.meta.main) {
  main();
  process.exitCode = 0;
}
