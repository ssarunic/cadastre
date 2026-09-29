<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/list-main-books.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Find the main book of a cadastral municipality

The land registry keeps its units in main books (glavne knjige), usually one
per cadastral municipality. This command finds a main book by name and shows
the number the tool calls the main book ID, together with the court that keeps
the book.

## When you would use this

- You have a land registry unit number from a document and know the cadastral municipality, but not the main book ID that [get-lr-unit](get-lr-unit.md) asks for.
- You want to know which municipal court keeps the land registry for a place.

## Before you start

You need the name of the cadastral municipality (katastarska općina) as it is
written on your document. The main book normally carries the same name.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral list-main-books --search SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral list-main-books --search SAVAR -->
   ```text
   1 main book(s):

   +----------------+--------+---------+-------------+
   |   Main Book ID | Name   | Court   |   Office ID |
   +================+========+=========+=============+
   |          21277 | SAVAR  | ZADAR   |         284 |
   +----------------+--------+---------+-------------+
   ```
   <!-- END GENERATED: output -->

4. **Main Book ID** is the number to give after `--main-book` in
   [get-lr-unit](get-lr-unit.md). **Court** is the municipal court whose land
   registry department keeps the book.

## Choices you can make

If you do not want to look the number up first, give the name straight to
[get-lr-unit](get-lr-unit.md) with `--main-book-name`; the tool runs this
search for you and uses the book it finds:

```bash
cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR
```

Add `--office` with the number of a land registry office to list every main
book that office keeps, or `--count-only` to get only the number of books.
`--format csv` with `--output` keeps the list as a spreadsheet file.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--search`, `-s` `TEXT` | Search by main book name | Not used |
| `--office`, `-o` `TEXT` | Filter by land registry office ID (e.g., 284) | Not used |
| `--institution` `TEXT` | Filter by institution name | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-out` `PATH` | Save output to file | Not used |
| `--count-only` | Show count only | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If no main book has the name you typed, the tool says so:

<!-- BEGIN GENERATED: output cadastral list-main-books --search NOWHERE -->
```text
No main books found
```
<!-- END GENERATED: output -->

Check the spelling of the cadastral municipality on your document, or search
for part of the name. Other messages are explained on the
[errors page](../errors.md).

## Related pages

- [get-lr-unit](get-lr-unit.md) reads the unit once you have the main book.
- [list-books-of-dc](list-books-of-dc.md) lists the books of deposited contracts, the other kind of land registry book.
- [search-municipality](search-municipality.md) finds the cadastral municipality itself.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral list-main-books --help` prints:

```text
Usage: cadastral list-main-books [OPTIONS]

  List land registry main books (glavne knjige).

  The main book ID is what get-lr-unit needs with --main-book; searching the
  cadastral municipality name finds the book that holds its units.

  Examples:
    cadastral list-main-books --search SAVAR
    cadastral list-main-books --office 284
    cadastral list-main-books --search SAVAR --format json

Options:
  -s, --search TEXT              Search by main book name
  -o, --office TEXT              Filter by land registry office ID (e.g., 284)
  --institution TEXT             Filter by institution name
  -f, --format [table|json|csv]  Output format
  -out, --output PATH            Save output to file
  --count-only                   Show count only
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
