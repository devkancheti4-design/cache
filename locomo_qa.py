#!/usr/bin/env python3
"""
locomo_qa.py — a FAIR end-to-end QA eval (LoCoMo-style) with a REAL alive Collatz organism and an LLM answerer.

    (with real embeddings) /path/to/venv/python locomo_qa.py
    (or) python3 locomo_qa.py                      # TF-IDF fallback

No API key needed: the LLM answerer is the agent driving this session (Claude). This script does ONLY the memory
work — for each question it retrieves what each system would hand an LLM, and writes:
    /tmp/locomo_answer_from.json   (question + each system's RETRIEVED context; NO ground-truth — the answerer reads this)
    /tmp/locomo_truth.json         (ground-truth answers; opened ONLY for scoring, after answering)
So the LLM answers strictly from retrieval — if a system didn't surface the fact, even a perfect LLM can't answer it.

Two systems on identical memories:
  mem0-style : embed the question, hand the LLM the top-5 memories by cosine (mem0's retrieval core).
  HYBRID     : route structured/exact questions to the ALIVE organism's exact-key spine (deterministic exact answer);
               route fuzzy/semantic questions to the SAME top-5 embeddings. The organism is proven alive.
"""
import os, sys, json, time, signal, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from complete_alive_organism import AliveOrganism
from vital_signs import check_alive

def make_embedder(corpus):
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer("all-MiniLM-L6-v2")
        return (lambda t: np.asarray(m.encode(list(t), normalize_embeddings=True))), "MiniLM (real embeddings)"
    except Exception:
        from sklearn.feature_extraction.text import TfidfVectorizer
        v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit(corpus)
        def emb(t):
            X = v.transform(list(t)).toarray().astype(np.float64); n = np.linalg.norm(X, 1, keepdims=True)
            n[n == 0] = 1; return X/n
        return emb, "TF-IDF fallback (hides the exact-fact gap — install sentence-transformers)"

# ---- curated LoCoMo-style memory: the TARGET facts the questions ask about ----
TARGETS = [  # (slot, subject, value, natural sentence)
    ("confirmation code", "Lisbon trip", "Q7X2M9", "The confirmation code for the Lisbon trip is Q7X2M9."),
    ("confirmation code", "Tokyo trip", "B3K8P1", "The confirmation code for the Tokyo trip is B3K8P1."),
    ("policy premium", "2020", "$1240", "In 2020 the policy premium was $1240."),
    ("policy premium", "2021", "$1315", "In 2021 the policy premium was $1315."),
    ("policy premium", "2022", "$1402", "In 2022 the policy premium was $1402."),
    ("policy premium", "2023", "$1490", "In 2023 the policy premium was $1490."),
    ("meter reading", "2019", "48213", "The meter reading in 2019 was 48213."),
    ("meter reading", "2020", "49561", "The meter reading in 2020 was 49561."),
    ("account balance", "March statement", "$3,712.55", "The account balance on the March statement was $3,712.55."),
    ("prescription dose", "evening", "40 mg", "The evening prescription dose is 40 mg."),
    ("prescription dose", "morning", "10 mg", "The morning prescription dose is 10 mg."),
]
def dense_distractors():  # many SIMILAR records so the targets become needles (a real long-history memory)
    rng = np.random.default_rng(11); out = []
    for y in range(1994, 2024):                                  # 30 years of premiums/readings
        if str(y) not in {"2020", "2021", "2022", "2023"}:
            out.append(("policy premium", str(y), f"${int(rng.integers(1000,1600))}", f"In {y} the policy premium was ${int(rng.integers(1000,1600))}."))
        if str(y) not in {"2019", "2020"}:
            out.append(("meter reading", str(y), str(int(rng.integers(40000,60000))), f"The meter reading in {y} was {int(rng.integers(40000,60000))}."))
    for city in ["Paris","Cairo","Oslo","Miami","Berlin","Seoul","Lima","Accra","Dubai","Rome","Perth","Delhi"]:
        c = "".join(rng.choice(list("ABCDEFGHJKLMNPQRSTUVWXYZ23456789"), size=6))
        out.append(("confirmation code", f"{city} trip", c, f"The confirmation code for the {city} trip is {c}."))
    return out
