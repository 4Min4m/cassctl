from rich.console import Console
from rich.table import Table

from cassctl.connection import get_cluster

console = Console()


def skew(top: int = 10) -> None:
    """Show the number of rows per partition for the by_merchant table (hot partition view)."""
    cluster = get_cluster()
    session = cluster.connect("payments")

    # Read merchant_ids from the helper table to avoid a full scan
    merchants = [r.merchant_id for r in session.execute(
        "SELECT DISTINCT merchant_id FROM by_merchant"
    )]

    counts = []
    for m in merchants:
        # COUNT over a single partition — since WHERE is on the entire partition key
        row = session.execute(
            "SELECT COUNT(*) AS c FROM by_merchant WHERE merchant_id = %s", (m,)
        ).one()
        counts.append((m, row.c))

    counts.sort(key=lambda kv: kv[1], reverse=True)
    total = sum(c for _, c in counts) or 1

    table = Table(title="Partition size distribution  (by_merchant)")
    for col in ("Partition (merchant_id)", "Rows", "% of total"):
        table.add_column(col)

    for m, c in counts[:top]:
        table.add_row(m, str(c), f"{100 * c / total:.1f}%")

    console.print(table)
    console.print(
        "\n[dim]This is a demonstration, not real-time hotspot detection. "
        "The actual on-disk partition size comes from nodetool tablehistograms.[/dim]"
    )
    cluster.shutdown()