---
name: weekly-win5-update
description: 月/金/土17時にWIN5土日各5レースのパドックページ(静止画+netkeiba映像リンク方式)を生成・更新。馬番未確定時は五十音順(暫定)、金(土曜分確定)・土(日曜分確定)の再実行で確定馬番順に上書き。コース分析リンク(既存のみ)・指数プロファイルPROFが空のコースのみ自動補完・index更新・commitまで(pushなし)
---

＜実行タイミング＞ 月・金・土の17時。狙い: 月曜は枠順(馬番)未確定でも暫定でページを用意し、金曜午後(=土曜レースの馬番確定後)・土曜午後(=日曜レースの馬番確定後)の再実行で確定馬番順に上書きする。馬番が取れなければ五十音順(パドック参照の並び)で暫定生成、取れれば確定馬番順で上書き。各実行で土日両方を最新データで作り直す(既存の該当パドックページ・stats・recordsは上書き)。

# 週次WIN5更新タスク（静止画＋映像リンク方式 / 走行タイプ・指数・成績つき / 馬番グレースフル）

## ⚠️ パドック"映像"は取得不可 → 静止画＋リンク方式
netkeibaのパドックは admint.biz クロスオリジン埋め込みに変わり m3u8(hash+ts)は取得不能(admint直fetch403、race-player403、拡張のネットワーク監視はネストiframe不可視、api_get_race_movieはNG/本文取得不可)。**旧 gen.py + template.html(hls.js) は使わない。** 各カードは cdnv2 の静止パドック画像 ＋ netkeiba のパドック映像ページへのリンクにする。生成器は `_tools/gen_still.py` + `_tools/template_still.html`(リポジトリ既存)。参考実装 `_tools/build_win5_still.py`(生TSVからdata/stats/records/htmlを一括生成)も既存、これを流用/更新するのが速い。

## ⚠️ Cowork URL漏洩検知の回避
JS実行ツールの戻り値にクエリ付きフルURL・生HTML・base64を絶対に含めない。race_id/馬id/馬番/指数/着順は整数、成績はx-x-x-x、cdnv2静止画URLは`?`無しなので可。映像URL(paddock_movie.html?...)は`?`を含むので**戻り値に入れず**、前走race_id(pr)と馬id(hid)を整数で返しPython側で組む。日本語が多いと表示が~1000字で切れるので**行境界で~800字チャンク**に分けwindow配列から1つずつ受け取る(ASCII/日本語どちらでも、URLさえ無ければ可)。

## 環境
- 対象: /Users/takesue/keiba-lap-analysis／公開: https://norimichitakesue2.github.io/keiba-lap-analysis/
- 必須: Chrome起動＋「Claude in Chrome」拡張＋netkeibaプレミアムでログイン済み。
- git(mountは削除不可): 操作前に必ず `find .git -name '*.lock' -type f | while read f; do mv "$f" "$f.old$RANDOM"; done`。**tmp_indexは書ける場所に**(例 `cp .git/index /sessions/.../mnt/outputs/gitidx; GIT_INDEX_FILE=<それ> git add ...`。/tmp は書けないことがある)。commit後 `git reset --mixed HEAD`。"unable to unlink"警告は無害。最後にlock再退避。

