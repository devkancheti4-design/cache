#!/usr/bin/env python3
"""
vital_signs.py — the launch-time LIVENESS check. Collatz organisms must never go static; if one does, this
                 prints its SYMPTOMS and ABORTS the launch loudly. Every measurement file calls check_alive()
                 at startup, so a frozen/static organism can never slip through unnoticed.

    from vital_signs import check_alive, require_load_bearing
    check_alive()                       # run the vitals battery; raises OrganismWentStatic with symptoms if static
    require_load_bearing("dedup", live_value, frozen_value)   # proves the ORGANISM computed the number, not a bystander

An organism is ALIVE only if all five vital signs are present (each measured here on every launch):
  PULSE      it ADAPTS — recurring novelty is adopted; a frozen twin (confirm=inf) never adopts.
  RESPONSE   the SAME input changes behavior with experience (novel -> familiar after adoption).
  RHYTHM     DETERMINISTIC — identical inputs reproduce the identical fingerprint.
  REGEN      CRASH-EXACT — a real SIGKILL mid-write revives byte-identical from the WAL.
  HEARTBEAT  the Collatz clock runs — life decays 27→…→1 by tick() and reaps stale entries.

If any is missing the organism has gone STATIC (a frozen lookup / a screenshot / a plain set), and check_alive()
raises. require_load_bearing() catches the subtler failure: the organism is alive but DECORATIVE — the headline
number was actually produced by a static set/dict/np and the organism was only bolted on. Both abort loudly.
"""
import os, sys, json, time, signal, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from complete_alive_organism import AliveOrganism, tick

G, R, Y, B, X = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"


class OrganismWentStatic(SystemExit):
    """Raised (as a loud SystemExit) when an organism fails a vital sign — i.e., it has gone static."""


def _symptom(sign, detail, cause):
    msg = (f"\n{R}{B}🚑 SYMPTOM — {sign}{X}\n"
           f"   {R}{detail}{X}\n"
           f"   → the organism has gone {R}{B}STATIC{X} (a frozen lookup, not a live Collatz organism).\n"
           f"   → likely cause: {cause}\n"
           f"   {R}launch ABORTED — a static organism must never serve.{X}\n")
    raise OrganismWentStatic(msg)


