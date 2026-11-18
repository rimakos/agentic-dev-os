// Conservative POSIX-ish shell tokeniser used by the git guard hook. It never executes anything and
// never throws: unterminated quotes or substitutions simply consume the rest of the input.
// Adapted from the AutopilotOS kit with its author's permission.

/** argv emitted for constructs whose effect cannot be seen statically; the guard asks when git is involved. */
export const OPAQUE = '\u0000opaque';

const MAX_DEPTH = 8;
const SHELLS = new Set(['sh', 'bash', 'zsh', 'dash', 'ksh', 'fish', 'ash', 'mksh', 'tcsh', 'csh', 'pwsh', 'powershell']);
const KEYWORDS = new Set(['if', 'then', 'else', 'elif', 'fi', 'do', 'done', 'while', 'until', '!', '{', '}', 'exec']);
const ASSIGN_RE = /^[A-Za-z_][A-Za-z0-9_]*\+?=/;
/** Environment assignments that let a command inject git config, hooks or helper programs. */
export const GIT_ENV_RE =
  /^(GIT_CONFIG_COUNT|GIT_CONFIG_KEY_\d+|GIT_CONFIG_VALUE_\d+|GIT_CONFIG_PARAMETERS|GIT_CONFIG|GIT_CONFIG_GLOBAL|GIT_CONFIG_SYSTEM|GIT_SSH|GIT_SSH_COMMAND|GIT_EDITOR|GIT_SEQUENCE_EDITOR|GIT_PAGER|GIT_EXTERNAL_DIFF|GIT_EXEC_PATH|GIT_ASKPASS)\+?=/;
const BRACE_RE = /(^|[^$])\{[^{}]*(,|\.\.)[^{}]*\}/;

type Simple = { words: string[]; subs: string[]; here: string[]; opaque: string | null };

export function basename(word: string): string {
  return word.slice(word.lastIndexOf('/') + 1);
}

/** Index just past the `)` matching an opening `(` that ends at `start - 1`. */
function matchParen(s: string, start: number): number {
  let depth = 1;
  let i = start;
  while (i < s.length) {
    const c = s[i];
    if (c === '\\') i += 2;
    else if (c === "'") {
      const e = s.indexOf("'", i + 1);
      i = e < 0 ? s.length : e + 1;
    } else if (c === '"') {
      i++;
      while (i < s.length && s[i] !== '"') i += s[i] === '\\' ? 2 : 1;
      i++;
    } else if (c === '(') {
      depth++;
      i++;
    } else if (c === ')') {
      depth--;
      i++;
      if (depth === 0) return i;
    } else i++;
  }
  return s.length;
}

function matchBacktick(s: string, start: number): number {
  let i = start;
  while (i < s.length && s[i] !== '`') i += s[i] === '\\' ? 2 : 1;
  return Math.min(i, s.length);
}

const ANSI: Record<string, string> = {
  a: '\x07', b: '\b', e: '\x1b', E: '\x1b', f: '\f', n: '\n', r: '\r', t: '\t', v: '\v',
  '\\': '\\', "'": "'", '"': '"', '?': '?',
};

/** Decode a `$'…'` body starting at `i` (just past the opening quote). `ok` is false on an unknown escape. */
function decodeAnsi(s: string, i: number): { text: string; end: number; ok: boolean } {
  let text = '';
  let ok = true;
  const take = (re: RegExp, max: number): string => {
    let d = '';
    while (d.length < max && i < s.length && re.test(s[i])) d += s[i++];
    return d;
  };
  while (i < s.length && s[i] !== "'") {
    if (s[i] !== '\\' || i + 1 >= s.length) {
      text += s[i++];
      continue;
    }
    const e = s[i + 1];
    i += 2;
    if (ANSI[e] !== undefined) text += ANSI[e];
    else if (e === 'x' || e === 'u' || e === 'U') {
      const d = take(/[0-9A-Fa-f]/, e === 'x' ? 2 : e === 'u' ? 4 : 8);
      const cp = d ? parseInt(d, 16) : NaN;
      if (Number.isNaN(cp) || cp > 0x10ffff) ok = false;
      else text += String.fromCodePoint(cp);
    } else if (/[0-7]/.test(e)) {
      i--;
      text += String.fromCharCode(parseInt(take(/[0-7]/, 3), 8) & 0xff);
    } else if (e === 'c' && i < s.length) {
      text += String.fromCharCode(s[i++].charCodeAt(0) & 0x1f);
    } else ok = false;
  }
  return { text, end: i + 1, ok };
}

