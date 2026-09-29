<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/download-gis.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Download the boundary data of a whole municipality

Fetches the file with the boundaries of every parcel in a cadastral
municipality and unpacks it into a folder of your choice, for use in a mapping
program.

## When you would use this

- A surveyor or an architect asks for the parcel boundaries of an area, not just one parcel.
- You want to open a whole municipality in a mapping program such as QGIS.

## Before you start

You need the municipality, by name or number, and a folder name where the
files should go. The folder is created if it does not exist. The files are in
GML, a text form for geographic data that mapping programs read.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral download-gis SAVAR --output ./gis_data
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral download-gis SAVAR --output ./gis_data -->
   ```text
   Downloading GIS data for municipality 334979...
   ✓ Downloaded: ko-334979.zip (0.7 KB)
   ✓ Extracted to: gis_data

   Files:
     • katastarske_cestice.gml (0.0 MB)

   Total parcels: 3

   To get parcel geometry: cadastral get-geometry <parcel> -m 334979
   ```
   <!-- END GENERATED: output -->

4. The tool reports the file it fetched, the folder it unpacked into, and the
   number of parcels in the data. The folder now contains a file named
   `katastarske_cestice.gml` with all parcel boundaries.

## Choices you can make

`--output` is required and names the folder. Add `--no-extract` to keep only
the downloaded ZIP file without unpacking it. Add `--clear-cache` to download
afresh even if the tool already has the data from an earlier run.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `MUNICIPALITY` | A value you type right after the command name, without a name in front of it | Required |
| `--output`, `-o` `PATH` | Output directory | Required |
| `--extract` / `--no-extract` | Extract ZIP file | `--extract` is used |
| `--clear-cache` | Clear cached data first | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If you forget `--output`, the tool stops and tells you the option is missing:

<!-- BEGIN GENERATED: output cadastral download-gis SAVAR -->
```text
Usage: cadastral download-gis [OPTIONS] MUNICIPALITY
Try 'cadastral download-gis --help' for help.

Error: Missing option '--output' / '-o'.
```
<!-- END GENERATED: output -->

Add it with a folder name.

If the download fails, the practice server may not be running. Ask the person
who installed the tool. Other messages are explained on the
[errors page](../errors.md).

## Related pages

- [get-geometry](get-geometry.md) gives the boundary of one parcel.
- [cache-clear](cache-clear.md) removes downloaded data from your computer.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral download-gis --help` prints:

```text
Usage: cadastral download-gis [OPTIONS] MUNICIPALITY

  Download complete GIS data for a municipality.

  Examples:
    cadastral download-gis 334979 --output ./gis_data
    cadastral download-gis SAVAR --output ./savar_gis --extract
    cadastral download-gis 334979 -o ./data --clear-cache

Options:
  -o, --output PATH         Output directory  [required]
  --extract / --no-extract  Extract ZIP file
  --clear-cache             Clear cached data first
  --help                    Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
