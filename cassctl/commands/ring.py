from collections import defaultdict

from rich.console import Console
from rich.table import Table

from cassctl.connection import get_cluster

console = Console()


def ring() -> None:
    """Show the token ownership distribution across the ring per node."""
    cluster = get_cluster()
    cluster.connect()  # The control connection discovers the metadata

    token_map = cluster.metadata.token_map
    if token_map is None:
        console.print("[red]Token map is not available — are the nodes up yet?[/red]")
        cluster.shutdown()
        return

    # The whole ring is an ordered list of tokens; each token belongs to an owner node.
    all_tokens = token_map.ring
    total = len(all_tokens)

    tokens_per_host: dict = defaultdict(int)
    for token in all_tokens:
        owner = token_map.token_to_host_owner[token]
        tokens_per_host[owner] += 1

    table = Table(title=f"Token ring ownership  (total {total} tokens)")
    for col in ("Address", "DC", "Rack", "vnodes (tokens)", "Ownership %"):
        table.add_column(col)

    for host, count in sorted(
        tokens_per_host.items(), key=lambda kv: kv[1], reverse=True
    ):
        pct = 100 * count / total
        table.add_row(
            str(host.address),
            host.datacenter or "-",
            host.rack or "-",
            str(count),
            f"{pct:.1f}%",
        )

    console.print(table)
    cluster.shutdown()