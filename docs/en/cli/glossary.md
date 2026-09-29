<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/glossary.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Glossary

The words of the cadastre and the land registry, and where the tool shows each
of them. Croatian terms are given as they appear on official documents.

| Term | What it means | Where you see it in the tool |
|---|---|---|
| Katastarska čestica (k.č.) | A parcel: one numbered piece of land in the cadastre. | The parcel number you type after `search`, `get-parcel` and `get-geometry`. |
| Katastarska općina (k.o.) | The cadastral municipality a parcel belongs to. Each has a name and a registration number (matični broj), which the tool prints as its code. | The value after `-m` in most commands. [search-municipality](commands/search-municipality.md) finds the number. |
| Posjedovni list | The possession sheet of the cadastre: who possesses a parcel according to the cadastre. Not proof of ownership. | [get-possession-sheet](commands/get-possession-sheet.md); [get-parcel](commands/get-parcel.md) with `--show-owners`. |
| Posjednik | A possessor recorded in the cadastre. | The rows of the possession sheet on [get-parcel](commands/get-parcel.md). |
| Zemljišnoknjižni uložak (ZK uložak) | The land registry unit: the record of the legal state of a property, kept by the land registry department of the municipal court. | [get-lr-unit](commands/get-lr-unit.md). Its number also appears on [get-parcel](commands/get-parcel.md), for one parcel or a list. |
| Čestica zgrade (zgr.) | A building parcel: a parcel of the old cadastre that covers a building alone. Written `35/1 ZGR`, `35/1.ZGR` or `zgr. 35/1`; it has no land registry unit of its own. | The parcel number on [get-parcel](commands/get-parcel.md) and [search](commands/search.md), printed as `zgr. 35/1`. |
| Glavna knjiga | The main book: the volume of the land registry that holds the units of one cadastral municipality. | `--main-book` or `--main-book-name` on [get-lr-unit](commands/get-lr-unit.md); [list-main-books](commands/list-main-books.md) finds the number. |
| Knjiga položenih ugovora (KPU) | The book of deposited contracts: the land registry book for flats and business premises sold before their building had a land registry unit. | [list-books-of-dc](commands/list-books-of-dc.md). |
| Upis | A registration entry: the act by which an owner, a right or a note was entered in the unit. Each owner's entry shows its order number, receipt date and diary number. | The entry column of sheet B on [get-lr-unit](commands/get-lr-unit.md). |
| Posjedovnica (list A) | Sheet A: the parcels that make up the unit. | The first table after the unit header on [get-lr-unit](commands/get-lr-unit.md). |
| Vlastovnica (list B) | Sheet B: the owners and their shares. | `--show-owners` on [get-lr-unit](commands/get-lr-unit.md). |
| Teretovnica (list C) | Sheet C: liens (mortgages), easements, real burdens and notes. | `--show-encumbrances` on [get-lr-unit](commands/get-lr-unit.md). |
| Suvlasnički udio | A co-ownership share, written as a fraction such as 1/2. | The share column of sheet B. |
| Plomba | A mark that a request for registration (prijedlog za upis) has been received and not yet decided. The unit may change. | The pending entries line on [get-lr-unit](commands/get-lr-unit.md); `--plombe-detail` shows what each request is. |
| Dnevnik, broj Z | The diary of the land registry and the file number (Z-number) of a request for registration. | The last diary number on [get-lr-unit](commands/get-lr-unit.md) and the file numbers of the pending entries. |
| Etažno vlasništvo | Ownership of a special part of a property (a flat or business premises), tied to a co-ownership share of the whole. | The unit type row of the unit header on [get-lr-unit](commands/get-lr-unit.md). |
| Kultura, način uporabe zemljišta | The land use recorded in the cadastre, such as arable land, pasture or orchard. | The land use table on [get-parcel](commands/get-parcel.md). |
| OIB | The personal identification number of a natural or legal person. | The OIB column of sheet B, when the registry has it. |
| Područni ured za katastar | A regional cadastral office. | [list-offices](commands/list-offices.md). |
| Granica čestice | The boundary of a parcel as coordinates. | [get-geometry](commands/get-geometry.md) and [download-gis](commands/download-gis.md). |
| HTRS96/TM (EPSG:3765) | The official coordinate system of Croatia, used for all boundaries. | Every coordinate the tool prints. |
