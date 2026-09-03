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
    # 走行タイプ別の要求プロフィール（勝ち筋ごとに整合した4値セット）
    per = per or {}
    def med(a):
        a = sorted(a)
        return a[len(a)//2] if len(a) % 2 else round((a[len(a)//2-1]+a[len(a)//2])/2)
    horses = []
    for nm, d in per.items():
        try:
            horses.append({"n": nm, "run": d.get("arun", ""),
                           "z": int(d["azmed"]), "s": int(d["asmed"]),
                           "o": int(d["aomed"]), "r": int(d["armed"])})
        except (ValueError, KeyError, TypeError):
            continue
    ORDER = ["先行型", "持続型", "耐久型", "加速型", "終い伸び型"]
    RCLS = {"先行型": "front", "持続型": "sus", "耐久型": "end", "加速型": "close", "終い伸び型": "close"}
    rowsh = []
    for t in ORDER:
        m = sorted([h for h in horses if h["run"] == t], key=lambda h: -h["z"])
        if not m:
            continue
        top = m[:max(1, round(len(m)/2))]
        z, s, o, r = (med([h[k] for h in top]) for k in ("z", "s", "o", "r"))
        bal = o - r
        tag = "前で押し切る" if bal >= 5 else ("差して勝つ" if bal <= -10 else "中間・立ち回り")
        rowsh.append(
            f'<tr><td class="pf-t"><span class="rtype rt-{RCLS.get(t,"oth")}">{t}</span>'
            f'<span class="pf-n">{len(m)}頭</span></td>'
            f'<td class="pf-tag">{tag}</td>'
            f'<td class="pf-v">{z}</td><td class="pf-v">{s}</td>'
            f'<td class="pf-v hl">{o}</td><td class="pf-v hl">{r}</td>'
            f'<td class="pf-ex">{top[0]["n"]}</td></tr>')
    master_html = (
        '<div class="ra-lab2">走行タイプ別の要求プロフィール'
        '<span class="ra-hint">（各タイプ上位半数の中央値＝勝ち筋ごとに実在する組み合わせ）</span></div>'
        '<table class="pf-tbl"><thead><tr><th>走行タイプ</th><th>勝ち筋</th>'
        '<th>全体</th><th>S</th><th>追走</th><th>上がり</th><th>該当上位</th></tr></thead>'
        '<tbody>' + "".join(rowsh) + '</tbody></table>') if rowsh else ""

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
        '<div class="ra-title">レース分析<span class="ra-sub">走行解析（各馬の過去最大20走・同距離優先）より</span></div>'
        + master_html +
        '<div class="ra-row" style="margin-top:8px">'
        f'<div class="ra-box"><div class="ra-lab">全体指数の勝ち負けライン</div>'
        f'<div class="ra-big">{summary.get("line","-")}</div>'
        f'<div class="ra-note">自己最高の上位3頭 {summary.get("top3","-")}</div></div>'
        f'<div class="ra-box"><div class="ra-lab">出走メンバー</div>'
        f'<div class="ra-big">{summary.get("n","-")}<span style="font-size:12px">頭</span></div>'
        f'<div class="ra-note">{summary.get("dist","")} ／ 中央値 {summary.get("zmed","-")}</div></div>'
        '</div>'
        '<div class="ra-cav">※ 上表は各走行タイプ内で実際に上位の馬から算出しているため、4指標の組み合わせが現実的。'
        '全体指数のラインはメンバーの相対水準であり、コース実績に基づく絶対基準ではありません。</div>'
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
.ra-hint{font-size:9px;color:var(--muted);font-weight:400;margin-left:6px;}
.pf-tbl{width:100%;border-collapse:collapse;background:var(--s2);border:1px solid var(--bd2);border-radius:5px;overflow:hidden;}
.pf-tbl th{font-size:9px;color:var(--muted);font-weight:400;padding:4px 6px;background:var(--s3);border-bottom:1px solid var(--bd);text-align:center;white-space:nowrap;}
.pf-tbl th:first-child,.pf-tbl th:nth-child(2){text-align:left;}
.pf-tbl td{padding:4px 6px;border-bottom:1px solid var(--bd);font-size:11px;}
.pf-tbl tr:last-child td{border-bottom:none;}
.pf-t{white-space:nowrap;}
.pf-n{font-family:monospace;font-size:9px;color:var(--muted);margin-left:5px;}
.pf-tag{font-size:10px;color:var(--muted);white-space:nowrap;}
.pf-v{font-family:monospace;font-size:14px;font-weight:600;text-align:center;color:var(--text);width:44px;}
.pf-v.hl{color:var(--gold);}
.pf-ex{font-size:10px;color:var(--muted);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.ra-cav{font-size:9px;color:var(--muted);margin-top:6px;line-height:1.5;}
"""



def load_hist(path, key):
    """過去10年傾向 (hist10_*.tsv)"""
    if not path or not key or not os.path.exists(path):
        return None
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.rstrip("\n").split("\t")
        if p[0] != key:
            continue
        try:
            n = int(p[1])
        except ValueError:
            n = 0
        return {"key": p[0], "n": n, "years": p[2], "band": p[3], "winpos": p[4],
                "fast": p[5], "f3": p[6], "b3": p[7], "time": p[8],
                "master": p[9] if len(p) > 9 else "", "note": p[10] if len(p) > 10 else ""}
    return None


def hist_html(h, proxy=""):
    if not h or h["n"] == 0:
        return ""
    BAND = ["1-3番手", "4-6番手", "7-9番手", "10番手～"]
    cells = []
    for lab, sp in zip(BAND, h["band"].split(",")):
        try:
            hit, tot = (int(x) for x in sp.split("/"))
        except ValueError:
            continue
        r = round(hit / tot * 100) if tot else 0
        w = max(2, r)
        cells.append(f'<div class="hb-row"><span class="hb-lab">{lab}</span>'
                     f'<span class="hb-bar"><i style="width:{w}%"></i></span>'
                     f'<span class="hb-val">{r}%</span>'
                     f'<span class="hb-n">{hit}/{tot}</span></div>')
    yrs = h["years"].split(",")

    def zipchips(vals, cls, fmt=lambda v: v):
        out = []
        for y, v in zip(yrs, vals.split(",")):
            out.append(f'<span class="hs-chip {cls}"><i>{y[2:]}</i>{fmt(v)}</span>')
        return "".join(out)

    def med(vals):
        a = sorted(float(x) for x in vals.split(",") if x)
        if not a:
            return "-"
        m = a[len(a)//2] if len(a) % 2 else (a[len(a)//2-1]+a[len(a)//2])/2
        return f"{m:g}"
    fast = [int(x) for x in h["fast"].split(",") if x]
    in3 = round(sum(1 for x in fast if x <= 3)/len(fast)*100) if fast else 0
    mrows = []
    for it in (h["master"] or "").split(","):
        q = it.split(":")
        if len(q) < 7:
            continue
        mrows.append(f'<tr><td class="hm-y">{q[0]}</td><td class="hm-r">{q[1]}着</td>'
                     f'<td class="hm-h">{q[2]}</td><td class="hm-v">{q[3]}</td>'
                     f'<td class="hm-v">{q[4]}</td><td class="hm-v hl">{q[5]}</td>'
                     f'<td class="hm-v hl">{q[6]}</td></tr>')
    mtbl = ('<div class="ra-lab2">タイム指数マスターの実測値（1〜3着）'
            '<span class="ra-hint">※マスター4値はnetkeibaで2024年以降（重賞は2023年〜）のみ算出</span></div>'
            '<table class="hm-tbl"><thead><tr><th>年</th><th>着</th><th>馬名</th>'
            '<th>全体</th><th>S</th><th>追走</th><th>上がり</th></tr></thead>'
            '<tbody>' + "".join(mrows) + '</tbody></table>') if mrows else ""
    px = f'<span class="hs-proxy">{proxy}</span>' if proxy else ""
    return (
        '<div class="race-ana hist10">'
        f'<div class="ra-title">過去{h["n"]}年の傾向'
        f'<span class="ra-sub">{h["note"]}</span>{px}</div>'
        f'<div class="ra-lab2">4角位置帯別 3着内率<span class="ra-hint">（{h["years"]} 全出走馬）</span></div>'
        f'<div class="hb-wrap">{"".join(cells)}</div>'
        f'<div class="ra-lab2">勝ち馬の4角位置<span class="ra-hint">（中央値 {med(h["winpos"])}番手）</span></div>'
        f'<div class="ra-chips">{zipchips(h["winpos"], "wp", lambda v: v + "番手")}</div>'
        f'<div class="ra-lab2">上がり3F最速馬の着順'
        f'<span class="ra-hint">（3着内率 {in3}%）</span></div>'
        f'<div class="ra-chips">{zipchips(h["fast"], "fq", lambda v: v + "着")}</div>'
        f'<div class="ra-lab2">前半3F<span class="ra-hint">（中央値 {med(h["f3"])}秒）</span></div>'
        f'<div class="ra-chips">{zipchips(h["f3"], "pc")}</div>'
        f'<div class="ra-lab2">後半3F<span class="ra-hint">（中央値 {med(h["b3"])}秒）</span></div>'
        f'<div class="ra-chips">{zipchips(h["b3"], "pc")}</div>'
        + mtbl +
        '<div class="ra-cav">※ 今年と同一競馬場・同一コース・同一距離で行われた回のみを集計。'
        '条件が異なる年は除外しているため、年数が10に満たない場合があります。</div>'
        '</div>'
    )


HIST_CSS = """
.hist10{background:var(--s2);}
.hb-wrap{display:flex;flex-direction:column;gap:3px;max-width:520px;}
.hb-row{display:flex;align-items:center;gap:7px;font-size:10px;}
.hb-lab{width:60px;color:var(--muted);white-space:nowrap;}
.hb-bar{flex:1;height:9px;background:var(--s3);border-radius:2px;overflow:hidden;}
.hb-bar i{display:block;height:100%;background:linear-gradient(90deg,#6b5a1e,var(--gold));}
.hb-val{width:32px;text-align:right;font-family:monospace;font-size:11px;color:var(--text);font-weight:600;}
.hb-n{width:48px;text-align:right;font-family:monospace;font-size:9px;color:var(--muted);}
.hs-chip{font-size:10px;padding:2px 6px;border-radius:3px;border:1px solid var(--bd2);background:var(--s1);font-family:monospace;color:var(--text);}
.hs-chip i{font-style:normal;color:var(--muted);font-size:9px;margin-right:4px;}
.hs-chip.wp{border-color:#3a5a8a;}
.hs-chip.fq{border-color:#6b5a1e;}
.hs-chip.pc{border-color:#2a2a3a;}
.hs-proxy{font-size:10px;color:var(--orange);margin-left:8px;}
.hm-tbl{width:100%;max-width:560px;border-collapse:collapse;background:var(--s1);border:1px solid var(--bd2);border-radius:5px;overflow:hidden;}
.hm-tbl th{font-size:9px;color:var(--muted);font-weight:400;padding:3px 6px;background:var(--s3);border-bottom:1px solid var(--bd);text-align:center;}
.hm-tbl td{padding:3px 6px;border-bottom:1px solid var(--bd);font-size:11px;}
.hm-tbl tr:last-child td{border-bottom:none;}
.hm-y,.hm-r{font-family:monospace;font-size:10px;color:var(--muted);white-space:nowrap;}
.hm-h{font-size:10px;max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.hm-v{font-family:monospace;font-size:12px;text-align:center;color:var(--text);width:40px;}
.hm-v.hl{color:var(--gold);}
"""


def build(tsv, title, h1, header_span, out, stats_path=None, rec_path=None, course_href=None,
          raceana_path=None, race_id=None, hist_path=None, hist_key=None, hist_proxy=""):
    stats = load_stats(stats_path)
    recs = load_records(rec_path)
    ana_sum, ana_per = load_raceana(raceana_path, race_id)
    hist = load_hist(hist_path, hist_key)
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
    hh = hist_html(hist, hist_proxy)
    if hh:
        if HIST_CSS not in html:
            html = html.replace("</style>", HIST_CSS + "</style>", 1)
        anchor = ra if ra and ra in html else None
        if anchor:
            html = html.replace(anchor, anchor + "\n" + hh, 1)
        else:
            m2 = re.search(r'(<div class="note">.*?</div>)', html, flags=re.S)
            if m2:
                html = html.replace(m2.group(1), m2.group(1) + "\n" + hh, 1)
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
    hist_path = sys.argv[11] if len(sys.argv) > 11 else None
    hist_key = sys.argv[12] if len(sys.argv) > 12 else None
    hist_proxy = sys.argv[13] if len(sys.argv) > 13 else ""
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], stats_path, rec_path, course_href,
          raceana_path, race_id, hist_path, hist_key, hist_proxy)
