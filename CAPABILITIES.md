# Capabilities — positives and negatives (adversarially verified)

Beyond the measured head-to-head in [README.md](README.md), a fan-out of probe agents proposed capabilities and a
second round of skeptic agents tried to **refute** each. Only what survived refutation is listed. Every item keeps
its **honest caveat** — the strongest true objection — because this is going to engineers who will test it.

## ✅ Positives that survived refutation

**1. Verifiable provenance / tamper-evidence.** From the append-only WAL + pinned config, an independent party
re-derives the byte-identical `fingerprint()`, points any recalled fact to the exact journaled line that justifies
it ("why recalled = exact-key match at line N", not a cosine rank), and detects out-of-band edits as fingerprint
divergence (caught 2/2). mem0 puts a **non-deterministic LLM in the write path**, so replaying the same inputs yields
a different memory set — no canonical state to hash, no per-input provenance.
*Caveat:* holds only in **observe-only, heartbeat-OFF, config-pinned** mode; heartbeat self-clean mutations are not
journaled, so if the Collatz heartbeat runs, the replay guarantee breaks.

**2. Point-in-time snapshot / rollback.** The write path is a pure deterministic function of the key sequence, so
the exact global state as of any past observe-index N is reconstructable and sha256-verifiable from the raw WAL.
*Caveat:* **not novel** — this is textbook event-sourcing (Datomic asOf, git, XTDB); a ~20-line op-logged vector
store replays too. The edge is that you get it *for free and deterministically*, not that only this can do it.

**3. Write-integrity against an adversary.** `observe` and `merge` are grow-only unions and pinned L3 rules are
checked before `normal`, exempt from heartbeat, and never removed by merge — so an attacker can at most **append**
a colliding value; they cannot silently overwrite or delete a legitimate memory or strip a pinned rule. mem0's
LLM-managed ADD/UPDATE/DELETE write path is the published **MINJA** memory-injection lever — it *can* silently
overwrite with no forensic trace. *Caveat:* the shipped reader can still *return* an injected colliding value on a
conflicted key (see Negative 1); the guarantee is "the original truth is preserved & auditable", not "the reader
always returns it".

**4. Machine-checkable erasure certificate (GDPR).** For a fact stored as an exact key, deletion yields a
deterministic proof: membership `→ False` plus a fingerprint an auditor independently recomputes as
`fp(corpus − fact)`. mem0's non-deterministic extraction scatters one disclosure across paraphrased vectors and can
only offer a similarity score — it can never *prove absence*. *Caveat:* the proof covers the **adopted** set; with
`confirm > 1` a secret still in the pending counter isn't covered, and anything already embedded elsewhere isn't.

**5. Zero-dependency, no-network exact recall.** The pure-stdlib exact spine recalls 100% with **0 model inferences
and 0 bytes leaving the device**; mem0's default retrieval is irreducibly neural (must embed the query), so under a
strict "no model, no network" sandbox it recalls 0%. *Caveat:* this is specifically vs **mem0's neural retrieval** —
a model-free BM25 lexical retriever also works offline, so it's not an advantage over *all* retrieval.

## ❌ Negatives that survived refutation (do not skip these)

**1. No UPDATE / supersession — grow-only store keeps contradictions.** `merge` is a grow-only G-Set
(`self.normal |= other.normal`). When two agents write different values for the *same logical key*
(`premium|2020|OLD` vs a later `premium|2020|NEW` correction), the merge keeps **both**, and `fingerprint()` (which
sorts) reports an identical converged state on both devices **yet recall could differ** — the raw-`set` `lookup()`
was non-deterministic across processes (returned OLD or NEW by `PYTHONHASHSEED`). *We fixed the non-determinism
(sorted iteration), but the deeper gap stands:* the grow-only store has **no notion of "latest"**, so it cannot
supersede a stale value the way mem0's mutable UPDATE/DELETE can. *Caveat:* fixable by swapping the G-Set for a
deterministic **LWW-map CRDT** (logical-key → latest-by-clock) — but the shipped store does not do this.

**2. Fuzzy query about an updated fact → can lose to mem0.** On a paraphrase (no exact key), the spine is inert
(`lookup → None`) and the hybrid degrades to a bare vector store holding **both** the stale and current mention with
no currency signal; the embedder can rank the stale one #1. mem0's write-time LLM consolidation collapses the two
into one current fact. *Caveat:* "can lose," not "always" — it's phrasing-dependent and not proven end-to-end here.

**3. Open-vocabulary facts that also drift over time.** When the attribute name is open-vocabulary (no canonical
key) **and** the fact updates/contradicts over time, mem0's per-write LLM consolidates by *meaning* — a mechanism
the meaning-blind spine lacks entirely, with no cheap fix that preserves determinism/0-API/exact-recall
(canonicalizing open vocab needs an LLM/embedding write path, i.e. it becomes mem0).

**4. Aliased keys → the flagship advantage evaporates to parity.** When the key arrives as an open-vocab **synonym**
("PNR" / "booking reference" for "confirmation code"), the exact spine matches **0%** (a byte-changed key can't
`startswith`-match), and neither an edit-distance normalizer nor an enumerated alias table rescues it. The only
recourse is to fall back to the same vector store mem0 uses — at which point the hybrid performs at **exactly mem0's
level**. So the headline "100% vs 38%@1" is **query-class-specific**: on aliased keys the spine adds zero and can at
best tie. mem0 gets alias robustness free from its embedder.

## Claims that did NOT survive (honest discards)
- "Silent extraction errors on drifted input" — refuted: the failure is not silent and not spine-specific.
- "Cannot consolidate a stream into a compact gist" — folded into Negative 3; as stated it was overbroad.
- "On multi-hop the spine adds nothing" — true but not a *loss* (the LLM answerer does multi-hop in both systems).

## Bottom line
The wins are **structural and real** where facts are **exact, keyed, and append-only** — audit, erasure proofs,
write-integrity, offline recall, determinism, free repeated recall. The losses are **also real** and all trace to
one root: the spine is **meaning-blind and grow-only** — so anything needing *supersession* or *open-vocabulary /
aliased / paraphrased* access falls back to (and cannot beat) the embedding layer. The honest product is a **hybrid
that adds a deterministic exact spine under mem0's embeddings** — not a replacement for them.
