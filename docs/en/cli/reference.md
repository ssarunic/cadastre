<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/reference.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Complete reference

<!-- BEGIN GENERATED: reference -->
Every command, with a link to its page. The command is what you type; the link is what it is for.

## Look up parcels and units

- `cadastral search`: [Check a parcel quickly](commands/search.md). Quick search for parcels with basic information.
- `cadastral get-parcel`: [See everything the cadastre holds about a parcel](commands/get-parcel.md). Get complete parcel information with ownership details.
- `cadastral get-lr-unit`: [Read the land registry unit: owners, parcels, encumbrances](commands/get-lr-unit.md). Get detailed land registry unit information.

## Find municipalities and offices

- `cadastral search-municipality`: [Find the number of a cadastral municipality](commands/search-municipality.md). Search and filter municipalities.
- `cadastral list-municipalities`: [List the cadastral municipalities of an office](commands/list-municipalities.md). List municipalities with optional filtering.
- `cadastral list-offices`: [List the cadastral offices](commands/list-offices.md). List all cadastral offices in Croatia.

## Boundaries and maps

- `cadastral get-geometry`: [Get the boundary of a parcel for a map](commands/get-geometry.md). Get parcel boundary coordinates for GIS integration.
- `cadastral download-gis`: [Download the boundary data of a whole municipality](commands/download-gis.md). Download complete GIS data for a municipality.

## Check the tool itself

- `cadastral info`: [Check that the tool is set up](commands/info.md). Display system information and cache status.
- `cadastral cache list`: [See which municipalities are stored on your computer](commands/cache-list.md). List cached municipalities.
- `cadastral cache info`: [See how much boundary data is stored](commands/cache-info.md). Show detailed cache information.
- `cadastral cache clear`: [Remove stored boundary data](commands/cache-clear.md). Clear cached GIS data.

## Other

- `cadastral get-possession-sheet`: [See a possession sheet with its parcels](commands/get-possession-sheet.md). Get a possession sheet (posjedovni list) with its parcels.
- `cadastral get-zoning`: [Find out whether a parcel is in a building area](commands/get-zoning.md). Find out which spatial-plan building area a parcel lies in.
- `cadastral list-books-of-dc`: [List the books of deposited contracts](commands/list-books-of-dc.md). List books of deposited contracts (knjige položenih ugovora, KPU).
- `cadastral list-main-books`: [Find the main book of a cadastral municipality](commands/list-main-books.md). List land registry main books (glavne knjige).
- `cadastral search-possession-sheet`: [Find a possession sheet by its number](commands/search-possession-sheet.md). Find a possession sheet (posjedovni list) by number.
<!-- END GENERATED: reference -->

## Other pages

- [Start here](start-here.md): the tutorial.
- [Glossary](glossary.md): the words of the land registry and the cadastre.
- [Errors](errors.md): what the messages mean.
- [Installation](install.md): for the technical colleague who sets the tool up.
