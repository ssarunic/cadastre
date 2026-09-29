# Response Cache Specification

A cache of upstream API responses inside the SDK client, so that a record read once is
served from memory (or disk, or a shared cache service) for the rest of its lifetime
instead of being fetched again. Four layers, selected by configuration, behind one
interface: in-process memory, memory plus disk, a separate cache process, and a
distributed cache.

Status: Phase 1 implemented (the cache package with the memory layer, the
client hook, `refresh`, `fetched_at`, the `info` line); section 11 and phases
2 to 4 are open.

## Scope Notice

This project is an educational demonstration. Every example, test and acceptance
criterion in this specification runs against the mock server at `http://localhost:8000`.
The cache stores whatever the configured upstream returns; using it against another
server is subject to the rights check in `docs/legal.md`.

## 1. Motivation

Two things cost the MCP server today, both because it keeps nothing between calls
except GIS files:

- **Paging refetches the whole record.** `get_lr_unit` pages sheet B with `offset` and
  `limit`, and filters it with `owner_name` and `condominium_unit`. Every page and every
  filter is a new `/lr/lr-unit` request. For a large condominium the upstream takes
  20 to 25 s to assemble the unit (see the `long_timeout` note in `CLAUDE.md`), so a
  five-page walk through one unit is five slow fetches and five upstream hits for data
  that did not change in between.
- **Every caller pays upstream latency for reference data.** Offices, municipalities
  and main books change rarely, yet `resolve_municipality` fetches the municipality
  list on every call that needs a code.

The client-side response-size ceiling (1 MB per tool result in Claude Desktop and
claude.ai, about 25,000 tokens in Claude Code) is a separate problem, solved by paging
and by the size guards in `mcp/src/cadastral_mcp/tools.py`. A cache does not change the
ceiling; it makes paging cheap enough to be the normal way to read a large record. The
companion change that closes the remaining ceiling gaps is in section 11.

## 2. Goals and Non-Goals

### Goals

- One cache interface in the SDK client, used by the CLI, the stdio MCP server and the
  gateway alike, with the backend chosen by configuration.
- Layer 1 (memory, in-process) is the default and needs no setup and no service.
- Layers 2 to 4 are backends behind the same interface; switching them never touches
  the client, the tools or the commands.
- Short lifetimes for anything that contains personal data, as a policy independent of
  the backend.
- Cache hits bypass the upstream rate limiter: the upstream sees strictly fewer requests
  than without the cache, never more.
- Purging is one command, and the current state is visible in `cadastral info`.
- A model or schema change never breaks on a cached entry: the worst a stale or
  unreadable entry can cost is one refetch.

### Non-Goals

- Caching GML files and parsed geometry. `GISCache` already does that, keyed by
  municipality, with its own commands; this specification leaves it untouched.
- Caching HTTP errors or empty results (negative caching). Section 14.
- A copy of the register. Nothing is kept longer than the lifetime in section 5, and
  the disk and service layers are opt-in.
- Cache invalidation on upstream change. The upstream sends `Cache-Control: no-store`
  and no validators, so a lifetime is the only signal available.

## 3. Design Decisions

### 3.1 Cache at the request layer of the SDK, not in the MCP tools

`CadastralAPIClient._request` is the one place every upstream call passes through. A
cache there serves every consumer and every method with one hook, and it stores what the
upstream sent (JSON), which every backend can hold as bytes. Caching parsed Pydantic
models in the MCP tools would help only the MCP server, would need one cache per model
type, and would put unpicklable objects in front of the disk and service layers.

Parsing a cached body again costs milliseconds (a 2.9 MB unit parses in 0.2 s); the
upstream fetch it replaces costs seconds.

### 3.2 Bytes in, bytes out

Every backend stores the compact UTF-8 JSON of the response body and returns those
bytes; the client decodes them on every hit. This keeps the memory layer identical in
behaviour to the other layers (no caller can mutate a shared object) and lets the
memory budget be measured in bytes.

### 3.3 Lifetimes by data class, fixed in code

