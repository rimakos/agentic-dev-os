#!/usr/bin/env python3
"""Preview a pull request, then create or update it only with --yes.

  pr.py describe --title T --body-file F [--ticket ID]
  pr.py create   --title T --body-file F [--target BRANCH] [--ticket ID] [--draft] [--yes]
  pr.py update PR_ID [--title T] [--body-file F] [--yes]

Run from the repo. Azure DevOps goes through `az`, GitHub through `gh`. Never pushes.
Exit codes: 0 done or previewed, 1 invalid input, 2 unknown host or missing CLI,
3 branch not on the remote.
"""
import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

CONVENTIONS = Path(__file__).resolve().parent.parent / "conventions" / "conventions.py"
HOSTS = {"dev.azure.com": "az", "visualstudio.com": "az", "github.com": "gh"}
# Azure DevOps rejects a longer description.
AZ_DESCRIPTION_MAX = 4000


class Stop(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def current_branch():
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch in ("", "HEAD"):
        raise Stop(1, "not on a branch: check out the branch the pull request is for")
    return branch


def default_target():
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").stdout.strip()
    return head.removeprefix("origin/")


def host_cli():
    url = git("remote", "get-url", "origin").stdout.strip()
    cli = next((c for host, c in HOSTS.items() if host in url), None)
    if cli is None:
        raise Stop(2, f"unknown git host for origin '{url}': need dev.azure.com, visualstudio.com or github.com")
    if shutil.which(cli) is None:
        raise Stop(2, f"'{cli}' is not on the PATH: install it and sign in")
    return cli


def check_title(title):
    if not title.strip():
        raise Stop(1, "the title is empty")
    if not CONVENTIONS.exists():
        return
    result = subprocess.run(
        [sys.executable, str(CONVENTIONS), "commit-msg", "--check", title],
        capture_output=True, text=True,
    )
    # 1 is a mismatch; any other code means no convention is configured here.
    if result.returncode == 1:
        raise Stop(1, f"title does not match the convention: {result.stdout.strip()}")


def read_body(body_file):
    path = Path(body_file).resolve()
    try:
        body = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise Stop(1, f"cannot read the body file {body_file}: {error}")
    if not body.strip():
        raise Stop(1, f"the body file {body_file} is empty")
    return path, body


def require_pushed(branch):
    result = git("ls-remote", "--exit-code", "--heads", "origin", branch)
    if result.returncode == 2:
        print(f"Branch '{branch}' is not on the remote. Push it yourself, then run this again:")
        print(f"  git push -u origin {branch}")
        raise Stop(3, "nothing was created")
    if result.returncode != 0:
        raise Stop(1, f"cannot reach origin: {result.stderr.strip()}")


def create_command(cli, args, branch, body_path):
    if cli == "az":
        # `=@file` makes az read the file itself, so the text never passes through a shell
        # and a body that starts with `-` or `@` is not read as an option or a file name.
        command = ["az", "repos", "pr", "create", "--title", args.title,
                   f"--description=@{body_path}", "--source-branch", branch]
        if args.target:
            command += ["--target-branch", args.target]
        if args.ticket:
            command += ["--work-items", args.ticket]
        if args.draft:
            command += ["--draft"]
        return command
    command = ["gh", "pr", "create", "--title", args.title,
               "--body-file", str(body_path), "--head", branch]
    if args.target:
        command += ["--base", args.target]
    if args.draft:
        command += ["--draft"]
    return command


def update_command(cli, args, body_path):
    if cli == "az":
        command = ["az", "repos", "pr", "update", "--id", args.pr_id]
        if args.title:
            command += ["--title", args.title]
        if body_path:
            command += [f"--description=@{body_path}"]
        return command
    command = ["gh", "pr", "edit", args.pr_id]
    if args.title:
        command += ["--title", args.title]
    if body_path:
        command += ["--body-file", str(body_path)]
    return command


def print_preview(rows, body):
    for label, value in rows:
        print(f"{label + ':':<8}{value}")
    if body is not None:
        print("--- body ---")
        print(body.rstrip("\n"))
        print("--- end of body ---")


def run(args):
    title = getattr(args, "title", None)
    body_file = getattr(args, "body_file", None)
    ticket = getattr(args, "ticket", None)
    if title is not None:
        check_title(title)
    body_path, body = read_body(body_file) if body_file else (None, None)

    if args.action == "describe":
        print_preview([("Title", title), ("Target", default_target() or "the repository's default branch"),
                       ("Source", current_branch()), ("Ticket", ticket or "none")], body)
        return

    if args.action == "update" and title is None and body is None:
        raise Stop(1, "update needs --title or --body-file")
    cli = host_cli()
    if cli == "az" and body is not None and len(body) > AZ_DESCRIPTION_MAX:
        raise Stop(1, f"the body is {len(body)} characters: Azure DevOps takes at most {AZ_DESCRIPTION_MAX}")

    if args.action == "create":
        branch = current_branch()
        require_pushed(branch)
        args.target = args.target or default_target()
        command = create_command(cli, args, branch, body_path)
        rows = [("Title", title), ("Target", args.target or "the repository's default branch"),
                ("Source", branch), ("Ticket", ticket or "none")]
        if ticket and cli == "gh":
            rows[-1] = ("Ticket", f"{ticket} (GitHub links it only if the body names it)")
        if args.draft:
            rows.append(("Draft", "yes"))
    else:
        command = update_command(cli, args, body_path)
        rows = [("PR", args.pr_id), ("Title", title or "unchanged")]
        if body is None:
            rows.append(("Body", "unchanged"))
    print_preview(rows, body)

    print(f"Command: {shlex.join(command)}")
    if not args.yes:
        print(f"Preview only, nothing was sent. Run again with --yes to {args.action}.")
        return
    sys.stdout.flush()
    code = subprocess.run(command).returncode
    if code != 0:
        raise Stop(1, f"{cli} exited with {code}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_subparsers(dest="action", required=True)

    describe = actions.add_parser("describe")
    describe.add_argument("--title", required=True)
    describe.add_argument("--body-file", required=True)
    describe.add_argument("--ticket")

    create = actions.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--body-file", required=True)
    create.add_argument("--target")
    create.add_argument("--ticket")
    create.add_argument("--draft", action="store_true")
    create.add_argument("--yes", action="store_true")

    update = actions.add_parser("update")
    update.add_argument("pr_id")
    update.add_argument("--title")
    update.add_argument("--body-file")
    update.add_argument("--yes", action="store_true")

    try:
        run(parser.parse_args())
    except Stop as stop:
        print(f"pr: {stop}", file=sys.stderr)
        return stop.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
