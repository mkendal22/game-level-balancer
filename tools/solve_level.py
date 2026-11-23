"""Level çözülebilir mi? DFS ile kontrol eder. Kurallar oyunla (scripts/game.gd) birebir:
kilit, panjur, donuk ürün, poşet, anahtarlı kasa, terazili kasa, döner kasa, joker (+ dengeleme),
zincirli kasa, konveyör kasa, çürüyen ürün (!n), bomba meyve (*), kavanoz (^), fiyat etiketi ($),
taze sandık (refill), dondurucu dolap (freezer), asansör kasa (lift), martı (gull). sim_level.py de aynı Rules'u kullanır.
python3 tools/solve_level.py data/level_01.json [cozum.json]"""
import json
import sys
from collections import Counter

BELT = 7
MARKS = "~?!*^$"
ROT_MATCHES = 3
BOMB_RADIUS = 380.0
FREEZE_EVERY = 6     # dondurucu her 6 hamlede bir komşu ürünü dondurur
GULL_LAND = 6        # martı 6. hamlede bir ürünün üstüne konar
GULL_GRAB = 8        # 8. hamlede o ürünü kasanın en arkasına taşır (o arada alınmadıysa)


def base(e):
    i = 0
    while i < len(e) and e[i] not in MARKS:
        i += 1
    return e[:i]


def _num(e, mark):
    k = e.find(mark)
    if k < 0:
        return 0
    i = k + 1
    while i < len(e) and e[i].isdigit():
        i += 1
    return int(e[k + 1:i] or 0)


def ice(e):
    return _num(e, "~")


def rot(e):
    return _num(e, "!")


def bomb(e):
    return "*" in e


def jar(e):
    return "^" in e


def tag(e):
    return "$" in e


def compose(t, n=0, bag=False, r=0, bm=False, jr=False, tg=False):
    return (t + ("~%d" % n if n > 0 else "") + ("?" if bag else "") + ("!%d" % r if r > 0 else "") + ("*" if bm else "")
            + ("^" if jr else "") + ("$" if tg else ""))


def retag(e, n=None, bag=None, r=None, jr=None):
    return compose(base(e), ice(e) if n is None else n, ("?" in e) if bag is None else bag,
                   rot(e) if r is None else r, bomb(e), jar(e) if jr is None else jr, tag(e))


def check_counts(d):
    """3'ün katı olmayan türler (jokerler eksikleri kapatabilir)."""
    total = Counter(base(i) for s in d["shelves"] for l in s["layers"] + s.get("refill", []) for i in l
                    if i and not i.startswith("key_"))
    jokers = total.pop("joker", 0)
    bad = {k: v for k, v in total.items() if v % 3}
    need = sum(3 - v % 3 for v in bad.values())
    return {} if need <= jokers and all(v % 3 == 2 for v in bad.values()) else bad


def best_pair(belt):
    best, bc = "", 0
    for x in belt:
        if x != "joker" and belt.count(x) > bc:
            best, bc = x, belt.count(x)
    return best


def insert_belt(belt, t):
    key = best_pair(belt) if t == "joker" else t
    if key and key in belt:
        k = len(belt) - 1 - belt[::-1].index(key) + 1
    else:
        k = len(belt)
    belt.insert(k, t)


def match_parts(belt, t):
    jokers = belt.count("joker")
    key = best_pair(belt) if t == "joker" else t
    if key:
        c = min(belt.count(key), 3)
        if c + jokers >= 3:
            return [key] * c + ["joker"] * (3 - c)
    if jokers >= 3:
        return ["joker"] * 3
    return []


def rebalance(sh, belt, key):
    """Joker başka türe gittiyse: key'in fazla ürünü (en arka katman) eksik türe çevrilir.
    sh: liste listesi (yerinde değişir). Bantta çevrildiyse çevrilen türü döndürür."""
    c = Counter(base(e) for s in sh for l in s for e in l if e)
    c.update(belt)
    if c[key] % 3 != 1:
        return None
    short = next((t for t in sorted(c) if t != "joker" and t != key and not t.startswith("key_") and c[t] % 3 == 2), None)
    if short is None:
        return None
    best = None
    for si, s in enumerate(sh):
        for li, l in enumerate(s):
            for j, e in enumerate(l):
                if e and base(e) == key and (best is None or li > best[1]):
                    best = (si, li, j)
    if best:
        si, li, j = best
        e = sh[si][li][j]
        sh[si][li][j] = compose(short, ice(e), "?" in e, rot(e), bomb(e), jar(e), tag(e))
        return None
    if key in belt:
        belt[len(belt) - 1 - belt[::-1].index(key)] = short
        return short
    return None


def freeze(S):
    return tuple(tuple(tuple(l) for l in s) for s in S)


