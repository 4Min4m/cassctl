import typer

from cassctl.commands import payment as payment_cmd
from cassctl.commands import ring as ring_cmd
from cassctl.commands import skew as skew_cmd
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


app.command("ring")(ring_cmd.ring)
app.command("payment")(payment_cmd.payment)
app.command("skew")(skew_cmd.skew)


if __name__ == "__main__":
    app()