function tokenize(s: string): Simple[] {
  const out: Simple[] = [];
  const fresh = (): Simple => ({ words: [], subs: [], here: [], opaque: null });
  let cmd = fresh();
  let cur = '';
  let raw = ''; // unquoted literal characters of the current word, for brace-expansion detection
  let inWord = false;
  let pending: 'herestring' | 'heredoc' | 'redirect' | null = null;
  const heredocs: { delim: string; strip: boolean; quoted: boolean; owner: Simple }[] = [];
  let stripTabs = false;
  let quotedDelim = false;

  const endWord = () => {
    if (!inWord) return;
    if (pending === 'herestring') cmd.here.push(cur);
    else if (pending === 'heredoc') heredocs.push({ delim: cur, strip: stripTabs, quoted: quotedDelim, owner: cmd });
    else if (pending !== 'redirect') {
      cmd.words.push(cur);
      if (BRACE_RE.test(raw)) cmd.opaque ??= 'brace expansion cannot be checked';
    }
    pending = null;
    quotedDelim = false;
    cur = '';
    raw = '';
    inWord = false;
  };
  const endCmd = () => {
    endWord();
    pending = null;
    if (cmd.words.length || cmd.subs.length || cmd.here.length || cmd.opaque) out.push(cmd);
    cmd = fresh();
  };
  /** Before a redirection operator: a bare fd number (`2>`) is not a word. */
  const endWordBeforeRedirect = () => {
    if (inWord && /^\d+$/.test(cur) && raw === cur) {
      cur = '';
      raw = '';
      inWord = false;
    } else endWord();
  };
  const readHeredocs = (i: number): number => {
    // i points just past a newline; consume each pending heredoc body in order.
    while (heredocs.length) {
      const h = heredocs.shift()!;
      const lines: string[] = [];
      for (;;) {
        if (i >= s.length) break;
        let e = s.indexOf('\n', i);
        if (e < 0) e = s.length;
        const line = s.slice(i, e);
        i = e + 1;
        if ((h.strip ? line.replace(/^\t+/, '') : line) === h.delim) break;
        lines.push(line);
      }
      const body = lines.join('\n');
      h.owner.here.push(body);
      if (!h.quoted) {
        // Unquoted heredoc bodies expand $(…) and backticks (quotes are literal there).
        for (let j = 0; j < body.length; j++) {
          if (body[j] === '\\') j++;
          else if (body[j] === '$' && body[j + 1] === '(') {
            const e = matchParen(body, j + 2);
            h.owner.subs.push(body.slice(j + 2, e - 1));
            j = e - 1;
          } else if (body[j] === '`') {
            const e = matchBacktick(body, j + 1);
            h.owner.subs.push(body.slice(j + 1, e));
            j = e;
          }
        }
      }
    }
    return i;
  };

  let i = 0;
  while (i < s.length) {
    const c = s[i];
    const n = s[i + 1];
    if (c === '\\') {
      if (n === '\n') i += 2;
      else {
        if (n !== undefined) cur += n;
        inWord = true;
        i += 2;
      }
    } else if (c === "'") {
      const e = s.indexOf("'", i + 1);
      const end = e < 0 ? s.length : e;
      cur += s.slice(i + 1, end);
      inWord = true;
      if (pending === 'heredoc') quotedDelim = true;
      i = end + 1;
    } else if (c === '$' && n === "'") {
      const d = decodeAnsi(s, i + 2);
      if (!d.ok) cmd.opaque ??= "unrecognised $'…' escape";
      cur += d.text;
      inWord = true;
      i = d.end;
    } else if (c === '"') {
      i++;
      inWord = true;
      if (pending === 'heredoc') quotedDelim = true;
      while (i < s.length && s[i] !== '"') {
        const d = s[i];
        if (d === '\\' && i + 1 < s.length) {
          const e = s[i + 1];
          if (e === '\n') {
            /* line continuation */
          } else if ('$`"\\'.includes(e)) cur += e;
          else cur += d + e;
          i += 2;
        } else if (d === '$' && s[i + 1] === '(') {
          const e = matchParen(s, i + 2);
          cmd.subs.push(s.slice(i + 2, e - 1));
          cur += s.slice(i, e);
          i = e;
        } else if (d === '`') {
          const e = matchBacktick(s, i + 1);
          cmd.subs.push(s.slice(i + 1, e));
          cur += s.slice(i, e + 1);
          i = e + 1;
        } else cur += s[i++];
      }
      i++;
    } else if ((c === '$' || c === '<' || c === '>') && n === '(') {
      const e = matchParen(s, i + 2);
      cmd.subs.push(s.slice(i + 2, e - 1));
      cur += s.slice(i, e);
      inWord = true;
      i = e;
    } else if (c === '`') {
      const e = matchBacktick(s, i + 1);
      cmd.subs.push(s.slice(i + 1, e));
      cur += s.slice(i, e + 1);
      inWord = true;
      i = e + 1;
    } else if (c === '<' && n === '<') {
      endWordBeforeRedirect();
      if (s[i + 2] === '<') {
        pending = 'herestring';
        i += 3;
      } else {
        pending = 'heredoc';
        stripTabs = s[i + 2] === '-';
        i += stripTabs ? 3 : 2;
      }
    } else if (c === '<' || c === '>' || (c === '&' && n === '>')) {
      // Redirection: `>`, `>>`, `>|`, `>&`, `<`, `<&`, `<>`, `&>`, `&>>`, with optional fd prefix.
      // The target word is dropped from argv.
      endWordBeforeRedirect();
      let j = i + (c === '&' ? 2 : 1);
      if (s[j] === '>' || s[j] === '&' || s[j] === '|') j++;
      pending = 'redirect';
      i = j;
    } else if (c === '#' && !inWord) {
      const e = s.indexOf('\n', i);
      i = e < 0 ? s.length : e;
    } else if (c === '\n') {
      endCmd();
      i = readHeredocs(i + 1);
    } else if (c === ';' || c === '&' || c === '|' || c === '(' || c === ')') {
      endCmd();
      i++;
    } else if (c === ' ' || c === '\t' || c === '\r') {
      endWord();
      i++;
    } else {
      cur += c;
      raw += c;
      inWord = true;
      i++;
    }
  }
  endCmd();
  return out;
}

