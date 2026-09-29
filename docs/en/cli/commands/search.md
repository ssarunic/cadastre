<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/search.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Check a parcel quickly

Type a parcel number and the cadastral municipality, and get the basics on one
screen: where the parcel is, how big it is, what the land is used for, and how
many people the cadastre records on it.

## When you would use this

- A client mentions a parcel and you want to confirm it exists before you go any further.
- You need the area and the land use of a parcel for a contract or a valuation.
- You want the registration number of the municipality and the parcel's internal number for a later, more detailed lookup.

## Before you start

You need two things: the parcel number (broj katastarske čestice, for example
103/2) and the cadastral municipality (katastarska općina) it belongs to. Both
are on any extract from the cadastre or the land registry, and on most contracts.

You can give the municipality by name (SAVAR) or by its registration number
(334979). The tool accepts either.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral search 103/2 -m SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral search 103/2 -m SAVAR -->
   ```text
   Parcel Number       103/2
   Municipality        SAVAR (334979)
   Address             POLJE
   Area                1,200 m²
   Land Use            MASLINJAK
   Building Permitted  No
   Possessors          2 possessors

   💡 For full details: cadastral get-parcel 103/2 -m 334979
   ```
   <!-- END GENERATED: output -->

4. Read the lines from top to bottom. **Parcel Number** and **Municipality**
   confirm that the tool found the parcel you meant. **Area** is the surface in
   square metres. **Land Use** is the cadastral culture, in the wording of the
   cadastre. **Building Permitted** tells you whether building is allowed on the
   parcel according to the cadastre. **Possessors** is the number of people
   the cadastre records on the parcel. They are possessors (posjednici), not
   necessarily the legal owners; the land registry has those.

5. The last line suggests the command for the full details. Copy it if you need
   more than this summary.

## Choices you can make

The part after `-m` is the municipality. It can be a name or a number. If two
municipalities share a name, use the number, which you can find with
[search-municipality](search-municipality.md).

If you only know the beginning of a parcel number, add `--partial` to see every
parcel that starts with what you typed:

```bash
cadastral search 1 -m SAVAR --partial
```

To keep the result as a file instead of reading it on screen, add `--format json`
or `--format csv` and `--output` with a file name. A JSON file can be read by
other programs; a CSV file opens in a spreadsheet.

```bash
cadastral search 103/2 -m SAVAR --format csv --output parcel.csv
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCEL_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code (e.g., SAVAR or 334979) | Required |
| `--exact` / `--partial` | Exact match or partial search | `--exact` is used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

If the parcel number does not exist in that municipality, the tool says so and stops:

<!-- BEGIN GENERATED: output cadastral search 999 -m SAVAR -->
```text
✗ Error: Parcel '999' not found in municipality 334979
```
<!-- END GENERATED: output -->

Check the number on your document. Parcel numbers often contain a slash, and
103 is not the same parcel as 103/2.

If the municipality is not recognised, the message names it. Check the spelling,
or use the number instead. Other messages are explained on the
[errors page](../errors.md).

## Related pages

- [get-parcel](get-parcel.md) shows everything the cadastre holds about the parcel, including the recorded possessors.
- [get-lr-unit](get-lr-unit.md) shows the land registry unit: owners, shares and encumbrances.
- [search-municipality](search-municipality.md) finds the number of a cadastral municipality.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral search --help` prints:

```text
Usage: cadastral search [OPTIONS] PARCEL_NUMBER

  Quick search for parcels with basic information.

  Examples:
    cadastral search 103/2 --municipality SAVAR
    cadastral search 103/2 -m 334979
    cadastral search 114 -m 334979 --partial

Options:
  -m, --municipality TEXT        Municipality name or code (e.g., SAVAR or
                                 334979)  [required]
  --exact / --partial            Exact match or partial search
  -f, --format [table|json|csv]  Output format
  -o, --output PATH              Save output to file
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
