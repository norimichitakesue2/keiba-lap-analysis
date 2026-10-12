import re,statistics as S,collections
races=[];cur=None
for l in open('review/res_1010-11.txt'):
    l=l.strip()
    if l.startswith('#'):
        rid,short,lap,c4=l[1:].split('|'); cur=dict(rid=rid,short=short,lap=lap,c4=c4); races.append(cur)
    else:
        cur['rows']=[dict(zip(['fin','um','name','pop','l3'],x.split(':'))) for x in l.split(',')]
def c4pos(s):
    s=s.replace('*','');pos={};p=1
    for tok in re.findall(r'\([^)]*\)|\d+',s):
        nums=re.findall(r'\d+',tok)
        for n in nums: pos[n]=p
        p+=len(nums)
    return pos
def laps(s): return [float(x) for x in re.findall(r'\d+\.\d',s)]
ana={};cur=None
for l in open('raceana_20261011.tsv'):
    p=l.rstrip('\n').split('\t')
    if p[0]=='#R': cur=p[1]; ana[cur]={}
    else: ana[cur][p[0]]=dict(rt=p[1],zmax=int(p[2]),z=int(p[3]),s=int(p[4]),o=int(p[5]),r=int(p[6]))
SIG=['zmax','z','s','o','r','pz','pr','pop']
hit=collections.defaultdict(list); out=[]
for R in races:
    A=ana[R['rid']]; pos=c4pos(R['c4']); L=laps(R['lap'])
    st={l.split('\t')[0]:l.rstrip('\n').split('\t') for l in open(f"stats/{R['short']}.tsv") if l.strip()}
    n=len(R['rows'])
    for h in R['rows']:
        a=A.get(h['name'],{}); h.update(a); h['c4']=pos.get(h['um'])
        s=st.get(h['name']); 
        h['pz']=int(s[2]) if s and s[2].isdigit() else None; h['pr']=int(s[5]) if s and s[5].isdigit() else None
        h['ptype']=s[1] if s else ''
        h['pop']=-int(h['pop'])
    # mikata picks
    mk=open(f"mikata/{R['short']}.html").read(); i=mk.find('有力馬')
    picks=re.findall(r'([◎○▲△注☆])\s*(\d+)\s',re.sub('<[^>]+>','',mk[i:]))
    if not picks: picks=[('-',m) for m in re.findall(r'<b>(\d+) ',mk[i:])]
    fin={h['um']:h['fin'] for h in R['rows']}
    top3=[h for h in R['rows'] if h['fin'] in('1','2','3')]
    f3=sum(L[:3]) if len(L)>=6 else None; b3=sum(L[-3:])
    out.append(f"\n## {R['short']} n={n} 前3F={f3:.1f} 後3F={b3:.1f} 差={b3-f3:+.1f}")
    out.append("  見立て: "+' '.join(f"{m}{u}→{fin.get(u,'?')}着" for m,u in picks))
    for h in top3:
        out.append(f"  {h['fin']}着 {h['um']} {h['name']} 人{-h['pop']} 4角{h['c4']}/{n} 上{h['l3']} | {h.get('rt','')} zmax{h.get('zmax')} z{h.get('z')} S{h.get('s')} 追{h.get('o')} 上{h.get('r')} | 前走{h['ptype']} {h['pz']}/{h['pr']}")
    for sg in SIG:
        v=[h for h in R['rows'] if h.get(sg) is not None]
        rk=sorted(v,key=lambda h:-h[sg])
        top=[h['um'] for h in rk[:3]]
        hit[sg].append(sum(1 for h in top3 if h['um'] in top))
    # pos band of top3
    for h in top3:
        b=h['c4']/n if h['c4'] else None
        hit['posfrac'].append(round(b,2) if b else None)
    # 4角1-3番手の成績
    hit['front3'].append(sum(1 for h in top3 if h['c4'] and h['c4']<=3))
    hit['l3best'].append(min(R['rows'],key=lambda h:float(h['l3']))['fin'])
print('\n'.join(out))
print('\n=== 各指標の上位3頭に3着内馬が何頭入ったか（10R合計/30）')
for sg in SIG: print(sg,sum(hit[sg]),hit[sg])
print('3着内の4角相対位置',hit['posfrac'])
print('3着内のうち4角1-3番手',sum(hit['front3']),hit['front3'])
print('上がり最速馬の着順',hit['l3best'])
print('\n=== 芝/ダ別')
DIRT={'jra50','goryo','tvshizuoka','uzumasa'}
for lab,grp in (('芝',[r for r in races if r['short'] not in DIRT]),('ダ',[r for r in races if r['short'] in DIRT])):
    res={}
    for sg in SIG:
        t=0
        for R in grp:
            v=[h for h in R['rows'] if h.get(sg) is not None]; top=[h['um'] for h in sorted(v,key=lambda h:-h[sg])[:3]]
            t+=sum(1 for h in R['rows'] if h['fin'] in('1','2','3') and h['um'] in top)
        res[sg]=t
    print(lab,len(grp)*3,res)
    print('  3着内の4角1-3番手',sum(1 for R in grp for h in R['rows'] if h['fin'] in('1','2','3') and h['c4'] and h['c4']<=3))