The lifetime of an entry follows the data class of its endpoint (section 5), not the
backend and not the caller. Classes that carry personal data have short lifetimes as a
policy; the lifetimes are constants in the SDK, and configuration can turn the cache off
or shorten it but never lengthen the personal-data classes beyond 30 min.

### 3.4 One interface, composable backends

`ResponseCache` is a protocol with five operations. The layers are backends that
implement it, and a `TieredCache` composes two of them (a memory front, a disk or
service back). Nothing else in the code base knows which backend is active.

### 3.5 Redis or Valkey for the service layer, not memcached

memcached rejects values over 1 MB by default and has no persistence; the records worth
caching most (large units, 2 to 3 MB) are exactly the ones it would refuse. Redis, or
its open-source fork Valkey, stores values of that size, expires keys itself and
persists optionally. The `redis` client library speaks to both.

### 3.6 Existing libraries for the storage, own code for the policy

| Layer | Library | Why |
|---|---|---|
| Memory | `cachetools` (`TLRUCache`) | Bounded LRU with a lifetime per entry, pure Python, no dependencies |
| Disk | `diskcache` | SQLite-backed, per-key TTL, size limit with eviction, safe across threads and across processes on one machine |
| Service | `redis` | Client for Redis and Valkey; `SET ... EX` gives per-key TTL |

The policy (keys, data classes, lifetimes, the personal-data rule, the tiering) is this
project's code and is tested independently of the libraries.

## 4. Interface

```python
class ResponseCache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ttl: float) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...
    def stats(self) -> CacheStats: ...   # backend name, entries, bytes, hits, misses
```

Backends: `NullCache` (cache off), `MemoryCache`, `DiskCache`, `RedisCache`,
`TieredCache(front, back)`.

`TieredCache.get` reads the front, then the back, and on a back hit fills the front with
the remaining lifetime. `set` writes both. `clear` clears both; `delete` deletes from
both. The front is always a `MemoryCache`.

### 4.1 Keys

The key is the SHA-256 hex digest of the canonical request:

```text
<base_url>|<method>|<endpoint>|<sorted query params as k=v&k=v>|<json body, sorted keys>
```

The base URL is part of the key so that the mock server and any other configured
server never share an entry. The digest keeps keys short and free of characters that a
backend might reject.

### 4.2 Client hook

`_request` gains a keyword `use_cache: bool = True`:

1. Compute the key and look up the data class of the endpoint (section 5). An endpoint
   with no data class is not cached.
2. On a hit, decode the bytes and return; the rate limiter is not consulted.
3. On a miss, run the existing rate-limited request. On success (a JSON body the client
   accepted) store the compact encoding with the class lifetime. Errors of every kind
   are not stored.

The public whole-record methods (`get_lr_unit_detailed`, `get_lr_unit_from_parcel`,
`get_parcel_info`, `get_possession_sheet*`) gain `refresh: bool = False`, which passes
`use_cache=False` down and overwrites the entry with the fresh response. On a composed
method (`get_lr_unit_from_parcel`, `get_possession_sheet_parcels`) it reaches the hops
that return personal data (the parcel record, the unit, the sheet); the municipality,
parcel-number and main-book lookups underneath may still be served from the cache,
since a caller asking for a fresh copy is asking about the people on the record.

### 4.3 In-flight requests

A miss holds a per-key lock for the duration of the upstream request, so that two
threads asking for the same large unit at the same time make one fetch, not two. The
locks live in the client (not the backend) and are dropped when the request completes.
This matters in the MCP server, whose tools run in worker threads, and in the gateway.

### 4.4 Constructor and configuration

`CadastralAPIClient(cache=...)` accepts a `ResponseCache` instance, a configuration
string, or `None` for the value of `CADASTRAL_CACHE`.

| Variable | Values | Default |
|---|---|---|
| `CADASTRAL_CACHE` | `memory`, `disk`, `redis://host:port/db`, `off` | `memory` |
| `CADASTRAL_CACHE_DIR` | Directory (already used by `GISCache`) | `~/.cadastral_api_cache` |
| `CADASTRAL_CACHE_MEMORY_MB` | Byte budget of the memory layer | `64` |
| `CADASTRAL_CACHE_DISK_MB` | Size limit of the disk layer | `512` |

