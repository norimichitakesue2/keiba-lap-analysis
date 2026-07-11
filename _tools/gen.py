#!/usr/bin/env python3
import re, json, sys, os

PREFIX = "https://race-player.netkeiba.com/5e4a7effafe26"
BASE = os.path.dirname(os.path.abspath(__file__))
TPL = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()

def load_stats(stats_path):
    """name -> {typ, zen, st, ch, ag} with index clamping (valid 0..200)."""
    stats = {}
    if not stats_path or not os.path.exists(stats_path):
        return stats
    def clamp(x):
        x = (x or "").strip()
        return x if (x.isdigit() and 0 <= int(x) <= 200) else ""
    for line in open(stats_path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        name = p[0]
        stats[name] = {
            "typ": p[1] if len(p) > 1 else "",
            "zen": clamp(p[2] if len(p) > 2 else ""),
            "st": clamp(p[3] if len(p) > 3 else ""),
            "ch": clamp(p[4] if len(p) > 4 else ""),
            "ag": clamp(p[5] if len(p) > 5 else ""),
        }
    return stats


def load_records(rec_path):
    """name -> {cr, dr} same-course / same-distance records (x-x-x-x)."""
    recs = {}
    if not rec_path or not os.path.exists(rec_path):
        return recs
    for line in open(rec_path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        p = line.split("\t")
        recs[p[0]] = {"cr": p[1] if len(p) > 1 else "", "dr": p[2] if len(p) > 2 else ""}
    return recs


def build(tsv_path, title, h1, header_span, out_path, stats_path=None, rec_path=None, course_href=None):
    stats = load_stats(stats_path)
    recs = load_records(rec_path)
    videos = []
    for line in open(tsv_path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        num, name, prev = parts[0], parts[1], parts[2]
        h = parts[3] if len(parts) > 3 else ""
        ts = parts[4] if len(parts) > 4 else ""
        if h and ts:
            m3u8 = f"{PREFIX}/media/{h}/{ts}.m3u8"
            thumb = f"{PREFIX}/thumbnail/{h}/{ts}.0000000.jpg"
        else:
            m3u8 = None
            thumb = None
        rec = {"num": num, "name": name, "prev": prev, "m3u8": m3u8, "thumb": thumb}
        s = stats.get(name)
        if s:
            rec.update(s)
        rr = recs.get(name)
        if rr:
            rec.update(rr)
        videos.append(rec)
    n = len(videos)
    vjson = json.dumps(videos, ensure_ascii=False)
    html = TPL
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1, flags=re.S)
    html = re.sub(r"<h1>🏇 .*?</h1>", f"<h1>🏇 {h1}</h1>", html, count=1, flags=re.S)
    html = re.sub(r'(<span style="font-size:11px;color:var\(--muted\)">)2026年[^<]*(</span>)',
                  rf'\g<1>{header_span}\g<2>', html, count=1)
    html = re.sub(r'(id="count-label">)\d+頭表示中(<)', rf'\g<1>{n}頭表示中\g<2>', html, count=1)
    html = re.sub(r"const VIDEOS=\[.*?\];", "const VIDEOS=" + vjson + ";", html, count=1, flags=re.S)
    if course_href:
        html = html.replace("__COURSE_HREF__", course_href)
    else:
        html = re.sub(r'\s*<a class="course-link"[^>]*>.*?</a>', "", html, count=1, flags=re.S)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    withv = sum(1 for v in videos if v["m3u8"])
    print(f"{os.path.basename(out_path)}: {n} horses, {withv} with video")

if __name__ == "__main__":
    # args: tsv, title, h1, header_span, out, [stats_tsv], [records_tsv], [course_href]
    stats_path = sys.argv[6] if len(sys.argv) > 6 else None
    rec_path = sys.argv[7] if len(sys.argv) > 7 else None
    course_href = sys.argv[8] if len(sys.argv) > 8 else None
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], stats_path, rec_path, course_href)
