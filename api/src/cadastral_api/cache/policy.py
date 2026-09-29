"""Cache policy: data classes, lifetimes, keys and the entry envelope.

Everything here is this project's own rule set, independent of the backend
that stores the bytes (``specs/response-cache-specification.md``, sections
3.3, 4.1, 4.6 and 5). The backends know keys, bytes and a lifetime; only
this module knows which endpoint holds what and for how long.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

#: Bumped on an incompatible change to the envelope, the key derivation or
#: the body encoding; entries written under another version are never read.
FORMAT_VERSION = 1
KEY_PREFIX = f"cadastral:v{FORMAT_VERSION}:"

#: The longest any class that names people may be cached, whatever the
#: configuration says (section 3.3).
MAX_PERSONAL_DATA_LIFETIME = 30 * 60


@dataclass(frozen=True)
class ClassPolicy:
    """What one data class is cached for, and whether it names people."""

    name: str
    lifetime: float
    personal_data: bool


#: The data classes of section 5. The WFS and result-artifact classes come
#: with later phases and are absent on purpose.
CLASSES: dict[str, ClassPolicy] = {
    policy.name: policy
    for policy in (
        ClassPolicy("reference", 24 * 3600, personal_data=False),
        ClassPolicy("search", 6 * 3600, personal_data=False),
        ClassPolicy("parcel_detail", 30 * 60, personal_data=True),
        ClassPolicy("possession_sheet", 30 * 60, personal_data=True),
        ClassPolicy("lr_unit", 30 * 60, personal_data=True),
        ClassPolicy("file_status", 5 * 60, personal_data=False),
    )
}

#: Endpoint path -> data class name. An endpoint absent here is not cached.
ENDPOINT_CLASS: dict[str, str] = {
    "/search-cad-parcels/offices": "reference",
    "/search-cad-parcels/municipalities": "reference",
    "/search-lr-parcels/main-books": "reference",
    "/search-lr-parcels/books-of-dc": "reference",
    "/search-cad-parcels/parcel-numbers": "search",
    "/cad/cad-parcels-search-data": "search",
    "/search-cad-parcels/possession-sheet-numbers": "search",
    "/cad/parcel-info": "parcel_detail",
    "/cad/possession-sheet": "possession_sheet",
    "/cad/possession-sheet-by-number": "possession_sheet",
    # A parcel search answers with whole parcel records, possessors and
    # (for a harmonized parcel) owners included: people, not numbers.
    "/cad/search-parcels": "possession_sheet",
    "/lr/lr-unit": "lr_unit",
    "/lr/file-status": "file_status",
}


def data_class_of(endpoint: str) -> ClassPolicy | None:
    """The policy of an endpoint, or None when the endpoint is not cached."""
    name = ENDPOINT_CLASS.get(endpoint)
    return CLASSES[name] if name is not None else None


def cache_key(
    base_url: str,
    method: str,
    endpoint: str,
    params: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> str:
    """The key of a request: a versioned prefix and the SHA-256 of its canonical form.

    The base URL is part of it so that two servers never share an entry;
    the params are sorted and the body is serialised with sorted keys so
    that argument order never makes a second entry.
    """
    query = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    body = (
        json.dumps(json_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if json_body is not None
        else ""
    )
    canonical = f"{base_url.rstrip('/')}|{method.upper()}|{endpoint}|{query}|{body}"
    return KEY_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Envelope:
    """A decoded entry: the body the upstream sent and when, from where."""

    body: Any
    fetched_at: str
    endpoint: str
    data_class: str

    def age_seconds(self, now: datetime | None = None) -> float:
        """Seconds since the body was fetched (never negative)."""
        now = now or datetime.now(timezone.utc)
        fetched = datetime.fromisoformat(self.fetched_at.replace("Z", "+00:00"))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        return max(0.0, (now - fetched).total_seconds())

    def remaining_lifetime(self, now: datetime | None = None) -> float:
        """Seconds until the class lifetime runs out (zero when the class is unknown)."""
        policy = CLASSES.get(self.data_class)
        if policy is None:
            return 0.0
        return max(0.0, policy.lifetime - self.age_seconds(now))


def encode(body: Any, *, fetched_at: str, endpoint: str, data_class: str) -> bytes:
    """The bytes of an entry: one JSON header line, then the compact body."""
    header = {
        "v": FORMAT_VERSION,
        "fetched_at": fetched_at,
        "endpoint": endpoint,
        "class": data_class,
    }
    return (
        json.dumps(header, separators=(",", ":")).encode("utf-8")
        + b"\n"
        + json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


def decode(raw: bytes) -> Envelope | None:
    """The entry the bytes hold, or None when they are unreadable or of another version.

    Never raises: an entry that cannot be decoded is a miss (section 4.6).
    """
    try:
        header_line, body_bytes = raw.split(b"\n", 1)
        header = json.loads(header_line)
        if not isinstance(header, dict) or header.get("v") != FORMAT_VERSION:
            return None
        return Envelope(
            body=json.loads(body_bytes),
            fetched_at=str(header["fetched_at"]),
            endpoint=str(header["endpoint"]),
            data_class=str(header["class"]),
        )
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