`disk` means `TieredCache(MemoryCache, DiskCache)` under `<CADASTRAL_CACHE_DIR>/responses/`;
`redis://...` means `TieredCache(MemoryCache, RedisCache)`. The memory front of a tiered
cache keeps an entry until the same lifetime as the back, so the two never disagree
about expiry.

### 4.5 Schema and version changes

The cache holds the upstream's JSON, not parsed models, so a change to a Pydantic model
is invisible to it: the cached body is parsed by whatever model the running code has,
exactly as a fresh response would be. What can still go wrong, and the rule for each:

- **The entry format changes** (the envelope of section 4.6, the key derivation, the
  compact encoding). The key prefix carries a format version (`cadastral:v1:`); an
  incompatible change bumps it, so entries written by an older SDK are never read and
  the disk and service layers sweep them by expiry (`clear` removes every version).
- **The model rejects a cached body.** The new code may reject a body an older version
  stored (a stricter validator, a field the upstream has since renamed, an entry
  written by a buggy version). A validation failure on a cache hit is treated as a
  miss: the entry is deleted, the record is fetched again, and only a failure on the
  fresh response is raised. A cache hit never raises where a miss would not have.
- **The request changes.** A method that starts sending a new parameter produces a new
  key by construction (section 4.1); old entries expire unread.
- **The backend library changes its on-disk format.** `DiskCache` opens the directory
  under a version subfolder (`responses/v1/`) so that a `diskcache` upgrade that
  cannot read the old files is a fresh start, not an error; a failure to open the
  backend at start falls back to `MemoryCache` with a logged warning.

Cached entries are always optional: any backend failure on `get` (corrupt entry,
unreachable service, permission error) is logged once and treated as a miss, and a
failure on `set` is logged and ignored. The client is never worse off with the cache
than without it.

### 4.6 Envelope

Each entry is the compact JSON of the body, preceded by a fixed-size header line:

```text
{"v":1,"fetched_at":"2026-09-16T12:33:25Z","endpoint":"/lr/lr-unit","class":"lr_unit"}\n<body>
```

The header gives `fetched_at` to the surfaces of section 8, the class for `stats()`
and for sweeps by class, and the format version for section 4.5. An entry whose
header does not parse or whose `v` is unknown is a miss and is deleted.

## 5. Data Classes and Lifetimes

| Data class | Endpoints | Lifetime | Personal data |
|---|---|---|---|
| Reference lists | `/search-cad-parcels/offices`, `/search-cad-parcels/municipalities`, `/search-lr-parcels/main-books`, `/search-lr-parcels/books-of-dc` | 24 h | No |
| Search (number to id) | `/search-cad-parcels/parcel-numbers`, `/cad/cad-parcels-search-data`, `/search-cad-parcels/possession-sheet-numbers` | 6 h | No |
| Parcel detail | `/cad/parcel-info` | 30 min | Yes |
| Possession sheet | `/cad/possession-sheet`, `/cad/possession-sheet-by-number`, `/cad/search-parcels` (whole parcel records with their possessors and, when harmonized, owners) | 30 min | Yes |
| Land-registry unit | `/lr/lr-unit` | 30 min | Yes |
| File status | `/lr/file-status` (POST) | 5 min | No, but changes often |
| Building areas (WFS) | planning WFS requests | 24 h | No |
| Result artifact | stored tool results (section 12) | 30 min with personal data, else 24 h | Depends on the result |

These are the lifetimes in the gateway specification's caching section, which this
document now owns; that section refers here. The 30 min on the personal-data classes
is the policy from section 3.3. The WFS class is included so that the planning client
uses the same cache once it is routed through the same hook; it is phase 2.

## 6. Layers

### 6.1 Layer 1: memory, in-process (default)

`MemoryCache` wraps one `cachetools.TLRUCache` with `getsizeof=len` and a byte budget,
behind a `threading.Lock`. `TLRUCache` expires each entry at its own time, so the
lifetime passed to `set` becomes that entry's expiry and every class shares the one
budget, least recently used out first. A response larger than the whole budget is not
stored. Entries die with the process. This layer alone makes every page after the first of a large unit free and
removes the municipality-list fetch from every parcel lookup within a session.