function skipOpts(argv: string[], withArg: Set<string>): string[] {
  let i = 1;
  while (i < argv.length && argv[i].startsWith('-') && argv[i] !== '-') {
    if (argv[i] === '--') return argv.slice(i + 1);
    i += withArg.has(argv[i]) ? 2 : 1;
  }
  return argv.slice(i);
}

const XARGS_ARG = new Set(['-I', '-n', '-L', '-P', '-d', '-E', '-s', '-a', '-l']);

type Stripped = { argv: string[]; scripts: string[]; viaXargs: boolean; gitEnv: boolean; opaque: string | null };

/** Strip assignments, keywords and transparent wrappers. Returns stripped argv plus extra scripts to recurse into. */
function strip(words: string[]): Stripped {
  const r: Stripped = { argv: words, scripts: [], viaXargs: false, gitEnv: false, opaque: null };
  const done = (opaque: string | null = null): Stripped => ({ ...r, argv: [], opaque });
  for (;;) {
    const argv = r.argv;
    const w = argv[0];
    if (w === undefined) break;
    const b = basename(w);
    if (ASSIGN_RE.test(w)) {
      if (GIT_ENV_RE.test(w)) r.gitEnv = true;
      r.argv = argv.slice(1);
    } else if (KEYWORDS.has(w)) r.argv = argv.slice(1);
    else if (w === 'function') r.argv = argv.slice(2);
    else if (b === 'env') {
      let i = 1;
      while (i < argv.length) {
        const a = argv[i];
        if (a === '-S' || a === '--split-string') {
          if (argv[i + 1] !== undefined) r.scripts.push(argv.slice(i + 1).join(' '));
          return done();
        }
        if (a === '-u' || a === '-C' || a === '--unset' || a === '--chdir') i += 2;
        else if (ASSIGN_RE.test(a)) {
          if (GIT_ENV_RE.test(a)) r.gitEnv = true;
          i++;
        } else if (a.startsWith('-') && a !== '--') i++;
        else if (a === '--') {
          i++;
          break;
        } else break;
      }
      r.argv = argv.slice(i);
    } else if (b === 'busybox') {
      r.argv = argv.slice(1);
    } else if (['command', 'builtin', 'nohup', 'time', 'nice', 'unbuffer'].includes(b)) {
      r.argv = skipOpts(argv, new Set(['-n']));
    } else if (b === 'sudo') {
      r.argv = skipOpts(argv, new Set(['-u', '-g', '-p', '-C', '-D', '-h', '-r', '-t', '-U']));
    } else if (b === 'doas') {
      r.argv = skipOpts(argv, new Set(['-u', '-C']));
    } else if (b === 'stdbuf') {
      r.argv = skipOpts(argv, new Set(['-i', '-o', '-e']));
    } else if (b === 'ionice') {
      r.argv = skipOpts(argv, new Set(['-c', '-n', '-p', '-P', '-u']));
    } else if (b === 'caffeinate') {
      r.argv = skipOpts(argv, new Set(['-w', '-t']));
    } else if (b === 'chrt' || b === 'taskset') {
      if (argv.includes('-p') || argv.includes('--pid')) return done();
      r.argv = skipOpts(argv, new Set(['-T', '-P', '-D'])).slice(1); // drop priority / cpu mask
    } else if (b === 'timeout') {
      r.argv = skipOpts(argv, new Set(['-s', '-k', '--signal', '--kill-after'])).slice(1);
    } else if (b === 'xargs') {
      r.argv = skipOpts(argv, XARGS_ARG);
      r.viaXargs = true;
    } else if (b === 'rtk') {
      r.argv = skipOpts(argv, new Set());
      if (r.argv[0] === 'proxy') r.argv = r.argv.slice(1);
    } else if (b === 'watch') {
      // watch joins its arguments and runs them with `sh -c`.
      const rest = skipOpts(argv, new Set(['-n', '--interval']));
      if (rest.length) r.scripts.push(rest.join(' '));
      return done();
    } else if (b === 'script') {
      const c = argv.findIndex((a) => a === '-c' || a === '--command');
      if (c >= 0) {
        if (argv[c + 1] !== undefined) r.scripts.push(argv[c + 1]);
        return done();
      }
      r.argv = skipOpts(argv, new Set(['-F', '-t', '-T', '-I', '-O', '-B', '-E'])).slice(1); // drop transcript file
    } else if (b === 'parallel') {
      return done('parallel runs commands that cannot be checked');
    } else break;
  }
  return r;
}

