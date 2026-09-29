"""MCP Prompts - Reusable templates for common workflows."""

import asyncio
import logging

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.models import ParcelInfo

logger = logging.getLogger(__name__)


class CadastralPrompts:
    """
    MCP Prompts for cadastral queries.

    Prompts are reusable, parameterized message templates that users
    can explicitly invoke (like slash commands) to standardize
    interactions with the AI.
    """

    def __init__(self, client: CadastralAPIClient) -> None:
        """Initialize prompts with a cadastral API client."""
        self.client = client

    async def _get_parcel(self, parcel_id: str) -> ParcelInfo:
        """The parcel record, read in a worker thread so the server stays responsive."""
        return await asyncio.to_thread(self.client.get_parcel_info, parcel_id)

    async def explain_ownership_structure(self, parcel_id: str) -> str:
        """
        Generate a prompt to explain parcel ownership structure.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt text with ownership data for AI analysis
        """
        try:
            logger.info(f"Generating ownership explanation prompt for parcel {parcel_id}")

            parcel = await self._get_parcel(parcel_id)

            prompt = f"""Analyze the ownership structure of parcel {parcel.parcel_number}:

**Basic Information:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.cad_municipality_name}
- Total Area: {parcel.area} m²
- Address: {parcel.address or 'N/A'}

**Ownership Records:**
"""

            if parcel.possession_sheets:
                for idx, sheet in enumerate(parcel.possession_sheets, 1):
                    prompt += f"\nPossession Sheet {idx}:\n"
                    if sheet.possessors:
                        for possessor in sheet.possessors:
                            ownership = possessor.ownership or "Not specified"
                            prompt += f"  - {possessor.name}\n"
                            prompt += f"    Ownership: {ownership}\n"
                            if possessor.address:
                                prompt += f"    Address: {possessor.address}\n"
                    else:
                        prompt += "  No possessors listed\n"
            else:
                prompt += "\nNo ownership records available for this parcel.\n"

            prompt += """
Please explain:
1. Who owns this parcel and what are their ownership percentages?
2. Are there multiple owners (co-ownership)?
3. Are there any unusual aspects of the ownership structure?
4. What does this ownership structure typically indicate?
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate ownership prompt for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e

    async def property_report(self, parcel_id: str) -> str:
        """
        Generate a comprehensive property report prompt.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for generating a detailed property report
        """
        try:
            logger.info(f"Generating property report prompt for parcel {parcel_id}")

            parcel = await self._get_parcel(parcel_id)

            prompt = f"""Generate a comprehensive property report for parcel {parcel.parcel_number}:

**Property Details:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.cad_municipality_name}
- Cadastral Office (institution id): {parcel.institution_id}
- Total Area: {parcel.area} m²
- Address: {parcel.address or 'N/A'}
- Building Rights: {'Yes' if parcel.has_building_right else 'No'}

**Land Use Classification:**
"""

            if parcel.parcel_parts:
                for part in parcel.parcel_parts:
                    prompt += f"  - {part.name}: {part.area} m²\n"
            else:
                prompt += "  No land use data available\n"

            prompt += "\n**Ownership:**\n"

            if parcel.possession_sheets:
                for sheet in parcel.possession_sheets:
                    if sheet.possessors:
                        for possessor in sheet.possessors:
                            ownership = possessor.ownership or "Not specified"
                            prompt += f"  - {possessor.name} ({ownership})\n"
            else:
                prompt += "  No ownership records available\n"

            prompt += """
