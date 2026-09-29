"""Parcel information commands for CLI."""

from typing import Any

import click
from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _, ngettext
from cadastral_api.models.entities import ParcelInfo
from cadastral_api.models.gis_entities import build_map_url
from rich.console import Console
from rich.table import Table

from cadastral_cli.formatters import (
    command_help,
    describe_error,
    error_type_value_label,
    print_error,
    print_output,
)
from cadastral_cli.input_parsers import ParcelInput, parse_cli_list, parse_input_file
from cadastral_cli.list_processing import (
    ListSummary,
    ListWording,
    parcel_row,
    print_list_errors,
    print_list_footer,
    process_parcel_list,
)

from .search import _resolve_municipality

console = Console()


_GET_PARCEL_HELP = command_help(_("""Get complete parcel information with ownership details.

One parcel, or a list of parcels: several numbers separated by commas (or
given as separate arguments), or a file with --input. For a list, the result
is one record per parcel with its status; a parcel that is not found does not
stop the others.

Examples:
  cadastral get-parcel 103/2 -m SAVAR
  cadastral get-parcel 103/2 -m 334979 --show-owners
  cadastral get-parcel 103/2 -m 334979 --detail owners
  cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json

  # A list: one row per parcel with its land registry unit
  cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry

  # A list from a file (CSV or JSON), saved as JSON for get-lr-unit --input
  cadastral get-parcel --input parcels.csv --detail registry --format json -o parcels-found.json

CSV file (an empty municipality cell repeats the row above):
  parcel_number,municipality
  103/2,SAVAR
  45,

JSON file:
  [{"parcel_number": "103/2", "municipality": "SAVAR"}, {"parcel_id": "6564715"}]"""))


