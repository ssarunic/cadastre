<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/search-municipality.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Find the number of a cadastral municipality

Every cadastral municipality (katastarska općina, k.o.) has a registration
number. This command finds it from the name, or lists the municipalities that
belong to a cadastral office.

## When you would use this

- Two municipalities have the same or a similar name and you want to be sure which one you are looking at.
- A command refused the municipality name and you need the number instead.
- You want to know which cadastral office (područni ured za katastar) and department a municipality belongs to.

## Before you start

You need the name of the municipality, or part of it.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral search-municipality SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral search-municipality SAVAR -->
   ```text
   Found 1 municipalities (search='SAVAR'):

   +--------+--------+----------+--------------+
   |   Code | Name   |   Office |   Department |
   +========+========+==========+==============+
   | 334979 | SAVAR  |      114 |          116 |
   +--------+--------+----------+--------------+
   ```
   <!-- END GENERATED: output -->

4. **Code** is the registration number you can give to any other command after
   `-m`. **Office** and **Department** are the numbers of the cadastral office
   and its department.

## Choices you can make

To list every municipality of one office, give the office number with
`--office`. You can combine it with a name to narrow the list:

```bash
cadastral search-municipality --office 114
```

If you only want to know how many municipalities match, add `--count-only`. To
keep the list as a file, add `--format csv` and `--output` with a file name.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `SEARCH_TERM` | Optional. A value you type right after the command name | Not used |
| `--office`, `-o` `TEXT` | Filter by cadastral office ID (e.g., 114) | Not used |
| `--department`, `-d` `TEXT` | Filter by department ID (e.g., 116) | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-out` `PATH` | Save output to file | Not used |
| `--count-only` | Show count only | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If nothing matches, you will see this:

<!-- BEGIN GENERATED: output cadastral search-municipality NOWHERE -->
```text
✗ Error: No municipalities found for 'NOWHERE'
```
<!-- END GENERATED: output -->

Try a shorter part of the name, or list the whole office with `--office` and
look for the name in the list. Other messages are explained on the
[errors page](../errors.md).

## Related pages

- [list-municipalities](list-municipalities.md) does the same job with a different set of filters.
- [list-offices](list-offices.md) shows the office numbers to use with `--office`.
- [search](search.md) is where you use the number you found.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral search-municipality --help` prints:

```text
Usage: cadastral search-municipality [OPTIONS] SEARCH_TERM

  Search and filter municipalities.

  Examples:
    cadastral search-municipality SAVAR
    cadastral search-municipality --office 114
    cadastral search-municipality --office 114 --department 116
    cadastral search-municipality SAVAR --office 114

Options:
  -o, --office TEXT              Filter by cadastral office ID (e.g., 114)
  -d, --department TEXT          Filter by department ID (e.g., 116)
  -f, --format [table|json|csv]  Output format
  -out, --output PATH            Save output to file
  --count-only                   Show count only
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
