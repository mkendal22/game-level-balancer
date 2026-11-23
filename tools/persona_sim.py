"""Oyuncu tipleri (persona) ile bölüm analizi: her bölümü rastgele, acemi, dikkatsiz, ortalama, iyi ve usta
oyunculara oynatır. Her oyun için kazanma, hamle sayısı ve kaybedince kalan ürün ("az kalsın") kaydedilir.
Kurallar solve_level.Rules ile oyunla birebir aynı (sim_level.py'deki gibi). Yetenek/güçlendirme kullanılmaz.

python3 tools/persona_sim.py [ilk] [son] [çıktı.json]      (varsayılan 1 1000 data/analysis/personas.json)
python3 tools/persona_sim.py liste=4,8,15                  (yalnız bu bölümler, sonuç ekrana)"""
import json
import os
import random
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from solve_level import freeze  # noqa: E402
from sim_level import Sim  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")

# ad: (oyun sayısı, politika, beceri)
PERSONAS = {
    "rastgele": (30, "random", 0),
    "acemi": (30, "novice", 0),
    "dikkatsiz": (30, "skill", 0.15),
    "ortalama": (30, "skill", 1.0),
    "iyi": (24, "lookahead", 1.5),
    "usta": (16, "lookahead", 6.0),
}
NEAR = 0.2  # kaybedince ürünlerin en fazla bu kadarı (en az 6) kaldıysa "az kalsın"


def _items(st):
    n = len(st[1])
    for sh in st[0]:
        for row in sh:
            for e in row:
                if e:
                    n += 1
    return n


def play(sim, d, rng, policy, skill):
    R = sim.R
    st = (freeze([s["layers"] for s in d["shelves"]]),) + R.start()[1:]
    moves = 0
    while True:
        if st[2] >= len(R.custs):
            return True, moves, 0
        mv = R.moves(st)
        if not mv:
            r = R.stuck(st)
            if r is True:
                return True, moves, 0
            if r is False:
                return False, moves, _items(st)
            st = r
            continue
        if policy == "random":
            si, j = mv[rng.randrange(len(mv))]
            nst = R.take(st, si, j)
        elif policy == "novice":
            # banttaki bir çifti tamamlayan ürünü görürse alır, yoksa rastgele
            belt = st[1]
            pick = [(si, j) for si, j in mv if belt.count(_base(st[0][si][0][j])) == 2]
            si, j = (pick or mv)[rng.randrange(len(pick or mv))]
            nst = R.take(st, si, j)
        else:
            best = None
            for si, j in mv:
                e = st[0][si][0][j]
                cand = R.take(st, si, j)
                if cand is None:
                    sc = -999.0
                else:
                    sc = sim._value(cand) + (25 if cand[4] > st[4] else 0)
                    if "?" in e:
                        sc = sim._value(cand) * 0.3
                    if policy == "lookahead" and cand[2] < len(R.custs):
                        nxt = R.moves(cand)
                        if nxt:
                            look = -999.0
                            for s2, j2 in nxt[:24]:
                                c2 = R.take(cand, s2, j2)
                                if c2 is not None:
                                    look = max(look, sim._value(c2) + (25 if c2[4] > cand[4] else 0))
                            sc = sc * 0.4 + look * 0.6
                sc += rng.uniform(0, 12.0 / skill)
                if best is None or sc > best[0]:
                    best = (sc, cand)
            nst = best[1]
        if nst is None:
            return False, moves, _items(st)
        st = nst
        moves += 1


def _base(e):
    for i, ch in enumerate(e):
        if ch in "~?!*^$":
            return e[:i]
    return e


def persona_rate(d, name, runs=None, seed=1):
    """Tek bir oyuncu tipinin kazanma oranı (üretici, aday bölümü süzerken kullanır)."""
    r, policy, skill = PERSONAS[name]
    sim = Sim(d)
    rng = random.Random(seed * 7919 + sum(map(ord, name)))
    n = runs or r
    return sum(play(sim, d, rng, policy, skill)[0] for _ in range(n)) / n


def analyze(n):
    p = os.path.join(DATA, "level_%03d.json" % n)
    d = json.load(open(p))
    sim = Sim(d)
    total = sum(1 for s in d["shelves"] for l in s["layers"] for e in l if e)
    out = {"n": n, "tier": d.get("tier", ""), "kind": d.get("kind", ""), "items": total, "shelves": len(d["shelves"]),
           "types": len({_base(e) for s in d["shelves"] for l in s["layers"] for e in l if e}), "p": {}}
    for name, (runs, policy, skill) in PERSONAS.items():
        rng = random.Random(n * 7919 + sum(map(ord, name)))
        wins = 0
        near = 0
        moves = []
        lefts = []
        for _ in range(runs):
            ok, mv, left = play(sim, d, rng, policy, skill)
            wins += ok
            moves.append(mv)
            if not ok:
                lefts.append(left)
                near += left <= max(6, NEAR * total)
        losses = runs - wins
        out["p"][name] = {"win": round(wins / runs, 3), "moves": round(sum(moves) / len(moves), 1),
                          "near": round(near / losses, 3) if losses else None,
                          "left": round(sum(lefts) / len(lefts), 1) if lefts else None}
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0].startswith("liste="):
        for n in [int(x) for x in args[0][6:].split(",")]:
            r = analyze(n)
            print(n, r["tier"], {k: v["win"] for k, v in r["p"].items()})
        sys.exit()
    a = int(args[0]) if len(args) > 0 else 1
    b = int(args[1]) if len(args) > 1 else len([x for x in os.listdir(DATA) if x.startswith("level_")])
    dst = args[2] if len(args) > 2 else os.path.join(ROOT, "docs", "analysis", "personas.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    res = []
    with Pool(10) as pool:
        for i, r in enumerate(pool.imap(analyze, range(a, b + 1), chunksize=2)):
            res.append(r)
            if (i + 1) % 50 == 0:
                print("... %d/%d" % (i + 1, b - a + 1), flush=True)
    json.dump(res, open(dst, "w"), ensure_ascii=False)
    print("yazıldı:", dst, len(res))
