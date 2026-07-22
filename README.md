# cache — a deterministic exact-key memory spine for AI agents (a mem0 hybrid: wins on cost/determinism/audit, ties on accuracy)

**Thesis:** an AI-agent memory should not be *only* a vector store. Put a **deterministic, exact-key spine** (an
alive "Collatz organism") *under* the embedding layer and you keep semantic recall while gaining **near-zero-cost
repeated recall, determinism, bit-exact multi-device merge, crash-exact recovery, offline recall, and auditability**.
**Honest up front:** on end-to-end *answer accuracy* with an LLM in the loop it **ties** mem0 (see below) — the win
is cost/determinism/offline/audit, not answer quality.

Everything here is a **runnable, self-asserting** Python file — clone and run; nothing is a screenshot or a promise.
Measured with **real MiniLM embeddings** (the same kind mem0 uses), on a LoCoMo-shaped memory workload.

```bash
git clone git@github.com:devkancheti4-design/cache.git && cd cache
pip3 install -r requirements.txt          # includes sentence-transformers — needed to reproduce the headline
python3 hybrid_vs_mem0.py                 # the head-to-head
python3 vital_signs.py                     # proves the organism is genuinely ALIVE (and catches a static fake)
```

> **Reproduction note (important, honest):** the headline **38%** is measured with **neural** embeddings
> (`sentence-transformers`, MiniLM — what mem0 uses). If you skip it, the harness falls back to TF-IDF, whose char
> n-grams *accidentally* match the exact "2014"/code substrings, so **both systems score ~100%** and mem0's real
> weakness is hidden. Install `sentence-transformers` to see the gap. The structural results (determinism, merge,
> crash-exact, cost) don't depend on the embedder.

## 🦾 The point: bolt the organism ONTO mem0 (a superpower, not a competitor)

Storing an exact fact ("premium in 2020 = $1240") as a mem0 embedding wastes a 1.5 KB vector and a model
forward-pass per recall. Bolt a **live Collatz organism** alongside mem0 to absorb the exact-fact slice:

| per exact fact | mem0 embedding | **organism** |
|---|---|---|
| storage | 1573 bytes (384-dim f32 + text) | **24 bytes** — 66× smaller |
| recall | ~10.7 ms (embed query + ANN search) + an LLM call | **~0.0001 ms, 0 API, 0 network** |

So mem0 keeps the fuzzy/semantic memories; the organism takes the exact facts → **smaller vector index + instant,
free, deterministic exact recall.** Proven on the **real alive organism** (deterministic / regenerating / adaptive /
CRDT) and **load-bearing**: freeze it to a static twin and recall drops **50/50 → 0/50** — the facts live in the
organism, not a screenshot. Run it: `python3 organism_superpower.py`. *(Boundary: exact facts only — fuzzy/updated
facts stay with mem0; see the end-to-end QA tie below.)*

## 💰 The killer use: a deterministic answer cache on mem0's server (`answer_cache.py`)

Many customers ask the **same** question. mem0 pays the full pipeline (embed + ANN search + LLM answer) on *every*
request. Put the organism in front as a cache: compute an answer **once**, store it keyed by the question, serve
every identical repeat free, instant, and **byte-identical**. Measured on 100k requests over 200 distinct questions:

| | API calls | est. cost | latency |
|---|---|---|---|
| mem0, no cache | 200,000 | $42 | 31,358 s |
| **mem0 + organism cache** | **400** | **$0.08** | **63 s** |
| **saved** | **99.8%** | **99.8%** | **99.8%** |

