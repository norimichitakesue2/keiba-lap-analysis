#!/usr/bin/env python3
# Monday provisional build (枠順未確定 -> 五十音順, num blank) for 8/22-8/23 WIN5.
import os, subprocess, sys
BASE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.dirname(BASE)
RAW="/sessions/kind-stoic-volta/mnt/outputs/win5_raw_0817.tsv"
IMG="https://cdnv2.netkeiba.com/img/paddock/2026/{}.jpg"
MOV="https://race.netkeiba.com/race/paddock_movie.html?race_id={}&id={}"
# short, rid, racename, jyor, surface_dist, date, course_href
META=[
 ("oobu","202607030106","大府特別","中京6R","ダ1800m","2026年8月22日","chukyo_dart1800_corner4.html"),
 ("wasj1","202601020110","WASJ第1戦","札幌10R","芝1200m","2026年8月22日","sapporo_1200_corner4.html"),
 ("toki","202604030107","朱鷺S","新潟7R","芝1400m","2026年8月22日","niigata_1400_corner4.html"),
 ("iga","202607030107","伊賀S","中京7R","ダ1400m","2026年8月22日","chukyo_dart1400_corner4.html"),
 ("wasj2","202601020111","WASJ第2戦","札幌11R","芝2000m","2026年8月22日","sapporo_2000_corner4.html"),
 ("arimatsu","202607030206","有松特別","中京6R","芝1600m","2026年8月23日","chukyo_1600_corner4.html"),
 ("wasj3","202601020210","WASJ第3戦","札幌10R","ダ1700m","2026年8月23日",""),
 ("niigata2sai","202604030207","新潟2歳S","新潟7R","芝1600m","2026年8月23日","niigata_1600_corner4.html"),
 ("nagoyajo","202607030207","名古屋城S","中京7R","ダ1800m","2026年8月23日","chukyo_dart1800_corner4.html"),
 ("keeneland","202601020211","キーンランドC","札幌11R","芝1200m","2026年8月23日","sapporo_1200_corner4.html"),
]
races={}; cur=None
for line in open(RAW,encoding="utf-8"):
    line=line.rstrip("\n")
    if line.startswith("#R "): cur=line[3:].split()[0]; races[cur]=[]
    elif line.strip(): races[cur].append(line.split("\t"))
summary=[]
for short,rid,rname,jyor,sd,date,course in META:
    rows=races.get(rid,[])
    data_path=os.path.join(REPO,"data",f"{short}.tsv")
    with open(data_path,"w",encoding="utf-8") as f:
        for r in rows:
            nm=r[0] if len(r)>0 else ""
            prev=r[1] if len(r)>1 else ""
            imgid=r[2] if len(r)>2 else ""
            pr=r[3] if len(r)>3 else ""
            hid=r[4] if len(r)>4 else ""
            img=IMG.format(imgid) if imgid else ""
            mov=MOV.format(pr,hid) if pr and hid else ""
            f.write(f"\t{nm}\t{prev}\t{img}\t{mov}\n")  # num blank
    n=len(rows)
    title=f"{rname} 前走パドック（静止画＋映像リンク）"
    h1=f"{rname} 前走パドック"
    header=f"{date} {jyor} {sd} ／ 前走パドック {n}頭 (馬番順) (暫定・枠順未確定/五十音順)"
    out=os.path.join(REPO,f"paddock_2026_{short}.html")
    args=[sys.executable,os.path.join(BASE,"gen_still.py"),data_path,title,h1,header,out,
          os.path.join(REPO,"stats",f"{short}.tsv"),os.path.join(REPO,"records",f"{short}.tsv")]
    if course: args.append(course)
    subprocess.run(args,check=True)
    summary.append((short,rid,rname,jyor,sd,n,course or "(none)"))
print("=== SUMMARY ===")
for s in summary: print(s)
