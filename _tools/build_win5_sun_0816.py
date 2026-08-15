#!/usr/bin/env python3
# Sunday 8/16 WIN5 rebuild with CONFIRMED 馬番 (枠順確定). Overwrites data/stats/records/html for the 5 Sunday races.
import os, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
RAW = os.path.join(BASE, "sun_raw_0816.tsv")   # num \t name \t prev \t imgid \t pr \t hid
IMG = "https://cdnv2.netkeiba.com/img/paddock/2026/{}.jpg"
MOV = "https://race.netkeiba.com/race/paddock_movie.html?race_id={}&id={}"

# short, rid, racename, jyo+R, surface_dist, date, course_href(or "")
META = [
 ("nagakute","202607020806","長久手特別","中京6R","芝2000m","2026年8月16日","chukyo_2000_corner4.html"),
 ("odoripark","202601010810","大通公園特別","札幌10R","ダ1000m","2026年8月16日",""),
 ("nst","202604020807","NST賞","新潟7R","ダ1200m","2026年8月16日","niigata_dart1200_corner4.html"),
 ("chukyokinen","202607020807","中京記念","中京7R","芝1600m","2026年8月16日","chukyo_1600_corner4.html"),
 ("sapporokinen","202601010811","札幌記念","札幌11R","芝2000m","2026年8月16日","sapporo_2000_corner4.html"),
]

# New horses (no paddock reference) -> append stats(blank)/records if missing
NEW_STATS = {
 "odoripark": ["カッタッパ"],
 "sapporokinen": ["ローシャムパーク", "ホウオウビスケッツ"],
}
NEW_RECS = {
 "odoripark": [("カッタッパ", "0-0-0-0", "1-0-0-1")],
 "sapporokinen": [("ローシャムパーク", "0-0-0-0", "3-3-0-3"), ("ホウオウビスケッツ", "0-0-0-1", "2-1-1-7")],
}

def append_missing(path, names_present_first_col, new_lines):
    have = set()
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            if l.strip():
                have.add(l.split("\t")[0])
    add = [l for l in new_lines if l.split("\t")[0] not in have]
    if add:
        with open(path, "a", encoding="utf-8") as f:
            for l in add:
                f.write(l + "\n")

# parse raw
races = {}; cur = None
for line in open(RAW, encoding="utf-8"):
    line = line.rstrip("\n")
    if line.startswith("#R "):
        cur = line[3:].split()[0]; races[cur] = []
    elif line.strip():
        races[cur].append(line.split("\t"))

summary = []
for short, rid, rname, jyor, sd, date, course in META:
    rows = races.get(rid, [])
    # append new-horse stats/records
    if short in NEW_STATS:
        append_missing(os.path.join(REPO, "stats", f"{short}.tsv"), 0,
                       [n for n in NEW_STATS[short]])
    if short in NEW_RECS:
        append_missing(os.path.join(REPO, "records", f"{short}.tsv"), 0,
                       [f"{n}\t{c}\t{d}" for n, c, d in NEW_RECS[short]])
    # data file (confirmed 馬番)
    data_path = os.path.join(REPO, "data", f"{short}.tsv")
    with open(data_path, "w", encoding="utf-8") as f:
        for r in rows:
            num = r[0] if len(r) > 0 else ""
            nm = r[1] if len(r) > 1 else ""
            prev = r[2] if len(r) > 2 else ""
            imgid = r[3] if len(r) > 3 else ""
            pr = r[4] if len(r) > 4 else ""
            hid = r[5] if len(r) > 5 else ""
            img = IMG.format(imgid) if imgid else ""
            mov = MOV.format(pr, hid) if pr and hid else ""
            f.write(f"{num}\t{nm}\t{prev}\t{img}\t{mov}\n")
    n = len(rows)
    stats_path = os.path.join(REPO, "stats", f"{short}.tsv")
    rec_path = os.path.join(REPO, "records", f"{short}.tsv")
    title = f"{rname} 前走パドック（静止画＋映像リンク）"
    h1 = f"{rname} 前走パドック"
    header = f"{date} {jyor} {sd} ／ 前走パドック {n}頭 (馬番順)"
    out = os.path.join(REPO, f"paddock_2026_{short}.html")
    args = [sys.executable, os.path.join(BASE, "gen_still.py"), data_path, title, h1, header, out, stats_path, rec_path]
    if course:
        args.append(course)
    subprocess.run(args, check=True)
    summary.append((short, rid, rname, jyor, sd, n, course or "(none)"))

print("=== SUMMARY ===")
for s in summary:
    print(s)
