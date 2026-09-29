<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/cache-clear.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Remove stored boundary data

Deletes the boundary data of one municipality, or of all of them, from your
computer. The tool downloads the data again the next time you ask for a
boundary.

## When you would use this

- The boundaries of a municipality have changed and you want the tool to fetch the current data.
- You want to free disk space.

## Before you start

Decide whether you want to remove one municipality or all of them. Nothing
else is affected: the stored data is only a copy of what the server can send
again.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter. Replace SAVAR with the
   municipality you want to remove.

   ```bash
   cadastral cache clear -m SAVAR --force
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral cache clear -m SAVAR --force -->
   ```text
   ✓ Cleared municipality 334979 (0.7 KB freed)
   ```
   <!-- END GENERATED: output -->

4. The tool confirms what it removed and how much space it freed.

## Choices you can make

`--force` skips the question the tool otherwise asks before deleting. Without
it, the tool asks you to confirm; type `y` and press Enter to go ahead, or just
press Enter to keep the data.

To remove everything, use `--all` instead of naming a municipality:

```bash
cadastral cache clear --all
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--municipality`, `-m` `TEXT` | Clear specific municipality | Not used |
| `--all`, `-a` | Clear all cache | Not switched on |
| `--force`, `-f` | Skip confirmation | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If you name a municipality that is not stored, the tool tells you so and
removes nothing:

<!-- BEGIN GENERATED: output cadastral cache clear -m LUKA --force -->
```text
Municipality 334731 is not cached
```
<!-- END GENERATED: output -->

If you name neither a municipality nor `--all`, you will see this:

<!-- BEGIN GENERATED: output cadastral cache clear -->
```text
✗ Error: Either --municipality or --all is required

Try: cadastral cache clear --help
```
<!-- END GENERATED: output -->

## Related pages

- [cache-list](cache-list.md) shows what is stored before you remove it.
- [download-gis](download-gis.md) downloads a municipality again.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral cache clear --help` prints:

```text
Usage: cadastral cache clear [OPTIONS]

  Clear cached GIS data.

  Examples:
    cadastral cache clear --municipality 334979
    cadastral cache clear --all
    cadastral cache clear -m SAVAR --force

Options:
  -m, --municipality TEXT  Clear specific municipality
  -a, --all                Clear all cache
  -f, --force              Skip confirmation
  --help                   Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