class Rules:
    """Bölümün sabit bilgisi ve tek dokunuşun sonucu. Durum: (sh, belt, ci, rem, m, kg, bank, rl)
    sh: kasalar (tuple), belt: liste, ci: müşteri, rem: kalan sipariş, m: eşleşme sayısı,
    kg: açılmış koşullar (anahtar rengi, "n:tür" terazi, "c:k" kırılan zincir, "*" takılma),
    bank: müşteri başına ayrılmış üçlüler, rl: kirli bant gözlerinin kalan eşleşmeleri."""

    def __init__(self, d):
        sv = d["shelves"]
        self.meta = [(s.get("lock", 0), s.get("opens_for", -1), s.get("key", "")) for s in sv]
        self.needs = [s.get("needs", "") for s in sv]
        self.rotates = [bool(s.get("rotate", False)) for s in sv]
        self.hides = [bool(s.get("hide", False)) for s in sv]
        self.chains = [int(s.get("chain", -1)) for s in sv]
        self.conveyors = [bool(s.get("conveyor", False)) for s in sv]
        self.refills = [[list(l) for l in s.get("refill", [])] for s in sv]
        self.freezers = [bool(s.get("freezer", False)) for s in sv]
        self.lifts = [int(s.get("lift", -1)) for s in sv]
        self.gull = bool(d.get("gull", False))
        pos = [s.get("pos", [0, 0]) for s in sv]
        # dondurucunun hedef sırası: uzaklığa göre komşular
        self.by_dist = [sorted((k for k in range(len(sv)) if k != i),
                               key=lambda k, i=i: ((pos[k][0] - pos[i][0]) ** 2 + (pos[k][1] - pos[i][1]) ** 2, k))
                        for i in range(len(sv))]
        self.near = [[k for k in range(len(sv)) if k != i and
                      ((pos[k][0] - pos[i][0]) ** 2 + (pos[k][1] - pos[i][1]) ** 2) ** 0.5 <= BOMB_RADIUS]
                     for i in range(len(sv))]
        self.custs = [dict(c["list"]) for c in d["customers"]]
        self.belt0 = BELT

    def start(self):
        return (None, [], 0, dict(self.custs[0]), 0, (), tuple(() for _ in self.custs), ())

    def is_open(self, si, m, ci, kg):
        if "*" in kg:
            return True
        lk, of, key = self.meta[si]
        return (m >= lk and ci >= of and (not key or key in kg)
                and (not self.needs[si] or "n:" + self.needs[si] in kg)
                and (self.chains[si] < 0 or "c:%d" % si in kg))

    def order(self, c, bk):
        b = dict(bk[c]) if bk else {}
        return {k: max(0, v - b.get(k, 0)) for k, v in self.custs[c].items()}

    def bank_add(self, bk, ci, t):
        for c in range(ci + 1, len(self.custs)):
            if dict(bk[c]).get(t, 0) < self.custs[c].get(t, 0):
                b = dict(bk[c])
                b[t] = b.get(t, 0) + 3
                return bk[:c] + (tuple(sorted(b.items())),) + bk[c + 1:]
        return bk

    def advance(self, ci, bk):
        ci += 1
        while ci < len(self.custs) and all(v == 0 for v in self.order(ci, bk).values()):
            ci += 1
        return ci, (self.order(ci, bk) if ci < len(self.custs) else {})

    def _thaw(self, S, m, ci, kg):
        for si, s in enumerate(S):
            if s and self.is_open(si, m, ci, kg):
                s[0] = [retag(e, max(0, ice(e) - 1), False) if e else e for e in s[0]]

    def _score(self, t, nb, st):
        """Bantta oluşan üçlüyü siparişe ya da sonraki müşteriye işler. st: [rem, ci, m, bank, kg, rl, S]"""
        rem, ci, m, bk, kg, rl, S = st
        m += 1
        if rem.get(t, 0) > 0:
            rem[t] = max(0, rem[t] - 3)
            if all(v == 0 for v in rem.values()):
                ci, rem = self.advance(ci, bk)
        else:
            bk = self.bank_add(bk, ci, t)
        self._thaw(S, m, ci, kg)
        kg.add("n:" + t)
        rl = [v - 1 for v in rl if v > 1]
        st[:] = [rem, ci, m, bk, kg, rl, S]

    def take(self, state, si, j):
        """Tek dokunuş. Yeni durum ya da kayıpsa None. Oyundaki sırayla: bant ve eşleşme, katman kayması,
        döner kasalar, zincir kırılması, bomba, konveyör, çürüme sayacı, joker dengelemesi."""
        sh, belt, ci, rem, m, kg, bk, rl = state
        S = [[list(l) for l in s] for s in sh]
        e = S[si][0][j]
        if jar(e):
            # kavanozun kapağı açılır: ürün yerinde kalır, hamle sayılır
            S[si][0][j] = retag(e, jr=False)
            kg = set(kg)
            rl = list(rl)
            self._ticks(S, m, ci, kg, rl)
            return freeze(S), list(belt), ci, rem, m, tuple(sorted(kg)), bk, tuple(rl)
        it = base(e)
        S[si][0][j] = ""
        advanced = all(not x for x in S[si][0])
        nb = list(belt)
        st = [dict(rem), ci, m, bk, set(kg), list(rl), S]
        parts = []
        if it.startswith("key_"):
            st[4].add(it[4:])
        else:
            insert_belt(nb, it)
            parts = match_parts(nb, it)
            if parts:
                for x in parts:
                    nb.remove(x)
                self._score(parts[0], nb, st)
        rem, ci, m, bk, kg, rl, S = st
        if advanced:
            S[si].pop(0)
        if parts:
            for k, s2 in enumerate(S):
                if self.rotates[k] and len(s2) >= 2 and self.is_open(k, m, ci, kg):
                    S[k] = s2[1:] + s2[:1]
        if advanced:
            for k in range(len(S)):
                if self.chains[k] == si:
                    kg.add("c:%d" % k)
        if self.lifts[si] >= 0:
            p = self.lifts[si]
            if len(S[p]) >= 2 and self.is_open(p, m, ci, kg):
                S[p] = S[p][1:] + S[p][:1]
        if bomb(e):
            for k in self.near[si]:
                if S[k]:
                    S[k][0] = [retag(x, 0, False) if x else x for x in S[k][0]]
                if self.chains[k] >= 0:
                    kg.add("c:%d" % k)
        self._ticks(S, m, ci, kg, rl)
        if parts and "joker" in parts and parts[0] != "joker":
            t2 = rebalance(S, nb, parts[0])
            if t2 and nb.count(t2) >= 3:
                for _ in range(3):
                    nb.remove(t2)
                st = [rem, ci, m, bk, kg, rl, S]
                self._score(t2, nb, st)
                rem, ci, m, bk, kg, rl, S = st
        if len(nb) >= self.belt0 - len(rl):
            return None
        return freeze(S), nb, ci, rem, m, tuple(sorted(kg)), bk, tuple(rl)

    @staticmethod
    def _counter(kg, name):
        for x in kg:
            if x.startswith(name + ":"):
                return int(x.split(":")[1])
        return 0

    @staticmethod
    def _set(kg, name, v):
        for x in [x for x in kg if x.startswith(name + ":")]:
            kg.discard(x)
        if v:
            kg.add("%s:%s" % (name, v))

    def _ticks(self, S, m, ci, kg, rl):
        """Her hamleden sonra (ürün alma ya da kavanoz açma): konveyör, çürüme, dondurucu, martı, taze sandık."""
        for k, s2 in enumerate(S):
            if self.conveyors[k] and len(s2) >= 2 and self.is_open(k, m, ci, kg):
                S[k] = s2[1:] + s2[:1]
        for k, s2 in enumerate(S):
            if not s2 or not self.is_open(k, m, ci, kg):
                continue
            for j2, x in enumerate(s2[0]):
                if x and rot(x) > 0 and ice(x) == 0:
                    r = rot(x) - 1
                    s2[0][j2] = retag(x, r=r)
                    if r == 0:
                        rl.append(ROT_MATCHES)
        # dondurucu: kendisi doluyken her FREEZE_EVERY hamlede en yakın kasanın ön sırasından bir ürünü dondurur
        fz = [k for k in range(len(S)) if self.freezers[k] and S[k]]
        if fz:
            c = self._counter(kg, "F") + 1
            if c >= FREEZE_EVERY:
                c = 0
                self._freeze_one(S, fz[0], m, ci, kg)
            self._set(kg, "F", c)
        # martı: 6. hamlede konar (hedef seçilir), 8. hamlede hedef hâlâ oradaysa en arkaya taşır
        if self.gull:
            c = self._counter(kg, "G") + 1
            if c == GULL_LAND:
                t = self._gull_target(S, m, ci, kg)
                if t:
                    kg.add("GT:%d:%d:%s" % t)
            elif c >= GULL_GRAB:
                c = 0
                tg = next((x for x in kg if x.startswith("GT:")), None)
                if tg:
                    kg.discard(tg)
                    _, a, b, ent = tg.split(":", 3)
                    a, b = int(a), int(b)
                    if S[a] and S[a][0][b] == ent:
                        self._gull_move(S, a, b)
            self._set(kg, "G", c)
        # taze sandık: ilk kez boşalan kasa bir kez yeniden dolar
        for k in range(len(S)):
            if not S[k] and self.refills[k] and ("R:%d" % k) not in kg:
                S[k] = [list(l) for l in self.refills[k]]
                kg.add("R:%d" % k)

    def _freeze_one(self, S, fk, m, ci, kg):
        for k in self.by_dist[fk]:
            if not S[k] or not self.is_open(k, m, ci, kg):
                continue
            for j, x in enumerate(S[k][0]):
                if x and not x.startswith("key_") and ice(x) == 0 and not jar(x):
                    S[k][0][j] = retag(x, n=1)
                    return

    def _gull_target(self, S, m, ci, kg):
        best = None
        for k, s in enumerate(S):
            if not s or len(s) < 2 or not self.is_open(k, m, ci, kg):
                continue
            n = sum(1 for x in s[0] if x)
            if best is None or n > best[0]:
                best = (n, k)
        if best is None:
            return None
        k = best[1]
        for j, x in enumerate(S[k][0]):
            if x and not x.startswith("key_") and ice(x) == 0:
                return (k, j, x)
        return None

    @staticmethod
    def _gull_move(S, k, j):
        # martı ürünü görünen arka sıraya saklar; orası doluysa en alttaki boş göze, o da yoksa yeni katmana
        x = S[k][0][j]
        S[k][0][j] = ""
        last = S[k][-1]
        if len(S[k]) >= 2 and "" in S[k][1]:
            S[k][1][S[k][1].index("")] = x
        elif "" in last and len(S[k]) >= 2:
            last[last.index("")] = x
        else:
            S[k].append([x] + [""] * (len(S[k][0]) - 1))
        if all(not y for y in S[k][0]):
            S[k].pop(0)

    def moves(self, state):
        sh, _b, ci, _r, m, kg = state[:6]
        out = []
        for si, s in enumerate(sh):
            if not s or not self.is_open(si, m, ci, kg):
                continue
            for j, e in enumerate(s[0]):
                if e and ice(e) == 0:
                    out.append((si, j))
        return out

    def stuck(self, state):
        """Hamle yoksa (oyundaki takılma kuralı): buz erir; yoksa kasalar açılır; yoksa son paket.
        Yeni durum, ya da bitti/kaybetti için True/False."""
        sh, belt, ci, rem, m, kg, bk, rl = state
        S = [[list(l) for l in s] for s in sh]
        melted = False
        for si, s in enumerate(S):
            if s and self.is_open(si, m, ci, kg) and any(x and ice(x) > 0 for x in s[0]):
                s[0] = [retag(x, 0) if x else x for x in s[0]]
                melted = True
        if melted:
            return freeze(S), belt, ci, rem, m, kg, bk, rl
        if any(sh) and "*" not in kg:
            return sh, belt, ci, rem, m, tuple(sorted(set(kg) | {"*"})), bk, rl
        return not any(sh)


