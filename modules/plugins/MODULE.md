# plugins

## What it does

Baseline plugin pack from the official marketplace: process discipline
(superpowers), live library docs (context7), and browser automation
(playwright).

## Prerequisites

- Claude Code with plugin support (`/plugin` works in a session).

## Install

Run in a Claude Code session. These are slash commands: the USER must type
them at the prompt; the agent cannot run slash commands.

1. `/plugin install superpowers@claude-plugins-official`
   (brainstorming, TDD, systematic debugging, verification-before-completion)
2. `/plugin install context7@claude-plugins-official`
   (live, current library/framework docs instead of training-data guesses)
3. `/plugin install playwright@claude-plugins-official`
   (browser automation; REQUIRED if the ticket-testing skill will be used)

## Verify

`/plugin` — the installed list shows superpowers, context7, and playwright as
enabled.

## Remove

1. `/plugin uninstall superpowers@claude-plugins-official`
2. `/plugin uninstall context7@claude-plugins-official`
3. `/plugin uninstall playwright@claude-plugins-official`