const GIT_ARG_OPTS = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env', '--super-prefix']);

/** Git subcommand after skipping global options, plus `-c` values and `--config-env` specs seen. */
export function gitSubcommand(argv: string[]): {
  sub: string | undefined;
  args: string[];
  configs: string[];
  configEnv: string[];
} {
  const configs: string[] = [];
  const configEnv: string[] = [];
  let i = 1;
  while (i < argv.length && argv[i].startsWith('-')) {
    const a = argv[i];
    if (GIT_ARG_OPTS.has(a)) {
      if (a === '-c') configs.push(argv[i + 1] ?? '');
      if (a === '--config-env') configEnv.push(argv[i + 1] ?? '');
      i += 2;
    } else {
      if (a.startsWith('--config-env=')) configEnv.push(a.slice('--config-env='.length));
      i++;
    }
  }
  return { sub: argv[i], args: argv.slice(i + 1), configs, configEnv };
}

function expand(cmd: string, depth: number, out: string[][]): void {
  if (depth > MAX_DEPTH) {
    out.push([OPAQUE, 'shell nesting too deep to inspect']);
    return;
  }
  for (const simple of tokenize(cmd)) {
    if (simple.opaque) out.push([OPAQUE, simple.opaque]);
    const { argv, scripts, viaXargs, gitEnv, opaque } = strip(simple.words);
    if (opaque) out.push([OPAQUE, opaque]);
    const nested: string[] = [...scripts, ...simple.subs];
    // Any command (shells and wrappers included) inherits these variables into the git it may run.
    if (gitEnv) out.push([OPAQUE, 'git config or helpers injected via environment']);
    if (argv.length) {
      const b = basename(argv[0]);
      if (['export', 'declare', 'typeset', 'readonly', 'local'].includes(b) && argv.some((a) => GIT_ENV_RE.test(a))) {
        out.push([OPAQUE, 'git config or helpers injected via environment']);
      }
      if (viaXargs && b === 'git' && gitSubcommand(argv).sub === undefined) {
        out.push([OPAQUE, 'git subcommand supplied by xargs input']);
      } else out.push(argv);
      if (b === 'git') {
        // git submodule foreach runs its remaining arguments as a shell command.
        const g = gitSubcommand(argv);
        const f = g.args.indexOf('foreach');
        if (g.sub === 'submodule' && f >= 0) {
          const rest = g.args.slice(f + 1);
          while (rest.length && rest[0].startsWith('-')) rest.shift();
          if (rest.length) nested.push(rest.join(' '));
        }
      }
      if (SHELLS.has(b)) {
        let script: string | undefined;
        let file = false;
        let wantC = false;
        for (let i = 1; i < argv.length; i++) {
          const a = argv[i];
          if (/^-[A-Za-z]+$/.test(a) && a.includes('c')) wantC = true;
          else if (a === '--command' || /^-command$/i.test(a)) wantC = true;
          else if (a === '-o' || a === '+o') i++;
          else if (/^[-+]/.test(a)) continue;
          else if (wantC) {
            script = a;
            break;
          } else {
            file = true;
            break;
          }
        }
        if (script !== undefined) nested.push(script);
        else if (simple.here.length) nested.push(...simple.here);
        else if (!file) out.push([OPAQUE, `${b} reads commands from stdin`]);
      } else if (b === 'eval') nested.push(argv.slice(1).join(' '));
      // find -exec / -execdir / -ok run their argument words as a command.
      for (let i = 1; i < argv.length; i++) {
        if (['-exec', '-execdir', '-ok', '-okdir'].includes(argv[i])) {
          const rest: string[] = [];
          for (i++; i < argv.length && argv[i] !== ';' && argv[i] !== '+'; i++) rest.push(argv[i]);
          if (rest.length) {
            const inner = strip(rest);
            if (inner.argv.length) out.push(inner.argv);
            nested.push(...inner.scripts);
          }
        }
      }
    }
    for (const n of nested) expand(n, depth + 1, out);
  }
}

/** argv per simple command, wrappers stripped, with nested shells/eval/substitutions expanded. */
export function splitCommands(cmd: string): string[][] {
  const out: string[][] = [];
  try {
    expand(cmd, 0, out);
  } catch {
    out.push([OPAQUE, 'command could not be parsed']);
  }
  return out;
}
