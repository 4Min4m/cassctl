import typer
from cassctl.commands.health import health

app = typer.Typer(
    help="cassctl - Cassandra cluster operation check",
    no_args_is_help=True,
)

@app.callback()
def main() -> None:
    """cassctl - Cassandra cluster operation check"""
    pass

@app.command("health")
def health_cmd() -> None:
    """Show Cassandra cluster health."""
    health()

if __name__ == "__main__":
    app()