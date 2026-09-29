<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-zoning.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Find out whether a parcel is in a building area

Tells you where a parcel lies with respect to the building areas of the
spatial plans: inside the building area of a settlement, in a separate zone
outside a settlement (a tourist settlement, a camp, an industrial zone), or
outside every building area. It names the zone, its designation code and the
plan it comes from. It does not tell you whether anything may be built there.

## When you would use this

- A client is about to buy a parcel and you want a first check of whether it lies in a building area at all, before reading the plan.
- You want to know whether a parcel is in a tourist zone before a valuation.
- You are checking which spatial plan applies to a parcel before asking the
  municipality for a lokacijska informacija.

## Before you start

You need the parcel number and the cadastral municipality, as for
[get-geometry](get-geometry.md). The boundary data of the municipality is
downloaded once and kept on your computer.

The answer comes from the building areas (građevinska područja) that the
county spatial-planning institutes drew from the plans in force. It is an
interpretation of the plans, not the plans themselves: the tool says so at the
end of every answer, and an official answer still needs the plan or a
lokacijska informacija from the municipality.

Being inside a building area is not permission to build. The plan's
provisions, the size of the plot, access, utilities, protected areas and the
need for a more detailed plan are not checked by this tool, so the
**Buildability** line always says it was not determined.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-zoning 396/1 -m SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-zoning 396/1 -m SAVAR -->
   ```text
   SPATIAL PLAN: BUILDING AREAS
   ============================
     Parcel          396/1
     Municipality    334979
     Area (GIS)      2077.00 m²
     Status          In a detached building area outside a settlement
     Buildability    Not determined (screening only)
     Plans           PPUO SALI - III. ID

                                                  Zones
   ┏━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
   ┃ Kind     ┃ Code ┃ Designation                     ┃ Zone         ┃ Plan                ┃ Overlap ┃
   ┡━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
   │ detached │ T3   │ GOSPODARSKA - UGOSTITELJSKO     │ SAVAR - KAMP │ PPUO SALI - III. ID │ 27%     │
   │          │      │ TURISTIČKA (KAMP)               │              │                     │         │
   └──────────┴──────┴─────────────────────────────────┴──────────────┴─────────────────────┴─────────┘

   Building areas are an interpretation of the spatial plans by the county spatial-planning institutes
   and may deviate from the plans in force. They must not be used to issue acts for spatial
   interventions or other public documents; for official purposes use the original plans in force.
   Source: Građevinska područja (MPGI)
   Whether anything may be built is not determined here; read the plan or ask for a lokacijska
   informacija.
   ```
   <!-- END GENERATED: output -->

4. **Status** is the short answer: inside a settlement building area, in a
   detached building area outside a settlement, touching a building area
   below the overlap threshold, or outside building areas.
   The **Zones** table lists every zone that covers part of the parcel, with
   its **Code** (for example `T3` for a camp or `GPN` for a settlement area),
   its **Designation** as written in the plan, the **Zone** name, the
   **Plan** it was read from and the share of the parcel it covers
   (**Overlap**). The yellow note at the end is the warning that must go with
   any use of this answer.

## Choices you can make

`--format` chooses the form of the answer. `table` is what you see above.
`json` gives the same data for other programs, including the plan identifier
and the county and municipality of the zone. `csv` gives one line per zone for
a spreadsheet, including the zones under the threshold, which are marked in
the `match` column. `geojson` gives the zone outlines for a mapping program,
marked the same way; add `--show-geometry` to include them in the `json` form
as well.

Zones that cover only a sliver of the parcel are listed separately, below
the table, because plan boundaries are drawn on small-scale maps and rarely
follow parcel lines exactly. `--min-overlap` sets that threshold as a
percentage of the parcel, between 0 and 100; the usual value is 2.

To keep the answer, write it to a file with `--output`:

```bash
cadastral get-zoning 396/1 -m SAVAR --format csv --output zoning-396-1.csv
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCEL_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code | Required |
| `--format`, `-f` | Output format (`table`, `json`, `csv`, `geojson`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
| `--show-geometry` | Include the zone polygons in JSON output | Not switched on |
| `--min-overlap` `FLOAT RANGE` | Zones covering less than this share of the parcel (percent) are listed separately | `2.0` is used |
<!-- END GENERATED: options -->

## If something goes wrong

If the parcel is not in the boundary data of the municipality, you will see this:

<!-- BEGIN GENERATED: output cadastral get-zoning 999 -m SAVAR -->
```text
✗ Error: Geometry not found for parcel '999'

Note: GIS data must be downloaded first (this happens automatically)
```
<!-- END GENERATED: output -->

The boundary data and the cadastre are not always in step; check the parcel
with [search](search.md) first.

If the answer says the building areas could not be reached, the plan service
is down or the tool is not set up for it; ask the person who installed the
tool. Other messages are explained on the [errors page](../errors.md).

## Related pages

- [get-geometry](get-geometry.md) shows the parcel boundary the answer is based on.
- [get-parcel](get-parcel.md) shows what the cadastre records for the parcel.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-zoning --help` prints:

```text
Usage: cadastral get-zoning [OPTIONS] PARCEL_NUMBER

  Find out which spatial-plan building area a parcel lies in.

  Matches the parcel boundary against the building areas (građevinska područja)
  derived from the spatial plans in force: inside a settlement, in a detached
  zone with its designation (for example T2 tourist settlement), or outside.
  This is a screening only: it does not say whether anything may be built, and
  the result is an interpretation of the plans, not the plans themselves.

  Examples:
    cadastral get-zoning 103/2 -m SAVAR
    cadastral get-zoning 396/1 -m 334979 --format json
    cadastral get-zoning 45 -m SAVAR --format csv -o zoning.csv
    cadastral get-zoning 103/2 -m SAVAR --format geojson --show-geometry

Options:
  -m, --municipality TEXT         Municipality name or code  [required]
  -f, --format [table|json|csv|geojson]
                                  Output format
  -o, --output PATH               Save output to file
  --show-geometry                 Include the zone polygons in JSON output
  --min-overlap FLOAT RANGE       Zones covering less than this share of the
                                  parcel (percent) are listed separately
                                  [default: 2.0; 0<=x<=100]
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
