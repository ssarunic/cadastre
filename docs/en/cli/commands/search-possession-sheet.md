<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/search-possession-sheet.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Find a possession sheet by its number

A possession sheet (posjedovni list) is the cadastre's record of who possesses
a group of parcels. This command checks whether a sheet number exists in a
cadastral municipality and shows the number the cadastre uses internally for
it.

## When you would use this

- A document names a possession sheet number and you want to confirm it exists in that cadastral municipality.
- You typed part of a sheet number and want to see which sheets start with it.

## Before you start

You need the possession sheet number and the cadastral municipality
(katastarska općina), both usually printed on the extract from the possession
sheet.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral search-possession-sheet 363 -m SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral search-possession-sheet 363 -m SAVAR -->
   ```text
   +----------------+------------+
   |   Sheet Number |   Sheet ID |
   +================+============+
   |            363 |   11731543 |
   +----------------+------------+

   💡 Possessors and parcels of a sheet: cadastral get-possession-sheet <SHEET_NUMBER> -m 334979
   --show-owners
   ```
   <!-- END GENERATED: output -->

4. Every sheet whose number starts with what you typed is listed. **Sheet ID**
   is the cadastre's internal number for the sheet; you will not normally need
   it.

## Choices you can make

This command only confirms the sheet. For the sheet itself, with its
possessors and every parcel on it, use
[get-possession-sheet](get-possession-sheet.md) with the exact number.

`--format json` with `--output` keeps the result as a file.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `SHEET_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code (e.g., SAVAR or 334979) | Required |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

If no sheet starts with the number you typed, the tool stops with this line:

<!-- BEGIN GENERATED: output cadastral search-possession-sheet 999 -m SAVAR -->
```text
✗ Error: Possession sheet '999' not found in municipality SAVAR
```
<!-- END GENERATED: output -->

Check the number and the cadastral municipality on your document. Other
messages are explained on the [errors page](../errors.md).

## Related pages

- [get-possession-sheet](get-possession-sheet.md) shows a sheet with its possessors and parcels.
- [get-parcel](get-parcel.md) shows the possession sheet of a parcel with its possessors.
- [search](search.md) finds a parcel by its number.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral search-possession-sheet --help` prints:

```text
Usage: cadastral search-possession-sheet [OPTIONS] SHEET_NUMBER

  Find a possession sheet (posjedovni list) by number.

  Shows the sheet numbers that start with the number you give and the internal
  ID of each sheet. For the sheet itself, with its possessors and parcels, use
  get-possession-sheet with the exact number.

  Examples:
    cadastral search-possession-sheet 363 -m SAVAR
    cadastral search-possession-sheet 36 -m 334979 --format json

Options:
  -m, --municipality TEXT        Municipality name or code (e.g., SAVAR or
                                 334979)  [required]
  -f, --format [table|json|csv]  Output format
  -o, --output PATH              Save output to file
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
