from rich.console import Console
from rich.table import Table

from cassctl.connection import get_cluster

console = Console()


def health() -> None:
    cluster = get_cluster()
    cluster.connect()

    table = Table(title="Cassandra cluster health")
    for col in ("Address", "Status", "DC", "Rack", "Version"):
        table.add_column(col)

    for host in sorted(cluster.metadata.all_hosts(), key=lambda h: str(h.address)):
        status = {True: "UP", False: "DOWN", None: "?"}[host.is_up]
        table.add_row(
            str(host.address), status,
            host.datacenter or "-", host.rack or "-",
            host.release_version or "-",
        )

    console.print(table)
    cluster.shutdown()