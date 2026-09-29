# Gateway Service Specification

Hosted web service exposing the cadastral SDK as a REST API and as a remote MCP server,
so that no local installation is needed and the tools are reachable from claude.ai on
web and mobile.

Status: Draft, not yet implemented.

## Scope Notice

This project is an educational demonstration. The gateway's upstream URL is configuration
and defaults to the mock server at `http://localhost:8000`. Nothing in this specification
depends on, or is to be used against, Croatian government production systems. All examples,
tests, and acceptance criteria run against the mock server.

## 1. Goals and Non-Goals

### Goals

- Expose the existing SDK use-cases over HTTP as a resource-oriented REST API.
- Expose the same use-cases as a remote MCP server reachable from claude.ai (web and
  mobile) without any local process.
- Share one cache and one upstream rate limiter across all callers, so the upstream sees
  strictly less traffic than the sum of the clients would generate.
- Be deployable and operable by one person: one container, one volume, one config file.
- Keep the existing CLI and the existing stdio MCP server working unchanged.

### Non-Goals

- Horizontal scaling. The service runs as exactly one replica. See section 10 for the
  triggers that would change this.
- A raw passthrough proxy of upstream endpoints. The gateway hides the upstream's
  municipality, parcel search, and detail workflow behind stable resources.
- Long-term storage of ownership data. The gateway caches for minutes, not days.
- A web UI. Out of scope for this spec; the REST API is designed so a UI could be added.

## 2. Design Decisions

Recorded here so they are not re-litigated.

### 2.1 One process for REST and MCP

The upstream requires a minimum interval between requests. Every caller must therefore
share one rate limiter and one cache. Two separate deployments would need to coordinate
that state through an external store. One ASGI application hosting both `/v1/*` and `/mcp`
avoids that entirely. A `--mode rest|mcp|all` flag keeps the option of splitting later.

### 2.2 No Redis, no S3, no Postgres

Each of these solves a problem the service does not have.

| Component | What it would solve | Why it is not needed |
|---|---|---|
| Redis | Cache and rate limiter shared across replicas | One replica. An in-process limiter and a SQLite cache table are sufficient. |
| S3 or object storage | GML files shared across replicas or hosts | One host. The existing `GISCache` already writes to a local directory. Mount a volume. |
| Postgres | Concurrent writers, large datasets | Tens of users at most, kilobytes per row. SQLite in WAL mode handles this trivially. |
| Message queue and workers | Batch jobs surviving process restarts across a fleet | Batch jobs run in a background thread inside the single process, with state in SQLite. |

Total state of the service: one SQLite file and one directory of GML files, both on one
mounted volume. Backup is a file copy.

### 2.3 Keep the SDK synchronous for v1

The current client in `api/src/cadastral_api/client/api_client.py` is synchronous httpx
with `time.sleep` throttling. Rewriting it as async is real work with little payoff at this
scale. Instead, the gateway runs SDK calls in a worker thread (FastAPI does this for plain
`def` endpoints; use `anyio.to_thread.run_sync` elsewhere). An async client can be added
later without changing the REST or MCP surface.

Consequence: the upstream rate limiter must be thread-safe. It is, since the MCP
server's HTTP transport: `cadastral_api.rate_limiter.RateLimiter` hands concurrent
callers consecutive slots one interval apart. See section 6 for what the gateway adds.

### 2.4 Resource-oriented REST, not passthrough

The upstream's three-step lookup (municipality code, then parcel id, then detail) is an
implementation detail. Clients address parcels and land registry units directly. A
`/v1/raw/*` passthrough is deliberately not offered; it would leak upstream shape into
client code and bypass the cache policy.

## 3. Architecture

```text
 Clients                                  Gateway (single container)
 ───────                                  ──────────────────────────
 CLI ─────── upstream directly, or ──┐
             --backend gateway       │
 Claude Desktop ── stdio (unchanged) │  (local, not via gateway)
 claude.ai web / mobile ── MCP ──────┤
 scripts ─────────── REST ───────────┤
                                     ▼
                     TLS edge (Caddy or Cloudflare Tunnel)
                                     │
                                     ▼
                     FastAPI app
                       ├─ /v1/*            REST routers
                       ├─ /mcp             MCP streamable HTTP (mounted MCPServer app)
                       ├─ /healthz
                       │
                       ▼
                     cadastral_service     use-cases, auth, cache policy, audit
                       ├─ cache table ─────────────► SQLite   (one file on volume)
                       ├─ users, api_keys, audit, jobs ► SQLite
                       ├─ upstream limiter ────────► in-process lock
                       ├─ GML files ───────────────► directory on volume
                       ▼
                     CadastralAPIClient (existing sync SDK, one shared instance)
                       ▼
                     upstream (mock server by default)
```

