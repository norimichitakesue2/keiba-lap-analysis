---
name: weekly-win5-update
description: 月/金/土17時にWIN5土日各5レースのパドックページ(静止画+netkeiba映像リンク方式/レース分析つき)を生成・更新。馬番未確定時は五十音順(暫定)、金(土曜分確定)・土(日曜分確定)の再実行で確定馬番順に上書き。走行解析(最大20走)から走行タイプ別の要求指数プロフィールを算出・掲載。同レース過去N年傾向(hist10・勝ち馬サーチ由来/N=0は月曜も収集・条件変更は代用proxy明記)を各ページに掲載。コース分析リンク(既存のみ)・指数プロファイルPROFが空のコースのみ自動補完・index更新・commitまで(pushなし)
---

＜実行タイミング＞ 月・金・土の17時。狙い: 月曜は枠順(馬番)未確定でも暫定でページを用意し、金曜午後(=土曜レースの馬番確定後)・土曜午後(=日曜レースの馬番確定後)の再実行で確定馬番順に上書きする。馬番が取れなければ五十音順(パドック参照の並び)で暫定生成、取れれば確定馬番順で上書き。各実行で土日両方を最新データで作り直す(既存の該当パドックページ・stats・records・raceanaは上書き)。

# 週次WIN5更新タスク（静止画＋映像リンク方式 / 走行タイプ・指数・成績・レース分析・過去N年傾向つき / 馬番グレースフル）

## ⚠️ パドック"映像"は取得不可 → 静止画＋リンク方式
netkeibaのパドックは admint.biz クロスオリジン埋め込みに変わり m3u8(hash+ts)は取得不能(admint直fetch403、race-player403、拡張のネットワーク監視はネストiframe不可視、api_get_race_movieはNG/本文取得不可)。**旧 gen.py + template.html(hls.js) は使わない。** 各カードは cdnv2 の静止パドック画像 ＋ netkeiba のパドック映像ページへのリンクにする。生成器は `_tools/gen_still.py` + `_tools/template_still.html`(リポジトリ既存)。参考実装 `_tools/build_win5_still.py` も既存。

## ⚠️ Cowork URL漏洩検知の回避
JS実行ツールの戻り値にクエリ付きフルURL・生HTML・base64を絶対に含めない。race_id/馬id/馬番/指数/着順は整数、成績はx-x-x-x、cdnv2静止画URLは`?`無しなので可。映像URL(paddock_movie.html?...)は`?`を含むので**戻り値に入れず**、前走race_id(pr)と馬id(hid)を整数で返しPython側で組む。日本語が多いと表示が~1000字で切れるので**行境界で~800字チャンク**に分けwindow配列から1つずつ受け取る。

## 環境
- 対象: /Users/takesue/keiba-lap-analysis／公開: https://norimichitakesue2.github.io/keiba-lap-analysis/
- 必須: Chrome起動＋「Claude in Chrome」拡張＋netkeibaプレミアムでログイン済み。
- git(mountは削除不可): 操作前に必ず `find .git -name '*.lock' -type f | while read f; do mv "$f" "$f.old$RANDOM"; done`。**tmp_indexは書ける場所に**(例 `cp .git/index /sessions/.../mnt/outputs/gitidx; GIT_INDEX_FILE=<それ> git add ...`)。commit後 `git reset --mixed HEAD`。"unable to unlink"警告は無害。最後にlock再退避。

