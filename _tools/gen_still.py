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


def build(tsv, title, h1, header_span, out, stats_path=None, rec_path=None, course_href=None):
    stats = load_stats(stats_path)
    recs = load_records(rec_path)
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
        videos.append(rec)
    n = len(videos)
    vjson = json.dumps(videos, ensure_ascii=False)
    html = TPL
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1, flags=re.S)
    html = re.sub(r"<h1>🏇 .*?</h1>", f"<h1>🏇 {h1}</h1>", html, count=1, flags=re.S)
    html = re.sub(r'(<span style="font-size:11px;color:var\(--muted\)">)2026年[^<]*(</span>)',
                  rf'\g<1>{header_span}\g<2>', html, count=1)
    html = re.sub(r"const VIDEOS=\[\];", "const VIDEOS=" + vjson + ";", html, count=1)
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
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], stats_path, rec_path, course_href)