def solve(d, budget=300000):
    """Çözüm yolu [(raf, göz), ...] ya da None."""
    R = Rules(d)
    if d.get("belt"):
        R.belt0 = int(d["belt"])
    seen = set()
    count = [0]

    def rec(state, path):
        sh, belt, ci, rem, m, kg, bk, rl = state
        if ci >= len(R.custs):
            return path
        count[0] += 1
        if count[0] > budget:
            return None
        k = (sh, tuple(sorted(belt)), ci, tuple(sorted(rem.items())), min(m, 99), kg, bk, rl)
        if k in seen:
            return None
        seen.add(k)
        mv = R.moves(state)
        if not mv:
            r = R.stuck(state)
            if r is True:
                return path
            if r is False:
                return None
            return rec(r, path)
        mv.sort(key=lambda x: (not base(sh[x[0]][0][x[1]]).startswith("key_"),
                               -belt.count(base(sh[x[0]][0][x[1]])),
                               -(rem.get(base(sh[x[0]][0][x[1]]), 0) > 0)))
        for si, j in mv:
            r = R.take(state, si, j)
            if r is None:
                continue
            res = rec(r, path + [(si, j)])
            if res is not None:
                return res
        return None

    sys.setrecursionlimit(20000)
    s0 = R.start()
    s0 = (freeze([s["layers"] for s in d["shelves"]]),) + s0[1:]
    return rec(s0, [])


def main():
    d = json.load(open(sys.argv[1]))
    bad = check_counts(d)
    if bad:
        print("3'ün katı olmayan:", bad)
        return 1
    path = solve(d)
    if path is None:
        print("ÇÖZÜLMEZ (ya da bütçe aşıldı)")
        return 1
    print("ÇÖZÜM:", len(path), "dokunuş")
    if len(sys.argv) > 2:
        json.dump([list(p) for p in path], open(sys.argv[2], "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
