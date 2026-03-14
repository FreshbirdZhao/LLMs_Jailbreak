# Jailbreak Launcher Sync Design

**Date:** 2026-03-14

**Goal:** Update `Jelly_Z/bin/jailbreak` to launch the new multi-turn `single_jail/` and `multi_jail/` entry points after the legacy flat scripts were removed.

## Scope

- Keep the interactive menu text unchanged:
  - `单步越狱（single-step）`
  - `多步越狱（multi-step）`
- Replace old flat script paths with the new package entry scripts.
- Adapt the CLI arguments passed by the launcher so they match the new Python interfaces.
- Preserve the rest of the shell workflow as much as possible.

## Current Problem

The launcher still points to deleted files:

- `Jailbreak/jailbreak_tools/single_jail.py`
- `Jailbreak/jailbreak_tools/multi.py`

It also passes legacy flags such as:

- `--scale`
- `--resume`
- `--concurrency`
- `--enable-defense`
- `--defense-config`
- `--dataset-name-for-output`

The new Python entry points do not accept those options.

## Recommended Approach

Use a minimal compatibility update:

- `single` mode launches `Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- `multi` mode launches `Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`
- `single` continues to pass one dataset via `--dataset`
- `multi` passes the selected dataset via `--datasets`
- both modes pass `--max-rounds 6`

For removed features:

- keep the defense selection UI, but print that defense is currently unsupported by the new multi-turn launcher and ignore those parameters
- keep the partial dataset extraction logic because it still produces a valid dataset file for the new launchers
- stop passing removed flags so the launcher does not fail at runtime

## Alternatives

### Option 1: Minimal sync update

Pros:

- smallest change
- low regression risk
- unblocks the launcher immediately

Cons:

- defense toggles remain UI-only for now

### Option 2: Rebuild launcher around new multi-turn feature set

Pros:

- cleaner long-term UX

Cons:

- larger shell refactor
- unnecessary for current goal

## Testing

- shell script help or dry-run style verification if possible
- direct execution of new Python entry points with `--help`
- targeted unit test covering the launcher script path mapping if practical
- manual review that no deleted script paths remain in `Jelly_Z/bin/jailbreak`
