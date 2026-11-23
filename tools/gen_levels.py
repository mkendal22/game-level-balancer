"""Bölüm üretici v3: 5 durak × 200 bölüm (1000 bölüm). Her bölüm DFS çözücüyle çözülebilir ve
sezgisel oyuncu simülasyonunda hedef kazanma oranına oturtulur (docs/BOLUM_PLANI.md).
python3 tools/gen_levels.py [ilk] [son]   (varsayılan 1 1000) → data/level_NNN.json + data/levels_report.json"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from solve_level import solve, check_counts  # noqa: E402
from sim_level import win_rate, random_rate  # noqa: E402
from persona_sim import persona_rate  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
PER_STOP = 200

BASE_POOL = ["tomato", "cucumber", "pepper", "lemon", "orange", "grape", "onion", "potato", "eggplant",
             "watermelon", "apple", "banana", "carrot", "strawberry", "broccoli", "corn", "cherry", "mushroom"]
STOP_NEW = [[], ["pineapple", "coconut", "kiwi", "papaya", "lychee", "starfruit", "melon"],
            ["pear", "plum", "walnut", "chestnut", "pumpkin", "garlic", "radish", "beet"],
            ["avocado", "peach", "lettuce", "cauliflower", "artichoke", "asparagus", "peas", "chili"],
            ["mango", "dragonfruit", "pomegranate", "fig", "persimmon", "blueberry", "raspberry", "olive"]]

# mekaniklerin ilk göründüğü bölüm (global numara). Tanıtım bölümü her zaman "nefes", ardından 3 "kolay" gelir;
# tanıtımlar 20'lik dalganın sakin kısmına (konum 1..8) denk getirilir. 1. durakta temel engeller, 2. durakta yeniler.
# şans payı sınırları: bir rafta en fazla 1 çanta, buz en fazla 2 kat
BAG_MAX = 1
ICE_MAX = 2
UNLOCK = {"ice": 4, "w2": 10, "lock": 22, "bag": 26, "w1": 34, "gold": 44, "joker": 52, "shutter": 64, "key": 84,
          "quick": 91, "rotate": 104, "timed": 124, "needs": 144, "hide": 164,
          "rot": 206, "chain": 226, "conveyor": 246, "bomb": 266, "jar": 286,
          # 3.–5. durağın yeni engelleri
          "freezer": 406, "refill": 426, "lift": 606, "tag": 626, "gull": 806}

# sıra türü → simülasyon kazanma oranı aralığı (yeteneksiz sezgisel oyuncu; insan biraz daha iyidir)
TIERS = {
    "nefes": (0.88, 1.01),
    "kolay": (0.78, 0.95),
    "orta": (0.40, 0.58),
    "zor": (0.10, 0.24),
    "cokzor": (0.04, 0.12),
    "patron": (0.05, 0.14),
}

# satır tipleri: [(genişlik, x)]
ROW_TYPES = {
    "33": [(3, 190), (3, 530)],
    "3": [(3, 360)],
    "222": [(2, 125), (2, 360), (2, 595)],
    "22": [(2, 200), (2, 520)],
    "212": [(2, 140), (1, 360), (2, 580)],
    "131": [(1, 90), (3, 360), (1, 630)],
    "1111": [(1, 117), (1, 279), (1, 441), (1, 603)],
    "11111": [(1, 96), (1, 228), (1, 360), (1, 492), (1, 624)],
    "323": [(3, 190), (2, 530)],
    "3L": [(3, 190)],
    "3R": [(3, 530)],
    "2C": [(2, 360)],
    "2L": [(2, 200)],
    "2R": [(2, 520)],
    "1C": [(1, 360)],
    "11": [(1, 250), (1, 470)],
    "1L1R": [(1, 110), (1, 610)],
    "121": [(1, 95), (2, 360), (1, 625)],
    "113": [(1, 85), (1, 232), (3, 530)],
    "311": [(3, 190), (1, 488), (1, 635)],
    "3_1": [(3, 240), (1, 580)],
    "1_3": [(1, 140), (3, 480)],
    "2_1": [(2, 230), (1, 520)],
    "1_2": [(1, 200), (2, 490)],
}

# yerleşim kataloğu: ad → (satırlar, gereken kasa türleri). Aynı şekil art arda gelmez.
SHAPES = {
    "klasik": (["33", "33", "33"], ()),
    "ikiz": (["33", "33"], ()),
    "merdiven": (["3L", "3", "3R"], ()),
    "dev": (["3", "33"], ()),
    "piramit": (["3", "22", "222"], ("w2",)),
    "ters piramit": (["222", "22", "3"], ("w2",)),
    "V": (["33", "22", "3"], ("w2",)),
    "zigzag": (["3L", "22", "3R"], ("w2",)),
    "kule": (["1111", "1111", "1111"], ("w1",)),
    "köprü": (["1111", "3", "1111"], ("w1",)),
    "yıldız": (["131", "222", "131"], ("w1", "w2")),
    "karışık": (["212", "33", "212"], ("w1", "w2")),
    "çit": (["11111", "22", "11111"], ("w1", "w2")),
    "kale": (["131", "131", "33"], ("w1",)),
    "kum saati": (["33", "3", "33"], ()),
    "T": (["33", "3", "3"], ()),
    "ters T": (["3", "3", "33"], ()),
    "L": (["3L", "3L", "33"], ()),
    "ters L": (["3R", "3R", "33"], ()),
    "elmas": (["2C", "222", "2C"], ("w2",)),
    "merdiven 2": (["2L", "2C", "2R"], ("w2",)),
    "ok": (["131", "22", "3"], ("w1", "w2")),
    "pencere": (["212", "3", "212"], ("w1", "w2")),
    "kafes": (["1111", "22", "1111"], ("w1", "w2")),
    "çapraz": (["3L", "1111", "3R"], ("w1",)),
    "yan yana": (["113", "311", "113"], ("w1",)),
    "sütunlar": (["121", "121", "121"], ("w1", "w2")),
    "kuleler": (["11", "1111", "11"], ("w1",)),
    "dalga": (["3_1", "1_3", "3_1"], ("w1",)),
    "köşeler": (["1L1R", "3", "1L1R"], ("w1",)),
    "tepe": (["1C", "121", "33"], ("w1", "w2")),
    "kanat": (["2_1", "1_2", "2_1"], ("w1", "w2")),
}

# bölüm temaları: boyut ve mekanik çarpanları
THEMES = {
    "normal": {},
    "derin": {"layers": 2, "two_rows": True},
    "geniş": {"layers": -1},
    "çok çeşit": {"types": 2},
    "az çeşit": {"types": -2},
    "buz festivali": {"ice": 2.5, "need": "ice"},
    "poşet günü": {"bag": 2.5, "need": "bag"},
    "kilitli": {"locks": 2, "need": "lock"},
}


def shape_for(n):
    """Bölümün yerleşimi: açık kasa türlerine uygun, bir öncekiyle aynı olmayan şekil."""
    if n <= 2:
        return "dev" if n == 1 else "ikiz"
    if n == UNLOCK["w2"]:
        return "piramit"
    if n == UNLOCK["w1"]:
        return "kule"
    prev = shape_for(n - 1)
    ok = [k for k, (_, req) in SHAPES.items() if all(unlocked(n, r) for r in req) and k != prev]
    rng = random.Random(n * 7919)
    # yeni açılan kasa türlerini içeren şekiller birkaç bölüm daha sık gelir
    weights = [3 if any(n - UNLOCK[r] < 12 for r in SHAPES[k][1]) else 1 for k in ok]
    return rng.choices(ok, weights)[0]


FORCE_NORMAL = set()


def theme_for(n):
    if n in FORCE_NORMAL:
        return "normal"
    if n <= 3 or tier_of(n) == "nefes":
        return "normal"
    rng = random.Random(n * 104729)
    ok = [k for k, v in THEMES.items() if "need" not in v or unlocked(n, v["need"])]
    # yeni mekaniğin tanıtımından sonraki bölümler o mekaniğe ağırlık verir
    for m, k in (("ice", "buz festivali"), ("bag", "poşet günü"), ("lock", "kilitli")):
        if 1 <= n - UNLOCK[m] <= 3:
            return k
    prev = theme_for(n - 1) if n > 4 else "normal"
    ok = [k for k in ok if k != prev or k == "normal"]
    return rng.choice(ok)
ROW_Y = {2: [420, 740], 3: [330, 590, 850]}

NAMES = [
    ["Sabah", "Taze", "Neşeli", "Bereketli", "Renkli", "Mis Kokulu", "Çıtır", "Güneşli", "Tatlı", "Komşu",
     "Cumartesi", "Bayram", "Hasat", "Yeşil", "Altın"],
    ["Tezgâh", "Pazar", "Reyon", "Sepet", "Kasa", "Köşe", "Sokak", "Bahçe", "Manav", "Sergi"],
]
STOP_WORDS = [
    ["Mahalle", "Çeşme", "Fırın", "Bakkal", "Avlu"],
    ["Kumsal", "Dalga", "Martı", "İskele", "Fener"],
    ["Yayla", "Değirmen", "Dere", "Bağ", "Zirve"],
    ["Çarşı", "Meydan", "Gökdelen", "Metro", "Pasaj"],
    ["Lagün", "Palmiye", "Volkan", "Mercan", "Şelale"],
]


# 20'lik dalga (konum 0..19). Arka arkaya iki bölüm arasında uçurum yok: en büyük sıçrama nefes→orta ve orta→çok zor.
WAVE = ["nefes", "kolay", "orta", "kolay", "orta", "orta", "zor", "nefes", "orta", "orta",
        "kolay", "orta", "orta", "zor", "nefes", "orta", "zor", "orta", "orta", "cokzor"]
INTRO = set(UNLOCK.values())


def tier_of(n):
    t = _tier_raw(n)
    # kolay/nefes bölümünün ardından zor ya da çok zor gelmez: arada en az bir orta olur
    if t in ("zor", "cokzor") and n > 1 and _tier_raw(n - 1) in ("kolay", "nefes"):
        return "orta"
    if t == "cokzor" and n <= 60:
        return "zor"               # ilk 60 bölümde çok zor yok
    if n <= 10 and t in ("orta", "zor", "cokzor"):
        return "kolay"             # ilk oturum (ilk 10 bölüm) kaybettirmez; kolaylar yine "az kalsın" hissi verir
    return t


def _tier_raw(n):
    k = (n - 1) % PER_STOP + 1
    if k == PER_STOP or k == PER_STOP // 2:
        return "patron"            # durak sonu büyük patron, durak ortası ara patron
    if n <= 3 or n in INTRO:
        return "nefes"             # başlangıç ve yeni mekaniğin tanıtımı
    if any(1 <= n - u <= 3 for u in INTRO):
        return "kolay"             # tanıtımdan sonraki 3 bölüm mekaniği öğretir
    if k == 1 or k == PER_STOP // 2 + 1:
        return "nefes"             # patrondan sonra nefes
    if k <= 6:
        return "kolay"             # her durak yumuşak başlar
    return WAVE[(k - 1) % 20]


# rastgele dokunan oyuncunun en fazla kazanma oranı: bölüm düşünmeden bitmesin (1–3 öğretici hariç)
RANDOM_CAP = {"nefes": 0.50, "kolay": 0.25, "orta": 0.15, "zor": 0.10, "cokzor": 0.10, "patron": 0.10}


# usta oyuncunun (iki hamle ileriyi gören) en az kazanma oranı: bölüm ustaya haksız gelmesin
USTA_MIN = {"nefes": 0.95, "kolay": 0.85, "orta": 0.60, "zor": 0.30, "cokzor": 0.18, "patron": 0.20}
# iyi oyuncunun (bir hamle ileriyi gören) en fazla kazanma oranı: zor bölümler iyi oyuncuya da kolay geçilmesin
IYI_MAX = {"zor": 0.48, "cokzor": 0.36, "patron": 0.40}
# usta ile rastgele arasında en az bu kadar fark: beceri işe yaramalı (şans bölümü olmasın)
SKILL_GAP = 0.25


def random_cap(n):
    # ilk 3 bölüm öğretici: sınır yok; yeni mekaniğin tanıtımı sade ama yine biraz dikkat ister
    if n <= 3:
        return 1.01
    return 0.75 if n in INTRO else RANDOM_CAP[tier_of(n)]


def window(n):
    """Hedef aralık; duraktan durağa hafifçe zorlaşır, bir durak içinde de azıcık sıkılaşır."""
    lo, hi = TIERS[tier_of(n)]
    if n <= 40 and tier_of(n) == "zor":
        # ilk zor bölümler öğretici: zor etiketli ama gerçekten kaybettirmeyecek kadar yumuşak
        return 0.30, 0.46
    s = (n - 1) // PER_STOP
    k = (n - 1) % PER_STOP + 1
    drop = {"nefes": 0.0, "kolay": 0.02, "orta": 0.025, "zor": 0.008, "cokzor": 0.004, "patron": 0.003}[tier_of(n)]
    d = drop * (s + k / PER_STOP)
    return max(0.03, lo - d), hi - d


def level_name(n, rng):
    s = (n - 1) // PER_STOP
    k = (n - 1) % PER_STOP + 1
    if k == PER_STOP:
        return "%s Finali" % STOP_WORDS[s][0]
    if k == PER_STOP // 2:
        return "%s Finali" % STOP_WORDS[s][2]
    a = NAMES[0][(n * 7) % len(NAMES[0])]
    b = NAMES[1][(n * 3 + s) % len(NAMES[1])]
    if k % 5 == 0:
        return "%s %s" % (STOP_WORDS[s][(k // 5) % 5], b)
    return "%s %s" % (a, b)


def curve(n):
    """Bölüm numarasına göre boyut ve mekanik parametreleri."""
    s = (n - 1) // PER_STOP
    k = (n - 1) % PER_STOP + 1
    p = min(1.0, (k - 1) / 190.0)         # durak içi ilerleme
    g = min(1.0, (n - 1) / 800.0)          # genel ilerleme
    tier = tier_of(n)
    big = {"nefes": -1, "kolay": 0, "orta": 0, "zor": 1, "cokzor": 1, "patron": 2}[tier]
    # durağın yeni ürünleri sırayla gelir: ilk ikisi baştan, sonra her 8 bölümde bir yenisi
    avail = min(len(STOP_NEW[s]), 2 + max(0, (k - 1) // 16))
    cur_new = STOP_NEW[s][:avail]
    pool = BASE_POOL + [t for st in STOP_NEW[1:s] for t in st] + cur_new
    if avail > 2 and (k - 1) % 16 < 6:
        featured = [cur_new[-1]]
    elif k <= 30:
        featured = cur_new[:2]
    else:
        featured = []
    return {
        "stop": s, "k": k, "tier": tier, "p": p, "g": g, "big": big,
        "types": max(3, min(len(pool), 4 + int(p * 4 + g * 3) + big)),
        "layers": 1 if n <= 2 else min(4, 2 + int(p * 1.5 + g * 0.8) + max(0, big)),
        "cust": 1 if n <= 4 else min(4, 2 + int(p * 1.5 + g) + max(0, big - 1)),
        "pool": pool, "new": featured,
    }


def unlocked(n, m):
    return n >= UNLOCK[m]


def kind_of(n):
    """Bölüm türü: "boss" (durak finali), "quick" (tek siparişli hızlı teslimat), "timed" (süreli) ya da ""."""
    k = (n - 1) % PER_STOP + 1
    if k == PER_STOP or k == PER_STOP // 2:
        return "boss"
    t = tier_of(n)
    if unlocked(n, "quick") and t == "kolay" and (k - 1) % 20 == 10 or n == UNLOCK["quick"]:
        return "quick"
    if unlocked(n, "timed") and t == "orta":
        # 64'ten sonraki her 4. "orta" bölüm süreli
        idx = sum(1 for x in range(UNLOCK["timed"], n) if tier_of(x) == "orta")
        if idx % 4 == 0:
            return "timed"
    return ""


def pick_rows(n, c, rng):
    rows = list(SHAPES[shape_for(n)][0])
    if THEMES[c["theme"]].get("two_rows") and len(rows) == 3:
        cut = rows[:2] if rng.random() < 0.5 else rows[1:]
        if sum(len(ROW_TYPES[r]) for r in cut) >= 4:
            rows = cut
    return rows


def build(n, rng, swaps, shrink=0):
    c = curve(n)
    c["theme"] = theme_for(n)
    th = THEMES[c["theme"]]
    c["types"] = max(3, min(len(c["pool"]), c["types"] - shrink + th.get("types", 0)))
    kind = kind_of(n)
    if kind == "quick":
        c["types"] = min(c["types"], 4)
    # 3 türle bant (7 göz) asla dolmaz: 7 üründen 3'ü hep aynı türdür, rastgele tıklama da kazanır.
    # Öğreticiden sonra en az 4, 8. bölümden sonra en az 5 tür: rahat ama düşünmek gerekir.
    if n >= 4 and kind != "quick":
        c["types"] = min(len(c["pool"]), max(c["types"], 5 if n >= 8 else 4))
    c["layers"] = max(1, c["layers"] + th.get("layers", 0))
    rows = pick_rows(n, c, rng)
    ys = ROW_Y[len(rows)]
    shelves = []
    for ri, rt in enumerate(rows):
        for w, x in ROW_TYPES[rt]:
            L = c["layers"] - shrink - (1 if c["tier"] == "nefes" and n > 20 else 0)
            if w == 2:
                L += 1
            elif w == 1:
                L += 2
            if n <= 2:
                L = 1
            shelves.append({"pos": [x, ys[ri]], "w": w, "L": max(1, L + rng.choice([0, 0, 0, -1, 1]))})
    # tanıtım bölümlerinde engelin oturacağı kasalar yeterince derin olsun
    need_depth = {UNLOCK["refill"]: 3, UNLOCK["lift"]: 2, UNLOCK["freezer"]: 2, UNLOCK["gull"]: 2}.get(n, 0)
    if need_depth:
        for sh in shelves[:2]:
            sh["L"] = max(sh["L"], need_depth)
    cap = sum(s["w"] * s["L"] for s in shelves)
    triples = cap // 3
    # türler: yeni ürünler önce
    ntypes = min(c["types"], triples)
    types = list(c["new"])
    rest = [t for t in c["pool"] if t not in types]
    rng.shuffle(rest)
    types = (types + rest)[:ntypes]
    counts = {t: 1 for t in types}
    for i in range(triples - ntypes):
        t = rng.choice(types)
        counts[t] += 1
    # siparişler: raftaki her üçlü bir siparişe gider, bölüm ancak kasalar boşalınca biter.
    # Müşteri başına en çok 4 tür (kart sırası ekrana sığar); yeni ürünler ilk müşteride.
    order_types = types[:]
    rng.shuffle(order_types)
    if c["new"]:
        for t in reversed(c["new"]):
            if t in order_types:
                order_types.remove(t)
                order_types.insert(0, t)
    per = 2 if n <= 6 else (3 if c["p"] < 0.5 else rng.choice([3, 3, 4]))
    if n == UNLOCK["shutter"]:
        per = 2   # tanıtım bölümünde en az 3 müşteri olsun
    if kind == "quick":
        per = len(order_types)
    elif kind == "boss":
        per = max(1, -(-len(order_types) // 3))
    customers = []
    for ci in range(0, len(order_types), per):
        chunk = order_types[ci:ci + per]
        customers.append({"id": "c%d" % len(customers), "list": {t: 3 * counts[t] for t in chunk}})
    # sıra: üçlüler art arda, sonra yakın takaslarla karıştırılır
    seq = []
    tl = [t for t in types for _ in range(counts[t])]
    rng.shuffle(tl)
    for t in tl:
        seq += [t] * 3
    for _ in range(swaps):
        i = rng.randrange(len(seq))
        j = min(len(seq) - 1, max(0, i + rng.randint(-14, 14)))
        seq[i], seq[j] = seq[j], seq[i]
    # gözler katman sırasına göre (katman içinde rastgele)
    maxL = max(s["L"] for s in shelves)
    for s in shelves:
        s["layers"] = [[""] * s["w"] for _ in range(s["L"])]
    spots = []
    for li in range(maxL):
        layer = [(si, li, j) for si, s in enumerate(shelves) if li < s["L"] for j in range(s["w"])]
        rng.shuffle(layer)
        spots += layer
    empties = len(spots) - len(seq)
    # boş kalan gözler en derin katmanlara
    for k, (si, li, j) in enumerate(spots[:len(seq)]):
        shelves[si]["layers"][li][j] = seq[k]
    # mekanikler
    normal = list(range(len(shelves)))
    meta = {}
    nshelf = len(shelves)
    if unlocked(n, "lock") and (n == UNLOCK["lock"] or c["theme"] == "kilitli" or rng.random() < 0.4 + 0.2 * c["p"]):
        nl = THEMES[c["theme"]].get("locks", 1)
        for si in rng.sample(range(nshelf), min(nl, max(1, nshelf // 3))):
            meta[si] = {"lock": rng.randint(2, 3 + int(c["p"] * 3)) + (2 if len(meta) else 0)}
    # "Yakında" kasası: yalnız 3+ müşterili bölümlerde; açıldığında işin çoğu hâlâ önde olsun.
    # İçi sonraki müşterilerin ürünlerinden karışık; hiçbir tür tamamen içinde değil (tek başına "tık tık" bitmesin).
    if unlocked(n, "shutter") and len(customers) >= 3 and (n == UNLOCK["shutter"] or rng.random() < 0.35):
        opens = 1 if len(customers) < 5 else 2
        cand = [i for i in range(nshelf) if i not in meta and sum(1 for l in shelves[i]["layers"] for x in l if x) >= 3]
        if cand:
            si = rng.choice(cand)
            if mix_shutter(shelves, si, customers, opens, rng):
                meta[si] = {"opens_for": opens}
    key_spot = None
    if unlocked(n, "key") and (n == UNLOCK["key"] or rng.random() < 0.3) and empties > 0:
        cand = [i for i in range(nshelf) if i not in meta]
        if len(cand) >= 2:
            ks = rng.choice(cand)
            color = rng.choice(["blue", "green", "yellow", "red"])
            meta[ks] = {"key": color}
            holder = rng.choice([i for i in cand if i != ks])
            key_spot = (holder, color)
    # özgün kasalar
    free = [i for i in range(nshelf) if i not in meta]
    rng.shuffle(free)
    if unlocked(n, "rotate") and free and (n == UNLOCK["rotate"] or rng.random() < 0.28):
        si = next((i for i in free if shelves[i]["L"] >= 2), None)
        if si is not None:
            shelves[si]["rotate"] = True
            free.remove(si)
    if unlocked(n, "needs") and len(free) >= 2 and (n == UNLOCK["needs"] or rng.random() < 0.26):
        si = free.pop()
        inside = {x for l in shelves[si]["layers"] for x in l}
        opts = [t for t in types if t not in inside] or types
        meta[si] = {"needs": rng.choice(opts)}
    if unlocked(n, "conveyor") and free and (n == UNLOCK["conveyor"] or rng.random() < 0.25):
        si = next((i for i in free if shelves[i]["L"] >= 3 and not shelves[i].get("rotate")), None)
        if si is not None:
            shelves[si]["conveyor"] = True
            free.remove(si)
    if unlocked(n, "chain") and len(free) >= 2 and (n == UNLOCK["chain"] or rng.random() < 0.25):
        a = free.pop()
        pa = shelves[a]["pos"]
        partners = sorted((i for i in free if not shelves[i].get("conveyor")),
                          key=lambda i: abs(shelves[i]["pos"][0] - pa[0]) + abs(shelves[i]["pos"][1] - pa[1]))
        if partners:
            meta[a] = {"chain": partners[0]}
        else:
            free.append(a)
    if unlocked(n, "hide") and free and (n == UNLOCK["hide"] or rng.random() < 0.25):
        si = next((i for i in free if shelves[i]["L"] >= 2), None)
        if si is not None:
            shelves[si]["hide"] = True
    # taze sandık: derin bir kasanın arka yarısı "yeniden dolum" olur (ürün sayısı değişmez)
    if unlocked(n, "refill") and (n == UNLOCK["refill"] or rng.random() < 0.25):
        si = next((i for i in free if shelves[i]["L"] >= 3 and not shelves[i].get("rotate") and not shelves[i].get("conveyor")
                   and not shelves[i].get("hide")), None)
        if si is not None:
            free.remove(si)
            shelves[si]["refill_k"] = shelves[si]["L"] // 2
    # dondurucu dolap: komşusu olan, en az iki katmanlı bir kasa
    if unlocked(n, "freezer") and nshelf >= 3 and (n == UNLOCK["freezer"] or rng.random() < 0.25):
        si = next((i for i in free if shelves[i]["L"] >= 2), None)
        if si is not None:
            free.remove(si)
            shelves[si]["freezer"] = True
    # asansör: birbirine yakın, ikisi de en az iki katmanlı iki kasa
    if unlocked(n, "lift") and len(free) >= 2 and (n == UNLOCK["lift"] or rng.random() < 0.25):
        cand = [i for i in free if shelves[i]["L"] >= 2 and not shelves[i].get("rotate") and not shelves[i].get("conveyor")]
        if len(cand) >= 2:
            a = cand[0]
            pa = shelves[a]["pos"]
            b = min(cand[1:], key=lambda i: abs(shelves[i]["pos"][0] - pa[0]) + abs(shelves[i]["pos"][1] - pa[1]))
            shelves[a]["lift"] = b
            shelves[b]["lift"] = a
            free.remove(a)
            free.remove(b)
    if unlocked(n, "gold") and (n == UNLOCK["gold"] or rng.random() < 0.18):
        shelves[rng.randrange(nshelf)]["gold"] = 30 + 10 * rng.randint(0, 3 + int(c["g"] * 6))
    for si, m in meta.items():
        shelves[si].update(m)
    # boş gözler: katman içinde ürünleri öne kaydırır, en arka tamamen boşsa siler
    for s in shelves:
        s["layers"] = [l for l in s["layers"] if any(l)]
        if not s["layers"]:
            s["layers"] = [[""] * s["w"]]
    for s in shelves:
        k = s.pop("refill_k", 0)
        if k and len(s["layers"]) > k:
            s["refill"] = s["layers"][-k:]
            s["layers"] = s["layers"][:-k]
    if key_spot:
        holder, color = key_spot
        s = shelves[holder]
        placed = False
        for li in range(min(2, len(s["layers"]))):
            for j in range(s["w"]):
                if s["layers"][li][j] == "":
                    s["layers"][li][j] = "key_" + color
                    placed = True
                    break
            if placed:
                break
        if not placed:
            s["layers"].insert(min(1, len(s["layers"])), ["key_" + color] + [""] * (s["w"] - 1))
    open_ids = [i for i in range(nshelf) if i not in meta]
    cells = [(si, li, j) for si in open_ids for li in range(len(shelves[si]["layers"])) for j in range(shelves[si]["w"])
             if shelves[si]["layers"][li][j] and not shelves[si]["layers"][li][j].startswith("key_")]
    rng.shuffle(cells)
    k = 0
    if unlocked(n, "ice"):
        nice = 0 if c["tier"] == "nefes" else (3 if n == UNLOCK["ice"] else rng.randint(0, 2 + int(4 * c["p"]) + c["big"]))
        nice = int(nice * THEMES[c["theme"]].get("ice", 1.0)) + (3 if c["theme"] == "buz festivali" else 0)
        for _ in range(nice):
            if k >= len(cells):
                break
            si, li, j = cells[k]
            k += 1
            shelves[si]["layers"][li][j] += "~%d" % min(ICE_MAX, rng.randint(1, 1 + int(c["p"] * 2)))
    if unlocked(n, "bag"):
        nb = 0 if c["tier"] == "nefes" else (4 if n == UNLOCK["bag"] else rng.randint(0, 2 + int(5 * c["p"])))
        nb = int(nb * THEMES[c["theme"]].get("bag", 1.0)) + (3 if c["theme"] == "poşet günü" else 0)
        for _ in range(nb):
            if k >= len(cells):
                break
            si, li, j = cells[k]
            k += 1
            e = shelves[si]["layers"][li][j]
            # rafta aynı anda en fazla BAG_MAX gizli çanta (şans payını azaltır)
            if "?" not in e and sum(1 for l in shelves[si]["layers"] for x in l if "?" in x) < BAG_MAX:
                shelves[si]["layers"][li][j] = e + "?"
    if unlocked(n, "joker") and (n == UNLOCK["joker"] or rng.random() < 0.33):
        # bir üçlünün bir tanesi joker olur
        while k < len(cells):
            si, li, j = cells[k]
            k += 1
            e = shelves[si]["layers"][li][j]
            if "~" not in e and "?" not in e:
                shelves[si]["layers"][li][j] = "joker"
                break
    if unlocked(n, "rot") and c["tier"] != "nefes" and (n == UNLOCK["rot"] or rng.random() < 0.3):
        nrot = 1 if n == UNLOCK["rot"] else rng.randint(1, 2 + int(c["p"] * 2))
        # çürüme yalnız ön sırada işler: ilk iki katmandaki ürünlere konur
        front = [x for x in cells[k:] if x[1] <= 1]
        for si, li, j in front[:nrot]:
            e = shelves[si]["layers"][li][j]
            if "~" in e or "?" in e or e == "joker":
                continue
            shelves[si]["layers"][li][j] = e + "!%d" % (rng.randint(6, 9) if c["tier"] in ("kolay", "orta") else rng.randint(4, 7))
            cells.remove((si, li, j))
    if unlocked(n, "jar") and c["tier"] != "nefes" or n == UNLOCK.get("jar"):
        if n == UNLOCK["jar"] or rng.random() < 0.3:
            nj = 3 if n == UNLOCK["jar"] else rng.randint(1, 2 + int(c["p"] * 2))
            for si, li, j in [x for x in cells[k:] if x[1] <= 1][:nj]:
                e = shelves[si]["layers"][li][j]
                if any(m in e for m in "~?!*") or e == "joker":
                    continue
                shelves[si]["layers"][li][j] = e + "^"
    if unlocked(n, "tag") and (n == UNLOCK["tag"] or rng.random() < 0.35):
        nt = 3 if n == UNLOCK["tag"] else rng.randint(1, 3)
        for si, li, j in cells[k:][-nt:]:
            e = shelves[si]["layers"][li][j]
            if e != "joker" and "$" not in e:
                shelves[si]["layers"][li][j] = e + "$"
    has_target = any("~" in e or "?" in e for s2 in shelves for l in s2["layers"] for e in l) or \
        any(s2.get("hide") for s2 in shelves) or any("chain" in m for m in meta.values())
    if unlocked(n, "bomb") and has_target and (n == UNLOCK["bomb"] or rng.random() < 0.3):
        for si, li, j in cells[k:]:
            e = shelves[si]["layers"][li][j]
            if li <= 2 and "~" not in e and "?" not in e and "!" not in e and e != "joker":
                shelves[si]["layers"][li][j] = e + "*"
                break
    tools = {}
    for tool, lv in (("undo", 5), ("magnet", 7), ("shuffle", 20), ("slot", 28), ("scoop", 150)):
        if n == lv:
            tools[tool] = 2
    out = {
        "name": level_name(n, rng),
        "tier": c["tier"],
        "shape": shape_for(n),
        "theme": c["theme"],
        "tools": tools,
        "customers": customers,
        "shelves": [{k2: v for k2, v in s.items() if k2 not in ("L",)} for s in shelves],
    }
    for s in out["shelves"]:
        if s["w"] == 3:
            del s["w"]
    if kind:
        out["kind"] = kind
    if unlocked(n, "gull") and any(len(s["layers"]) >= 2 for s in shelves) and (n == UNLOCK["gull"] or rng.random() < 0.3):
        out["gull"] = True
    if kind in ("timed", "quick"):
        items = sum(1 for s in shelves for l in s["layers"] for e in l if e)
        # süre sıkı ama adil: ürün başına ~1.6 sn (hızlı teslimatta 1.35) + kısa pay
        per_move, base = (1.6, 12) if kind == "timed" else (1.35, 10)
        out["time"] = int(round((items * per_move + base) / 5.0)) * 5
    return out


def mix_shutter(shelves, si, customers, opens, rng):
    """Kepenkli kasanın içini düzenler: açılana kadar gereken (ilk müşterilerin) ürünleri dışarı alınır,
    her türden en az bir tane dışarıda kalır, içeride en az iki farklı müşterinin ürünü bulunur.
    Takaslar aynı katman derinliğinde yapılır. Olmazsa False."""
    owner = {t: ci for ci, cu in enumerate(customers) for t in cu["list"]}
    inside = [(li, j) for li, l in enumerate(shelves[si]["layers"]) for j, x in enumerate(l) if x]
    outside = [(oi, li, j) for oi, s in enumerate(shelves) if oi != si
               for li, l in enumerate(s["layers"]) for j, x in enumerate(l) if x]
    rng.shuffle(outside)

    def get(p):
        return shelves[p[0]]["layers"][p[1]][p[2]]

    def swap(li, j, q):
        a = shelves[si]["layers"][li][j]
        shelves[si]["layers"][li][j] = get(q)
        shelves[q[0]]["layers"][q[1]][q[2]] = a

    def pick(ok, li):
        # önce aynı derinlik, yoksa en yakın derinlik
        best = None
        for q in outside:
            if ok(get(q)):
                d = abs(q[1] - li)
                if best is None or d < best[0]:
                    best = (d, q)
                    if d == 0:
                        break
        return best[1] if best else None

    for li, j in inside:
        x = shelves[si]["layers"][li][j]
        if owner.get(x, 0) < opens:
            q = pick(lambda y: owner.get(y, 0) >= opens, li)
            if q is None:
                return False
            swap(li, j, q)
    total = {}
    for s in shelves:
        for l in s["layers"]:
            for x in l:
                if x:
                    total[x] = total.get(x, 0) + 1
    for _ in range(12):
        cnt = {}
        for li, j in inside:
            x = shelves[si]["layers"][li][j]
            cnt[x] = cnt.get(x, 0) + 1
        full = [x for x, k in cnt.items() if k >= total[x]]
        if not full:
            break
        x = full[0]
        li, j = next((li, j) for li, j in inside if shelves[si]["layers"][li][j] == x)
        q = pick(lambda y: y != x and owner.get(y, 0) >= opens and cnt.get(y, 0) + 1 < total[y], li)
        if q is None:
            return False
        swap(li, j, q)
    kinds = {owner.get(shelves[si]["layers"][li][j], 0) for li, j in inside}
    return len(kinds) >= 2 or len(customers) - opens < 2


def make(n, tries=140, salt=0):
    lo, hi = window(n)
    rng = random.Random(9000 + n + salt * 100003)
    swaps = {"nefes": 0, "kolay": 2, "orta": 6, "zor": 12, "cokzor": 18, "patron": 22}[tier_of(n)]
    best = None
    rand_best = None   # zorluğu tutan ama rastgele sınırını aşan en iyi aday (yedek)
    shrink = 0
    low = 0
    unsolved = 0
    for attempt in range(tries):
        d = build(n, rng, swaps, shrink)
        if check_counts(d):
            continue
        wr = win_rate(d, 50, seed=n)
        if lo <= wr <= hi:
            rr = random_rate(d, 40, seed=n)
            if rr > random_cap(n):
                # düşünen için doğru zorlukta ama rastgele tıklamayla da bitiyor: daha karışık dene
                if (rand_best is None or rr < rand_best[2]) and solve(d, 400000) is not None:
                    rand_best = (d, wr, rr)
                swaps += 1
                continue
            us = persona_rate(d, "usta", 12, seed=n)
            if us < USTA_MIN[tier_of(n)] or (us < 0.95 and us - rr < SKILL_GAP):
                # ustaya haksız ya da beceri fark yaratmıyor (şans bölümü): başka diziliş
                if (rand_best is None or rr < rand_best[2]) and solve(d, 400000) is not None:
                    rand_best = (d, wr, 1.0 - us)
                continue
            if n > 40 and tier_of(n) in IYI_MAX and persona_rate(d, "iyi", 12, seed=n) > IYI_MAX[tier_of(n)]:
                # iyi oyuncu da rahat geçiyor: daha karışık dene
                swaps += 1
                continue
            if solve(d, 400000) is not None:
                return d, wr, attempt
            unsolved += 1
            if unsolved >= 5 and shrink < 3:
                shrink += 1
                unsolved = 0
            continue
        dist = lo - wr if wr < lo else wr - hi
        if best is None or dist < best[2]:
            if solve(d, 400000) is not None:
                best = (d, wr, dist)
        if wr > hi:
            swaps += 2
        elif wr < lo:
            if swaps == 0:
                low += 1
                if low >= 4 and shrink < 3:
                    shrink += 1
                    low = 0
            swaps = max(0, swaps - 2)
    if rand_best:
        return rand_best[0], rand_best[1], attempt
    if best:
        return best[0], best[1], -1
    if n not in FORCE_NORMAL:
        FORCE_NORMAL.add(n)
        return make(n, tries)
    raise RuntimeError("bölüm %d üretilemedi" % n)


def main():
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    rp = os.path.join(DATA, "levels_report.json")
    if len(sys.argv) > 3:
        # paralel üretim: her parça kendi rapor dosyasına yazar (sonra birleştirilir)
        rp = os.path.join(DATA, "levels_report_%d_%d.json" % (a, b))
    report = json.load(open(rp)) if os.path.exists(rp) else {}
    # oyunun okuduğu bölüm türü tablosu (Journey.tier): üreticiyle hep aynı kalsın
    json.dump({"per_stop": PER_STOP, "tiers": [tier_of(x) for x in range(1, 5 * PER_STOP + 1)],
               "kinds": [kind_of(x) for x in range(1, 5 * PER_STOP + 1)]}, open(os.path.join(DATA, "tiers.json"), "w"))
    for n in range(a, b + 1):
        d, wr, att = make(n)
        d["sim"] = round(wr, 2)
        json.dump(d, open(os.path.join(DATA, "level_%03d.json" % n), "w"), ensure_ascii=False, indent=1)
        report[str(n)] = {"shape": d["shape"], "theme": d["theme"], "tier": d["tier"], "sim": round(wr, 2), "fit": att >= 0, "shelves": len(d["shelves"]),
                          "items": sum(1 for s in d["shelves"] for l in s["layers"] for e in l if e)}
        json.dump(report, open(rp, "w"), ensure_ascii=False, indent=1, sort_keys=True)
        print("%3d %-7s %3.0f%% %s %-13s %-13s %s" % (n, d["tier"], wr * 100, "ok " if att >= 0 else "YAK", d["shape"], d["theme"], d["name"]), flush=True)
    json.dump(report, open(rp, "w"), ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
