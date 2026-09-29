<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-possession-sheet.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# See a possession sheet with its parcels

A possession sheet (posjedovni list) is the cadastre's record of who
possesses a group of parcels. This command shows the whole sheet: every
parcel on it, with its area, land use and land registry unit, and, when you
ask for them, the possessors recorded on the sheet.

## When you would use this

- An inheritance names a possession sheet, and you want the list of parcels
  on it before you look up each one in the land registry.
- A client says "our land is on posjedovni list 363" and you want to see how
  much land that is and who the cadastre records as possessing it.
- You want to check whether a parcel someone mentions is on the same sheet as
  the others.

## Before you start

You need the exact possession sheet number and the cadastral municipality
(katastarska općina), both printed on the extract from the possession sheet
and on most inheritance decisions. If you only know the start of the number,
[search-possession-sheet](search-possession-sheet.md) lists the sheets that
begin with it.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-possession-sheet 363 -m SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-possession-sheet 363 -m SAVAR -->
   ```text
   POSSESSION SHEET
   ================
     Sheet Number    363
     Sheet ID        11731543
     Municipality    SAVAR (334979)
     Possessors      119
     Parcels         7
     Total area      127,299 m²

   PARCELS
   =======
     Parcel Number    Area (m²)    Land Use          Cadastre/LR harmonized    LR Unit
     1090                48,494    PAŠNJAK 48,494              No              866 / 21277
     1098/1               4,863    PAŠNJAK 4,863               No              866 / 21277
     1110/1               2,604    PAŠNJAK 2,604               No              866 / 21277
     1111/1               8,610    PAŠNJAK 8,610               No              866 / 21277
     1122/1               1,618    VINOGRAD 1,618              No              449 / 21277
     1131/6              59,747    CESTA 59,747                No              866 / 21277
     1198                 1,363    PAŠNJAK 1,363               No              866 / 21277

   💡 Registered owners (land registry): cadastral get-lr-unit --unit-number <UNIT> --main-book
   <MAIN_BOOK> --show-owners
   ```
   <!-- END GENERATED: output -->

4. The first block names the sheet and counts what is on it. **Total area**
   adds up the cadastre areas of the parcels. The **PARCELS** table lists
   every parcel: **Land Use** is the cadastre's classification with the
   area of each kind, **Cadastre/LR harmonized** says whether the cadastre
   and the land registry agree about the parcel, and **LR Unit** gives the
   land registry unit and main book you pass to
   [get-lr-unit](get-lr-unit.md) for the registered owners.

## Choices you can make

Add `--show-owners` to see the possessors recorded on the sheet, with their
shares and addresses. They are possessors according to the cadastre, not
the registered owners; the registered owners are in the land registry unit
named in the **LR Unit** column, and the last line of the output shows the
command that reads it.

Some sheets are harmonized with the land registry: for them the cadastre
records no possessors of its own and refers to the land registry unit
instead. The tool then says **in the land registry (harmonized sheet)** on
the **Possessors** line and, with `--show-owners`, lists the registered
owners of that unit under **REGISTERED OWNERS (LAND REGISTRY)**; in JSON
`possessors_in_land_registry` is `true` and the people are under `owners`.

`--format json` writes the sheet as one document, with `parcels`,
`total_parcels`, `total_area_m2` and `parcels_complete`; `--format csv`
writes one row per parcel. Both go to a file with `--output`.

The cadastre's parcel search has never been seen to return more than 30
parcels for one sheet. When a sheet comes back with exactly that many, the
tool warns that the list may be incomplete and `parcels_complete` is
`false`; check the extract from the possession sheet in that case.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `SHEET_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code (e.g., SAVAR or 334979) | Required |
| `--show-owners` | Include the possessors recorded on the sheet | Not switched on |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

If there is no sheet with that exact number in the cadastral municipality,
the tool stops with this line:

<!-- BEGIN GENERATED: output cadastral get-possession-sheet 999 -m SAVAR -->
```text
✗ Error: Possession sheet '999' not found in municipality SAVAR
```
<!-- END GENERATED: output -->

Check the number on your document; the number must be complete, so try
[search-possession-sheet](search-possession-sheet.md) if you only know how it
starts. Other messages are explained on the [errors page](../errors.md).

## Related pages

- [get-lr-unit](get-lr-unit.md) shows the registered owners and the charges of the land registry unit a parcel belongs to.
- [get-parcel](get-parcel.md) shows one parcel in full, with its possession sheet.
- [search-possession-sheet](search-possession-sheet.md) finds the sheets whose number starts with a text.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-possession-sheet --help` prints:

```text
Usage: cadastral get-possession-sheet [OPTIONS] SHEET_NUMBER

  Get a possession sheet (posjedovni list) with its parcels.

  Shows the sheet, every parcel on it with its area, land use and land registry
  unit, and with --show-owners the possessors recorded on the sheet. The number
  is matched exactly; search-possession-sheet lists the sheets whose number
  starts with a text.

  Examples:
    cadastral get-possession-sheet 363 -m SAVAR
    cadastral get-possession-sheet 363 -m SAVAR --show-owners
    cadastral get-possession-sheet 363 -m 334979 --format json -o sheet.json

Options:
  -m, --municipality TEXT        Municipality name or code (e.g., SAVAR or
                                 334979)  [required]
  --show-owners                  Include the possessors recorded on the sheet
  -f, --format [table|json|csv]  Output format
  -o, --output PATH              Save output to file
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