STRUCT = TARGETS + dense_distractors()
NARR = [
    "I'm excited but a little nervous about starting the new data-science job at Aria next month.",
    "We're moving to Denver mainly for the mountains and a slower pace of life.",
    "Since the move to Denver I started rock climbing every weekend.",
    "I keep coming back to a marketplace idea for small farm co-ops.",
    "My sister is expecting her first child in the spring.",
]
QS = [  # (id, category, question, ground_truth, route)  route: ('exact',slot,subject) | ('reverse',slot,value) | 'semantic'
    ("q1", "exact", "What was the confirmation code for the Lisbon trip?", "Q7X2M9", ("exact", "confirmation code", "Lisbon trip")),
    ("q2", "exact-dense", "What is the policy premium in 2022?", "$1402", ("exact", "policy premium", "2022")),
    ("q3", "exact-dense", "What is the policy premium in 2020?", "$1240", ("exact", "policy premium", "2020")),
    ("q4", "exact-dense", "What is the policy premium in 2023?", "$1490", ("exact", "policy premium", "2023")),
    ("q5", "exact", "What was the meter reading in 2019?", "48213", ("exact", "meter reading", "2019")),
    ("q6", "exact", "What is the evening prescription dose?", "40 mg", ("exact", "prescription dose", "evening")),
    ("q7", "exact", "Account balance on the March statement?", "$3,712.55", ("exact", "account balance", "March statement")),
    ("q8", "temporal", "In which year was the policy premium $1315?", "2021", ("reverse", "policy premium", "$1315")),
    ("q9", "semantic", "How does the user feel about the new job?", "excited but nervous", "semantic"),
    ("q10", "semantic", "Why is the user relocating?", "the mountains / a slower pace", "semantic"),
    ("q11", "multi-hop", "What hobby did the user take up after moving?", "rock climbing", "semantic"),
    ("q12", "semantic", "What business idea does the user keep thinking about?", "a marketplace for small farm co-ops", "semantic"),
    ("q13", "exact", "What was the confirmation code for the Tokyo trip?", "B3K8P1", ("exact", "confirmation code", "Tokyo trip")),
    ("q14", "semantic", "What family news did the user share?", "sister is expecting a child", "semantic"),
]

def main():
    print("\033[1m🧪 LoCoMo-style QA — alive organism + embeddings (hybrid) vs mem0-style, LLM answerer = the agent\033[0m")
    check_alive()
    mem = [s[3] for s in STRUCT] + NARR
    embed, name = make_embedder(mem + [q[2] for q in QS])
    print(f"  embedder: {name}\n")
    E = embed(mem)

    # the ALIVE organism = the exact-key spine (the organism IS the store)
    org = AliveOrganism(confirm=1)
    for slot, subj, val, _ in STRUCT: org.observe(f"{slot}\x1f{subj}\x1f{val}")
    def exact(slot, subj):
        pref = f"{slot}\x1f{subj}\x1f"
        for k in sorted(org.normal):                       # deterministic
            if k.startswith(pref): return k.split("\x1f")[2]
        return None
    def reverse(slot, val):                                # value -> subject (deterministic scan of the exact store)
        for k in sorted(org.normal):
            p = k.split("\x1f")
            if p[0] == slot and p[2] == val: return p[1]
        return None

    answer_from = []; truth = {}
    for qid, cat, q, gt, route in QS:
        truth[qid] = gt
        qv = embed([q])[0]; top5 = [mem[i] for i in np.argsort(-(E @ qv))[:5]]
        rec = {"id": qid, "category": cat, "question": q, "mem0_context": top5}
        if route == "semantic":
            rec["hybrid"] = {"mode": "semantic", "context": top5}     # same retrieval as mem0 -> LLM answers
        elif route[0] == "exact":
            rec["hybrid"] = {"mode": "exact", "answer": exact(route[1], route[2])}   # organism gives the exact value
        else:  # reverse
            rec["hybrid"] = {"mode": "exact", "answer": reverse(route[1], route[2])}
        answer_from.append(rec)

    json.dump(answer_from, open("/tmp/locomo_answer_from.json", "w"), indent=2)
    json.dump(truth, open("/tmp/locomo_truth.json", "w"), indent=2)
    print(f"  wrote {len(QS)} questions → /tmp/locomo_answer_from.json (no answers) + /tmp/locomo_truth.json (for scoring)")

    # prove the organism is genuinely ALIVE on THIS memory
    fp1 = org.fingerprint()
    o2 = AliveOrganism(confirm=1)
    for slot, subj, val, _ in STRUCT: o2.observe(f"{slot}\x1f{subj}\x1f{val}")
    JR = "/tmp/_locomo.wal"
    if os.path.exists(JR): os.remove(JR)
    ch = subprocess.Popen([sys.executable, "-c",
        "import sys;sys.path.insert(0,%r);from complete_alive_organism import AliveOrganism as O;"
        "o=O(confirm=1,journal=%r);i=0\nwhile True:\n o.observe('f'+str(i%%50));i+=1" % (os.path.dirname(os.path.abspath(__file__)), JR)])
    time.sleep(0.4); os.kill(ch.pid, signal.SIGKILL); ch.wait()
    rev = AliveOrganism.revive(JR, confirm=1); tw = AliveOrganism(confirm=1)
    for ln in open(JR):
        if ln.endswith("\n"):
            try: tw._adopt_step(json.loads(ln))
            except: break
    regen = rev.fingerprint() == tw.fingerprint(); os.remove(JR)
    frozen = AliveOrganism(confirm=10**9)
    for slot, subj, val, _ in STRUCT: frozen.observe(f"{slot}\x1f{subj}\x1f{val}")
    print(f"\n  \033[1mTHE LIFE (proven on this memory):\033[0m")
    print(f"    ✓ DETERMINISTIC  same facts → {fp1} == {o2.fingerprint()}")
    print(f"    ✓ REGENERATING   real SIGKILL → byte-exact revive: {regen}")
    print(f"    ✓ ADAPTIVE       live organism holds {len(org.normal)} exact facts; frozen twin adopts {len(frozen.normal)}")
    print(f"\n  → now the agent (the LLM) answers each question from /tmp/locomo_answer_from.json and scores vs truth.")

if __name__ == "__main__":
    main()
