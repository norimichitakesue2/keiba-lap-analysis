#!/usr/bin/env python3
import json, re, os
REPO="/sessions/clever-cool-babbage/mnt/keiba-lap-analysis"
agg=json.load(open("/sessions/clever-cool-babbage/mnt/outputs/sapporo_dart1000_agg.json"))
tpl=open(os.path.join(REPO,"kokura_dart1000_corner4.html"),encoding="utf-8").read().splitlines(keepends=True)

CORNER=json.dumps(agg["corner"],ensure_ascii=False)
DEV=json.dumps(agg["dev"],ensure_ascii=False)

# hint items sorted by races desc
COL={"kinko":"#5b9cf6","hptai":"#e05555","hpsho":"#a080f0"}
hint=sorted(agg["hint"],key=lambda h:-h["races"])
sumR=agg["sumTotal"]
hint_html=[]
for h in hint:
    pct=round(h["runners"]/sumR*100,1)
    hint_html.append(f'  <div class="hint-item"><span class="hdot" style="background:{COL[h["cls"]]}"></span>{h["name"]} {h["runners"]}件({pct}%)</div>\n')
hint_html.append('  <div class="hint-item" style="margin-left:auto">ラップタイプをクリックで 4角順位別成績を表示</div>\n')

out=[]
in_hint=False
for ln in tpl:
    if ln.startswith("const CORNER = "):
        out.append(f"const CORNER = {CORNER};\n"); continue
    if ln.startswith("const DEV = "):
        out.append(f"const DEV = {DEV};\n"); continue
    if "<h1>小倉ダ1000m" in ln:
        out.append('  <h1>札幌ダ1000m｜展開×ラップ×4角分析</h1>\n'); continue
    if 'class="chip"' in ln:
        out.append(f'  <span class="chip">{sumR}件 / 札幌 ダ1000m</span>\n'); continue
    if "netkeiba勝ち馬サーチより集計" in ln:
        out.append('  <p>netkeiba勝ち馬サーチ＋ラップ分析より集計（走行タイプ対応の2024〜2026年 全42R・459頭）／ 上位3展開タイプ（合計 100.0%）を掲載</p>\n'); continue
    if "<title>" in ln and "小倉ダ1000m" in ln:
        out.append("<title>札幌ダ1000m 展開×ラップ×4角分析</title>\n"); continue
    if '<div class="hint-bar">' in ln:
        out.append(ln); in_hint=True
        for hh in hint_html: out.append(hh)
        continue
    if in_hint:
        if "</div>" in ln and 'hint-item' not in ln:
            in_hint=False; out.append(ln)
        # skip original hint-item lines
        continue
    out.append(ln)

open(os.path.join(REPO,"sapporo_dart1000_corner4.html"),"w",encoding="utf-8").write("".join(out))
print("written sapporo_dart1000_corner4.html")
