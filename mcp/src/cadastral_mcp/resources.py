"""MCP Resources - Read-only contextual data that AI can auto-fetch."""

import asyncio
import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError

logger = logging.getLogger(__name__)


class CadastralResources:
    """
    MCP Resources for cadastral data.

    Resources are read-only data entities that the AI can automatically
    fetch and include in context. They use URI-based access patterns.
    """

    def __init__(self, client: CadastralAPIClient) -> None:
        """Initialize resources with a cadastral API client."""
        self.client = client

    async def get_parcel_resource(self, parcel_id: str) -> dict[str, Any]:
        """
        Get full parcel details by parcel ID.

        Resource URI: cadastral://parcel/{parcel_id}

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Dictionary containing complete parcel information including ownership

        Raises:
            CadastralAPIError: If parcel cannot be fetched
        """
        try:
            logger.info(f"Fetching parcel resource: {parcel_id}")
            parcel = await asyncio.to_thread(self.client.get_parcel_info, parcel_id)
            return parcel.model_dump(mode="json")
        except CadastralAPIError as e:
            logger.error(f"Failed to fetch parcel {parcel_id}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve parcel {parcel_id}. Please verify the ID.") from e

    async def get_municipality_resource(self, code: str) -> dict[str, Any]:
        """
        Get municipality information by registration code.

        Resource URI: cadastral://municipality/{code}

        Args:
            code: Municipality registration number (e.g., "334979")

        Returns:
            Dictionary with municipality details (name, code, full name)

        Raises:
            CadastralAPIError: If municipality cannot be found
        """
        try:
            logger.info(f"Fetching municipality resource: {code}")
            # Search by code; the server also matches the code as a substring
            # of the name field, so pick the record whose code is exactly this.
            municipalities = await asyncio.to_thread(self.client.find_municipality, code)
            for muni in municipalities:
                if muni.municipality_reg_num == code:
                    return muni.model_dump(mode="json")

            raise ValueError(f"Municipality with code {code} not found")
        except CadastralAPIError as e:
            logger.error(f"Failed to fetch municipality {code}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve municipality {code}.") from e

    async def get_office_resource(self, code: str) -> dict[str, Any]:
        """
        Get cadastral office information by office code.

        Resource URI: cadastral://office/{code}

        Args:
            code: Cadastral office code

        Returns:
            Dictionary with office details

        Raises:
            CadastralAPIError: If office cannot be found
        """
        try:
            logger.info(f"Fetching cadastral office resource: {code}")
            offices = await asyncio.to_thread(self.client.list_cadastral_offices)

            # Find office by code
            for office in offices:
                if str(office.id) == str(code):
                    return office.model_dump(mode="json")

            raise ValueError(f"Cadastral office with code {code} not found")
        except CadastralAPIError as e:
            logger.error(f"Failed to fetch office {code}: {e}", exc_info=True)
            raise ValueError(f"Could not retrieve cadastral office {code}.") from e
