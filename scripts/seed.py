import uuid
from datetime import datetime, timezone

from cassctl.connection import get_cluster

# One whale merchant and a few normal merchants — so skew becomes visible
WHALE = ("merchant-whale", 5000)
NORMALS = [(f"merchant-{i:03d}", 20) for i in range(1, 6)]


def seed() -> None:
    cluster = get_cluster()
    session = cluster.connect("payments")  # keyspace created by the payment step

    insert = session.prepare("""
        INSERT INTO by_merchant
        (merchant_id, payment_id, idempotency_key, amount_minor, currency, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'CAPTURED', ?)
    """)

    for merchant_id, count in [WHALE, *NORMALS]:
        print(f"Inserting {count} payments for {merchant_id} ...")
        for _ in range(count):
            now = datetime.now(timezone.utc)
            session.execute(insert, (
                merchant_id, uuid.uuid1(), str(uuid.uuid4()),
                1000, "EUR", now,
            ))

    print("Done.")
    cluster.shutdown()


if __name__ == "__main__":
    seed()