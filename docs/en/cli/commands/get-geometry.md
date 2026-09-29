<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-geometry.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Get the boundary of a parcel for a map

Prints the corner points of a parcel in the official Croatian coordinate
system, so that a surveyor or a mapping program can draw it. It can also tell
you the area computed from those points.

## When you would use this

- You want to hand the exact outline of a parcel to a surveyor or an architect.
- You want to compare the area computed from the boundary with the area recorded in the cadastre.
- You want to place the parcel on a map in a program that understands geographic data.

## Before you start

You need the parcel number and the cadastral municipality. The boundary data
for a whole municipality is downloaded once and kept on your computer; the
first lookup in a municipality therefore takes longer than the following ones.

The coordinates are in the HTRS96/TM system (EPSG:3765), the official
projection for Croatia. They are not the degrees you see in a car navigation
system. A mapping program will know what to do with them.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-geometry 103/2 -m SAVAR --show-stats
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-geometry 103/2 -m SAVAR --show-stats -->
   ```text
   GEOMETRY STATISTICS
   ===================
     Parcel               103/2
     Coordinate System    EPSG:3765
     Vertices             5
     Area (GIS)           1200.00 m²

     Bounding Box
       Min X              380,596.77 m
       Min Y              4,880,892.83 m
       Max X              380,636.77 m
       Max Y              4,880,922.83 m
       Width              40.00 m
       Height             30.00 m

     Map URL              https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layer
                          s=DOF5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_br
                          oj

   POLYGON((380596.77 4880892.83, 380636.77 4880892.83, 380636.77 4880922.83, 380596.77 4880922.83, 380596.77 4880892.83))
   ```
   <!-- END GENERATED: output -->

4. **GEOMETRY STATISTICS** summarises the shape: the number of corner points
   (**Vertices**), the area computed from them (**Area (GIS)**), the
   smallest rectangle that contains the parcel (**Bounding Box**), and a
   link (**Map URL**) that opens the official interactive map centred on the
   parcel. The last block is the boundary itself, written as a polygon in a
   standard text form. Each pair of numbers is one corner point.

## Choices you can make

`--format` chooses the form of the boundary. `wkt` is the standard text form
shown above. `geojson` is the form most web maps read. `csv` gives one corner
point per line for a spreadsheet. `json` gives the same data for other programs.
The `geojson` and `json` forms also carry the map link (`map_url`).

To hand the boundary to someone, write it to a file with `--output`. A GeoJSON
file can be dragged onto many online map viewers:

```bash
cadastral get-geometry 103/2 -m SAVAR --format geojson --output parcel-103-2.geojson
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCEL_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code | Required |
| `--format`, `-f` | Export format (`wkt`, `geojson`, `csv`, `json`) | `wkt` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
| `--show-stats` | Include geometry statistics | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If the parcel is not in the boundary data of the municipality, you will see this:

<!-- BEGIN GENERATED: output cadastral get-geometry 999 -m SAVAR -->
```text
✗ Error: Geometry not found for parcel '999'

Note: GIS data must be downloaded first (this happens automatically)
```
<!-- END GENERATED: output -->

The boundary data and the cadastre are not always in step; check the parcel
with [search](search.md) first.

If the boundary data of the municipality cannot be downloaded, ask the person
who installed the tool whether the practice server is running. Other messages
are explained on the [errors page](../errors.md).

## Related pages

- [download-gis](download-gis.md) downloads the boundary data of a whole municipality.
- [cache-list](cache-list.md) shows which municipalities are already on your computer.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-geometry --help` prints:

```text
Usage: cadastral get-geometry [OPTIONS] PARCEL_NUMBER

  Get parcel boundary coordinates for GIS integration.

  Examples:
    cadastral get-geometry 103/2 -m SAVAR
    cadastral get-geometry 103/2 -m 334979 --format wkt
    cadastral get-geometry 103/2 -m 334979 --format geojson -o parcel.geojson
    cadastral get-geometry 103/2 -m 334979 --format csv -o coords.csv

Options:
  -m, --municipality TEXT         Municipality name or code  [required]
  -f, --format [wkt|geojson|csv|json]
                                  Export format
  -o, --output PATH               Save output to file
  --show-stats                    Include geometry statistics
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
