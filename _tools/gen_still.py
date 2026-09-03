#!/usr/bin/env python3
# Still-image + external movie-link paddock page generator.
# data TSV columns: num \t name \t prev \t img_url \t movie_url
#   (num may be empty when 枠順 is not confirmed -> provisional/五十音 order)
# stats TSV: name \t 走行タイプ \t 全体 \t S \t 追 \t 上
# records TSV: name \t 同コース(x-x-x-x) \t 同距離(x-x-x-x)
import re, json, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
TPL = open(os.path.join(BASE, "template_still.html"), encoding="utf-8").read()


def load_stats(path):
    stats = {}
    if not path or not os.path.exists(path):
        return stats
    def clamp(x):
        x = (x or "").strip()
        return x if (x.isdigit() and 0 <= int(x) <= 200) else ""
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        stats[p[0]] = {
            "typ": p[1] if len(p) > 1 else "",
            "zen": clamp(p[2] if len(p) > 2 else ""),
            "st": clamp(p[3] if len(p) > 3 else ""),
            "ch": clamp(p[4] if len(p) > 4 else ""),
            "ag": clamp(p[5] if len(p) > 5 else ""),
        }
    return stats


def load_records(path):
    recs = {}
    if not path or not os.path.exists(path):
        return recs
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        recs[p[0]] = {"cr": p[1] if len(p) > 1 else "", "dr": p[2] if len(p) > 2 else ""}
    return recs


def load_raceana(path, race_id):
    """走行解析(newspaper_master)由来: レース要約 + 各馬の過去走ベース指数プロフィール"""
    if not path or not os.path.exists(path) or not race_id:
        return None, {}
    summary, per, cur = None, {}, False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        if p[0] == "#R":
            cur = (len(p) > 1 and p[1] == str(race_id))
            if cur:
                summary = {
                    "dist": p[2] if len(p) > 2 else "", "n": p[3] if len(p) > 3 else "",
                    "top3": p[4] if len(p) > 4 else "", "line": p[5] if len(p) > 5 else "",
                    "zmed": p[6] if len(p) > 6 else "", "run": p[7] if len(p) > 7 else "",
                    "dev": p[8] if len(p) > 8 else "",
                }
            continue
        if cur and len(p) >= 8:
            per[p[0]] = {"arun": p[1], "zmax": p[2], "azmed": p[3],
                         "asmed": p[4], "aomed": p[5], "armed": p[6],
                         "an": p[7], "asame": p[8] if len(p) > 8 else "0"}
    return summary, per