## ステップ
### 1. 日付
bashで次の日曜=`date -v +Sun -j +%Y%m%d`、前日の土曜も。
### 2. WIN5対象(土日)
`race.netkeiba.com/top/win5.html?kaisai_date=<日曜>` を開き3〜4秒待つ。現在表示(idx=0=土/親要素classがActive)の5 race_idを整数抽出、`win5.html?idx=1`(日)で日曜5件。race_id=YYYY+JyoCD(2)+回(2)+日目(2)+R(2)。JyoCD英名:01sapporo,02hakodate,03fukushima,04niigata,05tokyo,06nakayama,07chukyo,08kyoto,09hanshin,10kokura。土曜開催無しの週は日曜のみ。
### 3. 各馬の基本(race.netkeibaタブ)
- shutuba.html?race_id=<id>: `.RaceName`/`.RaceData01` から レース名・芝ダ・距離・登録頭数。馬番=`td.Umaban`テキスト(**未確定だと空**→五十音順、確定なら馬番昇順)。
- paddock.html?race_id=<id> 生HTML→DOMParse。`.ReferencePaddockListItem`(name重複排除)。各馬: 名=`.ReferencePaddockHorse`、前走説明=`.ReferencePaddockName`(レース名+着)+' '+`.ReferencePaddockDate`(日付+場+芝ダ距離)、静止画imgid=`img`srcの`/paddock/2026/<ID>.jpg`のID(例 `86926_0` のようにアンダースコアを含むので正規表現は `([\w]+)` で拾う)、pr/hid=参照リンク(`paddock_movie`優先)hrefの`race_id=`/`id=`。
- 収集は window に貯め、行境界チャンクで受け取り、bash側で生TSV `名\t前走\timgid\tpr\thid`(#R見出し付)に保存。
- ※shutuba/paddock/result 等 race.netkeiba は **UTF-8**(`res.text()`。EUC-JP指定は文字化けするので不可)。db.netkeiba のみ EUC-JP。
### 4. 走行タイプ・タイム指数マスター(前走 result.html) ※検証済みセレクタ
各馬 前走 `race.netkeiba.com/race/result.html?race_id=<pr>` fetch(同一オリジン、resultドキュメントはprで重複するのでキャッシュ)。DOMParse後:
- **タイム指数マスター**: `#lap_summary` テーブル内で対象馬行(`a[href*="/horse/<hid>"]`を含むtr)の `.IndexMasterCell` を4つ = 全体/スタート/追走/上がり(0〜200整数のみ有効、範囲外/空は空欄)。
- **走行タイプ**: RunTypeは別テーブル。`[...doc.querySelectorAll('table')].find(tb=>tb.querySelector('.RunType'))` で走行解析テーブルを取り、対象馬行の `.RunType` テキスト(例 先行型/持続型/耐久型/加速型/終い伸び型、「加速型(ストライド走法)」等の括弧付きもそのまま)。
- 名前キーで `stats/<short>.tsv`: `名\t走行タイプ\t全体\tS\t追\t上`。gen_still.pyが取り込み(指数105+は金枠、走行タイプは色分け)。
### 5. 当該コース/距離成績(db.netkeiba) ※検証済み
別タブを `https://db.netkeiba.com/horse/<任意hid>/` にnavigateして db.netkeiba 同一オリジン化 → 各馬 `/horse/result/<hid>/` fetch。**EUC-JP**: `new TextDecoder('euc-jp').decode(await res.arrayBuffer())`。`table.db_h_race_results` の `tbody tr` 各行(td数<15はスキップ): 開催=td[1](例"1函館9"→数字を除いて場漢字"函館")、距離=td[14](`(芝|ダ|障)(\d+)`)、着順=td[11](整数)。同距離=芝ダ+距離一致、同コース=同距離かつ場一致。着順1/2/3/着外で `w-p-s-o` を集計。名前キーで `records/<short>.tsv`: `名\t同コース\t同距離`。対象各レースの狙い(場・芝ダ・距離)は基本情報から。※未確定週は登録が多く重いので、余裕が無ければ省略可(空欄で綺麗に縮退)。
### 6. ページ生成
`data/<short>.tsv`(`num\t名\t前走\t静止画URL\t映像URL`。num=馬番or空、静止画=`https://cdnv2.netkeiba.com/img/paddock/2026/<imgid>.jpg`、映像=`https://race.netkeiba.com/race/paddock_movie.html?race_id=<pr>&id=<hid>`)を書き、`python3 _tools/gen_still.py data/<short>.tsv "<title>" "<h1>" "<header_span>" paddock_2026_<short>.html stats/<short>.tsv records/<short>.tsv [course_href]`。header_span=`<実日付> <場R> <芝ダ距離> ／ 前走パドック <n>頭 (馬番順)`、未確定週は末尾 `(暫定・枠順未確定/五十音順)`。course_hrefはコース分析ページ既存時のみ(命名: 芝`<英名>_<距離>_corner4.html`、ダ`<英名>_dart<距離>_corner4.html`、例外 阪神芝1600=corner4_full.html)。無ければ省略しリンク無し。<short>は既存 paddock_2026_* と非衝突(同レースは踏襲し上書き)。
### 7. index.html(折りたたみUI既存・壊さない)
`<div class="section-title">パドック映像比較</div>` 直後の**先頭**に、日付グループを**日→土順**で追加。各グループ=`group-title`(日付+WIN5バッジ、未確定は`<span class="cnt">暫定・枠順未確定/五十音順</span>`) + `grid` に5枚の `<a class="course-card turf|dirt" href="paddock_2026_<short>.html">`(既存カード同形式: course-label/course-name/course-meta/dev-tags/arrow。dev-tagは「前走パドック」「静止画+映像リンク」)。同レースのカードが既にあれば重複追加せず差し替え。既存の他カードは非破壊。

### 7.4 コース分析ページ(新テンプレ) 新規作成 ※任意・可能なら
今週WIN5コースの `<course>_corner4.html` が無い場合、新テンプレ `_tools/template_corner4_idx.html` で新規作成可能(生成器 `_tools/build_corner4_idx.py` = CORNER/DEV/IDX/PROF/PROFD を注入。IDX/PROF/PROFD が空でもテンプレは正常degrade)。データは **netkeiba「勝ち馬サーチ」内部API** から実収集(下記7.5の列挙方式と同じ)。
- **CORNER/DEV(展開×脚質×4角)**: 勝ち馬サーチを `コース(JyoCD)×距離×芝ダ(TrackCDGroup1 1芝/2ダ)×展開(DevelopmentTypeName)×個別ラップ=脚質(LapTypeName)` で絞り、各馬の `JyuniGroup`(コーナー通過順、末尾=4角順位)と `KakuteiJyuni`(着順) を集計。上位3展開のみ掲載。母数=「全脚質ラベル付き馬」= LapTypeName に5脚質を全指定した件数。**手法検証済**(旧ページ nakayama_2000 の CORNER と18/18完全一致)。
- **展開タイプ(訂正)**: 均衡戦/瞬発戦/消耗戦/前残り戦/加速戦/持続戦/ハイペース消耗戦/ハイペース耐久戦/ロングスパート戦 は **勝ち馬サーチのフィルタ条件として存在する**(＝取得可能。旧SKILLの「非公開」は誤り)。cls: 均衡戦=kinko/瞬発戦=shunpatsu/持続戦=jizoku/前残り戦=mae/ハイペース耐久戦=hptai/ハイペース消耗戦=hpsho/ロングスパート戦=longsp/加速戦=kasoku。

### 7.5 指数プロファイル/指数水準 自動補完（PROF優先・空コースのみ / IDX・PROFDは任意）
今週WIN5各コースの分析ページ `<course>_corner4.html`(既存のみ)のうち **`const PROF = {};`(空) のコースだけ** 補完。既にPROFが入っているコース、`DEV`/`CORNER` は触らない。PROF(展開不要)を確実に。IDX(指数水準)・PROFD(展開別)は取れれば入れる任意扱い(展開フィルタ付きAPIは断続500で不安定なため)。

- **⚠️ レース列挙は getSearchRaces API に変更(旧 `db.netkeiba/?pid=race_list` は廃止＝空レスポンス。使うな)**:
  1. `db-search.netkeiba.com/winner_search/list` を開く。検索条件は localStorage.formData に設定: `JyoCD=["<2桁>"]`, `TrackCDGroup1=[1]`(芝)/`[2]`(ダ), `KyoriGroup.Kyori.From=距離; .To=距離`, `DevelopmentTypeName=[]`, `LapTypeName=[]`。設定後 `/winner_search/list` に再navigateで結果表がロードされる。
  2. **動作するPOST bodyを捕捉**(重要): `window.fetch` と `XMLHttpRequest.prototype.send/open` をフックし、結果表ページャ `.CommonPager a` の数字(2など)を1つ `.click()` → フックが捕らえた `winner_search/api/getSearchRaces` の body(`{page, formData}`形式・~2300字)を window に保存。**localStorage.formData だけを自前で組んだbodyは500になる**(APIが要求する完全なformData構造が要る)。実リクエスト捕捉が確実。
  3. その body の `formData` を使い `fetch("https://db-search.netkeiba.com/winner_search/api/getSearchRaces",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({page,formData})})` を `page=1,2,…` でループ。`j.items[].RaceId`(12桁) を重複排除で収集。**ソートは KaisaiDate 降順なので、各itemの `KaisaiDate` が `2024-01-01` 未満になったら打ち切り**(走行タイプ/指数マスターは2024年以降のみ=対象全期間)。`j.total_row`=総件数(50件/頁)。
  4. **⚠️ db-search は連続アクセスを強くthrottleし500を返す(ハードブロックあり)**: 各fetch間に **~4〜5秒**空け、500は数回リトライ(待ち増やし)。ブロック時は **~40秒クールダウン**で回復。1回のJS実行(~45秒上限)では **~7ページずつ**など小分けにし、RaceIdは window に貯めて**分割実行**。※`result.html`(race.netkeiba)側は throttle されないので指数収集は従来通り高速。
  5. (IDX/PROFD をやる場合のみ) 展開別に race→展開 を作るには、上記2のbodyの `formData.DevelopmentTypeName=["<展開>"]` で展開別に列挙して RaceId を集める(展開はレース単位のラベル)。ただしこのフィルタ付きAPIは特に500が多いのでPROF優先、無理なら省略。
- **各レース収集(従来通り)**: `race.netkeiba.com/race/result.html?race_id=<id>` fetch。馬(hid)別に→ 着順=結果表 行先頭td整数、走行タイプ=`.RunType`を持つ表の対象馬行`.RunType`、タイム指数マスター=`#lap_summary`の対象馬行`.IndexMasterCell`×4(全体zen/スタートst/追走ou/上がりri)。戻り値にクエリURL混ぜない・行境界チャンクで受け取る(既存ルール)。PROFは3着内(着順≤3)だけで足りる。
- **PROF算出**(3着内馬=着順≤3 かつ 走行タイプと4指数が揃う馬のみ): ビン `b=clamp(floor(指数/10)-5, 0, 6)`(BINLAB=〜59/60-69/…/110〜)。走行タイプ別に、基準指数 base∈{zen,st,ou,ri} のビンごとに、そのビンに入る馬の**他3指数の中央値(四捨五入)**を出す。他指数の並び OTH= zen:[st,ou,ri] / st:[zen,ou,ri] / ou:[zen,st,ri] / ri:[zen,st,ou]。**各ビン n≥8 のみ採用**。`PROF[走行タイプ]={n:その走行タイプの3着内総数, byBase:{base:[{b,n,m:[3中央値]}], …}}`。採用ビンが1つも無い走行タイプは載せない。全走行タイプで空なら注入しない(母数不足=従来通り空のまま)。
- **IDX算出(任意)**: キー`展開_脚質_<base>`、各馬を base指数のビン `B=clamp(floor(指数/10)-5,0,6)` に振り、ビンごとに件数T・着別K(w-p-s-o)。展開が要るので上記5の race→展開 を使う。
- **注入**: 対象ページの `const PROF = {};` を `const PROF = <JSON.dumps(ensure_ascii=False)>;` に1行置換(IDXをやる場合は `const IDX = {};` も同様、`PROFD = {};`は任意)。node等で `const PROF`/`DEV`/`IDX`/`PROFD` をJSON.parseできること・プロファイルタブ表示パネル数>0を検算。commit対象に含める。
### 8. git(commitまで・pushしない)
ロック退避→ 上記の書ける場所のindexで `git add <生成/更新した個別ファイルのみ>`(無関係な残置はaddしない)→ `git commit -m "Update WIN5 (土日) paddock(静止画+映像リンク+走行/指数/成績) for <週> (<馬番状況>)"`→ reset→ lock再退避。**pushしない**。
### 9. 完了レポート
取得レース(土/日別: race_id数字+レース名+場/距離/登録頭数)、馬番確定状況(確定/五十音)、生成/上書きファイル、コースリンク無しレース、走行/指数/成績の取得率、PROF/IDX補完したコース(あれば)、index差分、`cd ~/keiba-lap-analysis && git push` を促す。

## 約束
push禁止／既存コース再生成しない(**例外: 指数プロファイルPROFが空のコースはPROF(可能ならIDXも)補完可。DEV/CORNERは触らない**)／戻り値にクエリURL・生HTML・base64を混ぜない／index既存カード非破壊。カードは馬番確定時は実馬番順、未確定時は五十音順＋header明記。走行タイプ/指数/成績は取れた馬のみ(空欄で縮退)。映像は静止画＋netkeibaリンク。**レース列挙は getSearchRaces API(旧 race_list は廃止)。db-search は連続アクセスで500するのでペース配分。** 将来 m3u8(hash+ts)が再取得可能になれば旧方式復帰を検討(本ファイルも更新)。