@click.command("get-parcel", help=_GET_PARCEL_HELP)
@click.argument("parcels", nargs=-1)
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help=_("File (CSV or JSON) with the parcels to look up, instead of typing them"),
)
@click.option(
    "--municipality", "-m", help=_("Municipality name or code (required unless --input)")
)
@click.option(
    "--detail",
    type=click.Choice(["basic", "full", "owners", "landuse", "geometry", "registry"]),
    default="full",
    help=_("Detail level; registry lists each parcel with its land registry unit"),
)
@click.option("--show-owners", is_flag=True, help=_("Include ownership details"))
@click.option("--show-geometry", is_flag=True, help=_("Include boundary coordinates"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-o", type=click.Path(), help=_("Save output to file"))
@click.option(
    "--continue-on-error/--stop-on-error",
    default=True,
    help=_("Continue processing after errors (default: continue)"),
)
@click.pass_context
def get_parcel(
    ctx: click.Context,
    parcels: tuple[str, ...],
    input_file: str | None,
    municipality: str | None,
    detail: str,
    show_owners: bool,
    show_geometry: bool,
    output_format: str,
    output: str | None,
    continue_on_error: bool,
) -> None:
    """Get complete parcel information with ownership details."""
    if not parcels and not input_file:
        print_error(_("Give at least one parcel number, or a file with --input"))
        raise SystemExit(1)
    if parcels and input_file:
        print_error(_("Cannot use both parcel numbers and --input"))
        raise SystemExit(1)
    if not input_file and not municipality:
        print_error(_("--municipality is required when parcels are given by number"))
        raise SystemExit(1)

    # A single number is one lookup; several numbers or a file are a list.
    is_list = bool(input_file) or len(parcels) != 1 or "," in parcels[0]
    if is_list:
        _get_parcel_list(
            ctx,
            parcels,
            input_file,
            municipality,
            detail,
            show_owners,
            show_geometry,
            output_format,
            output,
            continue_on_error,
        )
        return

    parcel_number = parcels[0]
    assert municipality is not None
    try:
        with CadastralAPIClient() as client:
            # Resolve municipality
            municipality_code = _resolve_municipality(client, municipality)

            # Get parcel
            with console.status(_("Fetching parcel {parcel_number}...").format(
                parcel_number=parcel_number
            )):
                parcel = client.get_parcel_by_number(parcel_number, municipality_code)

            if not parcel:
                print_error(_("Parcel '{parcel_number}' not found").format(
                    parcel_number=parcel_number
                ))
                raise SystemExit(1)

            # Get geometry if requested or for full detail (needed for accurate map URL)
            geometry = None
            if show_geometry or detail in ["geometry", "full"]:
                with console.status(_("Fetching geometry...")):
                    geometry = client.get_parcel_geometry(parcel_number, municipality_code)

            # Format output based on detail level
            if output_format != "table":
                # For non-table formats, output structured data
                data = _format_structured_data(parcel, geometry, detail, show_owners)
                print_output(data, output_format=output_format, file=output)
            else:
                # Rich formatted table output
                _print_table_output(parcel, geometry, detail, show_owners, show_geometry)

    except CadastralAPIError as e:
        if e.error_type == ErrorType.PARCEL_NOT_FOUND:
            parcel_num = e.details.get("parcel_number", parcel_number)
            muni_code = e.details.get("municipality_reg_num", municipality)
            print_error(
                _("Parcel '{parcel_number}' not found in municipality {municipality}").format(
                    parcel_number=parcel_num,
                    municipality=muni_code,
                )
            )
        else:
            print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# A list of parcels
# ---------------------------------------------------------------------------


def _get_parcel_list(
    ctx: click.Context,
    parcels: tuple[str, ...],
    input_file: str | None,
    municipality: str | None,
    detail: str,
    show_owners: bool,
    show_geometry: bool,
    output_format: str,
    output: str | None,
    continue_on_error: bool,
) -> None:
    """Look up several parcels and report one record per parcel."""
    try:
        try:
            if input_file:
                if output_format == "table":
                    console.print(
                        _("📄 Reading parcels from: {file}").format(file=input_file), style="dim"
                    )
                inputs = parse_input_file(input_file)
            else:
                assert municipality is not None
                inputs = parse_cli_list(parcels, municipality)
        except ValueError as e:
            print_error(_("Input parsing error: {error}").format(error=str(e)))
            raise SystemExit(1) from e

        if output_format == "table":
            console.print(
                ngettext(
                    "📊 Found {count} parcel to process\n",
                    "📊 Found {count} parcels to process\n",
                    len(inputs),
                ).format(count=len(inputs)),
                style="dim",
            )

        need_geometry = show_geometry or detail in ["geometry", "full"]
        with CadastralAPIClient() as client:
            summary = process_parcel_list(
                client, inputs, continue_on_error=continue_on_error, show_progress=True
            )
            geometries = _list_geometries(client, summary) if need_geometry else {}

        if output_format == "table":
            if detail == "registry":
                _print_list_overview(summary, show_owners)
            else:
                _print_list_details(summary, geometries, detail, show_owners, show_geometry)
        elif output_format == "json":
            rows = []
            for result in summary.results:
                row = parcel_row(result)
                if result.ok and detail != "registry":
                    row["full_data"] = _format_structured_data(
                        result.data, geometries.get(id(result)), detail, show_owners
                    )
                rows.append(row)
            print_output(summary.envelope(rows), output_format="json", file=output)
        else:
            print_output(_list_csv_rows(summary, show_owners), output_format="csv", file=output)

        print_list_footer(summary, _list_wording())
        if summary.failed > 0:
            raise SystemExit(1)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        if e.details:
            console.print(_("   Details: {details}").format(details=e.details), style="dim red")
        raise SystemExit(1) from e
    except SystemExit:
        raise
    except Exception as e:
        print_error(_("Unexpected error: {error}").format(error=str(e)))
        if ctx.obj.get("verbose"):
            raise
        raise SystemExit(1) from e


def _list_geometries(
    client: CadastralAPIClient, summary: ListSummary[ParcelInput, ParcelInfo]
) -> dict[int, Any]:
    """Best-effort geometry per successful result (for the map link and --show-geometry)."""
    geometries: dict[int, Any] = {}
    for result in summary.results:
        if not result.ok or result.data is None:
            continue
        try:
            geometries[id(result)] = client.get_parcel_geometry(
                result.data.parcel_number, result.data.municipality_reg_num
            )
        except Exception:  # noqa: BLE001 - the plain map link is used instead
            continue
    return geometries


def _describe_input(item: ParcelInput) -> str:
    if item.parcel_id:
        return f"ID: {item.parcel_id}"
    return f"{item.parcel_number} ({item.municipality})"


def _print_list_details(
    summary: ListSummary[ParcelInput, ParcelInfo],
    geometries: dict[int, Any],
    detail: str,
    show_owners: bool,
    show_geometry: bool,
) -> None:
    """Print every parcel as ``get-parcel`` prints one, with a header per parcel."""
    for index, result in enumerate(summary.results, 1):
        if not result.ok or result.data is None:
            console.print(
                f"\n[bold red]━━━ {_('Parcel')} {index}/{summary.total}: "
                f"✗ {_('ERROR')} ━━━[/bold red]"
            )
            console.print(f"{_('Parcel')}: {_describe_input(result.input)}")
            console.print(f"{_('Error')}: {error_type_value_label(result.error_type)}")
            console.print(f"{_('Message')}: {result.error_message or _('No error message')}")
            continue
        console.print(
            f"\n[bold green]━━━ {_('Parcel')} {index}/{summary.total} ━━━[/bold green]"
        )
        _print_table_output(
            result.data, geometries.get(id(result)), detail, show_owners, show_geometry
        )


def _print_list_overview(summary: ListSummary[ParcelInput, ParcelInfo], show_owners: bool) -> None:
    """One row per parcel: area, parcel ID and land registry unit (``--detail registry``)."""
    header = _("RESULTS")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("#", justify="right", style="dim")
    table.add_column(_("Status"), justify="center")
    table.add_column(_("Parcel"), style="bold")
    table.add_column(_("Municipality"))
    table.add_column(_("Area (m²)"), justify="right")
    table.add_column(_("Parcel ID"))
    table.add_column(_("LR Unit"))
    table.add_column(_("Main Book"))
    if show_owners:
        # Cadastre possession sheets list possessors, not legal owners.
        table.add_column(_("Possessors"), justify="right")

    for index, result in enumerate(summary.results, 1):
        parcel = result.data
        if result.ok and parcel is not None:
            lr_unit = parcel.resolved_lr_unit()
            row = [
                str(index),
                "[green]✓[/green]",
                parcel.parcel_number_display,
                f"{parcel.municipality_name} ({parcel.municipality_reg_num})",
                f"{parcel.area_numeric:,}" if parcel.area_numeric else _("N/A"),
                str(parcel.parcel_id),
                lr_unit.lr_unit_number if lr_unit else "-",
                str(lr_unit.main_book_id) if lr_unit and lr_unit.main_book_id else "-",
            ]
            if show_owners:
                row.append(str(parcel.total_possessors))
        else:
            shown = (
                f"ID: {result.input.parcel_id}"
                if result.input.parcel_id
                else result.input.parcel_number or ""
            )
            row = [
                str(index),
                "[red]✗[/red]",
                shown,
                result.input.municipality or _("N/A"),
                f"[red]{error_type_value_label(result.error_type)}[/red]",
                "-",
                "-",
                "-",
            ]
            if show_owners:
                row.append("-")
        table.add_row(*row)
    console.print(table)
    print_list_errors(summary, _describe_input, _list_wording())


def _list_wording() -> ListWording:
    """Words of the list summary, translated in the active language."""
    return ListWording(
        item_label=_("Parcel"),
        processed=lambda n: ngettext(
            "Successfully processed {total} parcel",
            "Successfully processed all {total} parcels",
            n,
        ),
        processed_partly=_("⚠️  Processed {successful}/{total} parcels ({rate}% success rate)"),
        failed=lambda n: ngettext(
            "   {count} parcel failed - see output for details",
            "   {count} parcels failed - see output for details",
            n,
        ),
    )


def _list_csv_rows(
    summary: ListSummary[ParcelInput, ParcelInfo], show_owners: bool
) -> list[dict[str, Any]]:
    """Flat rows for CSV: the summary record, plus the possessors when asked."""
    rows = []
    for result in summary.results:
        row = parcel_row(result)
        if show_owners and result.ok and result.data is not None:
            row["possessors"] = "; ".join(
                f"{p.name} ({p.ownership or _('N/A')})"
                for sheet in result.data.possession_sheets
                for p in sheet.possessors
            )
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# One parcel
# ---------------------------------------------------------------------------


def _print_table_output(
    parcel, geometry, detail: str, show_owners: bool, show_geometry: bool
) -> None:
    """Print rich formatted table output."""

    if detail == "basic":
        _print_basic_info(parcel)
    elif detail == "owners":
        _print_ownership_info(parcel)
    elif detail == "landuse":
        _print_landuse_info(parcel)
    elif detail == "registry":
        _print_registry_info(parcel)
    elif detail == "geometry":
        _print_basic_info(parcel)
        if geometry:
            _print_geometry_info(geometry)
    else:  # full
        print_parcel_details(
            parcel=parcel,
            geometry=geometry,
            show_owners=show_owners,
            show_geometry=show_geometry
        )


def print_parcel_details(
    parcel,
    geometry=None,
    show_owners: bool = False,
    show_geometry: bool = False,
) -> None:
    """Print the complete record of one parcel (the ``--detail full`` layout).

    Args:
        parcel: ParcelInfo object with parcel data
        geometry: Optional ParcelGeometry object for map URLs and geometry display
        show_owners: Whether to show ownership information
        show_geometry: Whether to show geometry details
    """
    # Basic info
    _print_basic_info(parcel)
    console.print()

    # Land use
    _print_landuse_info(parcel)

    # Ownership
    if show_owners or parcel.total_possessors > 0:
        console.print()
        _print_ownership_info(parcel)

    # Land registry
    console.print()
    _print_registry_info(parcel)

    # Geometry
    if show_geometry and geometry:
        console.print()
        _print_geometry_info(geometry)

    # Additional info (includes MAP URL)
    console.print()
    _print_additional_info(parcel, geometry)


def _print_basic_info(parcel) -> None:
    """Print basic parcel information."""
    header = _("PARCEL INFORMATION")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Parcel Number"), parcel.parcel_number_display)
    if parcel.is_building_parcel:
        # The API spells building parcels with a leading asterisk ("*35/1").
        table.add_row(_("Building parcel"), f"{_('Yes')} ({parcel.parcel_number})")
    table.add_row(_("Parcel ID"), str(parcel.parcel_id))
    table.add_row(_("Municipality"), f"{parcel.municipality_name} ({parcel.municipality_reg_num})")
    table.add_row(_("Address"), parcel.address or _("N/A"))
    table.add_row(_("Area"), f"{parcel.area_numeric:,} m²" if parcel.area_numeric else _("N/A"))
    table.add_row(_("Building Permitted"), _("Yes") if parcel.has_building_right else _("No"))
    table.add_row(
        _("Cadastre/LR harmonized"),
        _("Yes") if parcel.is_harmonized else "[bold red]" + _("No") + "[/bold red]",
    )

    console.print(table)

    if not parcel.is_harmonized:
        console.print(
            _("⚠️  Cadastre and land registry are NOT harmonized for this parcel - "
              "possessors (kataster) and registered owners (ZK) may differ."),
            style="yellow",
        )
        drill = (
            f"cadastral get-lr-unit --from-parcel {parcel.parcel_number} "
            f"-m {parcel.municipality_reg_num} --show-owners"
        )
        console.print(
            "   " + _("To see the other register, run: {command}").format(command=drill),
            style="dim",
        )


def _print_landuse_info(parcel) -> None:
    """Print land use information."""
    header = _("LAND USE")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    if not parcel.land_use_summary:
        console.print(_("No land use data available"), style="dim")
        return

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column(_("Type"), style="bold")
    table.add_column(_("Area (m²)"), justify="right")
    table.add_column(_("Percentage"), justify="right")
    table.add_column(_("Buildings"))
    table.add_column(_("Last change"), style="dim")

    total_area = parcel.area_numeric or sum(parcel.land_use_summary.values())

    for land_type, area in parcel.land_use_summary.items():
        percentage = (area / total_area * 100) if total_area > 0 else 0
        parts = [part for part in parcel.parcel_parts if part.name == land_type]
        # Find if this land type has buildings
        has_building = any(part.building for part in parts)
        # The administrative file of the last change, or the change-log number
        last_change = next(
            (
                part.last_change_log_file_num or part.last_change_log_number
                for part in parts
                if part.last_change_log_file_num or part.last_change_log_number
            ),
            "-",
        )
        table.add_row(
            land_type,
            f"{area:,}",
            f"{percentage:.1f}%",
            _("Yes") if has_building else _("No"),
            last_change,
        )

    console.print(table)


def _print_ownership_info(parcel) -> None:
    """Print cadastre possession-sheet data (posjedovni list).

    These are cadastre POSSESSORS, which are frequently NOT the registered
    land-registry owners. Registered owners (vlasnici) come from the land
    registry B-list - use ``cadastral get-lr-unit`` for those.
    """
    possessors_text = ngettext(
        "{count} possessor", "{count} possessors", parcel.total_possessors
    ).format(count=parcel.total_possessors)
    header = f"{_('POSSESSION SHEET (cadastre / posjedovni list)')} ({possessors_text})"
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    console.print(
        _("Note: cadastre possessors may differ from registered owners. "
          "For land-registry owners (vlasnici), use: cadastral get-lr-unit"),
        style="dim",
    )

    if not parcel.possession_sheets:
        console.print(_("No possession data available"), style="dim")
        return

    for i, sheet in enumerate(parcel.possession_sheets, 1):
        if len(parcel.possession_sheets) > 1:
            console.print(
                f"\n{_('Possession Sheet')} {i} - {sheet.possession_sheet_number or '-'}",
                style="bold yellow"
            )

        if not sheet.possessors:
            console.print(f"  {_('No possessors listed')}", style="dim")
            continue

        # Check if any possessor has condominium info
        has_condo_info = any(p.condominium_share_number for p in sheet.possessors)

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column(_("Name"), style="bold")
        table.add_column(_("Ownership"), justify="right")
        table.add_column(_("Address"))
        if has_condo_info:
            table.add_column(_("Unit"), justify="center", style="dim")
            table.add_column(_("Common Share"), justify="right", style="dim")

        for possessor in sheet.possessors:
            ownership_str = possessor.ownership or _("N/A")
            if possessor.ownership_decimal is not None:
                ownership_str = f"{possessor.ownership} ({possessor.ownership_decimal * 100:.1f}%)"

            row = [
                possessor.name,
                ownership_str,
                possessor.address or "-",
            ]
            if has_condo_info:
                row.append(possessor.condominium_share_number or "-")
                row.append(possessor.condominium_share_ownership or "-")

            table.add_row(*row)

        console.print(table)


def _print_registry_info(parcel) -> None:
    """Print land registry information."""
    header = _("LAND REGISTRY")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    lr = parcel.resolved_lr_unit()
    if lr is None:
        if parcel.is_building_parcel:
            console.print(
                _("Building parcels have no land registry unit of their own; the building "
                  "is registered on its land parcel."),
                style="dim",
            )
        else:
            console.print(
                _("This parcel is not in the land registry (cadastre only)"), style="dim"
            )
        return

    if parcel.lr_unit_from_links:
        console.print(
            _("(land registry unit resolved via related parcels - this parcel has "
              "no direct unit)"),
            style="dim",
        )

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Unit Number"), lr.lr_unit_number or _("N/A"))
    table.add_row(
        _("Main Book"),
        f"{lr.main_book_name} ({lr.main_book_id})" if lr.main_book_name else _("N/A")
    )
    table.add_row(_("Institution"), lr.institution_name or _("N/A"))
    table.add_row(_("Status"), _("Active") if lr.active else _("Inactive"))
    table.add_row(_("Verified"), _("Yes") if lr.verified else _("No"))

    console.print(table)


def _print_geometry_info(geometry) -> None:
    """Print geometry information."""
    header = _("GEOMETRY")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Coordinate System"), geometry.srs_name)
    table.add_row(_("Vertices"), str(geometry.coordinate_count))
    table.add_row(_("GIS Area"), f"{geometry.povrsina_graficka:.2f} m²")

    min_x, min_y, max_x, max_y = geometry.bounds
    table.add_row(_("Bounding Box"), "")
    table.add_row("  Min X", f"{min_x:,.2f} m")
    table.add_row("  Min Y", f"{min_y:,.2f} m")
    table.add_row("  Max X", f"{max_x:,.2f} m")
    table.add_row("  Max Y", f"{max_y:,.2f} m")
    table.add_row(_("  Width"), f"{max_x - min_x:,.2f} m")
    table.add_row(_("  Height"), f"{max_y - min_y:,.2f} m")

    console.print(table)
    console.print(
        f"\n💡 {_('To export coordinates')}: cadastral get-geometry {geometry.broj_cestice} "
        "--format wkt",
        style="dim"
    )


def _print_additional_info(parcel, geometry=None) -> None:
    """Print additional information."""
    header = _("ADDITIONAL INFO")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"), no_wrap=False, overflow="fold")

    # Map link centred on the parcel when geometry is available, plain viewer otherwise
    map_url = geometry.map_url() if geometry else build_map_url()

    table.add_row(_("Map URL"), map_url)
    table.add_row(_("Detail Sheet"), parcel.detail_sheet_number or _("N/A"))

    console.print(table)


def _format_structured_data(parcel, geometry, detail: str, show_owners: bool) -> dict:
    """Format parcel data for JSON/CSV export."""
    data = {
        "parcel_number": parcel.parcel_number,
        "parcel_number_display": parcel.parcel_number_display,
        "is_building_parcel": parcel.is_building_parcel,
        "parcel_id": parcel.parcel_id,
        "municipality_code": parcel.municipality_reg_num,
        "municipality_name": parcel.municipality_name,
        "address": parcel.address,
        "area_m2": parcel.area_numeric,
        "building_permitted": parcel.has_building_right,
        "cadastre_lr_harmonized": parcel.is_harmonized,
    }

    if detail in ["full", "landuse"]:
        data["land_use"] = parcel.land_use_summary
        data["parcel_parts"] = [
            {
                "type": part.name,
                "area": part.area_numeric,
                "has_building": part.building,
                "part_type": part.part_type,
                "building_right": part.building_right,
                "last_change_log_number": part.last_change_log_number,
                "last_change_log_file_num": part.last_change_log_file_num,
            }
            for part in parcel.parcel_parts
        ]

    if detail in ["full", "owners"] or show_owners:
        data["total_possessors"] = parcel.total_possessors
        data["ownership"] = [
            {
                "sheet_number": sheet.possession_sheet_number,
                "possessors": [
                    {
                        "name": p.name,
                        "ownership": p.ownership,
                        "ownership_decimal": p.ownership_decimal,
                        "address": p.address,
                        # Condominium-specific fields (included when present)
                        **(
                            {"condominium_unit": p.condominium_share_number}
                            if p.condominium_share_number
                            else {}
                        ),
                        **(
                            {"condominium_common_share": p.condominium_share_ownership}
                            if p.condominium_share_ownership
                            else {}
                        ),
                    }
                    for p in sheet.possessors
                ]
            }
            for sheet in parcel.possession_sheets
        ]

    if detail in ["full", "registry"]:
        # The unit may be reachable only through parcel links (no direct lrUnit).
        lr = parcel.resolved_lr_unit()
        data["land_registry"] = {
            "unit_number": lr.lr_unit_number if lr else None,
            "main_book": lr.main_book_name if lr else None,
            "main_book_id": lr.main_book_id if lr else None,
            "institution": lr.institution_name if lr else None,
            "active": lr.active if lr else None,
            "lr_reference_shape": parcel.lr_reference_shape,
            "reference_shape": lr.reference_shape if lr else None,
        }

    if geometry and detail == "geometry":
        data["geometry"] = {
            "srs_name": geometry.srs_name,
            "vertices": geometry.coordinate_count,
            "area_gis": geometry.povrsina_graficka,
            "bounds": {
                "min_x": geometry.bounds[0],
                "min_y": geometry.bounds[1],
                "max_x": geometry.bounds[2],
                "max_y": geometry.bounds[3],
            },
            "coordinates": [[c.x, c.y] for c in geometry.coordinates],
        }

    return data
