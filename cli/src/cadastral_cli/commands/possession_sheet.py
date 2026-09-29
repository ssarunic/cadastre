"""get-possession-sheet: a possession sheet with its possessors and parcels."""

from typing import Any

import click
from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _
from rich.console import Console
from rich.table import Table

from cadastral_cli.formatters import command_help, describe_error, print_error, print_output

console = Console()

_HELP = command_help(
    _("""Get a possession sheet (posjedovni list) with its parcels.

Shows the sheet, every parcel on it with its area, land use and land
registry unit, and with --show-owners the possessors recorded on the sheet.
The number is matched exactly; search-possession-sheet lists the sheets
whose number starts with a text.

Examples:
  cadastral get-possession-sheet 363 -m SAVAR
  cadastral get-possession-sheet 363 -m SAVAR --show-owners
  cadastral get-possession-sheet 363 -m 334979 --format json -o sheet.json""")
)


@click.command("get-possession-sheet", help=_HELP)
@click.argument("sheet_number")
@click.option(
    "--municipality",
    "-m",
    required=True,
    help=_("Municipality name or code (e.g., SAVAR or 334979)"),
)
@click.option("--show-owners", is_flag=True, help=_("Include the possessors recorded on the sheet"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-o", type=click.Path(), help=_("Save output to file"))
@click.pass_context
def get_possession_sheet(
    ctx: click.Context,
    sheet_number: str,
    municipality: str,
    show_owners: bool,
    output_format: str,
    output: str | None,
) -> None:
    """Read one possession sheet with its possessors and parcels."""
    try:
        with CadastralAPIClient() as client:
            with console.status(
                _("Reading possession sheet {sheet}...").format(sheet=sheet_number)
            ):
                result = client.get_possession_sheet_parcels(sheet_number, municipality)
    except CadastralAPIError as e:
        if e.error_type is ErrorType.POSSESSION_SHEET_NOT_FOUND:
            print_error(
                _("Possession sheet '{sheet}' not found in municipality {municipality}").format(
                    sheet=sheet_number, municipality=municipality
                )
            )
        elif e.error_type is ErrorType.MUNICIPALITY_NOT_FOUND:
            print_error(
                _("Municipality '{municipality}' not found").format(municipality=municipality)
            )
        else:
            print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e

    sheet, parcels = result.sheet, result.parcels
    if output_format == "table":
        _print_sheet(result, show_owners)
        return

    parcel_rows = [_parcel_row(p) for p in parcels]
    if output_format == "csv":
        for row in parcel_rows:
            row["sheet_number"] = sheet.possession_sheet_number
            row["municipality_code"] = sheet.cad_municipality_reg_num
            row.pop("land_use", None)
        print_output(parcel_rows, output_format="csv", file=output)
        return

    data: dict[str, Any] = {
        "possession_sheet_id": sheet.possession_sheet_id,
        "sheet_number": sheet.possession_sheet_number,
        "municipality_code": sheet.cad_municipality_reg_num,
        "municipality_name": sheet.cad_municipality_name,
        "is_condominium": sheet.is_condominium,
        "total_possessors": len(sheet.possessors),
    }
    data["possessors_in_land_registry"] = result.possessors_in_land_registry
    unit = result.lr_unit
    data["lr_unit_number"] = unit.lr_unit_number if unit else None
    data["main_book_id"] = unit.main_book_id if unit else None
    if show_owners:
        if result.possessors_in_land_registry:
            data["owners"] = [
                {
                    "name": row["name"],
                    "share": row.get("share"),
                    "tax_number": row.get("tax_number"),
                    "address": row.get("address"),
                }
                for row in result.owner_rows()
            ]
        else:
            data["possessors"] = [
                {"name": p.name, "ownership": p.ownership, "address": p.address}
                for p in sheet.possessors
            ]
    data.update(
        {
            "parcels": parcel_rows,
            "total_parcels": len(parcels),
            "total_area_m2": result.total_area_m2,
            "parcels_complete": not result.maybe_truncated,
        }
    )
    print_output(data, output_format="json", file=output)


def _parcel_row(parcel: Any) -> dict[str, Any]:
    unit = parcel.resolved_lr_unit()
    return {
        "parcel_number": parcel.parcel_number,
        "parcel_id": parcel.parcel_id,
        "area_m2": parcel.area_numeric,
        "land_use": parcel.land_use_summary,
        "is_building_parcel": parcel.is_building_parcel,
        "cadastre_lr_harmonized": parcel.is_harmonized,
        "lr_unit_number": unit.lr_unit_number if unit else None,
        "main_book_id": unit.main_book_id if unit else None,
    }


def _print_sheet(result: Any, show_owners: bool) -> None:
    sheet, parcels = result.sheet, result.parcels
    total_area, truncated = result.total_area_m2, result.maybe_truncated
    header = _("POSSESSION SHEET")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    info = Table(show_header=False, box=None, padding=(0, 2))
    info.add_column(_("Field"), style="bold")
    info.add_column(_("Value"))
    info.add_row(_("Sheet Number"), sheet.possession_sheet_number or "-")
    info.add_row(_("Sheet ID"), str(sheet.possession_sheet_id or "-"))
    info.add_row(
        _("Municipality"),
        f"{sheet.cad_municipality_name or ''} ({sheet.cad_municipality_reg_num or ''})".strip(),
    )
    if result.possessors_in_land_registry:
        info.add_row(_("Possessors"), _("in the land registry (harmonized sheet)"))
    else:
        info.add_row(_("Possessors"), str(len(sheet.possessors)))
    info.add_row(_("Parcels"), str(len(parcels)))
    info.add_row(_("Total area"), f"{total_area:,} m²")
    if sheet.is_condominium:
        info.add_row(_("Condominium"), _("Yes"))
    console.print(info)

    if show_owners and result.possessors_in_land_registry:
        header = _("REGISTERED OWNERS (LAND REGISTRY)")
        console.print(f"\n{header}", style="bold cyan")
        console.print("=" * len(header), style="bold cyan")
        table = Table(box=None, padding=(0, 2))
        table.add_column(_("Name"), style="bold")
        table.add_column(_("Share"), justify="right")
        table.add_column(_("Address"))
        for row in result.owner_rows():
            share = row.get("share") or {}
            table.add_row(
                row["name"],
                f"{share['num']}/{share['den']}" if share else "-",
                row.get("address") or "-",
            )
        console.print(table)
        console.print(
            _(
                "This sheet is harmonized with the land registry: the cadastre records no "
                "possessors of its own; the registered owners above are read from the land "
                "registry unit."
            ),
            style="dim",
        )
    elif show_owners:
        header = _("POSSESSORS")
        console.print(f"\n{header}", style="bold cyan")
        console.print("=" * len(header), style="bold cyan")
        table = Table(box=None, padding=(0, 2))
        table.add_column(_("Name"), style="bold")
        table.add_column(_("Share"), justify="right")
        table.add_column(_("Address"))
        for possessor in sheet.possessors:
            table.add_row(possessor.name, possessor.ownership or "-", possessor.address or "-")
        console.print(table)

    header = _("PARCELS")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    table = Table(box=None, padding=(0, 2))
    table.add_column(_("Parcel Number"), style="bold")
    table.add_column(_("Area (m²)"), justify="right")
    table.add_column(_("Land Use"))
    table.add_column(_("Cadastre/LR harmonized"), justify="center")
    table.add_column(_("LR Unit"))
    for parcel in parcels:
        unit = parcel.resolved_lr_unit()
        land_use = "; ".join(f"{name} {area:,}" for name, area in parcel.land_use_summary.items())
        table.add_row(
            parcel.parcel_number_display,
            f"{parcel.area_numeric:,}" if parcel.area_numeric else _("N/A"),
            land_use or "-",
            _("Yes") if parcel.is_harmonized else _("No"),
            f"{unit.lr_unit_number} / {unit.main_book_id}" if unit else "-",
        )
    console.print(table)
    if truncated:
        console.print(
            _(
                "⚠️  {count} parcels is the most the cadastre's parcel search has ever returned "
                "for one sheet; the list may be incomplete."
            ).format(count=len(parcels)),
            style="yellow",
        )
    console.print(
        f"\n💡 {_('Registered owners (land registry)')}: cadastral get-lr-unit "
        f"--unit-number <{_('UNIT')}> --main-book <{_('MAIN_BOOK')}> --show-owners",
        style="dim",
    )