## ステップ
### 1. 日付
bashで次の日曜=`date -v +Sun -j +%Y%m%d`、前日の土曜も。
### 2. WIN5対象(土日)
`race.netkeiba.com/top/win5.html?kaisai_date=<日曜>` を開き3〜4秒待つ。現在表示(idx=0=土)の5 race_idを整数抽出、`win5.html?idx=1`(日)で日曜5件。**確実には `win5.html?idx=0`(土)/`?idx=1`(日)へ直接navigateし、title「YYYY年M月D日」で土日を確認して取得するのが安全**。race_id=YYYY+JyoCD(2)+回(2)+日目(2)+R(2)。JyoCD英名:01sapporo,02hakodate,03fukushima,04niigata,05tokyo,06nakayama,07chukyo,08kyoto,09hanshin,10kokura。土曜開催無しの週は日曜のみ。
### 3. 各馬の基本(race.netkeibaタブ)
- shutuba.html?race_id=<id>: `.RaceName`/`.RaceData01` から レース名・芝ダ・距離・登録頭数。馬番は行(`.HorseName`を含むtr)の2番目のtd(=枠の次)。td.Umabanクラスが無いテーブルもあるので、行内の数値td/HorseName併用で拾う(**未確定だと空**→五十音順、確定なら馬番昇順)。ヘッダ行(名前="馬名")は除外。取消/非出走馬(馬番欠)は除外。
- paddock.html?race_id=<id> 生HTML→DOMParse。`.ReferencePaddockListItem`(name重複排除)。各馬: 名=`.ReferencePaddockHorse`、前走説明=`.ReferencePaddockName`+' '+`.ReferencePaddockDate`、静止画imgid=`img`srcの`/paddock/2026/<ID>.jpg`のID(例 `86926_0` とアンダースコアを含むので正規表現は `([\w]+)`)、pr/hid=参照リンク(`paddock_movie`優先)hrefの`race_id=`/`id=`。
- 収集は window に貯め、行境界チャンクで受け取り、bash側で生TSV `名\t前走\timgid\tpr\thid`(#R見出し付)に保存。
- ※race.netkeiba は **UTF-8**(`res.text()`。EUC-JP指定は文字化け)。db.netkeiba のみ EUC-JP。
### 4. 走行タイプ・タイム指数マスター(前走 result.html) ※検証済みセレクタ
各馬 前走 `race.netkeiba.com/race/result.html?race_id=<pr>` fetch(同一オリジン、prで重複するのでキャッシュ)。DOMParse後:
- **タイム指数マスター**: `#lap_summary` 内で対象馬行(`a[href*="/horse/<hid>"]`を含むtr)の `.IndexMasterCell` を4つ = 全体/スタート/追走/上がり(0〜200整数のみ有効)。
- **走行タイプ**: `[...doc.querySelectorAll('table')].find(tb=>tb.querySelector('.RunType'))` で走行解析テーブルを取り、対象馬行の `.RunType` テキスト。
- 名前キーで `stats/<short>.tsv`: `名\t走行タイプ\t全体\tS\t追\t上`。※これは**前走1走ぶん**でカード上段に出る。
### 4.5 走行解析＝各馬の過去走まとめ（レース分析の素材）★重要
`race.netkeiba.com/race/newspaper_master.html?race_id=<id>&view_limit=20` を fetch（同一オリジン。**`view_limit` を付けないと5走しか取れない**。20で頭打ち）。
- **⚠️ 生fetchだと最新1走ぶんのPastBoxしか展開されず、残りは `PastBox Past_Dummy`(遅延ロードのプレースホルダ)で空**。全過去走の指数を取るには、当該タブに **navigateしてページを描画→遅延ロード完了を待つ(必要なら各馬をscroll_toで可視化)** してから live DOM を parse する。前週の収集値はレース未開催の間は不変なので、当日再取得できない場合は既存 paddock_2026_<short>.html の `const VIDEOS`(各馬 arun/zmax/azmed/asmed/aomed/armed/an/asame) と レース分析paneから raceana を再構成してもよい(整合担保)。
- DOMParse後: 馬1頭=`dl.HorseList`。馬名=`a[href*="/horse/"]`。過去走1件=`.PastBox`(中身空の Past_Dummy はスキップ)。各 `.PastBox` テキストから正規表現で:
  - 指数＋走行タイプ: `/(\d{2,3})\s*\((\d{2,3})\s*-\s*(\d{2,3})\s*-\s*(\d{2,3})\)\s*(先行型|持続型|耐久型|加速型|終い伸び型)/` → 全体z/スタートs/追走o/上がりr/走行タイプ
  - 展開タイプ: `/(ハイペース消耗戦|ハイペース耐久戦|ロングスパート戦|均衡戦|瞬発戦|消耗戦|前残り戦|加速戦|持続戦)/`
  - 距離: `/(芝|ダ)(\d{3,4})/`
- 各馬の代表値: **同距離の走が2走以上あれば同距離のみ**、無ければ全過去走。z/s/o/r それぞれの**中央値**、zの**最高値**。走行タイプは**最頻値**。
- レース集計: 上位3頭の自己最高z、全体z中央値、脚質構成(走行タイプ別頭数)、メンバー経験の展開分布。
- 出力 `raceana_<週>.tsv`: レース行 `#R\t<race_id>\t<芝ダ距離>\t<頭数>\t<上位3のz(/区切り)>\t<ライン=3頭目>\t<z中央値>\t<脚質構成 型:数,>\t<展開分布 展開:数,>` ＋ 馬行 `名\t走行タイプ\tzmax\tz中\tS中\t追中\t上中\t集計走数\t同距離走数`。
- **⚠️ 4指標を独立集計しないこと**: 全体/S/追走/上がりを別々に上位値取りすると実在しない組合せになる(追走↑は上がり↓の逆相関)。必ず**走行タイプごとに、そのタイプ内で上位半数の馬から4値の中央値**を取ること。
### 4.6 同レース過去N年傾向(hist10) ★過去N年タブの素材 ※未収集(N=0含む)レースは月曜回で必ず収集
`hist/hist10_<年>.tsv`(キー=short、ヘッダ行 `#short\tN\tyears\tband(1-3,4-6,7-9,10-)\twinPos\tfastRank\tfirst3F\tlast3F\twinTime\tmaster(年:着:馬:全:S:追:上)\tnote`) に各WIN5レースの同レース過去最大10年の傾向を保持。**同一レースの過去傾向は毎年ほぼ不変なので、既にキーがあり N≥1 のレースは再収集せず流用**。**⚠️ 過去傾向は枠順に依存しないので、月曜(暫定)回でも見送らず必ず収集する**(月曜で採って金/土に流用するのが本来設計)。**キー未登録・またはN=0で残っているレースは全て収集対象**。1レースあたり数分で全10レース賄えるので「暫定回だから一括N=0」は禁止。
- **⚠️ 過去同レースの特定＝勝ち馬サーチ(winner_search)のRaceName検索が確実(旧 `db.netkeiba/?pid=race_list` は廃止＝空。result.htmlを年ごとに辿る必要もなし)**。手順:
  1. `db-search.netkeiba.com/winner_search/list` を一度開く(既存の `localStorage.formData` が完全な構造テンプレになる。無ければ一度検索して生成)。
  2. `formData` に `RaceName='<レース名の部分一致>'`(例 `オールカマー`/`九十九里`/`ながつき`)と `KaisaiDate={From:'2016-01-01',To:'2025-12-31'}` を設定し **localStorage に保存 → `/winner_search/list` に再navigate**(自前bodyのAPI直POSTは500。localStorage+navigate方式が安定)。**RaceNameは部分一致**(「産経賞オールカマー」も"オールカマー"でヒット)。
  3. 結果表 `table tbody tr` を全ページ収集: 列=馬名/日付/開催/レース名/グレード/映像/距離/馬場/枠番/馬番/性齢/斤量/騎手/人気/**着順(14)**/タイム(15)/着差/**コーナー通過順(17)**/**上がり3F(18)**/オッズ。**全出走馬が1行ずつ出る**(勝ち馬だけではない)ので、これ1枚から band/winPos/fastRank/winTime が全部作れる(result.html不要)。ページ送りは `.CommonPager a` の数字リンクを `.click()`(AJAX・同一コンテキスト維持)。
  4. **必ず今年の条件でフィルタ**: レース名に対象語を含み、かつ **距離列が今年と一致(芝/ダの別も含む)・開催列に今年の場を含む** 行だけ採用。dedupeは 年+馬名+着順。
- **⚠️ 条件変更(距離・馬場・場が過去と違う)を必ず検知**: フィルタ後 N=0 や、距離列に今年の条件が現れない場合は条件変更。**同コース・同距離の代表レースを代用**し、その代表レース名でRaceName検索 → 収集。代用時は **gen_still.py の hist_proxy 引数(第13引数)に「<代表レース>で代用｜<元レース>は20XXから<新条件>に変更」を渡す**(ページに代用注記が出る)。note列にも同条件を明記。例: ながつきS→中山ダ1800(=総武Sで代用)、汐留特別→芝からダ1200(=浦安特別で代用)、白井特別→中山芝1200(=セプテンバーSで代用)。姫路/改修等で場が違う年は除外(noteに明記)。
- **集計(1行)**: band=4角位置帯別(1-3/4-6/7-9/10-)の3着内数/母数(全年通算、コーナー通過順の末尾=4角)、winPos=各年勝ち馬(着順1)の4角位置(年順カンマ)、fastRank=各年の上がり3F最速馬の着順、winTime=各年勝ち時計。**first3F/last3F(前後半3F)とmaster(指数マスター)は勝ち馬サーチに無いため任意**(欲しければ各年 result.html の ラップ集計＋`#lap_summary` から別途。空なら該当サブ表は自動degradeするが、band/上がり/勝ち時計だけで過去N年タブは十分成立)。
- 収集不能/母数不足なら N=0 で行を置く(過去N年タブは非表示に degrade)。gen_still.py が hist_key=short で読み「過去N年」タブ(4角位置帯別3着内率/上がり最速の着順ほか)を出力。**代用レースは hist_proxy 引数で必ず注記**。
### 5. 当該コース/距離成績(db.netkeiba) ※検証済み ★必須(省略しない)
別タブを `https://db.netkeiba.com/horse/<任意hid>/` にnavigateして同一オリジン化 → 各馬 `/horse/result/<hid>/` fetch。**EUC-JP**: `new TextDecoder('euc-jp').decode(await res.arrayBuffer())`。`table.db_h_race_results` の `tbody tr` 各行(td数<15はスキップ): 開催=td[1](例"1函館9"→数字除去で場漢字)、距離=td[14](`(芝|ダ|障)(\d+)`)、着順=td[11]。同距離=芝ダ+距離一致、同コース=同距離かつ場一致。1/2/3/着外で `w-p-s-o` 集計。`records/<short>.tsv`: `名\t同コース\t同距離`。
- **⚠️ recordsは毎回必須。月曜暫定回でも省略しない(先週の確定ページと同構成を保つため)**。gen_still.py はrecords欠落を静かに空欄で通すのでミスに気づけない → 必ず全馬ぶん収集する。
- **重さ対策**: hidはページ間で重複するのでhidキャッシュ、db.netkeibaは連続アクセスで500するので各fetch間に~2秒スペース+リトライ、JS実行45秒上限を避けるため **fire-and-forgetで一括起動→window配列に貯め、`__RECS.length`をポーリングして完了待ち→行境界チャンクで受領**。156頭で~10分。取得後はレース別チェックサム(w-p-s-o総和+頭数)で照合。個々の馬で本当に成績が無い場合のみ 0-0-0-0(それは正常)。
### 6. ページ生成
`data/<short>.tsv`(`num\t名\t前走\t静止画URL\t映像URL`。num=馬番or空、静止画=`https://cdnv2.netkeiba.com/img/paddock/2026/<imgid>.jpg`、映像=`https://race.netkeiba.com/race/paddock_movie.html?race_id=<pr>&id=<hid>`)を書き、
`python3 _tools/gen_still.py data/<short>.tsv "<title>" "<h1>" "<header_span>" paddock_2026_<short>.html stats/<short>.tsv records/<short>.tsv <course_href|""> <raceana.tsvのパス> <race_id> hist/hist10_<年>.tsv <short> ""`
- **⚠️ 引数順: … stats records course_href raceana race_id hist_path hist_key hist_proxy。hist_path/hist_key(=short)/hist_proxy("") を必ず末尾に渡すこと**(省略すると「過去N年」タブが付かない)。course_href が無い場合も空文字 `""` を渡して位置をずらさない。hist10にキーが無い/N=0なら過去N年タブは自動で非表示に degrade。
- header_span=`<実日付> <場R> <芝ダ距離> ／ 前走パドック <n>頭 (馬番順)`、未確定週は末尾 `(暫定・枠順未確定/五十音順)`。course_hrefはコース分析ページ既存時のみ(命名: 芝`<英名>_<距離>_corner4.html`、ダ`<英名>_dart<距離>_corner4.html`、例外 阪神芝1600=corner4_full.html)。
- gen_still.py は raceana から **ヘッダに「レース分析」タブ**(走行タイプ別の要求プロフィール表＋全体指数ライン＋脚質構成＋経験展開)を、hist10 から **「過去N年」タブ**を、各カードに過去走ベースの指数バーを出力する。
### 7. index.html(折りたたみUI既存・壊さない)
`<div class="section-title">パドック映像比較</div>` 直後の**先頭**に、日付グループを**日→土順**で追加。各グループ=`group-title`(日付+WIN5バッジ、未確定は`<span class="cnt">暫定・枠順未確定/五十音順</span>`、確定は`枠順確定・馬番順`) + `grid` に5枚の `<a class="course-card turf|dirt" href="paddock_2026_<short>.html">`(既存カード同形式)。同レースのカードが既にあれば重複追加せず差し替え。**再実行で確定した場合は該当グループの cnt を「枠順確定・馬番順」に更新**。既存の他カードは非破壊。

### 7.4 コース分析ページ(新テンプレ) 新規作成 ※任意・可能なら
`<course>_corner4.html` が無い場合、`_tools/template_corner4_idx.html` + 生成器 `_tools/build_corner4_idx.py`(CORNER/DEV/IDX/PROF/PROFDを注入。IDX/PROF/PROFDが空でも正常degrade)で新規作成可。データは勝ち馬サーチから実収集(下記7.5の列挙方式)。
- **CORNER/DEV**: 勝ち馬サーチを `JyoCD×距離×TrackCDGroup1(1芝/2ダ)×DevelopmentTypeName(展開)×LapTypeName(脚質)` で絞り、各馬の `JyuniGroup`(コーナー通過順の末尾=4角順位)と `KakuteiJyuni`(着順)を集計。上位3展開のみ掲載。母数=LapTypeNameに5脚質を全指定した件数。**手法検証済**(旧nakayama_2000のCORNERと18/18完全一致)。旧テンプレのCORNERはvintage不整合の場合があるので移行より実収集が安全。
- **展開タイプ(訂正)**: 均衡戦/瞬発戦/消耗戦/前残り戦/加速戦/持続戦/ハイペース消耗戦/ハイペース耐久戦/ロングスパート戦 は**勝ち馬サーチのフィルタ条件として実在**(旧SKILLの「非公開」は誤り)。cls: 均衡戦=kinko/瞬発戦=shunpatsu/持続戦=jizoku/前残り戦=mae/ハイペース耐久戦=hptai/ハイペース消耗戦=hpsho/ロングスパート戦=longsp/加速戦=kasoku。

### 7.5 指数プロファイル/指数水準 自動補完（PROF優先・空コースのみ / IDX・PROFDは任意）
今週WIN5各コースの `<course>_corner4.html`(既存のみ)のうち **`const PROF = {};`(空)のコースだけ**補完。既にPROFが入っているコース、`DEV`/`CORNER` は触らない。
- **⚠️ レース列挙は getSearchRaces API(旧 `db.netkeiba/?pid=race_list` は廃止＝空レスポンス。使うな)**:
  1. `db-search.netkeiba.com/winner_search/list` を開く。条件は localStorage.formData に設定: `JyoCD=["<2桁>"]`, `TrackCDGroup1=[1]`(芝)/`[2]`(ダ), `KyoriGroup.Kyori.From/To=距離`, `DevelopmentTypeName=[]`, `LapTypeName=[]`。設定後 `/winner_search/list` に再navigateで結果表がロード。
  2. **動作するPOST bodyを捕捉**(重要): `window.fetch` と `XMLHttpRequest.prototype.send/open` をフックし、ページャ `.CommonPager a` の数字(現在ページと異なるもの)を `.click()` → 捕捉した `winner_search/api/getSearchRaces` の body(`{page, formData}`形式・~2300字)を保存。**localStorage.formDataを自前で組んだbodyは500になる**(APIが要求する完全な構造が要る)。
  3. その formData で `POST winner_search/api/getSearchRaces`(Content-Type: application/json, credentials:"include")を page=1,2,… でループ。`j.items[].RaceId` を重複排除で収集。**KaisaiDate降順なので各itemの `KaisaiDate` が `2024-01-01` 未満になったら打ち切り**。`j.total_row`=総件数(50件/頁)。itemsは RaceId/KettoNum/KakuteiJyuni/JyuniGroup/HaronTimeL3 等を含むが**指数マスター値は含まない**。
  4. **⚠️ 直fetchは断続的に500になる**(間隔を空けると通る場面もあるが不安定。ハードブロック時は~40秒クールダウン)。各fetch間に4〜6秒空け、リトライを入れ、1回のJS実行(~45秒上限)では数ページずつに小分けし window に貯めて分割実行。※画面遷移(navigate)方式の勝ち馬サーチは安定しているので、件数・着別だけで足りるIDXは**遷移方式で取るほうが確実**。
  5. IDXは「展開×脚質×指数レンジ」で絞れば件数＋着別が読めるので**勝ち馬サーチだけで完結**(result.html不要)。PROFは各ビンの他3指数の**中央値**が要るので**実数値が必要**→ result.html の `#lap_summary`。
- **PROF算出**(3着内=着順≤3 かつ走行タイプと4指数が揃う馬): ビン `b=clamp(floor(指数/10)-5,0,6)`(BINLAB=〜59/60-69/…/110〜)。走行タイプ別に、基準指数 base∈{zen,st,ou,ri} のビンごとに、そのビンの馬の**他3指数の中央値**。OTH= zen:[st,ou,ri]/st:[zen,ou,ri]/ou:[zen,st,ri]/ri:[zen,st,ou]。**各ビン n≥8 のみ採用**。`PROF[走行タイプ]={n:3着内総数, byBase:{base:[{b,n,m:[3中央値]}]}}`。全走行タイプで空なら注入しない。
- **IDX算出(任意)**: キー`展開_脚質_<base>`、各馬をビン `B=clamp(floor(指数/10)-5,0,6)` に振り、ビンごとに件数T・着別K(w-p-s-o)。
- **注入**: `const PROF = {};` を `const PROF = <JSON.dumps(ensure_ascii=False)>;` に1行置換(IDXも同様)。node等で JSON.parse できること・プロファイルタブ表示パネル数>0を検算。commit対象に含める。
### 8. git(commitまで・pushしない)
ロック退避→ 書ける場所のindexで `git add <生成/更新した個別ファイルのみ>`(hist10を更新したらそれも含む)→ `git commit -m "Update WIN5 (土日) paddock(静止画+映像リンク+走行/指数/成績+レース分析+過去N年) for <週> (<馬番状況>)"`→ reset→ lock再退避。**pushしない**。
### 9. 完了レポート
取得レース(土/日別: race_id+レース名+場/距離/登録頭数)、馬番確定状況、生成/上書きファイル、コースリンク無しレース、走行/指数/成績の取得率、**走行解析の収集走数(合計)と各レースの要求プロフィール要点**、過去N年(hist10)の新規収集/流用/代用したレース、PROF/IDX補完したコース(あれば)、index差分、`cd ~/keiba-lap-analysis && git push` を促す。

## 約束
push禁止／既存コース再生成しない(**例外: PROFが空のコースはPROF(可能ならIDXも)補完可。DEV/CORNERは触らない**)／戻り値にクエリURL・生HTML・base64を混ぜない／index既存カード非破壊。カードは馬番確定時は実馬番順、未確定時は五十音順＋header明記。走行タイプ/指数は取れた馬のみ(空欄で縮退)。**成績(records)は毎回必須で全馬収集(月曜暫定回も省略しない)—実際に成績が無い馬だけ0-0-0-0**。映像は静止画＋netkeibaリンク。**走行解析は必ず `view_limit=20`。要求指数は4指標を独立集計せず走行タイプ別に算出。過去N年(hist10)は N≥1 の既存キーのみ流用し、**未登録・N=0のレースは月曜(暫定)回でも必ず収集(枠順非依存なので見送り禁止)**。収集は**勝ち馬サーチ(winner_search)のRaceName検索＋localStorage.formData+navigate方式**(旧race_list廃止/result.html年次巡回は不要、全出走馬1枚でband/winPos/fastRank/winTime可)。**条件変更(距離・馬場・場が今年と不一致)は同コース同距離の代表レースで代用し hist_proxy 引数＋noteに明記**。gen_still.py にはhist引数(hist_path/short/hist_proxy)を必ず渡す。** レース列挙は getSearchRaces API(旧 race_list は廃止)、db-searchは連続アクセスで500するのでペース配分。将来 m3u8 が再取得可能になれば旧方式復帰を検討(本ファイルも更新)。
