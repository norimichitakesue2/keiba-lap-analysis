#!/usr/bin/env python3
# Friday re-run: order confirmed races by 馬番, keep provisional races 五十音.
# Reuses Monday's raw paddock/stats/records (前走 data is static).
import os, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
RAW = os.path.join(BASE, "win5_raw_0815.tsv")
STATS_RAW = os.path.join(BASE, "win5_stats_0815.tsv")
REC_RAW = os.path.join(BASE, "win5_records_0815.tsv")
NUM_MAP = os.path.join(BASE, "win5_num_0815.tsv")
IMG = "https://cdnv2.netkeiba.com/img/paddock/2026/{}.jpg"
MOV = "https://race.netkeiba.com/race/paddock_movie.html?race_id={}&id={}"

# short, rid, racename, jyo+R, surface_dist, date, course_href(or "")
META = [
 ("chishiro","202601010710","知床特別","札幌10R","芝1200m","2026年8月15日","sapporo_1200_corner4.html"),
 ("chita","202607020706","知多特別","中京6R","芝1200m","2026年8月15日","chukyo_1200_corner4.html"),
 ("joetsu","202604020707","上越S","新潟7R","ダ1200m","2026年8月15日","niigata_dart1200_corner4.html"),
 ("taisetsu","202601010711","大雪ハンデキャップ","札幌11R","ダ1700m","2026年8月15日",""),
 ("takayama","202607020707","高山S","中京7R","芝2000m","2026年8月15日","chukyo_2000_corner4.html"),
 ("nagakute","202607020806","長久手特別","中京6R","芝2000m","2026年8月16日","chukyo_2000_corner4.html"),
 ("odoripark","202601010810","大通公園特別","札幌10R","ダ1000m","2026年8月16日",""),
 ("nst","202604020807","NST賞","新潟7R","ダ1200m","2026年8月16日","niigata_dart1200_corner4.html"),
 ("chukyokinen","202607020807","中京記念","中京7R","芝1600m","2026年8月16日","chukyo_1600_corner4.html"),
 ("sapporokinen","202601010811","札幌記念","札幌11R","芝2000m","2026年8月16日","sapporo_2000_corner4.html"),
]

def parse_grouped(path):
    d = {}; cur = None
    if not os.path.exists(path):
        return d
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#R "):
            cur = line[3:].strip(); d[cur] = []
        elif line.strip():
            d[cur].append(line)
    return d

# parse raw -> rid -> list of [name, prev, imgid, pr, hid]
races = {}
cur = None
for line in open(RAW, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("#R "):
        cur = line[3:].strip(); races[cur] = []
    elif line.strip():
        races[cur].append(line.split("\t"))

# parse num map -> rid -> list of (num, name)  (confirmed races only)
num_map = {}
cur = None
for line in open(NUM_MAP, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("#R "):
        cur = line[3:].strip(); num_map[cur] = []
    elif line.strip():
        num, name = line.split("|", 1)
        num_map[cur].append((num, name))

stats_raw = parse_grouped(STATS_RAW)
rec_raw = parse_grouped(REC_RAW)

for d in ("data", "stats", "records"):
    os.makedirs(os.path.join(REPO, d), exist_ok=True)

summary = []
for short, rid, rname, jyor, sd, date, course in META:
    rows = races.get(rid, [])
    by_name = {r[0]: r for r in rows}
    confirmed = rid in num_map and len(num_map[rid]) > 0
    ordered = []  # (num, name, prev, imgid, pr, hid)
    if confirmed:
        for num, name in num_map[rid]:
            r = by_name.get(name)
            if r:
                ordered.append((num, r[0], r[1], r[2], r[3], r[4]))
            else:
                ordered.append((num, name, "", "", "", ""))  # graceful
    else:
        for r in rows:  # 五十音 order from paddock reference
            ordered.append(("", r[0], r[1], r[2], r[3], r[4]))

    data_path = os.path.join(REPO, "data", f"{short}.tsv")
    with open(data_path, "w", encoding="utf-8") as f:
        for num, nm, prev, imgid, pr, hid in ordered:
            img = IMG.format(imgid) if imgid else ""
            mov = MOV.format(pr, hid) if pr and hid else ""
            f.write(f"{num}\t{nm}\t{prev}\t{img}\t{mov}\n")

    stats_path = os.path.join(REPO, "stats", f"{short}.tsv")
    with open(stats_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stats_raw.get(rid, [])) + "\n")
    rec_path = os.path.join(REPO, "records", f"{short}.tsv")
    with open(rec_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rec_raw.get(rid, [])) + "\n")

    n = len(ordered)
    title = f"{rname} 前走パドック（静止画＋映像リンク）"
    h1 = f"{rname} 前走パドック"
    if confirmed:
        header = f"{date} {jyor} {sd} ／ 前走パドック {n}頭 (馬番順)"
    else:
        header = f"{date} {jyor} {sd} ／ 前走パドック {n}頭 (暫定・枠順未確定/五十音順)"
    out = os.path.join(REPO, f"paddock_2026_{short}.html")
    args = [sys.executable, os.path.join(BASE, "gen_still.py"), data_path, title, h1, header, out, stats_path, rec_path]
    if course:
        args += [course]
    subprocess.run(args, check=True)
    summary.append((short, rid, rname, jyor, sd, n, "CONF" if confirmed else "PROV", course or "(none)"))

print("=== SUMMARY ===")
for s in summary:
    print(s)