### 6.2 Layer 2: memory plus disk, in-process

`DiskCache` wraps `diskcache.Cache(directory, size_limit=...)`, which stores values in
SQLite and files, expires per key, evicts by size and is safe for several threads and
several processes on one machine. `TieredCache(MemoryCache, DiskCache)` puts the memory
layer in front.

Opt-in (`CADASTRAL_CACHE=disk`), because it writes personal data to disk. The directory
is created with mode `0700` and lives next to the GIS cache so that one setting names
both. Because `diskcache` is process-safe, a CLI run and a running MCP server on the
same machine share the entries.

### 6.3 Layer 3: a separate cache process

`RedisCache` wraps a `redis.Redis` client; `set` uses `SET key value EX ttl`, `clear`
deletes the keys under the configured prefix (`cadastral:` by default) and nothing else
in the instance. `TieredCache(MemoryCache, RedisCache)` puts the memory layer in front.

This layer earns its keep only where several processes on different hosts, or the
hosted gateway's workers, must share entries and a single upstream budget. It is a
dependency of the gateway (`specs/gateway-service.md`), not of the CLI or the stdio
MCP server, and it is an optional extra of the SDK package.

### 6.4 Layer 4: distributed

A Redis or Valkey cluster behind the same `RedisCache`, configured by URL. No code
change; recorded here so the interface is not designed without it. Not planned.

## 7. Personal Data

Parcel detail, possession sheets and land-registry units name people. The rules, in
force at every layer:

- Lifetime at most 30 min (section 5); configuration may shorten it, not lengthen it.
- Memory only by default. Disk and service layers are explicit choices of the operator,
  who is responsible for the storage (`docs/legal.md`).
- `cadastral cache clear --responses` purges every entry of the configured backend;
  `--all` now purges responses as well as GIS data.
- Nothing from a response cache is ever committed: `<cache_dir>/responses/` joins the
  ignore list, and `scripts/redact_capture.py` does not read from it.

## 8. Surfaces

### 8.1 SDK

The constructor parameter, the environment variables (section 4.4), `refresh=` on the
whole-record methods, `client.cache.stats()` and `client.cache.clear()`.
`docs/sdk-guide.md` gains a "Caching" section under Configuration.

### 8.2 CLI

- `cadastral info` prints the cache backend, the number of entries, the bytes held and
  the hit ratio of the process (`Cache: memory, 12 entries, 3.1 MB`).
- `cadastral cache clear --responses` and `cadastral cache clear --all`. `cache list`
  stays about GIS data.
- No per-command `--refresh` in phase 1; a CLI process is short-lived, so its memory
  cache is empty at start. `--refresh` on `get-parcel` and `get-lr-unit` comes with the
  disk layer (phase 2), when a stale entry can outlive the process.

Croatian names for the new option and output keys go in `localized.py` and
`output_keys.py` with translations in `po/hr.po`, and the command pages under
`docs/en/cli/commands/` are updated in the same commit (`specs/documentation-guide.md`).

### 8.3 MCP server

The server passes `config.cache` through to the client; `CADASTRAL_CACHE` is read by
the SDK, so Claude Desktop's `env` block configures it. `get_lr_unit` and `get_parcel`
gain `refresh: bool = False`, documented as "read the record again from the server
even if a copy from the last 30 minutes exists". The response `dataset` or `page` block
of a unit or parcel gains `fetched_at` (ISO 8601) so the agent can say how old the
record is.

### 8.4 Gateway

The gateway's cache is this interface with `redis://` (or `disk` for a single host).
Its caching section is reduced to a reference here plus the REST header mapping
(`Cache-Control: max-age` from the class lifetime, `X-Cache: HIT|MISS` from the
lookup).

## 9. Repository Changes

