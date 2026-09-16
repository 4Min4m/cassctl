# cassctl

A small operational CLI for inspecting a local Apache Cassandra cluster: node health, token-ring ownership, idempotent payment writes, and partition-skew inspection.

I built it to get hands-on with Cassandra's core operational surfaces — the token ring, replication, and tunable consistency — by running a real multi-node cluster locally rather than reading about it. It's a learning project, not production software, and this README is honest about where it stops.

## What it does

Four subcommands, each connecting to the cluster from outside:

- `health` — per-node up/down status, DC, rack, version (cluster membership via gossip)
- `ring` — token ownership and vnode distribution per node, surfacing imbalance (consistent hashing, replication factor)
- `payment` — an idempotent payment write using a lightweight transaction, so the same idempotency key registers only once (consistency levels, LWT, data modeling)
- `skew` — row count per partition, surfacing a hot/large partition from a deliberately skewed key (partition-key design)

Only `payment` writes and reads data. The other three inspect the cluster's structure and health — `cassctl` is an operator's tool that talks to the database from the outside, not the database itself.

## Setup

The cluster is a 3-node single-DC cluster defined in `docker-compose.yml`, tuned to run on a small machine.

```bash
docker compose up -d
docker exec cass1 nodetool status     # wait until all three nodes show UN
pip install -e .

cassctl health
cassctl ring
cassctl payment --idempotency-key tx-1 --duplicate-attempts 3
python scripts/seed.py && cassctl skew
```

`payment` creates the keyspace and tables, so run it before `skew`.

## A few design decisions

- Single DC, but nodes run `GossipingPropertyFileSnitch` with a DC and rack, so the payments keyspace can use `NetworkTopologyStrategy`. That's enough to reason about multi-DC replication (per-DC replication factor, `LOCAL_QUORUM`) without actually running two datacenters.
- Nodes start one at a time — two joining simultaneously can clash over token ownership.
- Heap is capped manually because Cassandra's default sizing is too large for three containers on a small machine.
- Idempotency lives on a separate table keyed by the idempotency key itself, because a lightweight transaction is only atomic within a single partition.

## Issues I hit while building

Half the learning here was operational, not code:

- **Gossip vs. health check timing** — cass2 crashed on join with `Unable to gossip with any peers`. The health check was going green (via JMX) before the gossip port was ready to accept peers. Fixed by switching the health check to a native-protocol probe and raising the start period.
- **Simultaneous bootstrap** — two non-seed nodes joining at the same time destabilised the cluster. Fixed by staggering startup so each node joins only after the previous one is healthy.
- **Typer single-command quirk** — with only one registered command, Typer treats it as a bare CLI and drops the command name. Fixed with an empty `@app.callback()` so it's treated as a command group.
- **`Cannot achieve consistency level QUORUM`** — `payment` failed with `alive_replicas: 1`. Not a code bug: the cluster wasn't fully joined. A good reminder of the difference between `Unavailable` (the coordinator fails fast because it knows there aren't enough live replicas) and a write timeout (the write was attempted and may have partially applied).

## Where it's useful

As an operator's lens on a cluster: checking node health and ring balance at a glance, demonstrating idempotent write semantics for a payments-style workload, and spotting a hot partition before it becomes a production problem. It's a teaching and diagnostic tool rather than a monitoring system — the kind of small utility you reach for while learning a cluster's shape, or explaining these concepts to someone else.

## Limitations

- `skew` counts rows as a proxy for partition size; true on-disk size comes from `nodetool tablehistograms`.
- From the host, query routing is whitelisted to the reachable contact point (docker-internal peer IPs aren't routable); topology metadata is still complete via the control connection. In production this would be a token-aware, DC-aware policy.
- The payment flow has a small race window between the guard insert and the main insert; production would close it with a status field or a reconciliation job.
