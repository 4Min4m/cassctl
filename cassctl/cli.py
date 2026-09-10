import typer
from cassctl.commands import health as health_cmd

app = typer.Typer(help="cassctl - Cassandra cluster opertaion check")
app.command("health")(health_cmd.health)

if __name__ == "__main__":
    app()