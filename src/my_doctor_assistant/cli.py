import typer

app = typer.Typer(help="Doctor‑Assistant command‑line tools")
# disable Typer’s auto‑completion flags
app = typer.Typer(
    help="Doctor‑Assistant command‑line tools",
    add_completion=False,
)

_ALLOWED = {"stdio", "sse"}

def _validate_transport(transport: str | None) -> str:
    if transport is None:
        typer.echo(
            "❌  Transport not specified.\n"
            "   Use --transport stdio   (local stdin/stdout)\n"
            "   or  --transport sse     (HTTP/SSE on port 8080)",
            err=True,
        )
        raise typer.Exit(code=1)
    transport = transport.lower()
    if transport not in _ALLOWED:
        typer.echo("Transport must be 'stdio' or 'sse'", err=True)
        raise typer.Exit(code=1)
    return transport

# ──────────────────────────────────────────────────────────────
# Server commands
# ──────────────────────────────────────────────────────────────
@app.command()
def server(
    transport: str | None = typer.Option(
        None,
        "--transport",
        "-t",
        metavar="stdio|sse",
        help="Required: choose the server transport layer",
    )
):
    """Start the MCP server (stdio or sse)."""
    transport = _validate_transport(transport)
    if transport == "stdio":
        from my_doctor_assistant.mcp.stdio.server.medical_graph_server import main
    else:
        from my_doctor_assistant.mcp.sse.server.medical_graph_server import main
    main()

# ──────────────────────────────────────────────────────────────
# Interactive QA shell
# ──────────────────────────────────────────────────────────────
@app.command()
def shell(
    domain: str = typer.Option(
        "schema",
        "--domain",
        "-d",
        help="Prompt slice: schema, vitals, appointments, diagnoses, treatment, medications, labs",
    ),
    transport: str | None = typer.Option(
        None,
        "--transport",
        "-t",
        metavar="stdio|sse",
        help="Required: choose the transport layer the shell will use",
    ),
):
    """Open an interactive QA shell using the selected transport."""
    transport = _validate_transport(transport)

    if transport == "stdio":
        from my_doctor_assistant.mcp.stdio.testagentMCPstdio import MedicalQAAgent
    else:
        from my_doctor_assistant.mcp.sse.testagentMCPsse import MedicalQAAgent

    agent = MedicalQAAgent(domain=domain)
    typer.echo(
        f"Interactive shell started (domain={domain}, transport={transport}). "
        "Type 'exit' to leave."
    )
    while True:
        try:
            q = input("› ")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nExiting shell…")
            break
        if q.strip().lower() in {"exit", "quit"}:
            break
        typer.echo(agent.answer(q))

# ──────────────────────────────────────────────────────────────
# Environment helper
# ──────────────────────────────────────────────────────────────
@app.command()
def env():
    """Reload and print environment variables from config/.env."""
    from my_doctor_assistant.utils.helper import load_environment_variables

    for k, v in load_environment_variables().items():
        print(f"{k}={v}")


if __name__ == "__main__":
    app()