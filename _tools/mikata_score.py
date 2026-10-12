# -*- coding: utf-8 -*-
"""見立ての読みを採点して review/mikata_log.tsv に追記する（月曜回で前週末分を実行）。
usage: python3 _tools/mikata_score.py review/res_<YYYYMMDD>.txt
結果ファイル形式（ブラウザで result.html から作成）:
  #<race_id>|<short>|<芝|ダ>|<ラップ(連結可 例 12.411.0...)>|<4角通過順(例 (*8,7,4)(2,6)...)>
  <着順>:<馬番>:<馬名>:<人気>:<上がり3F>,<...>   ← 1行に全馬
採点: ①ペース(実際=前後半の1F平均差を芝/ダ基準値と比較) ②有利位置(3着内の4角相対位置の平均)
      ③要求プロファイル(3着内のうち展開◯/△の頭数 vs 出走中の◯比率) ④◎の着順(参考)
予測は mikata/derive/<short>.json（レース前に保存されたもの）を使う。
"""
import sys, re, json, os
BASE = {"芝": 0.18, "ダ": -0.07}   # 9/5-10/12 70Rの中央値(前半平均-後半平均, 秒/F)。後付け調整しない
def c4pos(s):
    s = s.replace("*", ""); pos = {}; p = 1
    for tok in re.findall(r"\([^)]*\)|\d+", s):
        ns = re.findall(r"\d+", tok)
        for x in ns: pos[x] = p
        p += len(ns)
    return pos
def main(path):
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    out = []
    for i in range(0, len(lines), 2):
        rid, short, surf, lap, c4 = lines[i][1:].split("|")
        rows = [dict(zip(["fin", "um", "name", "pop", "l3"], x.split(":"))) for x in lines[i+1].split(",")]
        dj = f"mikata/derive/{short}.json"
        if not os.path.exists(dj): out.append(f"{rid}\t{short}\tNO_DERIVE"); continue
        d = json.load(open(dj, encoding="utf-8"))
        L = [float(x) for x in re.findall(r"\d+\.\d", lap)]
        if L and L[0] < 9: L = L[1:]
        h = len(L)//2; diff = sum(L[:h])/h - sum(L[-h:])/h - BASE.get(surf, 0)
        act_pace = "遅め" if diff > 0.12 else ("速め" if diff < -0.12 else "平均")
        pos = c4pos(c4); n = len(rows)
        top3 = [r for r in rows if r["fin"] in ("1", "2", "3")]
        rel = [pos[r["um"]]/n for r in top3 if r["um"] in pos]
        m = sum(rel)/len(rel) if rel else None
        act_pos = None if m is None else ("前" if m < 0.33 else ("前〜中団" if m <= 0.5 else "中団"))
        fit = {t["h"].split(" ")[0]: t["fit"] for t in d["table"]}
        mark = {t["h"].split(" ")[0]: t["mark"] for t in d["table"] if t["mark"]}
        f3 = sum(1 for r in top3 if fit.get(r["um"]) == "◯"); f3t = sum(1 for r in top3 if fit.get(r["um"]) == "△")
        share = sum(1 for v in fit.values() if v == "◯")/max(1, len(fit))
        hon = next((r["fin"] for r in rows if mark.get(r["um"]) == "◎"), "-")
        out.append("\t".join(map(str, [rid, short, surf, d["pace"], act_pace, int(d["pace"] == act_pace), d["favored"], act_pos,
                   int(d["favored"] == act_pos), f"{f3}/{len(top3)}", f3t, f"{share:.2f}", hon, f"{diff:+.2f}"])))
    log = "review/mikata_log.tsv"
    new = not os.path.exists(log)
    with open(log, "a", encoding="utf-8") as f:
        if new: f.write("#race_id\tshort\t芝ダ\t予測ペース\t実ペース\tペース的中\t予測有利位置\t実有利位置\t位置的中\t3着内の展開◯\t3着内の展開△\t出走中◯比率\t◎着順\t実ペース差\n")
        f.write("\n".join(out)+"\n")
    print("\n".join(out))
if __name__ == "__main__":
    main(sys.argv[1])
