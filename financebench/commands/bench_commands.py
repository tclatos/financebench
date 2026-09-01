"""Bench CLI commands for FinanceBench."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from genai_tk.cli.base import CliTopCommand
from financebench.bench.run import (
    ALL_STEPS,
    list_bench_profiles,
    load_bench_profile,
    run_bench,
)

console = Console()


class BenchCommands(CliTopCommand):
    """Benchmark commands for FinanceBench."""

    description: str = "Run and inspect FinanceBench evaluations"

    def get_description(self) -> tuple[str, str]:
        return "bench", self.description

    def register_sub_commands(self, cli_app: typer.Typer) -> None:
        @cli_app.command("list")
        def list_profiles(
            config_path: Annotated[
                str | None,
                typer.Option(
                    "-c", "--config", help="Path to bench YAML configuration file"
                ),
            ] = None,
        ) -> None:
            """List configured benchmark run profiles."""
            cfg_p = Path(config_path) if config_path else None
            profiles = list_bench_profiles(cfg_p)
            if not profiles:
                console.print(
                    "[yellow]No benchmark profiles found in configuration.[/yellow]"
                )
                return

            table = Table(title="FinanceBench Run Profiles")
            table.add_column("Profile", style="bold cyan")
            table.add_column("Description", style="white")
            table.add_column("Markdownize", style="magenta")
            table.add_column("Agent LLM", style="green")
            table.add_column("Judge LLM", style="blue")
            table.add_column("Files / Pathspecs", style="yellow")

            for name, data in profiles.items():
                desc = data.get("description", "")
                md_prof = data.get("markdownize_profile", "medium")
                llms = data.get("llms", {}) or {}
                agent_llm = llms.get("agent", "default")
                judge_llm = llms.get("judge", "default")
                files = data.get("files", {}) or data.get("questions", {}) or {}
                pathspecs = files.get("pathspecs", [])
                docs = files.get("docs", [])
                if pathspecs:
                    files_src = f"specs: {', '.join(pathspecs)}"
                elif docs:
                    files_src = f"{len(docs)} doc(s)"
                else:
                    files_src = "all docs"
                table.add_row(name, desc, md_prof, agent_llm, judge_llm, files_src)

            console.print(table)

        @cli_app.command("run")
        def run(
            profile: Annotated[
                str | None,
                typer.Option(
                    "-p",
                    "--profile",
                    help="Bench run profile key (defaults to default_profile in config)",
                ),
            ] = None,
            pathspecs: Annotated[
                str | None,
                typer.Option(
                    "-f",
                    "--files",
                    "--pathspecs",
                    help="Comma-separated pathspec patterns to filter documents (e.g. 'BESTBUY*,Pfizer*')",
                ),
            ] = None,
            docs: Annotated[
                str | None,
                typer.Option(
                    "-d",
                    "--docs",
                    help="Comma-separated doc_names overriding config files.docs",
                ),
            ] = None,
            judge: Annotated[
                bool | None,
                typer.Option(
                    "--judge/--no-judge",
                    help="Enable or disable LLM-as-judge analysis (default: from config)",
                ),
            ] = None,
            step: Annotated[
                str | None,
                typer.Option(
                    "--step", help="Run only this one step (fetch, build, run, grade)"
                ),
            ] = None,
            skip: Annotated[
                list[str] | None,
                typer.Option("--skip", help="Skip step(s) (fetch, build, run, grade)"),
            ] = None,
            limit: Annotated[
                int | None,
                typer.Option("-n", "--limit", help="Run only the first N questions"),
            ] = None,
            monitoring: Annotated[
                str | None,
                typer.Option(
                    "-m",
                    "--monitoring",
                    help="Tracing monitoring method ('none', 'langchain', 'langsmith', 'langfuse', 'local')",
                ),
            ] = None,
            force: Annotated[
                bool,
                typer.Option("--force", help="Force rebuild of OCR and document graph"),
            ] = False,
            config_path: Annotated[
                str | None,
                typer.Option(
                    "-c", "--config", help="Path to bench YAML configuration file"
                ),
            ] = None,
        ) -> None:
            """Execute a benchmark evaluation run.

            Examples:
                cli bench run
                cli bench run -p mistral_glm -n 3
                cli bench run --no-judge
                cli bench run -f 'BESTBUY*,Pfizer*'
                cli bench run --skip fetch --skip build
                cli bench run --step run -n 1
            """
            if step and step not in ALL_STEPS:
                console.print(
                    f"[red]Error:[/red] Invalid step '{step}'. Choose from: {ALL_STEPS}"
                )
                raise typer.Exit(1)

            if skip:
                invalid_skips = [s for s in skip if s not in ALL_STEPS]
                if invalid_skips:
                    console.print(
                        f"[red]Error:[/red] Invalid skip step(s) {invalid_skips}. Choose from: {ALL_STEPS}"
                    )
                    raise typer.Exit(1)

            cfg_p = Path(config_path) if config_path else None
            try:
                cfg = load_bench_profile(profile_name=profile, config_path=cfg_p)
            except Exception as exc:
                console.print(f"[red]Error loading profile:[/red] {exc}")
                raise typer.Exit(1) from exc

            if docs:
                cfg.docs = [d.strip() for d in docs.split(",") if d.strip()]
            elif pathspecs:
                specs_list = [s.strip() for s in pathspecs.split(",") if s.strip()]
                cfg.docs = cfg.resolve_docs(pathspecs_override=specs_list)

            if limit is not None:
                cfg.limit = limit
            if monitoring is not None:
                cfg.monitoring = monitoring
            if judge is not None:
                cfg.judge_enabled = judge
            if force:
                cfg.build_force = True

            console.print(
                f"[bold green]Starting benchmark run:[/bold green] profile=[cyan]{cfg.profile_name}[/cyan], "
                f"docs=[yellow]{len(cfg.docs)}[/yellow], judge=[magenta]{cfg.judge_enabled}[/magenta]"
            )
            try:
                run_bench(cfg, skip=skip, step=step)
            except Exception as exc:
                console.print(f"[red]Benchmark run failed:[/red] {exc}")
                raise typer.Exit(1) from exc
