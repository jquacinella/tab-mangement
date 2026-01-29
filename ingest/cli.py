"""
TabBacklog v1 - Ingest CLI

Command-line interface for ingesting Firefox bookmarks into the database.

Usage:
    python -m ingest.cli --file ~/bookmarks.html --user-id UUID
    python -m ingest.cli stats --file ~/bookmarks.html
"""

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .firefox_parser import FirefoxParser
from .db import IngestDB

console = Console()


def get_database_url() -> str:
    """Get database URL from environment"""
    url = os.environ.get("DATABASE_URL")
    if not url:
        console.print("[red]Error:[/red] DATABASE_URL environment variable not set")
        console.print("Set it with: export DATABASE_URL=postgresql://user:pass@host/db")
        sys.exit(1)
    return url


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """TabBacklog - Firefox Tab Ingest Tool"""
    pass


@cli.command()
@click.option(
    "--file", "-f",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to Firefox bookmarks HTML export file"
)
@click.option(
    "--user-id", "-u",
    required=True,
    help="User UUID for the tab owner"
)
@click.option(
    "--batch-size", "-b",
    default=100,
    type=int,
    help="Number of records to process per batch (default: 100)"
)
@click.option(
    "--dry-run", "-n",
    is_flag=True,
    help="Parse and show stats without writing to database"
)
def ingest(file: Path, user_id: str, batch_size: int, dry_run: bool):
    """
    Ingest Firefox bookmarks into the database.

    Parses the Firefox bookmarks HTML export and inserts tabs from
    Session-* folders into the database.
    """
    console.print(f"\n[bold blue]TabBacklog Ingest[/bold blue]")
    console.print(f"File: {file}")
    console.print(f"User ID: {user_id}")
    console.print()

    # Parse the bookmarks file
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing bookmarks file...", total=None)

        try:
            parser = FirefoxParser(file)
            stats = parser.get_stats()
            bookmarks = parser.parse()
        except Exception as e:
            console.print(f"[red]Error parsing file:[/red] {e}")
            sys.exit(1)

        progress.update(task, completed=True)

    # Display parsing results
    console.print(f"[green]Parsed successfully![/green]")
    console.print(f"  Session folders found: {stats['total_session_folders']}")
    console.print(f"  Total bookmarks: {stats['total_bookmarks']}")
    console.print()

    # Show folder breakdown
    if stats['session_folders']:
        table = Table(title="Session Folders")
        table.add_column("Window Label", style="cyan")
        table.add_column("Bookmark Count", justify="right", style="green")

        for folder in stats['session_folders']:
            table.add_row(folder['label'], str(folder['count']))

        console.print(table)
        console.print()

    if not bookmarks:
        console.print("[yellow]No bookmarks found in Session-* folders.[/yellow]")
        console.print("Make sure your bookmarks are organized in folders with 'Session-' prefix.")
        return

    if dry_run:
        console.print("[yellow]Dry run mode - no changes written to database[/yellow]")
        return

    # Ingest into database
    database_url = get_database_url()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Ingesting {len(bookmarks)} bookmarks...",
            total=None
        )

        try:
            db = IngestDB(database_url)
            result = db.ingest_bookmarks(bookmarks, user_id, batch_size)
        except Exception as e:
            console.print(f"[red]Database error:[/red] {e}")
            sys.exit(1)

        progress.update(task, completed=True)

    # Display results
    console.print()
    console.print("[bold green]Ingest Complete![/bold green]")

    results_table = Table(title="Results")
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Count", justify="right", style="green")

    results_table.add_row("Total processed", str(result.total_processed))
    results_table.add_row("New tabs inserted", str(result.inserted))
    results_table.add_row("Duplicates skipped", str(result.skipped_duplicates))
    results_table.add_row("Errors", str(result.errors))

    console.print(results_table)

    if result.error_messages:
        console.print()
        console.print("[yellow]Errors encountered:[/yellow]")
        for error in result.error_messages[:10]:  # Show first 10 errors
            console.print(f"  - {error}")
        if len(result.error_messages) > 10:
            console.print(f"  ... and {len(result.error_messages) - 10} more")

    # Show current totals
    try:
        total_tabs = db.get_user_tab_count(user_id)
        summary = db.get_ingest_summary(user_id)

        console.print()
        console.print(f"[bold]User now has {total_tabs} total tabs[/bold]")

        if summary:
            status_table = Table(title="Tabs by Status")
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", justify="right", style="green")

            for status, count in sorted(summary.items()):
                status_table.add_row(status, str(count))

            console.print(status_table)
    except Exception:
        pass  # Non-critical, just skip the summary


@cli.command()
@click.option(
    "--file", "-f",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to Firefox bookmarks HTML export file"
)
def stats(file: Path):
    """
    Show statistics about a bookmarks file without ingesting.

    Useful for previewing what would be imported.
    """
    console.print(f"\n[bold blue]Bookmarks File Statistics[/bold blue]")
    console.print(f"File: {file}")
    console.print()

    try:
        parser = FirefoxParser(file)
        stats = parser.get_stats()
    except Exception as e:
        console.print(f"[red]Error parsing file:[/red] {e}")
        sys.exit(1)

    console.print(f"Total Session folders: {stats['total_session_folders']}")
    console.print(f"Total bookmarks in Session folders: {stats['total_bookmarks']}")
    console.print()

    if stats['session_folders']:
        table = Table(title="Session Folders Breakdown")
        table.add_column("Window Label", style="cyan")
        table.add_column("Bookmark Count", justify="right", style="green")

        for folder in stats['session_folders']:
            table.add_row(folder['label'], str(folder['count']))

        console.print(table)
    else:
        console.print("[yellow]No Session-* folders found in the bookmarks file.[/yellow]")
        console.print()
        console.print("Expected folder structure:")
        console.print("  Session-Research")
        console.print("    └── bookmark1")
        console.print("    └── bookmark2")
        console.print("  Session-Work")
        console.print("    └── bookmark3")


@cli.command()
@click.option(
    "--user-id", "-u",
    required=True,
    help="User UUID to query"
)
def status(user_id: str):
    """
    Show current database status for a user.
    """
    database_url = get_database_url()

    try:
        db = IngestDB(database_url)
        total = db.get_user_tab_count(user_id)
        summary = db.get_ingest_summary(user_id)
    except Exception as e:
        console.print(f"[red]Database error:[/red] {e}")
        sys.exit(1)

    console.print(f"\n[bold blue]Database Status[/bold blue]")
    console.print(f"User ID: {user_id}")
    console.print(f"Total active tabs: {total}")
    console.print()

    if summary:
        table = Table(title="Tabs by Status")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for status_name, count in sorted(summary.items()):
            table.add_row(status_name, str(count))

        console.print(table)
    else:
        console.print("[yellow]No tabs found for this user.[/yellow]")


def main():
    """Entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()
