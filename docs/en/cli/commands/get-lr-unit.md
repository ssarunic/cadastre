<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-lr-unit.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Read the land registry unit: owners, parcels, encumbrances

The land registry unit (zemljišnoknjižni uložak) is the legal record of a
property. This command shows its three sheets: the parcels it covers
(posjedovnica, list A), the owners and their shares (vlastovnica, list B), and
the encumbrances such as mortgages and easements (teretovnica, list C). It also
shows pending entries (plombe).

## When you would use this

- You need to know who legally owns a parcel and in what shares.
- You are checking for mortgages, easements, notes or other charges before a sale or a loan.
- You want to know whether a request for registration (prijedlog za upis) is pending on the unit, for example an inheritance decision that has not been entered yet.

## Before you start

There are two ways to name the unit. If you start from a parcel, give the
parcel number and the cadastral municipality, and the tool finds the unit for
you. If you already have the unit number and the main book (glavna knjiga) it
belongs to, give those two instead.

The main book is identified by a number the tool calls the main book ID. You
get it from a [get-parcel](get-parcel.md) list result or from a previous
lookup. Starting from the parcel is the easier route.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all -->
   ```text
                    LAND REGISTRY UNIT
    Unit Number        657
    Main Book          SAVAR
    Institution        Test Land Registry Office SAVAR
    Status             Aktivan
    Unit Type          VLASNIČKI
    Last Diary Number  Z-12345/2024

          PARCEL LIST (SHEET A)
    Parcel Number  Address  Area (m²)
    103/2          POLJE         1200
    TOTAL                        1200
   Parcel list as recorded in the land register; the address column is the culture or toponym of the
   old land register, not a location.

                                    OWNERSHIP SHEET (LIST B)
    Share  Owner                  Address                 OIB  Entry
    1/2    IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -    1.1 · 2018-06-10 · Z-5678/2018
    1/2    IVIĆ ANA, KĆI PETRA    SAVAR                   -    2.1 · 2018-06-10 · Z-5678/2018

                                       ENCUMBRANCES SHEET (LIST C)
    Description  Details
    1.           • 1.1: Stig. 23. svibnja 1949.
                 Z 487/49
                 Na temelju presude 29. siječnja 1940. agr. 1996/31 Sreskog suda u Preku, uknjižuje se
                 pravo ploduživanja do udaje, u korist:
                   In favour of:
                     IVIĆ MARIJA, KĆI PETRA, SAVAR
    2.           • 2.1: Pr. 20. srpnja 1979.
                 Z 2444/79
                 Na temelju rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67,
                 Općinskog suda u Zadru, uknjižuje se pravo ploduživanja u korist:
                   In favour of:
                     IVIĆ JELA UD. PETRA ZA 2/6
   ```
   <!-- END GENERATED: output -->

4. The first table, **LAND REGISTRY UNIT**, identifies the unit: its number,
   the main book, the office that keeps it, and **Last Diary Number**, the most
   recent file number entered in the diary (dnevnik); the row is empty when the
   unit has no entry in the electronic diary. **PARCEL LIST (SHEET A)**
   is the posjedovnica, list A. **OWNERSHIP SHEET (LIST B)** is the
   vlastovnica, list B, with the share of each owner as a fraction.
   **ENCUMBRANCES SHEET (LIST C)** is the teretovnica, list C. When list C is
   empty, the tool prints **No encumbrances found**. When an entry is registered
   in favour of someone (its text ends with "u korist:"), the persons follow
   under **In favour of**, with their address and OIB when the registry has them.

5. If the unit has pending entries, an extra line **Pending entries (plombe)**
   appears in the first table with the file numbers, and a warning follows. A
   plomba means a request for registration (prijedlog za upis) has been
   received and the unit may be about to change. Do not treat the sheets as final until it is resolved.

## Choices you can make

`--all` shows the three sheets. To see only one, use `--show-owners` for list
B, `--show-parcels` for list A, or `--show-encumbrances` for list C. Without any
of them the tool prints the first table only.