### 3.1 Layers

- **SDK** (`api/`): models, parsing, HTTP to upstream. Unchanged in shape. Gains a
  thread-safe rate limiter.
- **Service layer** (new package `cadastral_service`): one function per use-case. Each
  function checks the cache, calls the SDK under the upstream limiter, stores the result,
  and writes an audit row. This is the only layer that knows about caching or auditing.
- **REST adapter**: FastAPI routers translating HTTP to service calls. No business logic.
- **MCP adapter**: tool, resource, and prompt registrations translating MCP calls to
  service calls. The same registrations are used by the local stdio server and the remote
  endpoint.

### 3.2 Use-cases

| Use-case | Existing SDK method |
|---|---|
| `list_offices()` | `list_cadastral_offices` |
| `find_municipality(query)` | `find_municipality` |
| `find_parcel(municipality, number)` | `find_parcel` |
| `get_parcel(parcel_id)` | `get_parcel_info` |
| `get_parcel_geometry(municipality, number)` | `get_parcel_geometry` |
| `get_lr_unit(main_book_id, unit_number, include_plombe)` | `get_lr_unit_detailed`, `get_plombe_details` |
| `get_lr_unit_from_parcel(municipality, number)` | `get_lr_unit_from_parcel` |
| `submit_batch(kind, items)` and `get_job(job_id)` | wraps the above in a background job |

## 4. REST API

Base path `/v1`. JSON only. All routes require authentication (section 7) except
`/healthz`.

```text
GET  /v1/offices
GET  /v1/municipalities?q={name_or_code}
GET  /v1/municipalities/{code}
GET  /v1/municipalities/{code}/parcels?number={parcel_number}
GET  /v1/parcels/{parcel_id}?include=owners,lr_unit
GET  /v1/parcels/{parcel_id}/geometry?format=geojson|wkt
GET  /v1/lr-units/{main_book_id}/{unit_number}?include=plombe
GET  /v1/lr-units/{main_book_id}/{unit_number}/plombe
POST /v1/batch/parcels        -> 202 { "job_id": "..." }
POST /v1/batch/lr-units       -> 202 { "job_id": "..." }
GET  /v1/jobs/{job_id}
GET  /healthz
```

### 4.1 Conventions

- **Schemas** are the SDK's Pydantic models, serialized directly. OpenAPI is generated by
  FastAPI; no hand-written schema.
- **Errors** use RFC 9457 Problem Details. Each SDK `ErrorType` maps to a stable `type`
  URI and HTTP status: not found to 404, upstream rate limited or unavailable to 503,
  validation to 422, authentication to 401, per-user limit to 429.
- **Language**: `Accept-Language: hr` or `en` selects the language of `title` and `detail`
  in error bodies, using the existing i18n module. Data fields are never translated.
- **Cache headers**: `Cache-Control: max-age` mirrors the cache TTL of the resource.
  `X-Cache: HIT|MISS` reports whether the response came from the cache table.
- **Batch** is asynchronous because a batch of parcels at the upstream rate limit takes
  minutes. The job resource reports `status`, `completed`, `total`, and `results` as they
  arrive. Maximum batch size is a config value, default 100.
- **Map URL** is embedded in the parcel resource as `links.map`, not a separate route.

## 5. Remote MCP

### 5.1 Transport

Mount the MCP Python SDK's streamable HTTP application at `/mcp`, stateless, JSON
responses. Stateless means no session affinity and clean restarts.

Status: `mcp/src/cadastral_mcp/http_server.py` already does exactly this for
`cadastral-mcp --transport http` (loopback, no authentication; see
`mcp-server.md`, "HTTP Mode"). The gateway reuses that mount and adds the
authentication and the service layer below.

### 5.2 Tools

The tool set is the existing one from `mcp/src/cadastral_mcp/server.py`, re-pointed at
the service layer. Adjustments for remote use:

- `batch_fetch_parcels` and `batch_lr_units` accept at most a configured number of items
  in one call (default 20) and run synchronously within that bound. Larger batches return
  a `job_id`, and a new `get_job` tool polls it.
- Tool results stay compact. Ownership sheets are summarized unless `detail=full` is
  requested, consistent with `specs/mcp-client-efficiency.md`.

### 5.3 Client requirements

claude.ai custom connectors require a public HTTPS URL and OAuth 2.1 with authorization
server discovery. A connector added on the web is available in the mobile app. Claude
Desktop continues to use the local stdio server.

## 6. Upstream Rate Limiting

One process-wide limiter guards every upstream call regardless of which adapter triggered
it.

- Implementation: the SDK's `RateLimiter` (slot reservation under a lock, one per
  client, shared by every worker thread), already in place. Interval from
  `CADASTRAL_API_RATE_LIMIT`. The gateway adds the fairness and backpressure below.
- Fairness: interactive requests (REST GET, MCP tool) take priority over batch jobs. The
  batch worker yields whenever an interactive request is waiting. A simple two-level
  queue is enough.
- Backpressure: if a request would wait longer than `GATEWAY_MAX_QUEUE_WAIT` (default 20
  seconds), return 503 with `Retry-After` rather than holding the connection.

## 7. Authentication and Authorization

### 7.1 REST: API keys

- Keys are random 32-byte tokens shown once at creation; only a SHA-256 hash is stored.
- Sent as `Authorization: Bearer <key>`.
- Each key belongs to a user row and carries a per-user request quota (default 600 per
  hour). Exceeding it returns 429.
- Management is a CLI subcommand on the gateway (`gateway user add`, `gateway key create`,
  `gateway key revoke`), not an HTTP route, to keep the attack surface small.

### 7.2 MCP: OAuth 2.1

This is the one genuinely non-trivial piece, and it is imposed by claude.ai, not by the
design. Status: the MCP server already is a small OAuth 2.1 authorization server whose
login credential is an access key from `.env` (`cadastral_mcp.auth`, see
`mcp-server.md`, "Access keys"); claude.ai connectors work against it behind an HTTPS
proxy. The gateway keeps that for a handful of trusted users, or replaces it with an
external authorization server when real accounts are needed: it then acts as an OAuth
resource server and validates JWTs. Candidates, to be decided in phase 3:

1. A hosted identity provider with a free tier and dynamic client registration.
2. Keycloak in the same Docker Compose file, if a hosted provider proves awkward.

Only allow-listed identities may connect. For a personal deployment the allow list is one
account. The same JWTs are accepted on REST routes, so a single identity works for both
surfaces.

## 8. Caching

A `cache` table in SQLite keyed by upstream request signature, with a TTL per data class.
The cache survives restarts and is bounded by a periodic sweep of expired rows.

| Data class | TTL | Contains personal data |
|---|---|---|
| Offices, municipalities | 24 h | No |
| Parcel search (number to id) | 6 h | No |
| Parcel detail | 30 min | Yes |
| Land registry unit | 30 min | Yes |
| Plombe and file status | 5 min | No, but changes frequently |
| Geometry (parsed) | 7 days | No |
| GML files | until manually cleared | No |

The short TTL on personal data is a policy choice, not a performance one: the gateway is
not a copy of the register. A `gateway cache clear` command exists for purging.

## 9. Persistence

One SQLite database in WAL mode on the mounted volume. Tables:

- `users` (id, display_name, identity, created_at, disabled)
- `api_keys` (id, user_id, key_hash, label, created_at, revoked_at)
- `audit` (id, user_id, at, surface `rest|mcp`, operation, arguments, cache_hit,
  upstream_calls, duration_ms, status)
- `cache` (key, data_class, body, expires_at)
- `jobs` (id, user_id, kind, status, total, completed, items, results, created_at,
  updated_at)

The audit table is a deliberate compliance feature, because responses contain ownership
records. Argument logging records identifiers (parcel id, municipality code) and never
response bodies. GML files live in a sibling directory managed by the existing `GISCache`.

## 10. Deployment