def _stat(vals):
    """[max, 上位3の3番目(=要求ライン), 中央値]"""
    v = sorted([x for x in vals if x is not None], reverse=True)
    if not v:
        return None
    line = v[2] if len(v) >= 3 else v[-1]
    s = sorted(v)
    med = s[len(s)//2] if len(s) % 2 else round((s[len(s)//2-1]+s[len(s)//2])/2)
    return {"max": v[0], "line": line, "med": med}


def race_ana_html(summary, per=None):
    if not summary:
        return ""
    # タイム指数マスター4指標の要求水準（各馬の代表値=同距離優先の中央値）
    per = per or {}
    def col(key):
        out = []
        for d in per.values():
            x = d.get(key, "")
            if str(x).isdigit():
                out.append(int(x))
        return _stat(out)
    MASTER = [("全体", "azmed"), ("スタート", "asmed"), ("追走", "aomed"), ("上がり", "armed")]
    cells = []
    for lab, k in MASTER:
        st = col(k)
        if not st:
            cells.append(f'<div class="mx-col"><div class="mx-lab">{lab}</div><div class="mx-line">—</div></div>')
            continue
        cells.append(
            f'<div class="mx-col"><div class="mx-lab">{lab}</div>'
            f'<div class="mx-line">{st["line"]}</div>'
            f'<div class="mx-sub">最高{st["max"]} / 中{st["med"]}</div></div>')
    master_html = ('<div class="ra-lab2">タイム指数マスター 要求水準（上位3頭目 / 最高・中央値）</div>'
                   '<div class="mx-grid">' + "".join(cells) + '</div>')

    def chips(s, cls):
        out = []
        for it in (s or "").split(","):
            it = it.strip()
            if not it or ":" not in it:
                continue
            k, v = it.rsplit(":", 1)
            out.append(f'<span class="ra-chip {cls}">{k}<b>{v}</b></span>')
        return "".join(out)
    top3 = (summary.get("top3") or "").split("/")
    t1 = top3[0] if top3 else "-"
    return (
        '<div class="race-ana">'
        '<div class="ra-title">レース分析<span class="ra-sub">走行解析（各馬の過去走・同距離優先）より</span></div>'
        + master_html +
        '<div class="ra-row" style="margin-top:8px">'
        f'<div class="ra-box"><div class="ra-lab">全体指数の勝ち負けライン</div>'
        f'<div class="ra-big">{summary.get("line","-")}</div>'
        f'<div class="ra-note">自己最高の上位3頭 {summary.get("top3","-")}</div></div>'
        f'<div class="ra-box"><div class="ra-lab">出走メンバー</div>'
        f'<div class="ra-big">{summary.get("n","-")}<span style="font-size:12px">頭</span></div>'
        f'<div class="ra-note">{summary.get("dist","")} ／ 中央値 {summary.get("zmed","-")}</div></div>'
        '</div>'
        f'<div class="ra-lab2">脚質構成</div><div class="ra-chips">{chips(summary.get("run"),"rt")}</div>'
        f'<div class="ra-lab2">メンバーが経験した展開</div><div class="ra-chips">{chips(summary.get("dev"),"dv")}</div>'
        '</div>'
    )


RA_CSS = """
.race-ana{padding:10px 14px;background:var(--s1);border-bottom:1px solid var(--bd);flex-shrink:0;}
.ra-title{font-size:12px;font-weight:700;color:var(--gold);letter-spacing:.05em;margin-bottom:8px;}
.ra-sub{font-size:10px;color:var(--muted);font-weight:400;margin-left:8px;}
.ra-row{display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;}
.ra-box{background:var(--s2);border:1px solid var(--bd2);border-radius:5px;padding:7px 12px;min-width:150px;}
.ra-lab{font-size:10px;color:var(--muted);margin-bottom:2px;}
.ra-big{font-size:20px;font-weight:600;font-family:monospace;color:var(--text);line-height:1.1;}
.ra-note{font-size:10px;color:var(--muted);margin-top:2px;font-family:monospace;}
.ra-lab2{font-size:10px;color:var(--muted);margin:6px 0 3px;}
.ra-chips{display:flex;gap:5px;flex-wrap:wrap;}
.ra-chip{font-size:10px;padding:2px 7px;border-radius:3px;border:1px solid var(--bd2);background:var(--s2);color:var(--muted);}
.ra-chip b{font-family:monospace;color:var(--text);margin-left:4px;font-weight:600;}
.ra-chip.rt{border-color:#3a5a8a;}
.ra-chip.dv{border-color:#5a4a3a;}
.mx-grid{display:flex;gap:6px;flex-wrap:wrap;}
.mx-col{flex:1;min-width:78px;background:var(--s2);border:1px solid var(--bd2);border-radius:5px;padding:6px 8px;text-align:center;}
.mx-lab{font-size:10px;color:var(--muted);margin-bottom:2px;}
.mx-line{font-family:monospace;font-size:19px;font-weight:600;color:var(--gold);line-height:1.1;}
.mx-sub{font-family:monospace;font-size:9px;color:var(--muted);margin-top:2px;}
"""


def build(tsv, title, h1, header_span, out, stats_path=None, rec_path=None, course_href=None,
          raceana_path=None, race_id=None):
    stats = load_stats(stats_path)
    recs = load_records(rec_path)
    ana_sum, ana_per = load_raceana(raceana_path, race_id)
    videos = []
    for line in open(tsv, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        num = p[0] if len(p) > 0 else ""
        name = p[1] if len(p) > 1 else ""
        prev = p[2] if len(p) > 2 else ""
        img = p[3] if len(p) > 3 else ""
        movie = p[4] if len(p) > 4 else ""
        rec = {"num": num, "name": name, "prev": prev, "img": img, "movie": movie}
        rec.update(stats.get(name, {}))
        rec.update(recs.get(name, {}))
        rec.update(ana_per.get(name, {}))
        videos.append(rec)
    n = len(videos)
    vjson = json.dumps(videos, ensure_ascii=False)
    html = TPL
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1, flags=re.S)
    html = re.sub(r"<h1>🏇 .*?</h1>", f"<h1>🏇 {h1}</h1>", html, count=1, flags=re.S)
    html = re.sub(r'(<span style="font-size:11px;color:var\(--muted\)">)2026年[^<]*(</span>)',
                  rf'\g<1>{header_span}\g<2>', html, count=1)
    html = re.sub(r"const VIDEOS=\[\];", "const VIDEOS=" + vjson + ";", html, count=1)
    # レース分析セクション + CSS を挿入
    ra = race_ana_html(ana_sum, ana_per)
    if ra:
        html = html.replace("</style>", RA_CSS + "</style>", 1)
        m = re.search(r'(<div class="note">.*?</div>)', html, flags=re.S)
        if m:
            html = html.replace(m.group(1), m.group(1) + "\n" + ra, 1)
    if course_href:
        html = html.replace("__COURSE_HREF__", course_href)
    else:
        html = re.sub(r'\s*<a class="course-link"[^>]*>.*?</a>', "", html, count=1, flags=re.S)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    withv = sum(1 for v in videos if v["img"] or v["movie"])
    print(f"{os.path.basename(out)}: {n} horses, {withv} with paddock link")


if __name__ == "__main__":
    stats_path = sys.argv[6] if len(sys.argv) > 6 else None
    rec_path = sys.argv[7] if len(sys.argv) > 7 else None
    course_href = sys.argv[8] if len(sys.argv) > 8 else None
    raceana_path = sys.argv[9] if len(sys.argv) > 9 else None
    race_id = sys.argv[10] if len(sys.argv) > 10 else None
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], stats_path, rec_path, course_href,
          raceana_path, race_id)
