"""Discovery commands for CLI - list offices, municipalities, etc."""

from collections.abc import Callable, Sequence
from typing import Any

import click
from cadastral_api import CadastralAPIClient, __version__
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.i18n import _
from rich.console import Console

from cadastral_cli.formatters import command_help, describe_error, print_error, print_output

console = Console()


_LIST_OFFICES_HELP = command_help(_("""List all cadastral offices in Croatia.

Example:
  cadastral list-offices
  cadastral list-offices --format json"""))


@click.command("list-offices", help=_LIST_OFFICES_HELP)
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
def list_offices(ctx: click.Context, output_format: str, output: str | None) -> None:
    """List all cadastral offices in Croatia."""
    try:
        with CadastralAPIClient() as client:
            with console.status(_("Fetching cadastral offices...")):
                offices = client.list_cadastral_offices()

            if not offices:
                console.print(_("No offices found"), style="yellow")
                return

            # Format output
            data = [
                {
                    _("ID"): office.id,
                    _("Name"): office.name,
                }
                for office in offices
            ]

            if output_format == "table":
                console.print(_("\n{count} Cadastral Offices in Croatia:\n").format(
                    count=len(offices)
                ), style="green")
                print_output(data, output_format="table")
            else:
                export_data = [
                    {
                        "office_id": office.id,
                        "office_name": office.name,
                    }
                    for office in offices
                ]
                print_output(export_data, output_format=output_format, file=output)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


def municipality_table_rows(municipalities: Sequence[Any]) -> list[dict[str, Any]]:
    """Municipality search results as rows of the terminal table."""
    return [
        {
            _("Code"): m.municipality_reg_num,
            _("Name"): m.municipality_name,
            _("Office"): m.institution_id,
            _("Department"): m.department_id or _("N/A"),
        }
        for m in municipalities
    ]


def municipality_export_rows(municipalities: Sequence[Any]) -> list[dict[str, Any]]:
    """Municipality search results as JSON/CSV records."""
    return [
        {
            "municipality_code": m.municipality_reg_num,
            "municipality_name": m.municipality_name,
            "office_id": m.institution_id,
            "department_id": m.department_id,
            "display_name": m.display_value,
        }
        for m in municipalities
    ]


_LIST_MUNICIPALITIES_HELP = command_help(_("""List municipalities with optional filtering.

Examples:
  cadastral list-municipalities
  cadastral list-municipalities --office 114
  cadastral list-municipalities --office 114 --department 116
  cadastral list-municipalities --search ZADAR"""))


