@AGENTS.md

## Shell
Run shell commands with `bash` (`/usr/local/bin/bash`, 5.x), not zsh: zsh does not word-split
unquoted variables (e.g. `$files`) and errors on unmatched globs. Use `bash -c '...'` for anything
that relies on either.