```text
api/src/cadastral_api/cache/
├── __init__.py          # ResponseCache protocol, CacheStats, from_config()
├── policy.py            # data classes, lifetimes, endpoint -> class, key()
├── memory.py            # MemoryCache
├── disk.py              # DiskCache (import guarded; extra "disk")
├── redis.py             # RedisCache (import guarded; extra "redis")
└── tiered.py            # TieredCache, NullCache
api/src/cadastral_api/client/api_client.py   # hook in _request, refresh=, in-flight locks
api/pyproject.toml                            # cachetools required; extras disk, redis
cli/src/cadastral_cli/commands/cache.py       # clear --responses / --all
cli/src/cadastral_cli/commands/discovery.py   # info: cache line
mcp/src/cadastral_mcp/config.py               # cache setting passthrough
mcp/src/cadastral_mcp/tools.py                # refresh=, fetched_at
docs/sdk-guide.md, docs/en/cli/commands/*.md, docs/mcp-usage-guide.md, .env.example
specs/gateway-service.md                      # section 8 refers here
CHANGELOG.md
```

## 10. Testing

- **Backend contract tests**, one parametrised suite run against every backend: set
  then get, expiry with a fake clock, `delete`, `clear`, byte budget eviction, and that
  `get` returns equal bytes but never the same object. The Redis case runs only when
  `CADASTRAL_TEST_REDIS_URL` is set and is skipped otherwise.
- **Policy tests**: every endpoint in `api_client.py` maps to a class or is listed as
  uncached; personal-data classes never exceed 30 min whatever the configuration; the
  key differs when only the base URL differs; a body is part of the key for POST.
- **Client tests** with an `httpx` mock transport: the second identical call makes no
  request; an error response is not stored; `refresh=True` requests and overwrites; a
  hit does not wait for the rate limiter; two threads requesting one key make one
  request.
- **Schema-change tests**: an entry stored with an older format version is a miss; a
  cached body the current model rejects is deleted and refetched, and the fresh
  response's failure is the one raised; a corrupt entry and an unreachable backend
  degrade to a miss without raising; a `set` failure is ignored.
