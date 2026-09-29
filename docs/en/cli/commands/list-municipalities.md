<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/list-municipalities.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# List the cadastral municipalities of an office

Shows the cadastral municipalities with their registration numbers, filtered
by cadastral office, by department, or by part of a name.

## When you would use this

- You work with one cadastral office and want the numbers of all its municipalities on one sheet.
- You want to check which department a municipality belongs to before you contact the office.

## Before you start

You need the number of the cadastral office. The
[list-offices](list-offices.md) page shows all of them.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral list-municipalities --office 114
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral list-municipalities --office 114 -->
   ```text
   9 municipalities (office=114):

   +--------+----------+----------+--------------+
   |   Code | Name     |   Office |   Department |
   +========+==========+==========+==============+
   | 334731 | LUKA     |      114 |          116 |
   +--------+----------+----------+--------------+
   | 223417 | BIBINJE  |      114 |          116 |
   +--------+----------+----------+--------------+
   | 228826 | SUKOŠAN  |      114 |          116 |
   +--------+----------+----------+--------------+
   | 229652 | KALI     |      114 |          117 |
   +--------+----------+----------+--------------+
   | 334488 | PAŠMAN   |      114 |          117 |
   +--------+----------+----------+--------------+
   | 335355 | PREKO    |      114 |          117 |
   +--------+----------+----------+--------------+
   | 443512 | VRSI     |      114 |          116 |
   +--------+----------+----------+--------------+
   | 332445 | NOVIGRAD |      114 |          116 |
   +--------+----------+----------+--------------+
   | 334979 | SAVAR    |      114 |          116 |
   +--------+----------+----------+--------------+
   ```
   <!-- END GENERATED: output -->

4. **Code** is the number to give after `-m` in the other commands. The first
   line tells you how many municipalities the office has.

## Choices you can make

Add `--department` to narrow the list to one department of the office, or
`--search` with part of a name to look for one municipality:

```bash
cadastral list-municipalities --office 114 --search KALI
```

Without any filter the tool lists every municipality it knows, which is a long
list. Add `--count-only` to get only the number, or `--format csv` with
`--output` to keep the list as a spreadsheet file.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--office`, `-o` `TEXT` | Filter by cadastral office ID | Not used |
| `--department`, `-d` `TEXT` | Filter by department ID | Not used |
| `--search`, `-s` `TEXT` | Search by name | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-out` `PATH` | Save output to file | Not used |
| `--count-only` | Show count only | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If the office number is wrong, you will see this:

<!-- BEGIN GENERATED: output cadastral list-municipalities --office 999 -->
```text
✗ Error: API error: Municipality not found (office_id=999)
```
<!-- END GENERATED: output -->

Check the number on the [list-offices](list-offices.md) page. Other messages
are explained on the [errors page](../errors.md).

## Related pages

- [search-municipality](search-municipality.md) searches by name.
- [list-offices](list-offices.md) gives the office numbers.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral list-municipalities --help` prints:

```text
Usage: cadastral list-municipalities [OPTIONS]

  List municipalities with optional filtering.

  Examples:
    cadastral list-municipalities
    cadastral list-municipalities --office 114
    cadastral list-municipalities --office 114 --department 116
    cadastral list-municipalities --search ZADAR

Options:
  -o, --office TEXT              Filter by cadastral office ID
  -d, --department TEXT          Filter by department ID
  -s, --search TEXT              Search by name
  -f, --format [table|json|csv]  Output format
  -out, --output PATH            Save output to file
  --count-only                   Show count only
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