- One Docker image built from the monorepo, entry point `gateway serve`.
- One volume mounted at `/data` holding `gateway.sqlite` and `gis/`.
- TLS at the edge, choose one:
  - Caddy in the same Compose file with automatic certificates, or
  - Cloudflare Tunnel, which needs no open inbound port and is convenient for a home
    server or small VPS.
- Configuration by environment variables with a `GATEWAY_` prefix, loaded through
  pydantic-settings. Upstream settings reuse the existing `CADASTRAL_API_*` variables.
- Logs are JSON lines to stdout with a request id. Health is `/healthz`.
- No cloud-specific services. The same image runs on a laptop, a VPS, or a container
  platform.

### 10.1 When to upgrade

Change the design only when one of these is actually observed:

| Observation | Change |
|---|---|
| A second replica is required for availability | Move cache and limiter to Redis; move GML to object storage |
| SQLite write contention appears in logs | Move to Postgres |
| Batch jobs are lost on restart and this matters | Persist job progress per item (already possible in SQLite) before considering a queue |
| Upstream rate limit is the bottleneck for users | Nothing architectural helps; the limit is upstream's. Improve cache hit rate. |

## 11. Repository Changes

New top-level project following `specs/naming-conventions.md`:

```text
gateway/
├── src/cadastral_gateway/
│   ├── app.py            # ASGI composition: routers, MCP mount, middleware
│   ├── settings.py       # pydantic-settings, GATEWAY_* variables
│   ├── main.py           # `gateway serve|user|key|cache` CLI
│   ├── service/          # use-cases (section 3.2)
│   ├── rest/             # routers, problem-details mapping
│   ├── mcp_adapter/      # shared tool registrations, streamable HTTP mount
│   ├── auth/             # API keys, JWT verification, allow list
│   ├── store/            # SQLite schema, cache, audit, jobs
│   └── limiter.py        # upstream limiter with interactive priority
├── tests/
│   ├── contract/         # gateway against mock server
│   └── unit/
├── Dockerfile
├── docker-compose.yml    # gateway + Caddy (or tunnel)
└── pyproject.toml
```

Changes to existing projects:

- `api/`: `_wait_for_rate_limit` is thread-safe since the HTTP transport
  (`cadastral_api.rate_limiter.RateLimiter`); the interactive-priority queue of
  section 6 is still to do. No other change required for v1.
- `mcp/`: tool bodies move to `cadastral_gateway.mcp_adapter` or to a shared module the
  stdio server imports; `http_server.py` stays as the unauthenticated local transport,
  or `main.py --transport http` prints a pointer to the gateway, to be decided when
  the gateway exists.
- `cli/`: optional `--backend gateway --gateway-url ... --api-key ...` so the CLI can use
  the shared cache instead of calling upstream. Phase 2, not required.
- `mock-server/`: unchanged; it is the upstream for contract tests.

## 12. Phases

1. **Foundations.** Thread-safe limiter in the SDK. `cadastral_gateway` package with
   service layer, SQLite store, and settings. Existing stdio MCP server re-pointed at the
   service layer and verified against the mock.
2. **REST.** Routers, API keys, audit, cache policy, batch jobs, Dockerfile and Compose,
   contract tests. Deploy behind TLS. Optional CLI gateway backend.
3. **Remote MCP.** Streamable HTTP mount, OAuth resource server, external authorization
   server, allow list. Connect from claude.ai web, then verify on mobile.
4. **Hosted-only features.** Watchlists: a user registers land registry units and the
   gateway polls file status on a schedule and notifies when a plomba appears. This is
   the first capability the local tools cannot offer.

## 13. Acceptance Criteria

- All REST routes and MCP tools return correct results against the mock server in
  contract tests.
- Two concurrent clients never cause the upstream to see two requests closer together
  than the configured interval (asserted with the mock server's request log).
- A cached parcel detail is served without an upstream call and expires at its TTL.
- A request without credentials returns 401; a revoked key returns 401; a user over quota
  returns 429.
- Every successful and failed operation produces one audit row without response bodies.
- The container restarts with cache, keys, and audit intact from the volume.

## 14. Open Questions

- Which authorization server for phase 3. Decide after checking current MCP SDK auth
  support and claude.ai connector documentation.
- Whether audit rows should be retained indefinitely or pruned after a fixed period.
- Whether the CLI gateway backend is worth maintaining, or whether the CLI stays a pure
  local tool.
