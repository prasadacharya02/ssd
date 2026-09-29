# Federated threat-fingerprint exchange

The network effect, made concrete: when one node contains a file as a
confirmed threat, every other node can ask *"have I seen this
fingerprint before?"* and answer *yes* — with provenance (who saw it,
how many times) — instead of re-learning the same threat from scratch.

This is the layer the pitch claims the blockchain exists to serve. It
is now **built and measured**, not just asserted.

## What it is

- **Registry** — `blockchain/fingerprint_exchange.py`. Maps a
  SHA-256 content fingerprint to `sightings` (writes), `sources`
  (distinct node ids), first-seen time, and the first evidence string.
  In this lab the "network" is one SQLite file
  (`blockchain/exchange.db`) opened by several simulated nodes; in a
  deployment the same schema and API *is* the network.
- **Write path** — `execute_response` shares a fingerprint only for
  **confirmed threats** (files actually quarantined), and only when it
  holds the file's real content hash. A path hash, an alert (a
  suspicion, not a fact), or an already-deleted file is never published.
- **Read path** — `collect_threat_flags` (the same function the live
  pipeline and the benchmark use) looks up the fingerprint on every
  event that carries a content hash.

## The confirmation rule (and why it exists)

| Sightings on record | Flag | Effect |
| --- | --- | --- |
| 0 | — | no exchange signal |
| 1 (single node) | `known_threat` | corroboration only: +25 to the threat score, evidence in the explanation — **never** quarantines alone |
| ≥ `ENTROPY_EXCHANGE_CONFIRM_THRESHOLD` (default **2** *independent* nodes) | `known_threat_confirmed` | hard confirmation: auto-quarantine, like a ransom note or defense tamper |

The threshold is the defence against a poisoned or buggy node seeding
the exchange with a clean file's hash: one node cannot make every other
node destroy files. Two *independent* nodes must agree.

## Measured behaviour (multi-node simulation)

`benchmark/exchange_simulation.py` runs several tenants (distinct
identities, each with its own local entropy history) against one shared
exchange, driving the **real** decision + response chain (dry-run).

The test strain: a ransom note plus in-place encryption of a
deterministic 64 KB payload. The *ambiguous* case: that same payload
alone — high entropy, unknown extension, **no note, no baseline, no
local history** — which on its own is only an ALERT (score 40).

| Phase | Tenant | Exchange state | Local score | Decision |
| --- | --- | --- | --- | --- |
| Cold start | charlie | empty | 40 | **ALERT** |
| Seeding | alpha | — | note + 70 | QUARANTINE ×2 (seeds both fingerprints) |
| Single sighting | delta | 1 source | 40 (+25) | **ALERT** — corroborated, no quarantine |
| Seeding | bravo | 1 → 2 sources | note + 70 | QUARANTINE ×2 |
| Warm start | charlie (fresh, no history) | 2 sources | 40 | **QUARANTINE** — `KNOWN THREAT (CONFIRMED BY EXCHANGE)` |
| Workload | charlie | threat-only store | 0 | IGNORE ×4, **0** new exchange records |

**The headline:** a fresh node with zero local history quarantines a
file that is locally ambiguous (alert-only) because two independent
nodes have already contained that exact payload. The exchange adds
cross-node memory; it never fires on legitimate work.

Run it:

```bash
python -m benchmark.exchange_simulation
# → prints the table above + writes benchmark/results/exchange_simulation_<ts>.json
```

Invariants are pinned by `tests/test_exchange_simulation.py`.

## What it is deliberately not

- **Not a standalone detector.** A fingerprint match alone can never
  quarantine a file that is otherwise clean. Detection still comes from
  the entropy/behaviour engine; the exchange *confirms* and
  *corroborates*.
- **Not the immutability story.** The blockchain log
  (`blockchain/connector.py`) remains the tamper-evident anchor for a
  node's *own* incidents. The exchange is the cross-node memory; in a
  real deployment it would be replicated and anchored to that chain.
- **Not a network in this lab.** One SQLite file plays the role of the
  shared store so several simulated nodes can genuinely see each
  other's writes. The API is written so the store can be swapped for a
  network backend without touching the decision logic.
