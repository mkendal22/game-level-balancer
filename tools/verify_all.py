"""Bütün bölümleri paralel olarak çözücüyle doğrular ve sayıları kontrol eder.
python3 tools/verify_all.py [ilk] [son]"""
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from solve_level import solve, check_counts  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def one(n):
    p = os.path.join(DATA, "level_%03d.json" % n)
    if not os.path.exists(p):
        return n, "dosya yok"
    d = json.load(open(p))
    if check_counts(d):
        return n, "sayı hatası"
    if solve(d, 600000) is None:
        return n, "çözülmedi"
    return n, ""


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    b = int(sys.argv[2]) if len(sys.argv) > 2 else len([x for x in os.listdir(DATA) if x.startswith("level_")])
    with Pool(12) as pool:
        res = pool.map(one, range(a, b + 1), chunksize=4)
    bad = [(n, r) for n, r in res if r]
    print("doğrulanan:", b - a + 1, "sorunlu:", len(bad), bad[:20])
