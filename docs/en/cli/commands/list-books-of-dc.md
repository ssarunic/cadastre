<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/list-books-of-dc.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# List the books of deposited contracts

Besides the main books, the land registry keeps books of deposited contracts
(knjiga položenih ugovora, KPU). They hold flats and business premises that
were sold before their building had a land registry unit. This command lists
those books with the land registry office that keeps each one.

## When you would use this

- A flat you are checking is not in any land registry unit and you suspect it is recorded in a book of deposited contracts.
- You want to know which land registry offices keep such books for a place.

## Before you start

You need the name of the place, usually the town or the cadastral municipality,
as it appears on your document. Without a name the tool lists every book it
knows, which can be long.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral list-books-of-dc --search ZADAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral list-books-of-dc --search ZADAR -->
   ```text
   1 book(s) of deposited contracts:

   +-----------+--------+------------------------------+-------------+
   |   Book ID | Name   | Land registry office         |   Office ID |
   +===========+========+==============================+=============+
   |     20501 | ZADAR  | Zemljišnoknjižni odjel Zadar |         284 |
   +-----------+--------+------------------------------+-------------+
   ```
   <!-- END GENERATED: output -->

4. **Book ID** is the number of the book, and the last two columns name the
   land registry office (zemljišnoknjižni odjel) that keeps it.

## Choices you can make

Add `--office` with the number of a land registry office to list only its
books, or `--count-only` to get only the number of books. `--format csv` with
`--output` keeps the list as a spreadsheet file.

The tool cannot yet open a book of deposited contracts the way it opens a land
registry unit; it only finds the book. Ask the land registry office named in
the list for the record itself.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--search`, `-s` `TEXT` | Search by book name | Not used |
| `--office`, `-o` `TEXT` | Filter by land registry office ID (e.g., 284) | Not used |
| `--institution` `TEXT` | Filter by institution name | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-out` `PATH` | Save output to file | Not used |
| `--count-only` | Show count only | Not switched on |
<!-- END GENERATED: options -->

## If something goes wrong

If no book has the name you typed, the tool says so:

<!-- BEGIN GENERATED: output cadastral list-books-of-dc --search NOWHERE -->
```text
No books of deposited contracts found
```
<!-- END GENERATED: output -->

Try a shorter part of the name, or leave `--search` out to see the whole list.
Other messages are explained on the [errors page](../errors.md).

## Related pages

- [list-main-books](list-main-books.md) lists the main books, where most land registry units are.
- [get-lr-unit](get-lr-unit.md) reads a land registry unit.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral list-books-of-dc --help` prints:

```text
Usage: cadastral list-books-of-dc [OPTIONS]

  List books of deposited contracts (knjige položenih ugovora, KPU).

  A book of deposited contracts holds flats that were sold before their building
  had a land registry unit. The list gives the book ID and the land registry
  office that keeps it.

  Examples:
    cadastral list-books-of-dc --search ZADAR
    cadastral list-books-of-dc --office 284 --format json

Options:
  -s, --search TEXT              Search by book name
  -o, --office TEXT              Filter by land registry office ID (e.g., 284)
  --institution TEXT             Filter by institution name
  -f, --format [table|json|csv]  Output format
  -out, --output PATH            Save output to file
  --count-only                   Show count only
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
