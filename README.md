# cache — a deterministic exact-key memory spine for AI agents (a hybrid that beats mem0 where it matters)

**Thesis:** an AI-agent memory should not be *only* a vector store. Put a **deterministic, exact-key spine** (an
alive "Collatz organism") *under* the embedding layer and you keep semantic recall **and** gain exact factual
recall, determinism, bit-exact multi-device merge, crash-exact recovery, and near-zero-cost repeated recall.

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
- **Cost / latency at scale** — 0-API µs recall; repeated calls are free.
- **On-device / offline / private** — exact recall needs no network and no LLM.

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
| [`vital_signs.py`](vital_signs.py) | launch-time liveness check — aborts with named symptoms if the organism is static |
| [`CAPABILITIES.md`](CAPABILITIES.md) | fuller, adversarially-verified map of positives **and** negatives |
