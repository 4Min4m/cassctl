import time
import uuid
from datetime import datetime, timezone

import typer
from cassandra.query import SimpleStatement
from cassandra import ConsistencyLevel
from rich.console import Console

from cassctl.connection import get_cluster

console = Console()


def _ensure_schema(session) -> None:
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS payments WITH replication =
        {'class': 'NetworkTopologyStrategy', 'dc1': 3}
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS payments.by_merchant (
            merchant_id text, payment_id timeuuid, idempotency_key text,
            amount_minor bigint, currency text, status text, created_at timestamp,
            PRIMARY KEY ((merchant_id), payment_id)
        ) WITH CLUSTERING ORDER BY (payment_id DESC)
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS payments.idempotency (
            idempotency_key text PRIMARY KEY,
            payment_id timeuuid, merchant_id text, created_at timestamp
        )
    """)


def _process_payment(session, merchant_id, idempotency_key, amount_minor, currency):
    """Register a payment idempotently. Returns: (payment_id, was_new)."""
    payment_id = uuid.uuid1()          # timeuuid: unique + time-ordered
    now = datetime.now(timezone.utc)

    # First act: the LWT guard on the idempotency table (atomic within this partition)
    guard = SimpleStatement("""
        INSERT INTO payments.idempotency (idempotency_key, payment_id, merchant_id, created_at)
        VALUES (%s, %s, %s, %s) IF NOT EXISTS
    """, consistency_level=ConsistencyLevel.QUORUM)
    result = session.execute(guard, (idempotency_key, payment_id, merchant_id, now))
    row = result.one()

    if not row.applied:
        # Duplicate: read the previous payment_id from the same response (echoed back)
        return row.payment_id, False

    # Second act: since the key was new, record the payment in the main table
    session.execute(SimpleStatement("""
        INSERT INTO payments.by_merchant
        (merchant_id, payment_id, idempotency_key, amount_minor, currency, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, consistency_level=ConsistencyLevel.QUORUM),
        (merchant_id, payment_id, idempotency_key, amount_minor, currency, "CAPTURED", now))

    return payment_id, True


def payment(
    merchant_id: str = typer.Option("merchant-001"),
    idempotency_key: str = typer.Option(..., help="Unique key for this transaction"),
    amount_minor: int = typer.Option(1000, help="Amount in the smallest unit (e.g. cents)"),
    currency: str = typer.Option("EUR"),
    duplicate_attempts: int = typer.Option(3, help="How many times to send the same key in a row"),
) -> None:
    """Simulate an idempotent payment; sending the same key multiple times must register only once."""
    cluster = get_cluster()
    session = cluster.connect()
    _ensure_schema(session)

    console.print(f"Sending [bold]{duplicate_attempts}[/bold] times with the same idempotency_key='{idempotency_key}':\n")
    for i in range(1, duplicate_attempts + 1):
        pid, was_new = _process_payment(session, merchant_id, idempotency_key, amount_minor, currency)
        tag = "[green]NEW[/green]  registered" if was_new else "[yellow]DUPLICATE[/yellow]  rejected, same result returned"
        console.print(f"  Attempt {i}: {tag}  → payment_id={pid}")
        time.sleep(0.1)

    console.print("\n[dim]Expected result: only the first attempt is NEW; the rest are DUPLICATE with the same payment_id.[/dim]")
    cluster.shutdown()