To see what each pending entry is about, add `--plombe-detail`. The tool then
asks the registry about every plomba, which takes one extra lookup each, and
prints a table with the type of the request for registration, its status and
the date it was received:

```bash
cadastral get-lr-unit --unit-number 449 --main-book 21277 --all --plombe-detail
```

<!-- BEGIN GENERATED: output cadastral get-lr-unit --unit-number 449 --main-book 21277 --all --plombe-detail -->
```text
                   LAND REGISTRY UNIT
 Unit Number               449
 Main Book                 SAVAR
 Institution               Zemljišnoknjižni odjel Zadar
 Status                    Aktivan
 Unit Type                 VLASNIČKI
 Last Diary Number         Z-18444/2026
 Pending entries (plombe)  Z-12564/2026
⚠️  This unit has pending entries (plombe) - a change may be in progress.

                             PENDING ENTRIES DETAIL (PLOMBE)
 File Number   Request                   Status                    Received  Outcome
 Z-12564/2026  Rješenje o nasljeđivanju  IZRADA NACRTA RJEŠENJA  2026-04-20  In progress

       PARCEL LIST (SHEET A)
 Parcel Number  Address  Area (m²)
 1122/1         OVČJA         3291
 TOTAL                        3291
Parcel list as recorded in the land register; the address column is the culture or toponym of the
old land register, not a location.

                           OWNERSHIP SHEET (LIST B)
 Share  Owner        Address    OIB          Entry
 1/4    Vlasnik 114  Adresa 75  00000000010  127.2 · 2026-05-14 · Z-15677/2026
 1/4    Vlasnik 115  Adresa 41  00000000028  128.1 · 2025-09-29 · Z-31325/2025
 1/4    Vlasnik 116  Adresa 31  00000000036  129.1 · 2025-09-29 · Z-31325/2025
 1/4    Vlasnik 116  Adresa 76  00000000036  133.1 · 2026-06-09 · Z-18444/2026

  ENCUMBRANCES SHEET (LIST C)
 Description            Details
 No encumbrances found
```
<!-- END GENERATED: output -->

To see at a glance whether anything registered against the unit stands in
the way of a sale, add `--blockers`. The tool reads the pending entries,
list C, the notes on the shares and the owners, names each finding by kind
(a mortgage, a dispute, an enforcement, a pre-emption right, a servitude, a
public body as co-owner) with the share or flat it applies to, and prints a
verdict: **No blockers**, **Conditional** or **Blocked**. Under the table it
lists the owners it flags as likely deceased, living abroad or a public body,
with the reason for each flag. Both are read from the register's text by a
fixed rule, which is printed under the table: treat them as a screening to
check against the sheets, not as a legal opinion. Add `--plombe-detail` as
well and each pending entry is named by the request it is.

```bash
cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR --blockers
```

