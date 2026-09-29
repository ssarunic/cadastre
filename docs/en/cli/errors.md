<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/errors.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.4.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# What the error messages mean

When something goes wrong, the tool stops and prints one line in red. This
page lists the messages and says what to do about each.

<!-- BEGIN GENERATED: errors -->
Every error starts with this mark and one of the messages below:

```text
✗ Error:
```

| What the tool prints | Kind of problem |
|---|---|
| **Connection error** | `connection` |
| **Request timed out** | `timeout` |
| **Rate limit exceeded** | `rate_limit` |
| **Invalid response from server** | `invalid_response` |
| **Parcel not found** | `parcel_not_found` |
| **Municipality not found** | `municipality_not_found` |
| **Land registry unit not found** | `lr_unit_not_found` |
| **Possession sheet not found** | `possession_sheet_not_found` |
| **Server error** | `server_error` |
| **Access denied** | `access_denied` |
| **HTTP error** | `http_error` |
<!-- END GENERATED: errors -->

## Messages about what you typed

**Parcel not found** means the parcel number does not exist in the
municipality you named. Check the number on your document, including the part
after the slash, and check that you named the right municipality.

**Municipality not found** means the name or number after `-m` is not known.
Check the spelling, or find the registration number with
[search-municipality](commands/search-municipality.md) and use that instead.

**Land registry unit not found** means the unit number and main book you gave
do not match a unit. Check both numbers. If you started from a parcel, the
parcel may not be entered in the land registry yet.

## Messages about the connection

**Connection error** means the tool could not reach the server. For practice
use, the practice server on your computer is not running. Ask the person who
installed the tool to start it, then run the command again.

**Request timed out** means the server did not answer in time. Wait a moment
and run the command again.

**Rate limit exceeded** means requests were sent too quickly. The tool already
spaces its requests; wait a minute and try again.

**Server error** and **Invalid response from server** mean the server answered
but not in the expected way. Try again later. If it keeps happening, tell the
person who installed the tool.

## Messages from Terminal itself

If Terminal answers `command not found`, the tool is not installed for your
account or Terminal was opened before the installation finished. Close
Terminal, open it again, and retry. If it still fails, ask the person who
installed the tool.

If the tool prints `Missing option` or `No such option`, part of the command is
misspelt. Compare your line with the example on the command's page.
