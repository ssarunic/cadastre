<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/start-here.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Start here

This tool lets you read the cadastre and the land registry from your own
computer, one typed line at a time. This page walks you through the five
things you will do most often. Each task ends with a link to the page that
explains the command in full.

## Before the first use

Ask a technical colleague to follow the [installation page](install.md). When
they are done, open Terminal and type the following line, then press Enter:

```bash
cadastral info
```

If you see a table with a version number and no red text, you are ready. If
Terminal says the command is not found, go back to your colleague.

Two things to know before you start. First, every command begins with the
word `cadastral`. Second, the tool works with practice data on your own
computer; nothing you type reaches the official registers.

## Task 1: check who owns a parcel

1. Find the parcel number and the cadastral municipality on your document.
2. Type the following line and press Enter:

   ```bash
   cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --show-owners
   ```

3. Read the table headed **OWNERSHIP SHEET (LIST B)**. Each row is one owner
   with their share.

Full explanation: [get-lr-unit](commands/get-lr-unit.md).

## Task 2: check for mortgages and other charges

1. Use the same parcel and municipality.
2. Type the following line and press Enter:

   ```bash
   cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all --plombe-detail
   ```

3. Read **ENCUMBRANCES SHEET (LIST C)**. If it says **No encumbrances found**,
   list C is empty.
4. Look for the line **Pending entries (plombe)** near the top. If it is
   there, a request for registration (prijedlog) is waiting to be decided and
   the sheets may change.

Full explanation: [get-lr-unit](commands/get-lr-unit.md).

## Task 3: look up many parcels at once

1. Write the parcel numbers in one line, separated by commas, inside quotes.
2. Type the following line and press Enter:

   ```bash
   cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry
   ```

3. Each row of the **RESULTS** table is one parcel. The **LR Unit** column is
   the land registry unit of each.

Full explanation: [get-parcel](commands/get-parcel.md), and
[get-lr-unit](commands/get-lr-unit.md) with `--input` for reading all those
units in one go.

## Task 4: save a result for a file or a colleague

1. Take any command from this page.
2. Add `--format json --output` and a file name at the end:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR --show-owners --format json --output parcel-103-2.json
   ```

3. The file appears in the folder Terminal is in, usually your home folder.
   Attach it to the case file or send it on. `--format csv` gives a file that
   opens in a spreadsheet instead.

Full explanation: the "Choices you can make" section of any command page.

## Task 5: see the parcel on a map

1. Type the following line and press Enter:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR
   ```

2. Near the bottom, under **ADDITIONAL INFO**, there is a **Map URL**. Copy it
   into your web browser to see the parcel on the public map.

Full explanation: [get-parcel](commands/get-parcel.md), and
[get-geometry](commands/get-geometry.md) if you need the boundary for a mapping
program.

## When something goes wrong

Every error starts with a red cross and a short message. The
[errors page](errors.md) lists them and says what to do. The most common cause
is a mistyped parcel number or municipality.

## Where to go next

- [Complete reference](reference.md): every command on one page, with links.
- [Glossary](glossary.md): the words of the land registry and what the tool calls them.