<!-- BEGIN GENERATED: output cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR --blockers -->
```text
               LAND REGISTRY UNIT
 Unit Number        769
 Main Book          SAVAR
 Institution        Zemljišnoknjižni odjel Zadar
 Status             Aktivan
 Unit Type          VLASNIČKI
 Last Diary Number  Z-27986/2025

Sale screening: Blocked
                                           SALE BLOCKERS
 Kind                             Severity     Applies to  Description                       Amount
 Social-assistance claim          blocking     share 1     Zaprimljeno 05.05.2016.g. pod          -
                                                           brojem Z-9139/2016 ZABILJEŽBA,
                                                           TRAŽBINA SOCIJALNE POMOĆI,
                                                           RJEŠENJE CENTRA ZA SOCIJALNU
                                                           SKRB ZADAR KLASA:
                                                           UP/I-551-04/16-02/29, UR…
 Likely estate (owner probably    conditional  share 1     Vlasnik 117 holds 4/8 and is           -
 deceased)                                                 likely deceased: the share sits
                                                           in an estate until the heirs are
                                                           registered (ostavina)
 Likely estate (owner probably    conditional  share 3     Vlasnik 119 holds 1/8 and is           -
 deceased)                                                 likely deceased: the share sits
                                                           in an estate until the heirs are
                                                           registered (ostavina)
 Likely estate (owner probably    conditional  share 4     Vlasnik 326 holds 1/8 and is           -
 deceased)                                                 likely deceased: the share sits
                                                           in an estate until the heirs are
                                                           registered (ostavina)
Rule: blocked when any counted blocker is blocking, conditional when any is conditional, otherwise
no blockers; deleted entries are not counted. A screening of the register's text, not a legal
opinion.

                                       OWNER FLAGS (INFERRED)
 Owner        Share  Likely deceased  Address abroad  Public body  Basis
 Vlasnik 117  1      Yes              -               No           carried over from an earlier
                                                                   unit; the original entry is
                                                                   older
 Vlasnik 119  3      Yes              -               No           carried over from an earlier
                                                                   unit; the original entry is
                                                                   older
 Vlasnik 326  4      Yes              -               No           carried over from an earlier
                                                                   unit; the original entry is
                                                                   older
Flags are inferred from the entry age, the name and the address; confirm them.

          SUMMARY
 Total Parcels     7
 Total Area        4369 m²
 Number of Owners  7
 Sheet C entries   Yes

💡 Use --show-owners to see ownership details
💡 Use --show-parcels to see all parcels
💡 Use --show-encumbrances to see encumbrances
```
<!-- END GENERATED: output -->

The first table is the unit header as before. **Sale screening** gives the
verdict, and **SALE BLOCKERS** lists one row per finding: its **Kind**, its
**Severity** (blocking, conditional or informational), what it **Applies
to** (the whole unit, or one share or flat), the text of the entry and the
amount when there is one. A pending entry counts as blocking until it is
decided. **OWNER FLAGS (INFERRED)** lists only the owners with a flag and
the **Basis** of each one; an owner carried over from an earlier unit, or
registered decades ago, is flagged as likely deceased because such an entry
usually belongs to an estate, not because the register says so.

To name the unit directly instead of starting from a parcel, use
`--unit-number` and `--main-book` together, as in the example above. If you
know the name of the main book (glavna knjiga, normally the cadastral
municipality) but not its number, give the name with `--main-book-name` and the
tool looks the number up for you:

```bash
cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR --show-owners
```

The last column of the ownership sheet, **Entry**, tells you how each owner
got there: the order number of the registration entry (upis), the date the
request was received and its diary number (Z-broj). With `--all` the tool also
lists, under a share, the notes registered on that share alone, such as a
lifetime maintenance contract or a dispute.

To keep the result as a file, add `--format json` and `--output` with a file
name.

To read several units in one go, put them in a file and name it with
`--input`. The easiest file is the JSON that [get-parcel](get-parcel.md)
writes for a list of parcels with `--detail registry`: the tool takes the unit
of every parcel found and reads each unit once. You can also prepare a CSV
file with two columns, `lr_unit_number` and `main_book_id`, like the example
[lr_units.csv](../examples/lr_units.csv):

<!-- BEGIN GENERATED: file lr_units.csv -->
```text
lr_unit_number,main_book_id
657,21277
769,21277
449,21277
```
<!-- END GENERATED: file -->

Open Terminal in the folder where the file is and type:

```bash
cadastral get-lr-unit --input parcels-found.json --show-owners
```

