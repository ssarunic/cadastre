#!/usr/bin/env python3.12
"""Test Pydantic validation with actual API response."""


# Sample response from API (truncated possessors list for testing)
response_data = {
    "parcelId": 6566195,
    "parcelNumber": "1122/1",
    "cadMunicipalityId": 2387,
    "cadMunicipalityRegNum": "334979",
    "cadMunicipalityName": "SAVAR",
    "institutionId": 114,
    "address": "OVČJA",
    "area": "1618",
    "buildingRemark": 0,
    "detailSheetNumber": "7",
    "hasBuildingRight": False,
    "parcelParts": [
        {
            "parcelPartId": 64022942,
            "name": "VINOGRAD",
            "area": "809",
            "possessionSheetId": 11731543,
            "possessionSheetNumber": "363",
            "lastChangeLogFileNum": "Automatska OIB promjena",
            "lastChangeLogNumber": "7/2025",
            "building": False
        }
    ],
    "possessionSheets": [
        {
            "possessionSheetId": 11731543,
            "possessionSheetNumber": "363",
            "cadMunicipalityId": 2387,
            "cadMunicipalityRegNum": "334979",
            "cadMunicipalityName": "SAVAR",
            "possessionSheetTypeId": 1,
            "possessors": [
                {
                    "name": "KOLAR RAJKA Ž. BRANKA",
                    "ownership": "1/128"
                },
                {
                    "name": "BOŽULIĆ VINKO POK. ANTE",
                    "ownership": "9/600",
                    "address": "ZAGREB"
                }
            ]
        }
    ]
}

print("Testing Pydantic validation...")
print(f"Response data keys: {response_data.keys()}")
print(f"Parcel number: {response_data['parcelNumber']}")
print(f"Ownership sheets: {len(response_data['possessionSheets'])}")
print(f"Possessors: {len(response_data['possessionSheets'][0]['possessors'])}")

# Try to import and validate
try:
    from cadastral_api.models.entities import ParcelInfo

    parcel = ParcelInfo.model_validate(response_data)
    print("\n✓ Validation successful!")
    print(f"  Parcel: {parcel.parcel_number}")
    print(f"  Area: {parcel.area_numeric} m²")
    print(f"  Owners: {parcel.total_possessors}")
except Exception as e:
    print(f"\n✗ Validation failed: {type(e).__name__}")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
