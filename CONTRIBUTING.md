# Contributing

One pull request adds or updates one plugin or one theme. `python3 check.py` must pass before review.

## What a reviewer checks

**Themes**
- The `id` is new, lowercase, and the file is `themes/<id>.json`.
- Text on background is readable (at least 4.5:1), in light and, with `"appearance": "auto"`, in dark.
- It looks like its description. A screenshot in the pull request helps.

**Plugins**
- The code at the pinned commit does what the description says, and nothing else.
- The permissions are the ones it needs. `network` and `shell` need a reason in the pull request.
- No obfuscated or downloaded code, no telemetry without saying so.

## Updating

- A theme: edit its file and raise `version` in `themes.json`.
- A plugin: add a version to the end of its `versions`, with its new tag and commit.

## Removing

Open a pull request that deletes the entry, or an issue if it is not yours. A plugin found to be harmful is removed at
once; Loam stops offering it and its updates.

The preview at the top of the README is drawn from the themes themselves: `python3 scripts/previews.py` after a theme
is added (a maintainer runs it when merging).