Please create a detailed property report including:
1. Executive summary of the property
2. Land use breakdown and analysis
3. Ownership structure
4. Development potential (based on building rights)
5. Any notable features or restrictions
6. Market context (if relevant)
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate property report for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e

    async def compare_parcels(self, parcel_ids: list[str]) -> str:
        """
        Generate a prompt to compare multiple parcels.

        Args:
            parcel_ids: List of parcel identifiers to compare

        Returns:
            Formatted prompt with data for all parcels
        """
        try:
            logger.info(f"Generating comparison prompt for {len(parcel_ids)} parcels")

            if len(parcel_ids) < 2:
                raise ValueError("At least 2 parcels are required for comparison")

            prompt = "Compare the following parcels:\n\n"

            for idx, parcel_id in enumerate(parcel_ids, 1):
                try:
                    parcel = await self._get_parcel(parcel_id)

                    prompt += f"**Parcel {idx}: {parcel.parcel_number}**\n"
                    prompt += f"- Municipality: {parcel.cad_municipality_name}\n"
                    prompt += f"- Area: {parcel.area} m²\n"
                    prompt += f"- Building Rights: {'Yes' if parcel.has_building_right else 'No'}\n"

                    if parcel.parcel_parts:
                        prompt += "- Land Use: "
                        land_uses = [part.name for part in parcel.parcel_parts]
                        prompt += ", ".join(land_uses) + "\n"

                    if parcel.possession_sheets and parcel.possession_sheets[0].possessors:
                        owner_count = len(parcel.possession_sheets[0].possessors)
                        prompt += f"- Owners: {owner_count}\n"

                    prompt += "\n"

                except CadastralAPIError as e:
                    prompt += f"**Parcel {idx}: {parcel_id}** - Error: Could not retrieve data\n\n"
                    logger.error(f"Failed to fetch parcel {parcel_id}: {e}")

            prompt += """Please provide a comparative analysis including:
1. Size comparison and total area
2. Land use differences
3. Development potential comparison
4. Ownership structure differences
5. Which parcel might be more valuable/desirable and why?
6. Any other notable differences or similarities
"""

            return prompt

        except Exception as e:
            logger.error(f"Failed to generate comparison prompt: {e}", exc_info=True)
            raise ValueError(f"Could not generate comparison: {e}") from e

    async def land_use_summary(self, parcel_id: str) -> str:
        """
        Generate a prompt to analyze land use distribution.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for land use analysis
        """
        try:
            logger.info(f"Generating land use summary prompt for parcel {parcel_id}")

            parcel = await self._get_parcel(parcel_id)

            prompt = f"""Analyze the land use distribution for parcel {parcel.parcel_number}:

**Parcel Information:**
- Parcel Number: {parcel.parcel_number}
- Municipality: {parcel.cad_municipality_name}
- Total Area: {parcel.area} m²

**Land Use Breakdown:**
"""

            if parcel.parcel_parts:
                total_area = float(parcel.area) if parcel.area else 0

                for part in parcel.parcel_parts:
                    part_area = float(part.area) if part.area else 0
                    percentage = (part_area / total_area * 100) if total_area > 0 else 0

                    prompt += f"""
- **{part.name}**
  - Area: {part.area} m²
  - Percentage: {percentage:.1f}%
  - Type: {part.part_type or 'N/A'}
"""
            else:
                prompt += "\nNo land use classification data available.\n"

            prompt += """
Please provide:
1. Summary of the land use distribution
2. What does this distribution tell us about the property?
3. Is this a single-use or mixed-use parcel?
4. What are the typical uses or development potential for each land category?
5. Any recommendations or observations about the land use pattern?
"""

            return prompt

        except CadastralAPIError as e:
            logger.error(f"Failed to generate land use summary for {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel data for {parcel_id}.") from e


    def due_diligence_report(
        self, parcels: str, municipality: str, language: str = "hr", format: str = "markdown"
    ) -> str:
        """The report request: what to call and how to render it (no data is read here).

        The data is the JSON ``build_assembly`` returns; the prompt fixes the
        section order, the terms, the provenance rule and the notices, and
        leaves the format to the reader. Pure text, so it costs nothing to
        render and can be pasted into any client.
        """
        refs = [ref.strip() for ref in parcels.split(",") if ref.strip()]
        if not refs:
            raise ValueError("Give at least one parcel number or parcel_id.")
        language = language.lower().strip() or "hr"
        format = format.lower().strip() or "markdown"
        if language not in ("hr", "en"):
            raise ValueError('language must be "hr" or "en".')
        if format not in ("markdown", "html"):
            raise ValueError('format must be "markdown" or "html".')
        references = ", ".join(
            f'{{"parcel_id": {ref}}}' if ref.isdigit() else
            f'{{"parcel_number": "{ref}", "municipality": "{municipality}"}}'
            for ref in refs
        )
        prose = "Croatian" if language == "hr" else "English"
        rendering = (
            "Markdown: tables for the parcels, the persons and the blockers; one heading per "
            "section; readable as plain text in an email."
            if format == "markdown"
            else "HTML: one self-contained file with inline CSS and no external resources, "
            "printable to PDF; a coloured badge per verdict (clear green, conditional amber, "
            "blocked red); the map_url of each parcel as a link; tables sortable only if the "
            "script is inline."
        )
        return f"""Prepare a due-diligence screening report of {len(refs)} parcel(s) in cadastral \
municipality {municipality} for a reader who did not run the tool and will forward it to a \
lawyer. Write the prose in {prose}; keep Croatian register terms with the English gloss on \
first use (zemljišnoknjižni uložak / land-registry unit, vlastovnica / sheet B (owners), \
posjedovni list / possession sheet (cadastre), teretovnica / sheet C (encumbrances), plomba / \
pending request, zabilježba / note, založno pravo / mortgage, služnost / servitude, pravo \
prvokupa / pre-emption right, ostavina / estate, suvlasnički udio / co-ownership share).

Step 1. Call build_assembly with parcels=[{references}], include_plombe_detail=true, \
include_zoning=true, persons_limit=null. If the response is too large, call again with \
include_blockers=false and read the blockers with export="blockers_csv" in a second call.

Step 2. Render the JSON as a report in this order, and in nothing else:

1. Header: the municipality, the parcel count and total area (totals), when and from where the \
registers were read (each parcel's provenance: register, source_url, retrieved_at), and the \
references that failed (failed, with error_type), so the reader knows what is missing.
2. Verdict roll-up: parcels by verdict (totals.parcels_by_verdict), persons likely deceased and \
abroad (totals.persons_likely_deceased, totals.persons_address_abroad), public bodies present \
(totals.public_body_parcels), and the three sentences those numbers mean for an acquisition.
3. Parcels, easiest first (the order of parcels): number, area, land use, the unit \
(lr_unit_number / main_book_id), distinct owners and possessors, relationship between the \
registers, zoning status when read, area_mismatch, sale_verdict with blocker_counts, score. \
Under each parcel list its rows of blockers: kind, severity, what it applies to (scope, \
share_order_number, condominium_unit), the description, amount and beneficiary, the entry \
(order_number, entry_date, diary_number) or file_number and request_kind for a plomba, and \
likely_lapsed where set. Quote an other_annotation entry's description for the reader.
4. Persons by controlled area (persons): name as the register writes it, party_type_inferred, \
owner_of and possessor_of, owned / possessed / controlled area, likely_deceased and \
address_abroad, fuzzy_matches. Then surname_groups with person_count, parcel_count, \
controlled_area_m2, likely_deceased_count and address_abroad_count.
5. Closing: the screening rule verbatim (any parcel's blockers carry it as rule in \
sale_blockers; quote: a screening of the register's text, not a legal opinion), the inference \
notice (party types, likely_deceased, address_abroad and likely_estate are inferred; each \
carries its basis), the zoning dataset disclaimer when zoning was read, and the notes.

Rules: copy every number, name, share, date and reference from the JSON, never recompute or \
round them; do not add a fact the JSON does not hold, and say "not read" where a field is \
null; keep every person exactly as the registers spell them; state the register (cadastre or \
land registry) behind every fact; do not give legal advice or a recommendation to buy; where \
the tool could not answer (unknown kind of plomba, unrecognised note), say so and name what \
would settle it (the plomba detail, the entry text, a lokacijska informacija for buildability).

Format. {rendering}
"""

