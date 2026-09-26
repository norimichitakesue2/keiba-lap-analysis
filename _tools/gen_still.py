#!/usr/bin/env python3
# Still-image + external movie-link paddock page generator.
# data TSV columns: num \t name \t prev \t img_url \t movie_url
#   (num may be empty when 枠順 is not confirmed -> provisional/五十音 order)
# stats TSV: name \t 走行タイプ \t 全体 \t S \t 追 \t 上
# records TSV: name \t 同コース(x-x-x-x) \t 同距離(x-x-x-x)
import re, json, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
TPL = open(os.path.join(BASE, "template_still.html"), encoding="utf-8").read()
MIKATA_CSS = """
.mikata{margin:0 14px 10px;background:var(--s1);border:1px solid var(--bd);border-radius:6px;overflow:hidden;}
.mikata>summary{cursor:pointer;list-style:none;padding:10px 14px;font-size:13px;font-weight:700;color:var(--gold);display:flex;align-items:center;gap:8px;user-select:none;}
.mikata>summary::-webkit-details-marker{display:none;}
.mikata>summary::before{content:"\25B6";font-size:10px;color:var(--muted);transition:transform .15s;}
.mikata[open]>summary::before{transform:rotate(90deg);}
.mk-hint{font-size:10px;font-weight:400;color:var(--muted);margin-left:auto;}
.mk-body{padding:2px 14px 8px;}
.mk-sec{margin:9px 0;}
.mk-sec h4{font-size:12px;color:var(--gold);margin:0 0 3px;border-left:3px solid var(--gold);padding-left:7px;font-weight:700;}
.mk-sec p{font-size:12.5px;line-height:1.7;color:var(--text);margin:0;}
.mk-sec b{color:var(--text);}
.mk-cav{font-size:10px;color:var(--muted);padding:0 14px 10px;line-height:1.5;}
"""


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
    # 勝ち馬の4角位置を起点にした前後半3Fセット表
    wp = [x for x in h["winpos"].split(",") if x]
    f3l = [x for x in h["f3"].split(",") if x]
    b3l = [x for x in h["b3"].split(",") if x]
    eds = []
    for i, y in enumerate(yrs):
        if i >= len(wp) or i >= len(f3l) or i >= len(b3l):
            continue
        eds.append({"y": y, "p": int(wp[i]), "f": float(f3l[i]), "b": float(b3l[i])})
    eds.sort(key=lambda e: e["p"])
    prow = []
    for e in eds:
        d = e["f"] - e["b"]
        dc = "fast" if d <= -0.5 else ("slow" if d >= 0.5 else "")
        pos = "front" if e["p"] <= 3 else ("mid" if e["p"] <= 6 else "back")
        prow.append(f'<tr><td class="pt-y">{e["y"]}</td>'
                    f'<td class="pt-p {pos}">{e["p"]}番手</td>'
                    f'<td class="pt-v">{e["f"]:.1f}</td><td class="pt-v">{e["b"]:.1f}</td>'
                    f'<td class="pt-d {dc}">{d:+.1f}</td></tr>')
    BANDS = [("1-3番手", 1, 3), ("4-6番手", 4, 6), ("7番手～", 7, 99)]
    brow = []
    for lab, lo, hi in BANDS:
        g = [e for e in eds if lo <= e["p"] <= hi]
        if not g:
            continue
        af = sum(e["f"] for e in g) / len(g)
        ab = sum(e["b"] for e in g) / len(g)
        d = af - ab
        dc = "fast" if d <= -0.5 else ("slow" if d >= 0.5 else "")
        brow.append(f'<tr><td class="pt-y">{len(g)}回</td>'
                    f'<td class="pt-p">{lab}で決着</td>'
                    f'<td class="pt-v">{af:.1f}</td><td class="pt-v">{ab:.1f}</td>'
                    f'<td class="pt-d {dc}">{d:+.1f}</td></tr>')
    pace_tbl = ('<div class="ra-lab2">勝ち馬の4角位置 × 前後半3F'
                '<span class="ra-hint">（4角位置の昇順。差＝前半3F−後半3F。マイナスほど前傾＝ハイペース、プラスは後傾＝上がり勝負）</span></div>'
                '<table class="pt-tbl"><thead><tr><th>年</th><th>勝ち馬の4角</th>'
                '<th>前半3F</th><th>後半3F</th><th>差</th></tr></thead>'
                '<tbody>' + "".join(prow) + '</tbody>'
                + ('<tfoot>' + "".join(brow) + '</tfoot>' if brow else '')
                + '</table>') if prow else ""

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
        + pace_tbl +
        f'<div class="ra-lab2">上がり3F最速馬の着順'
        f'<span class="ra-hint">（3着内率 {in3}%）</span></div>'
        f'<div class="ra-chips">{zipchips(h["fast"], "fq", lambda v: v + "着")}</div>'
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
.pt-tbl{width:100%;max-width:470px;border-collapse:collapse;background:var(--s1);border:1px solid var(--bd2);border-radius:5px;overflow:hidden;margin-bottom:2px;}
.pt-tbl th{font-size:9px;color:var(--muted);font-weight:400;padding:3px 6px;background:var(--s3);border-bottom:1px solid var(--bd);text-align:center;white-space:nowrap;}
.pt-tbl td{padding:3px 6px;border-bottom:1px solid var(--bd);font-size:11px;font-family:monospace;text-align:center;}
.pt-tbl tbody tr:last-child td{border-bottom:2px solid var(--bd2);}
.pt-tbl tfoot td{background:var(--s3);font-weight:600;border-bottom:1px solid var(--bd);}
.pt-tbl tfoot tr:last-child td{border-bottom:none;}
.pt-y{color:var(--muted);font-size:10px;width:44px;}
.pt-p{font-size:11px;color:var(--text);white-space:nowrap;width:92px;}
.pt-p.front{color:var(--orange);}
.pt-p.mid{color:var(--text);}
.pt-p.back{color:var(--blue);}
.pt-v{font-size:12px;color:var(--text);width:52px;}
.pt-d{font-size:12px;color:var(--muted);width:46px;}
.pt-d.fast{color:var(--red);}
.pt-d.slow{color:var(--blue);}
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
    panes = []
    ra = race_ana_html(ana_sum, ana_per)
    if ra:
        html = html.replace("</style>", RA_CSS + "</style>", 1)
        panes.append(('<div class="pane" data-pane="ana" data-pane-label="レース分析" hidden>'
                      + ra + '</div>'))
    hh = hist_html(hist, hist_proxy)
    if hh:
        if HIST_CSS not in html:
            html = html.replace("</style>", HIST_CSS + "</style>", 1)
        panes.append((f'<div class="pane" data-pane="hist" data-pane-label="過去{hist["n"]}年" hidden>'
                      + hh + '</div>'))
    if panes:
        m = re.search(r'<div class="grid-wrap pane"[^>]*>.*?</div></div>', html, flags=re.S)
        if m:
            html = html.replace(m.group(0), m.group(0) + "\n" + "\n".join(panes), 1)
    # 見立て(mikata)アコーディオン: mikata/<short>.html があれば上部に任意開閉で注入
    mk=""
    msrc=None
    mm=re.search(r'paddock_2026_([A-Za-z0-9_]+)\.html', os.path.basename(out))
    if mm:
        cand=os.path.join(os.path.dirname(os.path.abspath(out)) or ".", "mikata", mm.group(1)+".html")
        if os.path.exists(cand):
            msrc=cand
    if msrc:
        frag=open(msrc, encoding="utf-8").read().strip()
        if MIKATA_CSS not in html:
            html = html.replace("</style>", MIKATA_CSS + "</style>", 1)
        mk=('<details class="mikata"><summary>\U0001F9E0 \u898b\u7acb\u3066\uff08\u30c7\u30fc\u30bf\u5206\u6790\uff09'
            '<span class="mk-hint">\u30bf\u30c3\u30d7\u3067\u958b\u9589</span></summary>'
            '<div class="mk-body">'+frag+'</div>'
            '<div class="mk-cav">\u203b\u30b5\u30a4\u30c8\u306e\u8d70\u884c\u89e3\u6790\u30d9\u30fc\u30b9\u306e\u76f8\u5bfe\u6307\u6a19\u306b\u3088\u308b\u6574\u7406\u3067\u3001\u7684\u4e2d\u3092\u4fdd\u8a3c\u3059\u308b\u3082\u306e\u3067\u306f\u3042\u308a\u307e\u305b\u3093\u3002</div>'
            '</details>')
    html = html.replace("<!--MIKATA-->", mk, 1)
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
