#!/usr/bin/env python3
import os, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
RAW = os.path.join(BASE, "win5_raw_0815.tsv")
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
BY_RID = {m[1]: m for m in META}

# parse raw
races = {}
cur = None
for line in open(RAW, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("#R "):
        cur = line[3:].strip(); races[cur] = []
    elif line.strip():
        races[cur].append(line.split("\t"))

os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
summary = []
for short, rid, rname, jyor, sd, date, course in META:
    rows = races.get(rid, [])
    data_path = os.path.join(REPO, "data", f"{short}.tsv")
    with open(data_path, "w", encoding="utf-8") as f:
        for nm, prev, imgid, pr, hid in rows:
            img = IMG.format(imgid) if imgid else ""
            mov = MOV.format(pr, hid) if pr and hid else ""
            f.write(f"\t{nm}\t{prev}\t{img}\t{mov}\n")   # num empty (枠順未確定)
    n = len(rows)
    title = f"{rname} 前走パドック（静止画＋映像リンク）"
    h1 = f"{rname} 前走パドック"
    header = f"{date} {jyor} {sd} ／ 前走パドック {n}頭 (暫定・枠順未確定/五十音順)"
    out = os.path.join(REPO, f"paddock_2026_{short}.html")
    args = [sys.executable, os.path.join(BASE, "gen_still.py"), data_path, title, h1, header, out]
    args += ["", ""]  # no stats/records for provisional pass
    if course:
        args += [course]
    subprocess.run(args, check=True)
    summary.append((short, rid, rname, jyor, sd, n, course or "(none)"))

print("=== SUMMARY ===")
for s in summary:
    print(s)