@click.command("list-municipalities", help=_LIST_MUNICIPALITIES_HELP)
@click.option("--office", "-o", help=_("Filter by cadastral office ID"))
@click.option("--department", "-d", help=_("Filter by department ID"))
@click.option("--search", "-s", help=_("Search by name"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-out", type=click.Path(), help=_("Save output to file"))
@click.option("--count-only", is_flag=True, help=_("Show count only"))
@click.pass_context
def list_municipalities(
    ctx: click.Context,
    office: str | None,
    department: str | None,
    search: str | None,
    output_format: str,
    output: str | None,
    count_only: bool
) -> None:
    """List municipalities with optional filtering."""
    try:
        with CadastralAPIClient() as client:
            # Build filter description
            filter_parts = []
            if search:
                filter_parts.append(f"search='{search}'")
            if office:
                filter_parts.append(f"office={office}")
            if department:
                filter_parts.append(f"department={department}")

            status_msg = _("Fetching municipalities")
            if filter_parts:
                status_msg += _(" ({filters})").format(filters=', '.join(filter_parts))
            status_msg += "..."

            with console.status(status_msg):
                municipalities = client.find_municipality(
                    search_term=search,
                    office_id=office,
                    department_id=department
                )

            if not municipalities:
                console.print(_("No municipalities found"), style="yellow")
                return

            if count_only:
                console.print(_("Found {count} municipality(ies)").format(
                    count=len(municipalities)
                ), style="green")
                return

            if output_format == "table":
                filter_desc = ""
                if filter_parts:
                    filter_desc = _(" ({filters})").format(filters=", ".join(filter_parts))
                console.print(_("\n{count} municipalities{filter_desc}:\n").format(
                    count=len(municipalities),
                    filter_desc=filter_desc
                ), style="green")
                print_output(municipality_table_rows(municipalities), output_format="table")
            else:
                print_output(
                    municipality_export_rows(municipalities),
                    output_format=output_format,
                    file=output,
                )

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


_LIST_MAIN_BOOKS_HELP = command_help(_("""List land registry main books (glavne knjige).

The main book ID is what get-lr-unit needs with --main-book; searching the
cadastral municipality name finds the book that holds its units.

Examples:
  cadastral list-main-books --search SAVAR
  cadastral list-main-books --office 284
  cadastral list-main-books --search SAVAR --format json"""))


@click.command("list-main-books", help=_LIST_MAIN_BOOKS_HELP)
@click.option("--search", "-s", help=_("Search by main book name"))
@click.option("--office", "-o", help=_("Filter by land registry office ID (e.g., 284)"))
@click.option("--institution", help=_("Filter by institution name"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-out", type=click.Path(), help=_("Save output to file"))
@click.option("--count-only", is_flag=True, help=_("Show count only"))
@click.pass_context
def list_main_books(
    ctx: click.Context,
    search: str | None,
    office: str | None,
    institution: str | None,
    output_format: str,
    output: str | None,
    count_only: bool,
) -> None:
    """List land registry main books."""
    _list_books(
        fetch=lambda client: client.find_main_book(
            search=search, office_id=office, institution_name=institution
        ),
        status=_("Fetching main books..."),
        empty=_("No main books found"),
        count=lambda n: _("Found {count} main book(s)").format(count=n),
        heading=lambda n: _("\n{count} main book(s):\n").format(count=n),
        table_row=lambda book: {
            _("Main Book ID"): book.main_book_id,
            _("Name"): book.main_book_name,
            _("Court"): book.court_name or _("N/A"),
            _("Office ID"): book.institution_id or _("N/A"),
        },
        export_row=lambda book: {
            "main_book_id": book.main_book_id,
            "main_book_name": book.main_book_name,
            "court_name": book.court_name,
            "institution_id": book.institution_id,
            "display_name": book.display_value1,
        },
        output_format=output_format,
        output=output,
        count_only=count_only,
    )


_LIST_BOOKS_OF_DC_HELP = command_help(
    _("""List books of deposited contracts (knjige položenih ugovora, KPU).

A book of deposited contracts holds flats that were sold before their building
had a land registry unit. The list gives the book ID and the land registry
office that keeps it.

Examples:
  cadastral list-books-of-dc --search ZADAR
  cadastral list-books-of-dc --office 284 --format json""")
)


@click.command("list-books-of-dc", help=_LIST_BOOKS_OF_DC_HELP)
@click.option("--search", "-s", help=_("Search by book name"))
@click.option("--office", "-o", help=_("Filter by land registry office ID (e.g., 284)"))
@click.option("--institution", help=_("Filter by institution name"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-out", type=click.Path(), help=_("Save output to file"))
@click.option("--count-only", is_flag=True, help=_("Show count only"))
@click.pass_context
def list_books_of_dc(
    ctx: click.Context,
    search: str | None,
    office: str | None,
    institution: str | None,
    output_format: str,
    output: str | None,
    count_only: bool,
) -> None:
    """List books of deposited contracts."""
    _list_books(
        fetch=lambda client: client.find_book_of_dc(
            search=search, office_id=office, institution_name=institution
        ),
        status=_("Fetching books of deposited contracts..."),
        empty=_("No books of deposited contracts found"),
        count=lambda n: _("Found {count} book(s)").format(count=n),
        heading=lambda n: _("\n{count} book(s) of deposited contracts:\n").format(count=n),
        table_row=lambda book: {
            _("Book ID"): book.book_id,
            _("Name"): book.book_name,
            _("Land registry office"): book.office_name or _("N/A"),
            _("Office ID"): book.office_id or _("N/A"),
        },
        export_row=lambda book: {
            "book_id": book.book_id,
            "book_name": book.book_name,
            "office_name": book.office_name,
            "office_id": book.office_id,
            "display_name": book.display_value1,
        },
        output_format=output_format,
        output=output,
        count_only=count_only,
    )


def _list_books(
    *,
    fetch: Callable[[CadastralAPIClient], Sequence[Any]],
    status: str,
    empty: str,
    count: Callable[[int], str],
    heading: Callable[[int], str],
    table_row: Callable[[Any], dict[str, Any]],
    export_row: Callable[[Any], dict[str, Any]],
    output_format: str,
    output: str | None,
    count_only: bool,
) -> None:
    """Fetch a list of land registry books and print it (shared by the two list commands)."""
    try:
        with CadastralAPIClient() as client:
            with console.status(status):
                books = fetch(client)

            if not books:
                console.print(empty, style="yellow")
                return

            if count_only:
                console.print(count(len(books)), style="green")
                return

            if output_format == "table":
                console.print(heading(len(books)), style="green")
                print_output([table_row(book) for book in books], output_format="table")
            else:
                print_output(
                    [export_row(book) for book in books], output_format=output_format, file=output
                )

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


_INFO_HELP = command_help(_("""Display system information and cache status.

Example:
  cadastral info"""))


@click.command("info", help=_INFO_HELP)
@click.pass_context
def info(ctx: click.Context) -> None:
    """Display system information and cache status."""
    try:
        with CadastralAPIClient() as client:
            header = _("Croatian Cadastral CLI")
            console.print(f"\n{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            console.print(_("Version: {version}").format(version=__version__))
            console.print(_("API Base: {base_url}").format(base_url=client.base_url))
            console.print()

            header = _("Cache Information")
            console.print(f"{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            cache_dir = client.gis_cache.cache_dir
            console.print(_("Cache Directory: {cache_dir}").format(cache_dir=cache_dir))

            # Check cache size and cached municipalities
            if cache_dir.exists():
                cached = client.gis_cache.cached_municipalities()
                if cached:
                    total_size = sum(entry.size_bytes for entry in cached)
                    console.print(_("Cache Size: {size} MB").format(
                        size=f"{total_size / 1024 / 1024:.1f}"
                    ))
                    console.print(_("Cached Municipalities: {count}").format(count=len(cached)))
                    for entry in cached[:10]:  # Show first 10
                        console.print(
                            f"  • {entry.municipality_reg_num} ({entry.size_bytes / 1024:.1f} KB)"
                        )
                    if len(cached) > 10:
                        console.print(_("  ... and {more} more").format(more=len(cached) - 10))
                else:
                    console.print(_("Cache is empty"))
            else:
                console.print(_("Cache directory does not exist yet"))

            # Upstream responses kept between calls (memory by default; a CLI
            # process starts empty, so this mostly says which backend is on)
            stats = client.cache.stats()
            console.print(
                _("Response cache: {backend}, {entries} entries, {size} MB").format(
                    backend=stats.backend,
                    entries=stats.entries,
                    size=f"{stats.bytes / 1024 / 1024:.1f}",
                )
            )

            console.print()
            header = _("API Settings")
            console.print(f"{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            console.print(_("Rate Limit: {rate_limit} seconds between requests").format(
                rate_limit=client.rate_limit
            ))
            console.print(_("Timeout: {timeout} seconds").format(
                timeout=client.timeout
            ))
            console.print(_("Unknown server fields: {policy}").format(
                policy=client.unknown_fields
            ))
            console.print()

            console.print(_("To clear cache: cadastral cache clear --all"), style="dim")

    except Exception as e:
        print_error(_("Error getting system info: {error}").format(error=str(e)))
        raise SystemExit(1) from e
