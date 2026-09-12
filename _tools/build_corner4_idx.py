#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_corner4_idx.py  —  コース分析(4角分析)ページ生成器

template_corner4_idx.html に CORNER / DEV(および任意で IDX/PROF/PROFD)を注入して
<course>_corner4.html を生成する。

入力データ(JSON): netkeiba 勝ち馬サーチの走行タイプ(展開×脚質)付き全着順データを
1頭1レコードで並べたもの。
{
  "course_name": "中山芝1800m",      # h1/title用
  "jyo_name": "中山",                # chip用
  "track_dist": "芝1800m",           # chip用
  "period_label": "走行タイプ対応の2024〜2026年", # <p>注記の期間表現
  "records": [ {"dev":"均衡戦","lap":"持続型","corner":5,"chaku":9}, ... ]
}
 - dev  : 展開タイプ(均衡戦/瞬発戦/消耗戦/前残り戦/加速戦/持続戦/
           ハイペース消耗戦/ハイペース耐久戦/ロングスパート戦)
 - lap  : 脚質(先行型/持続型/耐久型/加速型/終い伸び型)
 - corner: 4コーナー通過順位(整数)。取れない周回(新馬の一部等)は省略可(そのレコードは4角集計から除外)
 - chaku : 確定着順(整数)

usage:
  python3 _tools/build_corner4_idx.py <records.json> <out.html> [template]
    template 省略時は _tools/template_corner4_idx.html

