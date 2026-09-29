<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-parcel.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# See everything the cadastre holds about a parcel

The full cadastral record of one parcel: location, area, land use, the
possession sheet (posjedovni list) with the people the cadastre records, and
the number of the land registry unit where the legal owners are.

## When you would use this

- You are preparing a contract and need the area, the land use and the cadastral state of the parcel in one place.
- You want to compare who the cadastre records as possessor with who the land registry records as owner.
- You need the number of the land registry unit (zemljišnoknjižni uložak) of a parcel so you can read its owners and encumbrances.
- You have a list of parcels, from a contract or a spreadsheet, and want the same record for each of them.

## Before you start

You need the parcel number and the cadastral municipality, by name or number,
as for [search](search.md).

Keep one distinction in mind while you read. The cadastre records possessors
(posjednici); the land registry records owners (vlasnici). They are often the
same people, but not always, and only the land registry is proof of ownership.
This page shows the cadastre. The [get-lr-unit](get-lr-unit.md) page shows the
land registry.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR --show-owners
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m SAVAR --show-owners -->
   ```text
   PARCEL INFORMATION
   ==================
     Parcel Number             103/2
     Parcel ID                 6564817
     Municipality              SAVAR (334979)
     Address                   POLJE
     Area                      1,200 m²
     Building Permitted        No
     Cadastre/LR harmonized    Yes


   LAND USE
   ========
     Type         Area (m²)    Percentage    Buildings    Last change
     MASLINJAK        1,200        100.0%    No           -


   POSSESSION SHEET (cadastre / posjedovni list) (2 possessors)
   ============================================================
   Note: cadastre possessors may differ from registered owners. For land-registry owners (vlasnici),
   use: cadastral get-lr-unit
     Name                     Ownership    Address
     IVIĆ MARKO, SIN PETRA          N/A    TESTNA ULICA 15, SPLIT
     IVIĆ ANA, KĆI PETRA            N/A    SAVAR


   LAND REGISTRY
   =============
     Unit Number    657
     Main Book      N/A
     Institution    N/A
     Status         Inactive
     Verified       No


   ADDITIONAL INFO
   ===============
     Map URL         https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layers=DOF
                     5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj
     Detail Sheet    4
   ```
   <!-- END GENERATED: output -->

4. The screen has five parts. **PARCEL INFORMATION** identifies the parcel;
   the line **Cadastre/LR harmonized** says whether the cadastre and the land
   registry agree about it. **LAND USE** splits the area by cadastral culture.
   **POSSESSION SHEET (cadastre / posjedovni list)** lists the possessors the
   cadastre records, with their share where the cadastre has one.
   **LAND REGISTRY** gives the number of the land registry unit
   (**Unit Number**) that you can look up next. **ADDITIONAL INFO** contains a
   link that opens the parcel on the public map.

5. Where a value is not recorded, the tool prints **N/A**. In the possession
   sheet this is common: the cadastre often records who possesses without
   recording a share.

## Choices you can make

Without `--show-owners` the possession sheet is left out and the screen is
shorter. Add it whenever you want to see the people.

`--detail` narrows the screen to one part: `basic` for the identification only,
`owners` for the possession sheet, `landuse` for the land use split, `geometry`
for the boundary coordinates, `registry` for the land registry unit, `full` for
everything.

A building parcel (čestica zgrade) is written on documents as `35/1 ZGR`,
`35/1.ZGR` or `zgr. 35/1`. Type it in any of these forms; the tool shows it as
`zgr. 35/1` and marks it as a building parcel. Building parcels have no land
registry unit of their own, because the building is registered on its land
parcel.

```bash
cadastral get-parcel 35/1.ZGR -m SAVAR --detail basic
```

```bash
cadastral get-parcel 103/2 -m SAVAR --detail landuse
```

To keep the record as a file, add `--format json` and `--output` with a file
name. This is the form to use when you want to attach the data to a case file
or pass it to a colleague.

```bash
cadastral get-parcel 103/2 -m SAVAR --show-owners --format json --output parcel-103-2.json
```

To look up several parcels in one go, type their numbers separated by commas,
inside quotes. Add `--detail registry` to get one row per parcel with its area,
its parcel ID and the land registry unit it belongs to:

```bash
cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry
```

<!-- BEGIN GENERATED: output cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry -->
```text
📊 Found 3 parcels to process


RESULTS
=======
  #    Status    Parcel    Municipality      Area (m²)    Parcel ID    LR Unit    Main Book
  1      ✓       103/2     SAVAR (334979)        1,200    6564817      657        21277
  2      ✓       45        SAVAR (334979)          981    6564715      138        21277
  3      ✓       396/1     SAVAR (334979)        2,077    6565198      645        21277

✓ Successfully processed all 3 parcels
```
<!-- END GENERATED: output -->

Each row of **RESULTS** is one parcel. **Status** shows a tick for found and a
cross for not found. **LR Unit** and **Main Book** identify the land registry
unit of the parcel, which is what [get-lr-unit](get-lr-unit.md) needs next.
Without `--detail registry` the full record of every parcel is printed, one
after another.

For a longer list, prepare a file instead. The simplest file is a CSV, which
you can save from any spreadsheet program. It has two columns, `parcel_number`
and `municipality`, and looks like this:

