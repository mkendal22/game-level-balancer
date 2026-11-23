"""Zorluk ölçer: sezgisel bir oyuncu bölümü yeteneksiz N kez oynar, kazanma oranını verir.
Kurallar solve_level.Rules ile aynı (oyunla birebir). Oyuncu poşetin içini bilmez, sürpriz kolinin
arkasını görmez; çürüyen ürünü sayacı azaldıkça önceler.
python3 tools/sim_level.py data/level_01.json [N]"""
import json
import random
import sys

from solve_level import Rules, base, ice, rot, freeze


class Sim:
    def __init__(self, d):
        self.d = d
        self.R = Rules(d)
        if d.get("belt"):
            self.R.belt0 = int(d["belt"])

    def _value(self, st):
        """Oyuncunun gördüğüyle durum değeri: bant doluluğu kötü, tamamlanabilir çiftler iyi."""
        sh, belt, ci, rem, m, kg, _b, rl = st
        R = self.R
        vis = {}
        danger = 0.0
        for si, s in enumerate(sh):
            if not s or not R.is_open(si, m, ci, kg):
                continue
            for e in s[0]:
                if e and ice(e) == 0 and "?" not in e:
                    vis[base(e)] = vis.get(base(e), 0) + 1
                if e and rot(e) > 0 and ice(e) == 0:
                    danger += 3.0 / rot(e)
            if len(s) > 1 and not R.hides[si]:
                for e in s[1]:
                    if e and "?" not in e:
                        vis[base(e)] = vis.get(base(e), 0) + 0.4
        cap = R.belt0 - len(rl)
        v = -(len(belt) + (R.belt0 - cap)) ** 1.6 * 2.0 - danger * 4.0
        for t in set(belt):
            c = belt.count(t)
            if vis.get(t, 0) >= 3 - c:
                v += 6 * c
            else:
                v -= 3
        return v + ci * 40 + m * 3

    def play(self, rng, skill=1.0):
        R = self.R
        st = (freeze([s["layers"] for s in self.d["shelves"]]),) + R.start()[1:]
        moves = 0
        while st[2] < len(R.custs):
            mv = R.moves(st)
            if not mv:
                r = R.stuck(st)
                if r is True or r is False:
                    return r, moves
                st = r
                continue
            best = None
            for si, j in mv:
                e = st[0][si][0][j]
                nst = R.take(st, si, j)
                if nst is None:
                    sc = -999.0
                else:
                    matched = nst[4] > st[4]
                    if "?" in e:
                        sc = self._value(nst) * 0.3 + rng.uniform(-4, 4)
                    else:
                        sc = self._value(nst) + (25 if matched else 0)
                    if rot(e) > 0:
                        sc += 8.0 / rot(e)
                sc += rng.uniform(0, 12.0 / skill)
                if best is None or sc > best[0]:
                    best = (sc, si, j, nst)
            if best is None or best[3] is None:
                return False, moves
            st = best[3]
            moves += 1
        return True, moves


def win_rate(d, n=60, seed=1, skill=1.0):
    sim = Sim(d)
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        ok, _ = sim.play(rng, skill)
        wins += ok
    return wins / n


def random_rate(d, n=60, seed=7):
    """Tamamen rastgele dokunan oyuncu (yalnız geçerli bir öne dokunur): bölüm düşünmeden bitiyor mu?"""
    sim = Sim(d)
    R = sim.R
    rng = random.Random(seed)
    wins = 0
    for _ in range(n):
        st = (freeze([s["layers"] for s in d["shelves"]]),) + R.start()[1:]
        ok = None
        while ok is None:
            if st[2] >= len(R.custs):
                ok = True
                break
            mv = R.moves(st)
            if not mv:
                r = R.stuck(st)
                if r is True or r is False:
                    ok = r
                    break
                st = r
                continue
            si, j = mv[rng.randrange(len(mv))]
            nst = R.take(st, si, j)
            if nst is None:
                ok = False
                break
            st = nst
        wins += bool(ok)
    return wins / n


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    print("kazanma: %.0f%%" % (win_rate(d, n) * 100))
