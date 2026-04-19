# rtk package

RTK (Rust Token Killer) compresses verbose command outputs via a Claude Code PreToolUse
hook, reducing token consumption on bash-heavy tasks.

## How it works

The package installs a `PreToolUse` hook that intercepts Bash tool output and passes it
through `rtk` before it reaches Claude's context. On bash-heavy benchmark tasks this
typically reduces token consumption 20–40%.

## Binary required

The `rtk` binary is not included in this repository. Place it at `bin/rtk` before
installing this package.

**Option 1: Download a release**

Download the appropriate binary for your platform from the
[rtk releases page](https://github.com/rubin-johnson/rtk/releases) and place it at
`packages/rtk/bin/rtk`.

**Option 2: Build from source**

```bash
cd /path/to/rtk
cargo build --release
cp target/release/rtk /path/to/token_miser/packages/rtk/bin/rtk
```

## Install

Once the binary is in place, install normally:

```bash
token-miser run --package rtk --task tasks/synth-001.yaml --baseline vanilla
```
