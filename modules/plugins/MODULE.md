# plugins

## What it does

Baseline plugin pack from the official marketplace: live library docs
(context7) and browser automation (playwright).

superpowers left the pack in 0.3.0. Its session injection pushes skill calls
with pressure language ("1% chance... MUST invoke") and adds verification
steps that current models already run, which Anthropic's Opus 5 prompting
guide says to remove.

## Prerequisites

- Claude Code with plugin support (`/plugin` works in a session).

## Install

Run in a Claude Code session. These are slash commands: the user types them
at the prompt; the agent cannot run slash commands.

1. `/plugin install context7@claude-plugins-official`
   (current library and framework docs instead of training-data guesses)
2. `/plugin install playwright@claude-plugins-official`
   (browser automation; the ticket-testing skill needs it)

## Verify

`/plugin`: the installed list shows context7 and playwright as enabled.

## Remove

1. `/plugin uninstall context7@claude-plugins-official`
2. `/plugin uninstall playwright@claude-plugins-official`
3. A pre-0.3.0 install also added superpowers:
   `/plugin uninstall superpowers@claude-plugins-official`.
