<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/info.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.3.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Check that the tool is set up

Shows the version of the tool, the server it talks to, and the boundary data
it has stored on your computer. This is the first thing to run after
installation, and the first thing to run when something does not work.

## When you would use this

- The tool has just been installed and you want to confirm it works.
- A command failed and you want to see whether the tool is pointed at the right server.

## Before you start

Nothing. This command takes no input and changes nothing.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral info
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral info -->
   ```text
   Croatian Cadastral CLI
   ======================
   Version: 0.3.0
   API Base: http://localhost:8000

   Cache Information
   =================
   Cache Directory: ~/.cadastral_api_cache
   Cache Size: 0.0 MB
   Cached Municipalities: 1
     • 334979 (0.7 KB)
   Response cache: memory, 0 entries, 0.0 MB

   API Settings
   ============
   Rate Limit: 0.375 seconds between requests
   Timeout: 10.0 seconds
   Unknown server fields: warn

   To clear cache: cadastral cache clear --all
   ```
   <!-- END GENERATED: output -->

4. **API Base** is the address of the server the tool talks to. For practice
   it is the address of the practice server on your own computer.
   **Cache Information** lists the municipalities whose boundary data is
   stored on your computer, and the **Response cache** line says whether
   answers from the server are kept in memory while a command runs (they
   are, unless it says `off`). **API Settings** shows how long the tool
   waits between requests and how long it waits for an answer.

## Choices you can make

None. If the tool prints this screen, it is installed correctly.

<!-- BEGIN GENERATED: options -->
This command has no choices. Type it as it is.
<!-- END GENERATED: options -->

## If something goes wrong

If Terminal says the command is not found, the tool is not installed for your
user account, or Terminal was opened before the installation finished. Close
Terminal, open it again and retry. If it still fails, ask the person who
installed the tool.

## Related pages

- [cache-list](cache-list.md) shows the stored boundary data in more detail.
- [Start here](../start-here.md) is the tutorial.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral info --help` prints:

```text
Usage: cadastral info [OPTIONS]

  Display system information and cache status.

  Example:
    cadastral info

Options:
  --help  Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