<!-- BEGIN GENERATED: output cadastral get-lr-unit --input parcels-found.json --show-owners -->
```text
📄 Reading LR units from: parcels-found.json
📊 Found 3 LR units to process

                 LAND REGISTRY UNIT
 Unit Number        657
 Main Book          SAVAR
 Institution        Test Land Registry Office SAVAR
 Status             Aktivan
 Unit Type          VLASNIČKI
 Last Diary Number  Z-12345/2024

                                 OWNERSHIP SHEET (LIST B)
 Share  Owner                  Address                 OIB  Entry
 1/2    IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -    1.1 · 2018-06-10 · Z-5678/2018
 1/2    IVIĆ ANA, KĆI PETRA    SAVAR                   -    2.1 · 2018-06-10 · Z-5678/2018

---

               LAND REGISTRY UNIT
 Unit Number        769
 Main Book          SAVAR
 Institution        Zemljišnoknjižni odjel Zadar
 Status             Aktivan
 Unit Type          VLASNIČKI
 Last Diary Number  Z-27986/2025

                          OWNERSHIP SHEET (LIST B)
 Share  Owner        Address    OIB          Entry
 4/8    Vlasnik 117  -          -            1.1 · 2012-04-05 · Z-3983/2012
 1/8    Vlasnik 119  -          -            3.1 · 2012-04-05 · Z-3983/2012
 1/8    Vlasnik 326  -          -            4.1 · 2012-04-05 · Z-3983/2012
 1/8    Vlasnik 116  Adresa 31  00000000036  5.2 · 2020-02-14 · Z-3937/2020
 1/24   Vlasnik 135  Adresa 10  00000000850  6.1 · 2018-03-21 · Z-6789/2018
 1/24   Vlasnik 327  Adresa 10  00000000868  7.1 · 2018-03-21 · Z-6789/2018
 1/24   Vlasnik 328  Adresa 32  00000000876  8.1 · 2018-03-21 · Z-6789/2018

---

                   LAND REGISTRY UNIT
 Unit Number               449
 Main Book                 SAVAR
 Institution               Zemljišnoknjižni odjel Zadar
 Status                    Aktivan
 Unit Type                 VLASNIČKI
 Last Diary Number         Z-18444/2026
 Pending entries (plombe)  Z-12564/2026
⚠️  This unit has pending entries (plombe) - a change may be in progress.

                           OWNERSHIP SHEET (LIST B)
 Share  Owner        Address    OIB          Entry
 1/4    Vlasnik 114  Adresa 75  00000000010  127.2 · 2026-05-14 · Z-15677/2026
 1/4    Vlasnik 115  Adresa 41  00000000028  128.1 · 2025-09-29 · Z-31325/2025
 1/4    Vlasnik 116  Adresa 31  00000000036  129.1 · 2025-09-29 · Z-31325/2025
 1/4    Vlasnik 116  Adresa 76  00000000036  133.1 · 2026-06-09 · Z-18444/2026

✓ Successfully processed all 3 LR units
```
<!-- END GENERATED: output -->

The units are printed one after another, separated by a line of dashes, each
laid out as above. The sheet choices apply to every unit. When one unit cannot
be read, the tool continues with the rest and lists the failures under
**ERRORS** at the end; add `--stop-on-error` to stop at the first problem
instead. For a long list, keep the result as a file with `--format json` and
`--output`.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--unit-number`, `-u` `TEXT` | Land registry unit number (e.g., '769') | Not used |
| `--main-book`, `-b` `INTEGER` | Main book ID (e.g., 21277) | Not used |
| `--main-book-name`, `-n` `TEXT` | Main book name (e.g., SAVAR), used instead of the ID | Not used |
| `--from-parcel`, `-p` `TEXT` | Get LR unit from parcel number | Not used |
| `--municipality`, `-m` `TEXT` | Municipality name or code (required with --from-parcel) | Not used |
| `--show-owners`, `-o` | Display ownership details (Sheet B) | Not switched on |
| `--show-parcels`, `-P` | Display all parcels in unit (Sheet A) | Not switched on |
| `--show-encumbrances`, `-e` | Display encumbrances (Sheet C) | Not switched on |
| `--plombe-detail`, `-D` | Resolve detail of pending entries (plombe) - one extra request per plomba | Not switched on |
| `--blockers` | Show what is registered against the unit that bears on a sale (plombe, mortgages, disputes...) and the inferred owner flags | Not switched on |
| `--all`, `-a` | Show all sheets | Not switched on |
| `--input`, `-i` `PATH` | File (CSV or JSON) with the units to read, or a get-parcel list result | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output` `PATH` | Save output to file | Not used |
| `--continue-on-error` / `--stop-on-error` | Continue processing after errors (default: continue) | `--continue-on-error` is used |
<!-- END GENERATED: options -->

