"""persona_sim.py çıktısını analiz eder: zorluk eğrisi, sıçramalar, şans bölümleri, fazla kolay / haksız zor,
tür uyumu, mekanik etkisi, "az kalsın" oranı, uzunluk. Ayar listesini (yeniden üretilecek bölümler) ve grafikleri yazar.
python3 tools/analyze_personas.py [personas.json] [çıktı_klasörü]"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "analysis", "personas.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "analysis")
P = ["rastgele", "acemi", "dikkatsiz", "ortalama", "iyi", "usta"]

# Hedefler (ortalama oyuncu = sezgisel, yeteneksiz; gerçek oyuncu yetenek ve güçlendirme de kullanır)
TARGET = {  # tür: (ortalama alt, ortalama üst, rastgele en çok, usta en az)
    "nefes": (0.85, 1.01, 0.50, 0.95),
    "kolay": (0.70, 0.97, 0.25, 0.85),
    "orta": (0.38, 0.65, 0.15, 0.60),
    "zor": (0.08, 0.26, 0.10, 0.30),
    "cokzor": (0.03, 0.14, 0.08, 0.18),
    "patron": (0.03, 0.16, 0.08, 0.20),
}
TUTORIAL = 3


def mechs(n):
    d = json.load(open(os.path.join(ROOT, "data", "level_%03d.json" % n)))
    m = set()
    for s in d["shelves"]:
        for k in ["lock", "opens_for", "chain", "key", "needs", "rotate", "hide", "conveyor", "freezer", "lift", "gold", "refill"]:
            if s.get(k) not in (None, 0, -1, "", False, []):
                m.add({"opens_for": "shutter"}.get(k, k))
        for l in s["layers"]:
            for e in l:
                for ch, name in (("~", "ice"), ("?", "bag"), ("!", "rot"), ("*", "bomb"), ("^", "jar"), ("$", "tag")):
                    if ch in e:
                        m.add(name)
                if e.startswith("key_"):
                    m.add("key")
                if e == "joker":
                    m.add("joker")
    if d.get("gull"):
        m.add("gull")
    if d.get("kind") == "timed":
        m.add("timed")
    return m


def main():
    res = json.load(open(SRC))
    res.sort(key=lambda r: r["n"])
    W = {p: [r["p"][p]["win"] for r in res] for p in P}
    issues = defaultdict(list)
    for r in res:
        n, t = r["n"], r["tier"]
        lo, hi, rmax, umin = TARGET[t]
        w = {p: r["p"][p]["win"] for p in P}
        if n > TUTORIAL and w["rastgele"] > rmax:
            issues["fazla_kolay"].append(n)
        if w["usta"] < umin:
            issues["haksiz_zor"].append(n)
        if w["ortalama"] < lo - 0.08:
            issues["tur_zor"].append(n)
        elif w["ortalama"] > hi + 0.05 and t not in ("nefes",):
            issues["tur_kolay"].append(n)
        # beceri işe yaramıyor: usta, rastgeleden ancak biraz iyi (ve bölüm kolay değil)
        if n > TUTORIAL and w["usta"] - w["rastgele"] < 0.25 and w["usta"] < 0.95:
            issues["sans"].append(n)
    # sıçrama: aynı türde komşu bölümlere göre ortalama oyuncu için ani zorluk
    for i, r in enumerate(res):
        if i == 0:
            continue
        prev = res[i - 1]
        if r["tier"] == prev["tier"] and prev["p"]["ortalama"]["win"] - r["p"]["ortalama"]["win"] > 0.35:
            issues["sicrama"].append(r["n"])
    # az kalsın: ortalama oyuncunun kayıplarının ne kadarı yakın
    near = [r["p"]["ortalama"]["near"] for r in res if r["p"]["ortalama"]["near"] is not None]
    near_low = [r["n"] for r in res if r["tier"] in ("orta", "zor") and r["p"]["ortalama"]["near"] is not None and r["p"]["ortalama"]["near"] < 0.25]
    issues["az_kalsin_dusuk"] = near_low
    # mekanik etkisi (ortalama oyuncu, türe göre beklenenden sapma)
    by_m = defaultdict(list)
    tier_mean = defaultdict(list)
    for r in res:
        tier_mean[r["tier"]].append(r["p"]["ortalama"]["win"])
    tm = {t: sum(v) / len(v) for t, v in tier_mean.items()}
    for r in res:
        for m in mechs(r["n"]):
            by_m[m].append(r["p"]["ortalama"]["win"] - tm[r["tier"]])
    mech = {m: (round(sum(v) / len(v), 3), len(v)) for m, v in by_m.items()}
    # uzunluk
    mv = [r["p"]["usta"]["moves"] for r in res]
    mv_sorted = sorted(mv)
    q1, q9 = mv_sorted[len(mv) // 10], mv_sorted[len(mv) * 9 // 10]
    # 50'lik gruplar
    groups = []
    for g in range(0, len(res), 50):
        chunk = res[g:g + 50]
        groups.append({"aralik": "%d-%d" % (chunk[0]["n"], chunk[-1]["n"]),
                       **{p: round(sum(c["p"][p]["win"] for c in chunk) / len(chunk), 3) for p in P}})
    per_tier = {t: {p: round(sum(r["p"][p]["win"] for r in res if r["tier"] == t) / max(1, sum(1 for r in res if r["tier"] == t)), 3) for p in P}
                for t in TARGET}
    for t in per_tier:
        per_tier[t]["adet"] = sum(1 for r in res if r["tier"] == t)
    regen = sorted(set(issues["fazla_kolay"]) | set(issues["haksiz_zor"]) | set(issues["tur_zor"]) | set(issues["tur_kolay"])
                   | set(issues["sans"]) | set(issues["sicrama"]))
    summary = {"bolum": len(res), "tur": per_tier, "gruplar": groups, "mekanik": mech,
               "sorunlar": {k: v for k, v in issues.items()}, "sorun_sayilari": {k: len(v) for k, v in issues.items()},
               "az_kalsin_ort": round(sum(near) / len(near), 3) if near else None, "hamle_p10_p90": [q1, q9],
               "yeniden_uret": regen}
    os.makedirs(OUT, exist_ok=True)
    json.dump(summary, open(os.path.join(OUT, "ozet_" + os.path.basename(SRC)), "w"), ensure_ascii=False, indent=1)
    # grafik
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(14, 9))
    xs = [r["n"] for r in res]
    cols = {"rastgele": "#bbbbbb", "acemi": "#f2a65a", "dikkatsiz": "#e8c547", "ortalama": "#3d7bff", "iyi": "#2fb05a", "usta": "#7b2fbf"}
    for p in P:
        sm = []
        for i in range(len(res)):
            win = W[p][max(0, i - 7):i + 8]
            sm.append(sum(win) / len(win))
        ax[0].plot(xs, sm, label=p, color=cols[p], lw=1.6)
    ax[0].set_title("Kazanma oranı (15 bölümlük kayan ortalama)")
    ax[0].set_ylim(0, 1.02)
    ax[0].legend(ncol=6, loc="lower left")
    ax[0].grid(alpha=0.3)
    tcol = {"nefes": "#9ad0ff", "kolay": "#7ad67a", "orta": "#ffd166", "zor": "#ff8a5c", "cokzor": "#d0465c", "patron": "#7b2fbf"}
    ax[1].scatter(xs, W["ortalama"], c=[tcol[r["tier"]] for r in res], s=10)
    ax[1].set_title("Ortalama oyuncu, bölüm bölüm (renk = bölüm türü)")
    ax[1].set_ylim(0, 1.02)
    ax[1].grid(alpha=0.3)
    plt.tight_layout()
    png = os.path.join(OUT, "egri_" + os.path.basename(SRC).replace(".json", ".png"))
    plt.savefig(png, dpi=90)
    print(json.dumps({k: summary[k] for k in ("tur", "sorun_sayilari", "az_kalsin_ort", "hamle_p10_p90")}, ensure_ascii=False, indent=1))
    print("mekanik:", sorted(mech.items(), key=lambda kv: kv[1][0]))
    print("gruplar:")
    for g in groups:
        print("  ", g)
    print("yeniden üretilecek:", len(regen))
    print("grafik:", png)


if __name__ == "__main__":
    main()
