# archive

Skills cut in 0.3.0. The plugin only loads `skills/`, so nothing here is active.

- `operating-flow`, `task-intake`, `subagent-execute`, `verify-done`, `session-capture`: the
  execution ritual. Opus 5 and later plan, delegate and verify on their own, and Anthropic's
  prompting guide for Opus 5 says to remove explicit verification steps and verification
  subagents. The project-specific checks the model cannot know live in hooks and in
  `ticket-impact`.
- `spec-gate`: an uncommitted draft that graded holdout scenarios with a subagent; dropped for the
  same reason.
- `mcp-impact`, `cross-repo-manual-test`: no fires in 90 days of real use.

To restore one, move its folder back into `skills/`.