## If something goes wrong

If you give a parcel but forget the municipality, the tool stops and asks for it:

<!-- BEGIN GENERATED: output cadastral get-lr-unit --from-parcel 103/2 -->
```text
✗ Error: --municipality is required when using --from-parcel
```
<!-- END GENERATED: output -->

Add `-m` and the municipality name or number.

If the unit number does not exist in that main book, the tool reports an error
that ends with `404 Not Found`. Check both numbers against your document. Other
messages are explained on the [errors page](../errors.md).

## Related pages

- [get-parcel](get-parcel.md) shows the cadastral side of the same parcel, including the possessors.
- [get-parcel](get-parcel.md) with `--detail registry` lists the units of many parcels, ready for `--input`.
- [Glossary](../glossary.md) explains list A, B and C and the plomba.
- [get-parcel](get-parcel.md) with `--show-owners` shows the possessors, to compare with the owners a blocker names.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-lr-unit --help` prints:

```text
Usage: cadastral get-lr-unit [OPTIONS]

  Get detailed land registry unit information.

  Retrieve complete information about a land registry unit (zemljišnoknjižni
  uložak), including ownership (Sheet B), parcels (Sheet A), and encumbrances
  (Sheet C).

  One unit, named by number and main book or found from a parcel; or a list of
  units from a file with --input: a CSV or JSON with lr_unit_number and
  main_book_id, or the JSON that get-parcel writes for a list of parcels.

  Examples:
    # Get by unit number and main book ID
    cadastral get-lr-unit --unit-number 769 --main-book 21277

    # Get by unit number and main book name (resolved through the main-book search)
    cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR

    # Get from parcel (automatic lookup)
    cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

    # Show only ownership information
    cadastral get-lr-unit -u 769 -b 21277 --show-owners

    # Show all sheets
    cadastral get-lr-unit -p 279/6 -m SAVAR --all

    # What is registered against the unit that bears on a sale, and the owner flags
    cadastral get-lr-unit -u 769 -n SAVAR --blockers

    # Export to JSON
    cadastral get-lr-unit -u 769 -b 21277 --format json --output lr-unit.json

    # Several units from a file, all sheets of each
    cadastral get-lr-unit --input lr_units.csv --all

    # The units of a list of parcels (pipeline)
    cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry --format json -o parcels.json
    cadastral get-lr-unit --input parcels.json --show-owners

  ⚠️  Demo project: before using any server other than the included mock, verify
  your rights to use it; use at your own risk

Options:
  -u, --unit-number TEXT          Land registry unit number (e.g., '769')
  -b, --main-book INTEGER         Main book ID (e.g., 21277)
  -n, --main-book-name TEXT       Main book name (e.g., SAVAR), used instead of
                                  the ID
  -p, --from-parcel TEXT          Get LR unit from parcel number
  -m, --municipality TEXT         Municipality name or code (required with
                                  --from-parcel)
  -o, --show-owners               Display ownership details (Sheet B)
  -P, --show-parcels              Display all parcels in unit (Sheet A)
  -e, --show-encumbrances         Display encumbrances (Sheet C)
  -D, --plombe-detail             Resolve detail of pending entries (plombe) -
                                  one extra request per plomba
  --blockers                      Show what is registered against the unit that
                                  bears on a sale (plombe, mortgages,
                                  disputes...) and the inferred owner flags
  -a, --all                       Show all sheets
  -i, --input PATH                File (CSV or JSON) with the units to read, or
                                  a get-parcel list result
  -f, --format [table|json|csv]   Output format
  --output PATH                   Save output to file
  --continue-on-error / --stop-on-error
                                  Continue processing after errors (default:
                                  continue)
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