<!-- BEGIN GENERATED: file parcels.csv -->
```text
parcel_number,municipality
103/2,SAVAR
45,
396/1,
```
<!-- END GENERATED: file -->

An empty municipality cell means "same as the row above". A JSON file with the
same content is accepted too. Example files:
[parcels.csv](../examples/parcels.csv), [parcels.json](../examples/parcels.json).
Open Terminal in the folder where the file is and name it with `--input`:

```bash
cadastral get-parcel --input parcels.csv --detail registry
```

To go on to the land registry, keep the result as a JSON file with
`--format json` and `--output`. The [get-lr-unit](get-lr-unit.md) page can read
that file directly:

```bash
cadastral get-parcel "103/2,279/6,1122/1" -m SAVAR --detail registry --format json --output parcels-found.json
cadastral get-lr-unit --input parcels-found.json --all
```

The field names in a JSON or CSV file follow the language of the tool, so a
colleague who runs it in the other language gets the names of that language.
The tool reads files back in either language.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCELS` | Optional. A value you type right after the command name | Not used |
| `--input`, `-i` `PATH` | File (CSV or JSON) with the parcels to look up, instead of typing them | Not used |
| `--municipality`, `-m` `TEXT` | Municipality name or code (required unless --input) | Not used |
| `--detail` | Detail level; registry lists each parcel with its land registry unit (`basic`, `full`, `owners`, `landuse`, `geometry`, `registry`) | `full` is used |
| `--show-owners` | Include ownership details | Not switched on |
| `--show-geometry` | Include boundary coordinates | Not switched on |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
| `--continue-on-error` / `--stop-on-error` | Continue processing after errors (default: continue) | `--continue-on-error` is used |
<!-- END GENERATED: options -->

## If something goes wrong

If the municipality is not recognised, the tool says so and stops:

<!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m NOWHERE -->
```text
✗ Error: Municipality 'NOWHERE' not found

Suggestions:
  • Search for municipalities: cadastral search-municipality NOWHERE
  • List all municipalities: cadastral list-municipalities
  • Use municipality code directly: --municipality 334979
```
<!-- END GENERATED: output -->

Check the spelling, or use the registration number instead of the name. You can
find it with [search-municipality](search-municipality.md).

If the parcel is not found, check the number on your document, including any
part after the slash. Other messages are explained on the
[errors page](../errors.md).

A parcel that does not exist does not stop a list. It gets a cross in the
**Status** column and an explanation in an **ERRORS** table at the end:

<!-- BEGIN GENERATED: output cadastral get-parcel "103/2,999" -m SAVAR --detail registry -->
```text
📊 Found 2 parcels to process


RESULTS
=======
  #    Status    Parcel    Municipality             Area (m²)    Parcel ID    LR Unit    Main Book
  1      ✓       103/2     SAVAR (334979)               1,200    6564817      657        21277
  2      ✗       999       SAVAR             Parcel not found    -            -          -

ERRORS
======
  #    Parcel         Error Type          Error Message
  2    999 (SAVAR)    Parcel not found    Parcel not found (parcel_number=999,
                                          municipality_reg_num=334979)

⚠️  Processed 1/2 parcels (50.0% success rate)
   1 parcel failed - see output for details
```
<!-- END GENERATED: output -->

Correct the number and run the command again for that parcel alone. If you
would rather stop at the first problem, add `--stop-on-error`. If the tool
cannot find the file you named with `--input`, check that Terminal is in the
folder where the file is, or type the full path to it.

## Related pages

- [get-lr-unit](get-lr-unit.md) reads the land registry unit whose number appears under the land registry heading.
- [search](search.md) is the short form of this command.
- [get-geometry](get-geometry.md) gives the boundary of the parcel for a map.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-parcel --help` prints:

```text
Usage: cadastral get-parcel [OPTIONS] PARCELS

  Get complete parcel information with ownership details.

  One parcel, or a list of parcels: several numbers separated by commas (or
  given as separate arguments), or a file with --input. For a list, the result
  is one record per parcel with its status; a parcel that is not found does not
  stop the others.

  Examples:
    cadastral get-parcel 103/2 -m SAVAR
    cadastral get-parcel 103/2 -m 334979 --show-owners
    cadastral get-parcel 103/2 -m 334979 --detail owners
    cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json

    # A list: one row per parcel with its land registry unit
    cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry

    # A list from a file (CSV or JSON), saved as JSON for get-lr-unit --input
    cadastral get-parcel --input parcels.csv --detail registry --format json -o parcels-found.json

  CSV file (an empty municipality cell repeats the row above):
    parcel_number,municipality
    103/2,SAVAR
    45,

  JSON file:
    [{"parcel_number": "103/2", "municipality": "SAVAR"}, {"parcel_id": "6564715"}]

Options:
  -i, --input PATH                File (CSV or JSON) with the parcels to look
                                  up, instead of typing them
  -m, --municipality TEXT         Municipality name or code (required unless
                                  --input)
  --detail [basic|full|owners|landuse|geometry|registry]
                                  Detail level; registry lists each parcel with
                                  its land registry unit
  --show-owners                   Include ownership details
  --show-geometry                 Include boundary coordinates
  -f, --format [table|json|csv]   Output format
  -o, --output PATH               Save output to file
  --continue-on-error / --stop-on-error
                                  Continue processing after errors (default:
                                  continue)
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
