# -*- coding: utf-8 -*-
"""見立て(6.5)の数値根拠を指数(スタート/追走/上がり/全体)から機械的に導出する。
usage: python3 _tools/mikata_derive.py <raceana.tsv> <race_id> <short> [芝|ダ]
入力: raceana(各馬 走行タイプ/zmax/z中/S中/追中/上中), stats/<short>.tsv(前走 全体), data/<short>.tsv(馬番)
出力: mikata/derive/<short>.json と標準出力サマリ（文章はこれを根拠に執筆）
"""
import sys, os, json, statistics as st

def med(a):
    a = sorted(a); n = len(a)
    return a[n//2] if n % 2 else (a[n//2-1]+a[n//2])/2

def rank(vals):  # 大きいほど上位、同値は平均順位
    s = sorted(vals.items(), key=lambda kv: -kv[1]); r = {}; i = 0
    while i < len(s):
        j = i
        while j+1 < len(s) and s[j+1][1] == s[i][1]: j += 1
        for k in range(i, j+1): r[s[k][0]] = (i+j)/2+1
        i = j+1
    return r

def main(ana_path, rid, short, surf=""):
    H = {}; hdr = None; cur = None
    for l in open(ana_path, encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if p[0] == "#R": cur = p[1]; hdr = p if cur == rid else hdr; continue
        if cur == rid and len(p) >= 7:
            H[p[0]] = dict(rt=p[1], zmax=int(p[2]), z=int(p[3]), s=int(p[4]), o=int(p[5]), r=int(p[6]))
    num = {}
    dp = f"data/{short}.tsv"
    if os.path.exists(dp):
        for l in open(dp, encoding="utf-8"):
            c = l.rstrip("\n").split("\t")
            if len(c) > 1: num[c[1]] = c[0]
    if num: H = {k: v for k, v in H.items() if k in num}   # 出走馬のみ
    pz = {}
    sp = f"stats/{short}.tsv"
    if os.path.exists(sp):
        for l in open(sp, encoding="utf-8"):
            c = l.rstrip("\n").split("\t")
            if len(c) >= 3 and c[0] in H and c[2].isdigit(): pz[c[0]] = int(c[2])
    n = len(H)
    lab = lambda k: (f"{num[k]} {k}" if num.get(k) else k)
    S = {k: v["s"] for k, v in H.items()}; O = {k: v["o"] for k, v in H.items()}; R = {k: v["r"] for k, v in H.items()}
    # 隊列: スタート上位4頭(同値含む)=先行集団
    s_sorted = sorted(H, key=lambda k: -S[k]); cut = S[s_sorted[min(3, n-1)]]
    front = [k for k in s_sorted if S[k] >= cut]
    o_med, s_med = med(O.values()), med(S.values())
    f_o, f_r = med([O[k] for k in front]), med([R[k] for k in front])
    press = [k for k in H if O[k] >= f_o - 2]          # 位置を取りに行ける追走水準の頭数
    lone = (S[s_sorted[0]] - S[s_sorted[1]] >= 4)        # 抜けた先手候補
    # ペース判定（指数のみ）
    if (len(press)/n >= 0.35) or (f_o - o_med >= 6):
        pace = "速め"; shape = "位置争いが続き中盤が緩まない持続〜前傾"
    elif lone and len(press)/n <= 0.2:
        pace = "遅め"; shape = "単騎先手で隊列が早く決まり、中盤が緩む瞬発戦寄り"
    elif f_o - o_med <= 2 and len(press)/n <= 0.25:
        pace = "遅め"; shape = "追走水準が低く前が楽、上がり勝負"
    else:
        pace = "平均"; shape = "平均ペースの総合力勝負"
    # 要求水準
    req_o = round(o_med)
    req_r = round(f_r + (4 if pace != "遅め" else 2))
    favored = "中団" if pace == "速め" else ("前" if pace == "遅め" else "前〜中団")
    # 地力 = 前走全体 + 過去走中央値全体 の順位和
    rz = rank({k: v["z"] for k, v in H.items()}); rp = rank(pz) if pz else {}
    power = {k: rz[k] + rp.get(k, len(H)) for k in H}
    prank = {k: i+1 for i, k in enumerate(sorted(H, key=lambda k: power[k]))}
    def fit(k):
        ok_o, ok_r = O[k] >= req_o, R[k] >= req_r
        ok_s = (S[k] >= s_med) if pace == "遅め" else True
        if ok_o and ok_r and ok_s: return "◯"
        near = (O[k] >= req_o-2) and (R[k] >= req_r-2)
        return "△" if near else "×"
    fits = {k: fit(k) for k in H}
    order = sorted(H, key=lambda k: power[k])
    marks = {}
    m_fit = [k for k in order if fits[k] == "◯"]
    for k, m in zip(m_fit, ["◎", "○", "○"]): marks[k] = m
    rest = [k for k in order if k not in marks]
    if rest: marks[rest[0]] = "▲"            # 地力最上位の展開不一致馬（理由を文中に明記）
    for k in [k for k in order if fits[k] == "△" and k not in marks][:2]: marks[k] = "△"
    out = dict(race_id=rid, short=short, n=n, pace=pace, shape=shape, favored=favored,
               front=[dict(h=lab(k), S=S[k], o=O[k], r=R[k], rt=H[k]["rt"]) for k in front],
               lone_leader=lone, press_count=len(press), o_med=o_med, s_med=s_med,
               front_o_med=f_o, front_r_med=f_r, req=dict(o=req_o, r=req_r, line=(hdr[5] if hdr else "")),
               table=[dict(h=lab(k), power_rank=prank[k], z=H[k]["z"], pz=pz.get(k), zmax=H[k]["zmax"], S=S[k], o=O[k], r=R[k], rt=H[k]["rt"], fit=fits[k], mark=marks.get(k, "")) for k in order])
    os.makedirs("mikata/derive", exist_ok=True)
    json.dump(out, open(f"mikata/derive/{short}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[{short}] n={n} ペース={pace}（{shape}）有利位置={favored} 先行集団={[(f['h'],f['S'],f['o'],f['r']) for f in out['front']]}")
    print(f"  追走水準: 先行集団中央値{f_o} / 全体中央値{o_med} / 位置を取りに行ける頭数{len(press)} 単騎先手={lone}")
    print(f"  要求: 追走≥{req_o} 上がり≥{req_r} 全体ライン{out['req']['line']}")
    for t in out["table"][:8]:
        print(f"  地力{t['power_rank']:>2} {t['mark']:1} {t['h']} z{t['z']} 前走{t['pz']} S{t['S']} 追{t['o']} 上{t['r']} {t['rt']} 展開{t['fit']}")

if __name__ == "__main__":
    main(*sys.argv[1:5])
