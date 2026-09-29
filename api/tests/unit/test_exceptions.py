#!/usr/bin/env python3.12
"""Test the CadastralAPIError string representation."""

from cadastral_api.exceptions import CadastralAPIError, ErrorType

# Test 1: Error with details
print("Test 1: Error with details")
error1 = CadastralAPIError(
    error_type=ErrorType.INVALID_RESPONSE,
    details={"endpoint": "/test", "reason": "validation_failed"}
)
print(f"  str(error): '{str(error1)}'")
print()

# Test 2: Error with cause
print("Test 2: Error with cause")
try:
    raise ValueError("JSON parsing failed")
except ValueError as e:
    error2 = CadastralAPIError(
        error_type=ErrorType.INVALID_RESPONSE,
        details={"endpoint": "/test"},
        cause=e
    )
    print(f"  str(error): '{str(error2)}'")
print()

# Test 3: Simple error
print("Test 3: Simple error")
error3 = CadastralAPIError(error_type=ErrorType.PARCEL_NOT_FOUND)
print(f"  str(error): '{str(error3)}'")
