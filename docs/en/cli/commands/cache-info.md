<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/cache-info.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# See how much boundary data is stored

Shows the folder where the tool keeps downloaded boundary data, the number of
municipalities and files, and the total size.

## When you would use this

- Your computer is short of disk space and you want to know how much the tool uses.
- You want to find the folder to back it up or to hand it to a colleague.

## Before you start

Nothing. This command takes no input and changes nothing.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral cache info
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral cache info -->
   ```text
   CACHE INFORMATION
   =================
   Location: ~/.cadastral_api_cache
   Status: Active
   Total Size: 0.00 MB
   Municipalities: 1
   ZIP Files: 1
   GML Files: 0

   To list cached municipalities: cadastral cache list
   To clear cache: cadastral cache clear --all
   ```
   <!-- END GENERATED: output -->

4. **Location** is the folder on your computer. **Total Size** is the disk
   space used. The last two lines remind you of the commands that list and
   clear the data.

## Choices you can make

None.

<!-- BEGIN GENERATED: options -->
This command has no choices. Type it as it is.
<!-- END GENERATED: options -->

## If something goes wrong

This command has nothing to fail on. If the folder does not exist yet, the
tool says so; run a boundary lookup and it will be created.

## Related pages

- [cache-list](cache-list.md) lists the municipalities.
- [cache-clear](cache-clear.md) removes stored data.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral cache info --help` prints:

```text
Usage: cadastral cache info [OPTIONS]

  Show detailed cache information.

  Example:
    cadastral cache info

Options:
  --help  Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
