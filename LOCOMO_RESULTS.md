# LoCoMo-style end-to-end QA — the FAIR result (and an honest correction)

Run it: `python3 locomo_qa.py` (writes the retrieved contexts + a held-out truth file), then an LLM answers each
question **only from what each system retrieved**, and it's scored. Here the **LLM answerer was the agent (Claude)** —
no API key needed. The organism is proven alive on the memory (deterministic / regenerating / adaptive) in every run.

## The result

**End-to-end QA accuracy (LLM reads each system's top-5):**

| | mem0-style (semantic) | hybrid (organism + embeddings) |
|---|---|---|
| 14 curated questions (exact, dense, temporal, semantic, multi-hop) | **14 / 14** | **14 / 14** — a **TIE** |

**At scale** — over all 77 structured facts, is the target record retrieved (= answerable by a perfect LLM)?

| | @top-1 | @top-5 | @top-10 |
|---|---|---|---|
| mem0-style | 82% | 97% | 100% |
| **hybrid (exact key)** | **100%** | **100%** | **100%** |

## The honest correction (read this)

The earlier headline **"38% vs 100%"** in the README is **retrieval@top-1**, *not* end-to-end QA accuracy. When you
give a capable LLM the **top-5** (which is what mem0 actually does) and the question carries a distinctive token
(a year, a city, "evening"), the right record is almost always in that window, so the **LLM recovers the answer** —
and the accuracy gap largely **collapses to a tie**. On this workload the hybrid did **not** beat mem0 on answer
accuracy; its only residual accuracy edge is the ~3% of dense facts that fall outside top-5 (and it grows with
record density — it was ~12% on the 5×-denser workload in `hybrid_vs_mem0.py`).

**So, fairly stated: the hybrid's value is NOT answer quality.** With an LLM in the loop, QA accuracy ties mem0.
The hybrid's decisive, measured wins are elsewhere:

- **Cost / latency** — 0 API calls, ~0.002 ms per exact recall, vs mem0's embed (+ usually an LLM) on *every* call
  (measured 8.9–27.7 ms). At high QPS or repeated recall this is the real prize, and it's large.
- **Determinism** — byte-identical store & fingerprint; mem0's LLM write path is non-deterministic.
- **Offline / on-device / private** — exact recall with no model and no network (mem0's default recall is neural).
- **Audit & erasure** — reproducible provenance and a machine-checkable erasure certificate (see `CAPABILITIES.md`,
  with its honest caveats).
- **Retrieval@1** — if you *don't* put an LLM on top (a cheap, latency-critical tier), the exact key answers at
  100%@1 where semantic-only is 82%@1 here (38%@1 at high density).

## Bottom line
**Choose the hybrid for cost, determinism, offline, and audit — not for answer accuracy.** On end-to-end QA with a
capable LLM answerer, it *ties* mem0. That is the fair result, stated plainly so nobody is misled.