任意注入(IDX/PROF/PROFD)は本スクリプトでは空のまま(テンプレートの既定 {} を維持)。
必要なら別途 records に指数を持たせて拡張する。
"""
import sys, os, json, re

# 展開タイプ -> (cls, hint色)   ※template CSS の .dev-name.<cls> に対応
DEV_STYLE = {
    "均衡戦":          ("kinko",     "#5b9cf6"),
    "瞬発戦":          ("shunpatsu", "#f0c040"),
    "持続戦":          ("jizoku",    "#56d08b"),
    "前残り戦":        ("mae",       "#f09050"),
    "加速戦":          ("kasoku",    "#50c0c0"),
    "ロングスパート戦": ("longsp",    "#e088c0"),
    "ハイペース耐久戦": ("hptai",     "#e05555"),
    "ハイペース消耗戦": ("hpsho",     "#a080f0"),
    "消耗戦":          ("shomo",     "#c0c0c0"),
}
LAP_ORDER = ["先行型", "持続型", "耐久型", "加速型", "終い伸び型"]


def wpso(chakus):
    """着順リスト -> (w,p,s,o) 1着/2着/3着/着外 の度数"""
    w = sum(1 for c in chakus if c == 1)
    p = sum(1 for c in chakus if c == 2)
    s = sum(1 for c in chakus if c == 3)
    o = len(chakus) - w - p - s
    return w, p, s, o


def rate(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def build_dev(records):
    """DEV(上位3展開・pctは上位3合計で正規化)を構築"""
    by_dev = {}
    for r in records:
        by_dev.setdefault(r["dev"], []).append(r)
    # 上位3展開(頭数)
    ranked = sorted(by_dev.items(), key=lambda kv: len(kv[1]), reverse=True)
    top3 = ranked[:3]
    top3_sum = sum(len(v) for _, v in top3) or 1
    dev = []
    for name, recs in top3:
        cls = DEV_STYLE.get(name, ("shomo", "#c0c0c0"))[0]
        w, p, s, o = wpso([r["chaku"] for r in recs])
        tot = len(recs)
        # 脚質別
        laps = []
        by_lap = {}
        for r in recs:
            by_lap.setdefault(r["lap"], []).append(r)
        for lap in sorted(by_lap, key=lambda l: (LAP_ORDER.index(l) if l in LAP_ORDER else 99)):
            lr = by_lap[lap]
            lw, lp, ls, lo = wpso([x["chaku"] for x in lr])
            lt = len(lr)
            laps.append({
                "name": lap, "total": lt,
                "results": f"{lw}-{lp}-{ls}-{lo}",
                "winRate": f"{rate(lw,lt)}%", "placeRate": f"{rate(lw+lp,lt)}%",
                "showRate": f"{rate(lw+lp+ls,lt)}%",
            })
        laps.sort(key=lambda d: d["total"], reverse=True)
        dev.append({
            "name": name, "cls": cls, "total": tot,
            "pct": f"{rate(tot, top3_sum)}%",
            "results": f"{w}-{p}-{s}-{o}",
            "winRate": f"{rate(w,tot)}%", "placeRate": f"{rate(w+p,tot)}%",
            "showRate": f"{rate(w+p+s,tot)}%",
            "laps": laps,
        })
    return dev, [name for name, _ in top3]


def build_corner(records, top3_devs):
    """CORNER[dev_lap] = [{I,T,K,W,D,P}] を構築(上位3展開のみ)"""
    corner = {}
    for r in records:
        if r["dev"] not in top3_devs:
            continue
        if r.get("corner") in (None, "", 0):
            continue  # 4角順位なしは除外
        key = f'{r["dev"]}_{r["lap"]}'
        corner.setdefault(key, {}).setdefault(int(r["corner"]), []).append(int(r["chaku"]))
    out = {}
    for key, bypos in corner.items():
        rows = []
        for I in sorted(bypos):
            chakus = bypos[I]
            w, p, s, o = wpso(chakus)
            T = len(chakus)
            rows.append({"I": I, "T": T, "K": f"{w}-{p}-{s}-{o}",
                         "W": rate(w, T), "D": rate(w + p, T), "P": rate(w + p + s, T)})
        out[key] = rows
    return out


def inject(template, course_name, jyo_name, track_dist, period_label, dev, corner):
    h = template
    total = sum(d["total"] for d in dev)
    # <title>
    h = re.sub(r"<title>.*?</title>",
               f"<title>{course_name} 展開×ラップ×4角分析</title>", h, count=1, flags=re.S)
    # <h1>
    h = re.sub(r"<h1>.*?</h1>",
               f"<h1>{course_name}｜展開×ラップ×4角分析</h1>", h, count=1, flags=re.S)
    # chip
    h = re.sub(r'<span class="chip">.*?</span>',
               f'<span class="chip">{total}件 / {jyo_name} {track_dist}</span>', h, count=1, flags=re.S)
    # <p> 注記
    pct_sum = round(sum(float(d["pct"].rstrip("%")) for d in dev), 1)
    note = (f'netkeiba勝ち馬サーチ＋走行タイプ分析より集計（{period_label} {total}頭）'
            f'／ 上位{len(dev)}展開タイプ（合計 {pct_sum}%）を掲載')
    h = re.sub(r"(<div class=\"ph\">.*?)<p>.*?</p>", lambda m: m.group(1) + f"<p>{note}</p>",
               h, count=1, flags=re.S)
    # hint-bar
    hints = "".join(
        f'\n  <div class="hint-item"><span class="hdot" style="background:{DEV_STYLE.get(d["name"],("shomo","#c0c0c0"))[1]}"></span>{d["name"]} {d["total"]}件({d["pct"]})</div>'
        for d in dev)
    hints += '\n  <div class="hint-item" style="margin-left:auto">ラップタイプをクリック → 4角順位別／指数水準／指数プロファイルを切替</div>'
    h = re.sub(r'(<div class="hint-bar">).*?(</div>\s*\n\s*<div class="container")',
               lambda m: m.group(1) + hints + "\n" + m.group(2), h, count=1, flags=re.S)
    # CORNER / DEV
    h = re.sub(r"const CORNER = \{.*?\};",
               "const CORNER = " + json.dumps(corner, ensure_ascii=False) + ";", h, count=1, flags=re.S)
    h = re.sub(r"const DEV = \[.*?\];",
               "const DEV = " + json.dumps(dev, ensure_ascii=False) + ";", h, count=1, flags=re.S)
    return h


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    tpl = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "template_corner4_idx.html")
    data = json.load(open(src, encoding="utf-8"))
    recs = data["records"]
    dev, top3 = build_dev(recs)
    corner = build_corner(recs, top3)
    template = open(tpl, encoding="utf-8").read()
    html = inject(template, data["course_name"], data["jyo_name"], data["track_dist"],
                  data.get("period_label", "走行タイプ対応期間"), dev, corner)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{os.path.basename(out)}: {sum(d['total'] for d in dev)} horses, top3={top3}, "
          f"CORNER keys={len(corner)}")


if __name__ == "__main__":
    main()
