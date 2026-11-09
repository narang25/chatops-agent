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
    multi: bool = typer.Option(
        False,
        "--multi",
        help="Use parallel multi-agent architecture (LogAgent + MetricsAgent + EventsAgent + Coordinator).",
    ),
) -> None:
    """
    Ask the ChatOps agent an incident question and get a cited diagnosis.

    \b
    Examples:
      chatops ask "Why did payment-service get OOMKilled?"
      chatops ask "inventory-service is crash-looping" --multi
      chatops ask "disk full on any service"  --no-stub
    """
    # Lazy import to avoid long cold-start on --help
    from agent.agent import ask as _ask

    console.print()
    mode_text = "[bold cyan]ChatOps AI SRE Agent[/bold cyan]"
    if multi:
        mode_text += " [bold magenta][Parallel Multi-Agent Mode][/bold magenta]"
    console.print(
        Panel(
            f"{mode_text}\n[dim]Investigating your incident...[/dim]",
            border_style="magenta" if multi else "cyan",
        )
    )

    start = time.perf_counter()
    if multi:
        from agent.multi.sub_agents import multi_agent_ask
        with Status("[bold magenta]Running concurrent specialists (Log + Metrics + Events) & Coordinator...[/bold magenta]", console=console, spinner="dots"):
            try:
                ma_res = multi_agent_ask(question=question, model_id=model, stub=stub)
                result = {
                    "question": question,
                    "answer": ma_res.get("diagnosis", ""),
                    "messages": [
                        {"type": "assistant", "content": ma_res.get("diagnosis", "")}
                    ],
                }
            except Exception as exc:
                console.print(f"\n[bold red]Error in multi-agent execution:[/bold red] {exc}")
                raise typer.Exit(code=1)
    else:
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


@app.command()
def learn(
    incident: str = typer.Argument(..., help="Natural-language description of resolved incident."),
    root_cause: Optional[str] = typer.Option(None, "--cause", "-c", help="Confirmed root cause."),
    fix: Optional[str] = typer.Option(None, "--fix", "-f", help="Verified remediation procedure."),
    service: Optional[str] = typer.Option(None, "--service", "-s", help="Affected service."),
) -> None:
    """
    Draft a new SRE runbook from a resolved incident (status: draft).
    The draft is saved in data/runbooks/drafts/ and is NOT searchable until approved.
    """
    from agent.learning.draft_runbook import draft_runbook_from_incident

    console.print()
    console.print(Rule("[bold cyan]Drafting New SRE Runbook[/bold cyan]"))
    with Status("[bold green]Synthesizing draft from incident notes...[/bold green]", console=console, spinner="dots"):
        content, draft_path = draft_runbook_from_incident(
            incident_description=incident,
            root_cause=root_cause,
            fix=fix,
            service=service,
        )

    console.print(Markdown(content))
    console.print()
    console.print(
        Panel(
            f"[bold green]Draft created successfully![/bold green]\n"
            f"[bold]Location:[/bold] {draft_path}\n"
            f"[dim]Status: draft (not indexed in Chroma until approved)[/dim]\n\n"
            f"To approve and publish: [bold cyan]chatops approve {draft_path.name}[/bold cyan]",
            title="[bold yellow]Human Approval Required[/bold yellow]",
            border_style="yellow",
        )
    )


@app.command()
def approve(
    draft_file: str = typer.Argument(..., help="Draft runbook filename or path to approve."),
) -> None:
    """
    Approve and publish a draft runbook.
    Moves the file to data/runbooks/ and immediately indexes it into Chroma.
    """
    from agent.learning.draft_runbook import approve_draft

    console.print()
    with Status("[bold green]Promoting and indexing approved runbook...[/bold green]", console=console, spinner="dots"):
        try:
            dest_path, chunks = approve_draft(draft_file)
        except Exception as exc:
            console.print(f"[bold red]Approval failed:[/bold red] {exc}")
            raise typer.Exit(code=1)

    console.print(
        Panel(
            f"[bold green]Runbook Approved and Published![/bold green]\n"
            f"[bold]Published Path:[/bold] {dest_path}\n"
            f"[bold]Chunks Indexed:[/bold] {chunks} chunk(s) active in Chroma\n"
            f"[dim]The agent can now retrieve and apply this playbook during live investigations.[/dim]",
            title="[bold green]Published[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
