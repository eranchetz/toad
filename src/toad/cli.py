import click
from toad.app import ToadApp


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Toad. The Batrachian AI."""
    if ctx.invoked_subcommand is not None:
        return
    app = ToadApp()
    app.run()


@main.command("acp")
@click.argument("command", metavar="COMMAND")
@click.option("--project-dir", metavar="PATH", default=None)
def acp(command: str, project_dir: str | None) -> None:
    app = ToadApp(acp_command=command, project_dir=project_dir)
    app.run()


if __name__ == "__main__":
    main()
