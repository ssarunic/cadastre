<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/cache-list.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# See which municipalities are stored on your computer

The boundary data of a municipality is downloaded once and then kept on your
computer. This command lists what is kept, how big it is and when it was last
updated.

## When you would use this

- You want to know whether the tool already has the data of a municipality before you ask for a boundary.
- You want to see how much disk space the stored data takes.

## Before you start

Nothing. This command takes no input and changes nothing.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral cache list
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral cache list -->
   ```text
   Cached GIS Data (1 municipalities):

     Municipality      Size    Last Modified
     334979          0.7 KB    2026-01-01 00:00

   Total Cache Size: 0.0 MB
   Cache Location: ~/.cadastral_api_cache
   ```
   <!-- END GENERATED: output -->

4. One row per municipality, with its number, the size of the data and the
   date of the last download. The last lines give the total size and the
   folder where the data lives.

## Choices you can make

None.

<!-- BEGIN GENERATED: options -->
This command has no choices. Type it as it is.
<!-- END GENERATED: options -->

## If something goes wrong

If nothing has been downloaded yet, the tool says the store is empty and
suggests the download command. That is not an error.

## Related pages

- [cache-info](cache-info.md) gives the totals only.
- [cache-clear](cache-clear.md) removes stored data.
- [download-gis](download-gis.md) adds a municipality.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral cache list --help` prints:

```text
Usage: cadastral cache list [OPTIONS]

  List cached municipalities.

  Example:
    cadastral cache list

Options:
  --help  Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