- **Mock-server integration**: `get_lr_unit` paged five times makes one `/lr/lr-unit`
  request (counted in the mock server's request log).
- **CLI gates** that already exist (`test_localized_cli.py`, `test_output_keys.py`,
  `test_docs_coverage.py`, `test_i18n_coverage.py`) cover the new option and keys.

## 11. Companion Change: Response-Size Ceilings

Not part of the cache, but the same investigation found it and the cache makes the
remedy (paging) cheap, so phase 1 ships both.

### 11.1 What the client receives

The MCP SDK sends every dict-returning tool result twice: as pretty-printed text in
`content` and as `structuredContent`. Measured against the mock server, the wire payload
is about 2.5 times the compact JSON that the size guards in `tools.py` measure. The
structured copy is the typed output the MCP specification is moving towards, and a
client that consumes results programmatically uses it; the clients targeted today
(Claude Desktop, claude.ai, Claude Code) hand the text to the model and ignore it.

Both copies stay on by default. `MCP_STRUCTURED_OUTPUT=off` registers the tools with
`structured_output=False` for an operator who needs the payload halved on a client
that reads only the text; the default is `on` so that a client which does read typed
output is served without reconfiguration. The wire budget below accounts for whichever
is configured.

### 11.2 A wire budget instead of fixed caps

The guards today measure compact characters against fixed ceilings (50,000 for a unit,
100,000 for a parcel) and refuse with a suggested smaller `limit`. Three tools have no
guard: `list_municipalities` with `limit=None` (about 3,300 records, about 1.3 MB on the
wire), `find_parcels_in_area` and `find_parcel_neighbours` with `limit=None` or
`include_geojson` on a large municipality, and `get_parcel_zoning` with
`include_geometry=True` (whole settlement polygons).

Rather than adding fixed caps to those three, every paged tool moves to one rule:

- A **wire budget** per result, `MCP_RESULT_BUDGET_BYTES`, default 800,000, applied to the
  serialised `CallToolResult` as it will be sent (text plus structured copy when the
  latter is on), not to the compact dict.
- `limit=None` means **as many as fit**: the tool serialises the window, and when it is
  over budget it shrinks the window to the largest prefix that fits (records are near
  uniform, so one proportional cut and at most one retry suffice) and sets
  `page.truncated` and `page.next_offset` as it does for an explicit limit. No refusal,
  no guessing a limit.
- An explicit `limit` that does not fit is cut the same way; the `page` block states
  the limit actually applied, so the agent sees that its request was reduced.
- A **single record** that does not fit on its own (one parcel entry with hundreds of
  possessors, a full unit dump, a zoning answer with polygons) is the only case that is
  still refused, with the existing message naming the smaller views, and in phase 2
  with the result artifact of section 12 instead.

The existing character ceilings become one function that measures the wire size, so
that the guarded tools and the three unguarded ones behave alike.

## 12. Result Artifacts

Some results are larger than any page: a whole unit for a spreadsheet, a k.o.-wide
parcel list with geometry, a due-diligence report. The cache gives them a home: a tool
stores the full result under an id, returns a summary with that id, and the caller
reads the rest in increments or hands the whole thing to a person.

A result artifact is a cache entry of data class `result` (lifetime 30 min when it
contains personal data, 24 h otherwise) with a random 128-bit id. It is read three ways,
by transport rather than by copying the data:

| Path | Where | Increment |
|---|---|---|
| `read_result(id, offset, limit)` tool | stdio and remote MCP | Records of a list result, or bytes of a document, within the wire budget |
| `cadastral://result/{id}` resource | MCP clients that read resources | The same, through the resource read API |
| `GET /v1/results/{id}` | Gateway | HTTP range requests, or `?offset=&limit=` for list results; content negotiation for JSON, CSV, XLSX |

The gateway URL is the useful one for people: the tool result carries a link the user
opens, and the agent never has to carry a spreadsheet through its context. The URL is
signed and expires with the entry, it is never listable, and the entry holds the same
personal data under the same lifetime as any cached response; the operator of the
gateway is the operator of that storage (section 7). The stdio server has no URL to
give: its artifacts are reachable through the tool and the resource only, which is why
the tool path exists at all. Whether Claude Desktop lets the model read a resource on
its own is an open question (section 14); the tool path works on every client.

Phase 2 delivers the tool and the resource for the results that section 11.2 still
refuses; the gateway path comes with the gateway.

## 13. Phases

| Phase | Delivers | Depends on |
|---|---|---|
| 1 | `cache` package with `NullCache`, `MemoryCache`, `TieredCache`; client hook, keys, envelope, lifetimes, in-flight locks, the section 4.5 rules; `CADASTRAL_CACHE=memory|off`; `info` line; MCP `refresh` and `fetched_at`; the wire budget and the structured-output flag of section 11 | nothing |
| 2 | `DiskCache`, `CADASTRAL_CACHE=disk`, `cache clear --responses`, CLI `--refresh`, planning WFS class; result artifacts through `read_result` and the resource | phase 1 |
| 3 | `RedisCache`, `redis://` URLs, prefix-scoped clear, gateway wiring, `GET /v1/results/{id}` with signed expiring URLs | phase 2, gateway phase 1 |
| 4 | Cluster URL documented and tested once, if ever needed | phase 3 |

## 14. Open Questions

- **Negative caching.** A parcel number that does not exist is asked for repeatedly by
  an agent trying spellings. Caching the 404 for a few minutes would help; caching a
  transient upstream error would hurt. Decide after phase 1 with the hit statistics.
- **Lifetime of file status.** Five minutes is a guess; plombe resolve over days, but an
  agent checks status right after reading a unit and again a minute later.
- **`fetched_at` on every tool** or only the whole-record ones. Every cached response
  has it; whether the agent needs it on a municipality list is doubtful.
- **Memory budget default.** 64 MB holds about twenty of the largest units. Whether the
  Desktop MCP process should hold more is a question of the machine, not the data.
- **Resources in Claude Desktop.** Claude Code reads MCP resources from the model's side;
  whether Claude Desktop lets the model do so, rather than the user attaching one, is
  unverified. Until it is, `read_result` is the path documented for artifacts.
- **Default wire budget.** 800,000 bytes leaves room under the 1 MB ceiling of Desktop
  and claude.ai; Claude Code's default ceiling is about 25,000 tokens, so an operator on
  Claude Code sets the budget lower or raises `MAX_MCP_OUTPUT_TOKENS`.