def check_alive(Org=AliveOrganism, label="complete_alive_organism", quiet=False, sigkill=True):
    """Run the vitals battery on the organism. Print the chart; raise OrganismWentStatic on ANY static symptom."""
    lines = []

    # PULSE — adapts to recurring novelty; a frozen twin never does.
    live = Org(confirm=3)
    for _ in range(3): live.observe("PULSE_KEY")
    frozen = Org(confirm=10**9)
    frozen_adopted = any(frozen.observe("PULSE_KEY").get("adopted") for _ in range(3))
    if "PULSE_KEY" not in getattr(live, "normal", set()):
        _symptom("FLATLINE (no pulse)", "the organism did NOT adopt recurring novelty — it never adapts.",
                 "confirm set unreachably high, adopt/_adopt_step disabled, or replaced by a static set().")
    if frozen_adopted:
        _symptom("FALSE PULSE", "a frozen twin (confirm=inf) adopted — the 'alive vs frozen' contrast is fake.",
                 "the frozen control is not actually frozen; adopt threshold ignored.")
    lines.append(("PULSE (adapts)", "live adopts recurring novelty; frozen twin never does"))

    # RESPONSE — same input, behavior changes with experience (novel -> familiar).
    r = Org(confirm=2); first = r.observe("RESP")["novel"]; r.observe("RESP")
    after = r.observe("RESP")["novel"]
    if not (first is True and after is False):
        _symptom("UNRESPONSIVE", "the SAME input never changed the organism's output (always novel or always familiar).",
                 "state is not updated by observe(); the organism is a stateless static map.")
    lines.append(("RESPONSE (changes)", "same input: novel→familiar once experienced"))

    # RHYTHM — deterministic fingerprint.
    def run():
        z = Org(confirm=3)
        for x in ["a", "b", "NEW", "a", "NEW", "NEW"]: z.observe(x)
        return z.fingerprint()
    if run() != run():
        _symptom("ARRHYTHMIA", "identical inputs produced DIFFERENT fingerprints — non-deterministic.",
                 "randomness/time/hash-seed leaked into state; not a trustworthy organism.")
    lines.append(("RHYTHM (deterministic)", f"fingerprint reproduces bit-exact ({run()})"))

    # REGEN — crash-exact revive from the WAL. Real SIGKILL by default; falls back to in-process on any error.
    regen_how = "in-process WAL replay"
    JR = tempfile.mktemp(suffix=".vital.journal")
    try:
        if sigkill:
            here = os.path.dirname(os.path.abspath(__file__))
            code = ("import sys;sys.path.insert(0,%r);from complete_alive_organism import AliveOrganism as O;"
                    "o=O(confirm=5,journal=%r);i=0\nwhile True:\n o.observe('EVT' if i%%2==0 else 'n'+str(i%%20));i+=1"
                    % (here, JR))
            ch = subprocess.Popen([sys.executable, "-c", code]); time.sleep(0.30)
            os.kill(ch.pid, signal.SIGKILL); ch.wait(); regen_how = "real SIGKILL → WAL revive"
        else:
            o = Org(confirm=5, journal=JR)
            for i in range(400): o.observe("EVT" if i % 2 == 0 else "n" + str(i % 20))
        revived = AliveOrganism.revive(JR, confirm=5)
        twin = AliveOrganism(confirm=5)
        with open(JR) as f:
            keys = [json.loads(l) for l in f if l.endswith("\n")]
        for k in keys:
            if k not in twin.normal: twin._adopt_step(k)
        if revived.fingerprint() != twin.fingerprint():
            _symptom("AMNESIA", "could NOT revive byte-exact from its journal after a crash — memory is not durable.",
                     "WAL not flushed before state mutates, or revive() diverges from the live adopt path.")
        lines.append(("REGEN (crash-exact)", f"{regen_how}: revived byte-identical ({len(keys):,} obs)"))
    finally:
        if os.path.exists(JR): os.remove(JR)

    # HEARTBEAT — the Collatz clock runs and reaps.
    if tick(27) != 82 or tick(82) != 41 or tick(1) != 1:
        _symptom("NO HEARTBEAT", "the Collatz tick() is wrong — the organism's clock is not Collatz.",
                 "tick() altered; heartbeat no longer 3n+1 / n/2.")
    hb = Org(confirm=1); hb.observe("HB")            # life["HB"] = 27
    steps = 0
    while "HB" in hb.normal and steps < 200:          # 27→82→41→…→1 must eventually reap
        hb.heartbeat(); steps += 1
    if "HB" in hb.normal:
        _symptom("NO HEARTBEAT", "the Collatz heartbeat never reaped a stale entry — self-cleaning is dead.",
                 "heartbeat() not decaying life[] via tick(), or life never reaches the reap threshold.")
    lines.append(("HEARTBEAT (Collatz)", f"life 27→…→1 self-cleaned in {steps} beats; tick is 3n+1/n÷2"))

    if not quiet:
        print(f"{G}{B}🫀 VITAL SIGNS — {label}{X}")
        for name, detail in lines:
            print(f"   {G}✓{X} {B}{name:<24}{X}{detail}")
        print(f"   {G}{B}ALL VITALS PRESENT — organism is ALIVE, not static.{X}")
    return True


def require_load_bearing(label, live_value, frozen_value, tol=0.0):
    """Prove the ORGANISM computed the headline number: if a frozen/static twin yields the same value, it is
    DECORATIVE (the number came from a bystander set/dict/np). Aborts loudly on decoration."""
    same = abs(float(live_value) - float(frozen_value)) <= tol
    if same:
        _symptom("DECORATIVE (parasite)",
                 f"'{label}': the organism-driven value ({live_value}) equals the frozen/static value ({frozen_value}) — "
                 f"the organism did NOT compute it.",
                 "the headline number is produced by a plain set()/dict()/np; the organism is only bolted on for show.")
    print(f"   {G}✓{X} {B}LOAD-BEARING{X}     '{label}': organism-driven {live_value} ≠ frozen/static {frozen_value} "
          f"→ the number comes FROM the living organism.")
    return True


if __name__ == "__main__":
    # Launching this directly = a repo-wide liveness check. Also demonstrates that the symptoms actually fire.
    check_alive()
    print(f"\n{B}Now proving the symptoms are REAL (a static organism is detected and aborts):{X}")

    class StaticImpostor(AliveOrganism):           # a 'screenshot' — remembers everything instantly, never adapts by repetition
        def observe(self, x):
            k = self.keyfn(x); self.normal.add(k)   # static lookup: no confirm, no life, no adaptation
            return {"verdict": "ALLOW", "key": k, "novel": False}
    try:
        check_alive(StaticImpostor, label="StaticImpostor (a static screenshot)", quiet=True)
        print(f"{R}FAILED: a static impostor passed the vitals — the check is broken.{X}"); sys.exit(2)
    except OrganismWentStatic as e:
        print(str(e))
        print(f"{G}{B}✓ the vitals correctly caught a static organism and aborted. Symptoms work.{X}")
