<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/install.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Installation, for the person setting this up

This page is for the technical colleague who installs the tool. The person who
will use it does not need to read it. It takes about ten minutes.

## What you are installing

`cadastral` is a command-line tool written in Python. It talks to a small
practice server, included in the same repository, that answers with made-up
cadastral data. Nothing here connects to the official Croatian systems, and it
must stay that way.

## Requirements

- Python 3.12 or newer.
- Git, to fetch the repository.
- A terminal the user can open: Terminal on macOS, Windows Terminal or PowerShell on Windows, any terminal on Linux.

## Step 1: fetch the repository and create an environment

```bash
git clone https://github.com/ssarunic/cadastre.git
cd cadastre
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate with `.venv\Scripts\activate` instead of the last line.

## Step 2: install the tool and the practice server

```bash
pip install -e ./api -e ./cli
pip install -r mock-server/requirements.txt
```

## Step 3: start the practice server

The practice server has to be running whenever the user works with the tool.
Start it in its own terminal window and leave that window open:

```bash
cd mock-server
python src/main.py
```

It listens on `http://localhost:8000`. The tool uses that address unless told
otherwise, so no further configuration is needed for practice use.

To have the server start automatically at login, create a user service
(launchd on macOS, a scheduled task on Windows, a systemd user unit on Linux)
that runs the two lines above inside the virtual environment.

## Step 4: choose the user's language

The tool prints in Croatian by default. Set the `CADASTRAL_LANG` environment
variable in the user's shell profile to `hr` or `en` so that they never have
to pass `--lang`. For example, in `~/.zshrc`:

```bash
export CADASTRAL_LANG=hr
```

The documentation exists in both languages. Give the user the link to the
edition that matches this setting.

Step 2 installs two program names, `cadastral` and `uz`. They are the same
program. The Croatian documentation uses `uz` with Croatian command and
option names, such as `uz čestica 103/2 -ko SAVAR`; the English
documentation uses `cadastral` with English names. Every command accepts
both spellings, so a line copied from either edition works.

## Step 5: verify

Open a new terminal as the user and run:

```bash
cadastral info
```

You should see this:

<!-- BEGIN GENERATED: output cadastral info -->
```text
Croatian Cadastral CLI
======================
Version: 0.4.0
API Base: http://localhost:8000

Cache Information
=================
Cache Directory: ~/.cadastral_api_cache
Cache Size: 0.0 MB
Cached Municipalities: 1
  • 334979 (0.7 KB)
Response cache: memory, 0 entries, 0.0 MB

API Settings
============
Rate Limit: 0.375 seconds between requests
Timeout: 10.0 seconds
Unknown server fields: warn

To clear cache: cadastral cache clear --all
```
<!-- END GENERATED: output -->

## Hand-over checklist

- The practice server starts on its own, or the user knows the two lines that start it.
- `cadastral info` prints the screen above in a fresh terminal opened by the user.
- `CADASTRAL_LANG` is set in the user's profile.
- The user has the link to [Start here](start-here.md) in their language.
- The user has your contact for when Terminal says the command is not found.
