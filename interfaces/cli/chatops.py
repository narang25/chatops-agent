"""
ChatOps CLI — interfaces/cli/chatops.py

Usage:
    python -m interfaces.cli.chatops ask "Why did payment-service fail?"
    python -m interfaces.cli.chatops ask "inventory keeps restarting" --stub
    python -m interfaces.cli.chatops ask "disk full on order service" --no-stub

    # Or via the entry point (after pip install -e .):
    chatops ask "Why did payment-service fail?"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.status import Status
from rich.text import Text

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="chatops",
    help="AI SRE ChatOps agent — diagnose microservice incidents from the command line.",
    add_completion=False,
)
console = Console()


def _render_answer(question: str, result: dict, elapsed: float) -> None:
    """Render the agent's answer with rich formatting."""
    console.print()
    console.print(
        Panel(
            Text(question, style="bold cyan"),
            title="[bold]Question[/bold]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(Rule("[bold green]Agent Diagnosis[/bold green]"))
    console.print()
    console.print(Markdown(result["answer"]))
    console.print()

    # Sources panel (extracted from tool call messages)
    sources = _extract_sources(result.get("messages", []))
    if sources:
        source_lines = "\n".join(f"  • {s}" for s in sources)
        console.print(
            Panel(
                source_lines,
                title="[bold yellow]Runbooks Cited[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print()

    console.print(
        f"[dim]Completed in {elapsed:.1f}s  |  "
        f"Mode: {'stub' if result.get('stub') else 'live'}[/dim]"
    )


def _extract_sources(messages: list[dict]) -> list[str]:
    """Pull cited runbook titles from the message history."""
    import json as _json

    sources: list[str] = []
    seen: set = set()
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        # Look for JSON blobs from search_runbooks tool results
        try:
            if '"failure_type"' in content and '"title"' in content:
                data = _json.loads(content)
                for r in data.get("results", []):
                    title = r.get("title", "")
                    source = r.get("source", "")
                    key = source or title
                    if key and key not in seen:
                        seen.add(key)
                        sources.append(f"{title}  [{source}]")
        except (_json.JSONDecodeError, AttributeError):
            pass
    return sources


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def ask(
    question: str = typer.Argument(..., help="Incident question to investigate."),
    stub: bool = typer.Option(
        True,
        "--stub/--no-stub",
        help="Use stub tools (default). Use --no-stub when Person B's infra MCP servers are running.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the model ID from agent/config.yaml.",
        show_default=False,
    ),
) -> None:
    """
    Ask the ChatOps agent an incident question and get a cited diagnosis.

    \b
    Examples:
      chatops ask "Why did payment-service get OOMKilled?"
      chatops ask "inventory-service is crash-looping"
      chatops ask "disk full on any service"  --no-stub
    """
    # Lazy import to avoid long cold-start on --help
    from agent.agent import ask as _ask
    from agent.llm import get_llm  # warm-up import

    console.print()
    console.print(
        Panel(
            "[bold cyan]ChatOps AI SRE Agent[/bold cyan]\n"
            "[dim]Investigating your incident...[/dim]",
            border_style="cyan",
        )
    )

    start = time.perf_counter()
    with Status("[bold green]Calling tools and reasoning...[/bold green]", console=console, spinner="dots"):
        try:
            result = _ask(question=question, stub=stub)
        except Exception as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1)

    elapsed = time.perf_counter() - start
    result["stub"] = stub
    _render_answer(question, result, elapsed)


@app.command()
def search(
    query: str = typer.Argument(..., help="Query to search runbooks for."),
    top_k: int = typer.Option(3, "--top-k", "-k", help="Number of results."),
) -> None:
    """
    Search the runbook knowledge base directly (no LLM call).

    Useful for debugging retrieval quality or finding a specific runbook quickly.
    """
    from mcp_servers.runbooks.server import search_runbooks

    console.print()
    with Status("[bold green]Searching runbooks...[/bold green]", console=console, spinner="dots"):
        result = search_runbooks(query=query, top_k=top_k)

    if "error" in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        raise typer.Exit(code=1)

    console.print(Rule(f"[bold]Top {top_k} runbook matches for: [cyan]{query}[/cyan][/bold]"))
    for i, r in enumerate(result.get("results", []), start=1):
        console.print(
            Panel(
                f"[bold]{r['title']}[/bold]\n"
                f"[dim]Service:[/dim] {r['service']}  "
                f"[dim]Type:[/dim] {r['failure_type']}  "
                f"[dim]Score:[/dim] {r['score']}\n"
                f"[dim]Source:[/dim] {r['source']}\n\n"
                + r["snippet"][:300] + "...",
                title=f"[yellow]#{i}[/yellow]",
                border_style="yellow",
            )
        )
    console.print()


if __name__ == "__main__":
    app()