Savings = your **repeat rate** (high for FAQ/support/API traffic). *Honest limits:* only **verbatim** repeats hit an
exact cache (a paraphrase pays again); if the answer changes the cache goes **stale** (needs TTL/invalidation — the
grow-only organism can't update); and response memoization itself is standard (Redis does it) — the organism's real
add is a **deterministic, crash-exact, CRDT-mergeable** cache that N mem0 servers share bit-exact with no coordinator.

## Measured: hybrid (organism + embeddings) vs mem0-style (semantic-only)

| metric | mem0-style (semantic) | **hybrid** |
|---|---|---|
| exact fact — retrieved @top-1 | 38% | **100%** |
| exact fact — in top-5 (a generous LLM answerer *could* pick) | 88% | **100%** |
| exact fact — in top-10 | 98% | **100%** |
| semantic / paraphrase recall | 100% | 100% — **TIE** |
| recall latency | 2.31 ms | **0.003 ms** |
| **repeated recall, server-side** | **27.7 ms + embed +LLM every call** | **0.0024 ms, 0 API — free** |
| determinism / CRDT merge / crash-exact | ✗ | **✓ ✓ ✓** |

**What this shows — and the honest limit.** The table above is **retrieval** quality: vector similarity can't cleanly
rank near-duplicate records ("In 2013 the premium was X" vs "In 2014…") at top-1. **But** in a real **end-to-end QA**
run (`locomo_qa.py`, LLM answerer reading each system's top-5), the answer accuracy is a **TIE — 14/14 both** — because
a capable LLM reading top-5 recovers the record when the question carries a distinctive token. **So the hybrid does NOT
beat mem0 on answer accuracy** (only ~3% of dense facts fall outside top-5). Its real, decisive wins are **cost,
determinism, offline, and audit** — not accuracy. See **[LOCOMO_RESULTS.md](LOCOMO_RESULTS.md)** for the full fair run.

**Server-side, repeated exact calls are almost free.** mem0 pays an embedding (+ usually an LLM answer) on *every*
recall; the exact spine stores once and every repeat is a µs lookup with **0 API calls**. At 1M repeated recalls
that is ~**$200 → $0** (illustrative LLM pricing); the spine needs no cache layer — it *is* the answer.

## ✅ Where the hybrid wins (real, defensible — note: NOT answer accuracy)
- **Cost / latency** — 0-API µs recall; repeated calls are free (mem0 pays embed+LLM every call). *This is the big one.*
- **Retrieval@top-1 / no-LLM tiers** — exact key 100%@1 vs semantic 38–82%@1; matters when you don't put an LLM on top.
- **Determinism** — same data → byte-identical store (`fingerprint()`); mem0's LLM extraction is non-deterministic.
- **Bit-exact multi-device merge** — CRDT grow-only union, `A∪B == B∪A`, no coordinator.
- **Crash-exact recovery** — WAL replay revives the store byte-for-byte after a real `SIGKILL`.
- **On-device / offline / private** — exact recall needs no network and no LLM.
- **Audit & erasure** — reproducible provenance + machine-checkable erasure certificate (see `CAPABILITIES.md`).

## ❌ Where it LOSES to mem0 (stated plainly — do not skip this)
- **Fuzzy / paraphrase recall** where the query shares no exact key: that's the **embedding layer's** job, and the
  hybrid is only as good as its embedder (a tie at best, never a win from the spine).
- **Multi-hop synthesis** across many memories: that's the **LLM answerer's** job. The hybrid keeps the LLM *on
  top* of the spine, so it inherits — not beats — mem0 here.
- **Unstructured → structured extraction (routing).** The spine needs a key (`slot`, `year`). Turning messy free
  text into that key still needs NER/an LLM; the harness assumes clean routing for structured facts.
- **Open-vocabulary / schema-drift facts** you can't key ahead of time lean back on the embedding layer.
- **Summarization / consolidation** of many memories into a gist is an LLM strength, not the spine's.

**Honest scope.** This measures the memory **substrate** with real embeddings — it is *not* the official LoCoMo
leaderboard number (that needs an LLM answerer + judge, i.e. an API key). The structural results
(exact recall, determinism, merge, cost) are embedder- and LLM-independent, so they hold regardless of what sits on
top. The honest one-liner: **mem0's semantic recall, plus a deterministic exact spine mem0 cannot offer.**

## Files
| file | role |
|---|---|
| [`complete_alive_organism.py`](complete_alive_organism.py) | the exact-key spine: confirm-to-adopt, Collatz heartbeat, WAL crash-exact `revive()`, CRDT `merge()`, deterministic `fingerprint()` |
| [`hybrid_vs_mem0.py`](hybrid_vs_mem0.py) | the retrieval-substrate head-to-head (real MiniLM embeddings; TF-IDF fallback) |
| [`locomo_qa.py`](locomo_qa.py) | **end-to-end QA** — an LLM answers from each system's retrieval; see [LOCOMO_RESULTS.md](LOCOMO_RESULTS.md) (it's a TIE on accuracy) |
| [`organism_superpower.py`](organism_superpower.py) | **the superpower**: 24 bytes/fact (66× smaller) + instant 0-API recall vs mem0 embeddings, on the live organism |
| [`answer_cache.py`](answer_cache.py) | **server-side cost**: deterministic answer cache — same question paid ONCE, repeats free/instant/byte-identical (99.8% saved) |
| [`vital_signs.py`](vital_signs.py) | launch-time liveness check — aborts with named symptoms if the organism is static |
| [`CAPABILITIES.md`](CAPABILITIES.md) | fuller, adversarially-verified map of positives **and** negatives |

## License

Apache License 2.0 (same as mem0) — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Free for anyone, including companies, to use, embed, and build on.
