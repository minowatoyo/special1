# NDLサーチ・CiNii Research・J-STAGE による日本語書誌の一次確認（取得方法・取得ログ・訂正記録）
> 要約: 国立国会図書館サーチ（NDLサーチ）、CiNii Research、J-STAGE の3ホストに 2026-11-11 に計130回アクセスし、日本語の書籍と論文の書誌を目録・論文ページで確認した。NDL と CiNii は OpenSearch API の応答（書誌レコード、CiNii は抄録つき）、J-STAGE は論文ページ（HTML）を取得して読んだ。書籍・論文の本文は読んでいない。
> 本文書は、取得の方法と再現手順（パラメータ、URL の型、制限）、取得ログの集計、既存文書への訂正・追記（LR-043・044・052・053・113 ほか）、取得できなかったものを記録する。NDL は応答の約半数が 429（同時アクセス制限）で、Bulkowski の邦訳などは未確認に残った。CiNii の書誌 JSON は WAF の判定（HTTP 202）で取得できず、回避していない。
> 成果物は [04_learning/02_books_japanese.md](../04_learning/02_books_japanese.md)（§2.4 邦訳の確認表、§2.5 日本語の専門書58点）と [03_evidence/03_japanese_literature.md](../03_evidence/03_japanese_literature.md)（日本語論文）。
> 最終更新: 2026-11-11

## 1. 方法と読み方

- 取得: `curl` のみ。User-Agent は `research-fetch/1.0`。取得ごとに 0.6〜2.5 秒の待機を入れた。取得物は作業用ディレクトリに保存し、全件の URL・取得時刻・HTTP 状態・バイト数・sha256 を CSV（`08_primary_sources/fetch_logs/ndl_cinii_jstage_fetch_log.csv`）に記録した（集計は §3）。生ファイルはリポジトリに含めない（著作権）。解析はファイルを引数に渡す Python（`-I`、標準ライブラリの `xml.etree`・`json`・`re`）で行い、ダウンロードしたものは実行していない。
- 検証区分: 本文書と成果物の ✅P は、次のいずれかを取得して読み、記載の事実を照合したことを指す。①NDL の OpenSearch 応答（書誌レコード）または書誌ページ、②CiNii Research の OpenSearch 応答（書誌と抄録）、③J-STAGE の論文ページ。**書籍・論文の本文は読んでいない**ので、内容の評価ではなく、書誌（題名・著者・出版者・年・ISBN・DOI）と抄録の確認である。
- 出典 ID: PB-001〜029 は NDL の取得物、PB-040〜060 は CiNii の検索の取得物（この文書の出典表）。論文ごとの出典は PB-201 以降（03_japanese_literature.md）。書籍の行は 04_learning/02_books_japanese.md の ID（LR-xxx）と、この文書の PB-0xx を併記する。
- 時間依存: NDL の蔵書や CiNii の収録は日々増える。件数（`totalResults`）は確認日 2026-11-11 の値である。

## 2. 公開インターフェースの動作（再現手順）

### 2.1 NDLサーチ OpenSearch

`https://ndlsearch.ndl.go.jp/api/opensearch?<パラメータ>` に GET する（認証不要）。応答は RSS 2.0＋dcndl 名前空間の XML。日本語はパーセントエンコードする。

| パラメータ | 働き | 確認結果（2026-11-11） |
|---|---|---|
| `title` | 題名 | 動作。空白で区切った複数語は AND（`title=Python 株` は両語を題名に含む4件） |
| `creator` | 創作者 | 動作。標目の形式で原綴りを `姓, 名` と指定すると邦訳も当たる（`Elder, Alexander`）。同姓の別人や記事が混ざる（`Murphy, John J` は 1,829 件） |
| `publisher` | 出版者 | 動作（`publisher=パンローリング`） |
| `any` | 全項目 | 動作（`any=Systematic trading Carver` で目的の邦訳1件と無関係の1件） |
| `ndc` | 日本十進分類 | 動作（`338.183`、`338.15`）。前方一致かどうかは未確認 |
| `from` | 出版年の下限 | 動作とみられる（`from=2005` の結果に 2005 年以前は含まれなかった） |
| `cnt` | 取得件数 | 5・20・40・60・100・200 で動作。200 件で 0.5〜1 MB |
| `idx` | 開始位置（ページ送り） | 試したが 429 で未確認 |
| `dpid=iss-ndl-opac` | 蔵書（NDL の書誌）に限定 | 動作。付けないと雑誌記事索引（`R000000004-…`）が混じる。付けると図書・雑誌・映像資料・学位論文などの蔵書が返る（`category` で区別） |
| `mediatype=1` | 資料種別 | 効かない。0件になり、チャネル題名が「テクニカル分析 1」と出た（"1" が検索語として扱われた。取得 #8） |

- 応答の項目: `link`（NDL の書誌ページ URL、`https://ndlsearch.ndl.go.jp/books/R100000002-I<書誌ID>`）、`dc:title`、`dcndl:volume`（巻次）、`description` 内の「責任表示」（著者・訳者の表記）、`dc:creator`（標目。例「本間, 宗久, 1717-1803」）、`dc:publisher`、`dcterms:issued`（出版年月）、`dc:identifier`（ISBN・JPNO・NDLBibID）、`dc:description`（注記。「原タイトル: …」「監訳: …」「原著第8版の翻訳」など）、`dc:extent`（頁数）、叢書名、`category`（図書／紙、映像資料／記録メディア、記事／紙 など）。邦訳の原著名と版は、この注記から拾える[PB-001][PB-015]。
- 並び順は関連度ではなく、題名の読みの順に近い。上位N件だけを見る使い方では取りこぼしが出る[PB-003][PB-029]。
- `dpid` を付けないと、`title=株価チャート` の 706 件のうち先頭100件の大半が『会社四季報』各号になった[PB-029]。語を絞るか、`ndc`・`publisher` を併用する。
- 1回の応答が大きくなるので、創作者名の検索は同姓の多い名前（Murphy など）を避けるか、題名語を足す[PB-002]。

### 2.2 NDLサーチ SRU（採用しなかった）

`https://ndlsearch.ndl.go.jp/api/sru?operation=searchRetrieve&version=1.2&query=<CQL>` を試した。`recordSchema=dcndl_simple` は「illegal recordSchema value」、`any="…" or any="…"` は「illegal query syntax」だった。`anywhere="…" or anywhere="…"`（`recordSchema=dcndl`）は HTTP 200 だが `numberOfRecords=19339097`（全件に近く、条件が効いていない）だった。OR 検索で邦訳をまとめて引く目的は果たせず、以後は OpenSearch に統一した（取得 #5・#6・#12〜#16）。

### 2.3 NDLサーチ 書誌ページ（HTML）

`https://ndlsearch.ndl.go.jp/books/R100000002-I000007436982` は HTTP 200、446 KB（446,377 バイト）のサーバー描画 HTML で、`<title>` に書名、本文に請求記号・書誌ID・資料種別・著者・出版者・出版年・頁数・NDC、各地の図書館の所蔵が現れる[PB-028]。ISBN は要約部には出ず、OpenSearch の応答で補った。1件（LR-043）だけ取得し、他は OpenSearch の応答で確認した。

### 2.4 CiNii Research OpenSearch

`https://cir.nii.ac.jp/opensearch/articles?q=<語>&count=<件数>&format=json`（論文。`all`・`books` など他の種別は未試験）。応答は JSON-LD で、`items[]` に次がある。

- `title`、`dc:creator[]`、`dc:publisher`、`prism:publicationName`・`prism:volume`・`prism:number`・`prism:startingPage`・`prism:endingPage`・`prism:publicationDate`、`dc:identifier[]`（`cir:DOI`・`cir:NAID`・`cir:NDL_BIB_ID`）、`link`（CRID の URL）。
- `description`（抄録）は、重複を除く361件のレコードのうち198件にあった。ただし中身は、抄録本文のほか、目次だけ、導入の数行だけ、`application/pdf` のようなファイル種別だけのものがある。`dc:subject`（キーワード）、`abstractLicenseFlag`（allow／disallow）もある。
- `q` は題名・キーワード中心に一致するとみられる。長い語句や3語以上は 0 件になりやすい（「移動平均 売買ルール 日経平均」「モメンタム 逆張り 東京証券取引所」「値幅制限 東京証券取引所」「処分効果 個人投資家」はいずれも 0 件）。1〜2語が有効だった。`count=50` まで確認。29回すべて HTTP 200[PB-040]。

### 2.5 CiNii の書誌レコード JSON（取得できなかった）

OpenSearch の `rdfs:seeAlso` が指す `https://cir.nii.ac.jp/crid/<CRID>.json` は、3回とも HTTP 202・本文 0 バイトで、応答ヘッダに `x-amzn-waf-action: challenge`（AWS WAF のボット判定）があった（取得 #67〜#69）。判定を迂回する手段は取らず、「取得不可」とした。抄録は OpenSearch 応答の `description` から読んだ。CRID の URL（`https://cir.nii.ac.jp/crid/<CRID>`）は書誌の識別子として引くにとどまり、ページ自体は取得していない。

### 2.6 J-STAGE の論文ページ

`https://www.jstage.jst.go.jp/article/<誌コード>/<巻>/<号>/<論文ID>/_article/-char/ja/` はサーバー描画の HTML で、`<meta name="citation_title">`・`citation_author`・`citation_journal_title`・`citation_volume`・`citation_firstpage`・`citation_lastpage`・`citation_doi`・`citation_pdf_url`・`citation_keywords`、`<meta name="abstract">`、本文の抄録欄がある。DOI から URL を機械的には組み立てられず、誌ごとに型を試した。

| 誌（コード） | URL の型（`<論文ID>` の部分） | 結果 |
|---|---|---|
| 行動経済学（jbef） | `jbef/<巻>/0/<巻>_<開始頁>` | 10巻・5巻は 200。2・3・4巻の5件（3巻は同じ URL を2回）は 500 |
| 現代ファイナンス（gendaifinance） | `gendaifinance/<巻>/0/<巻>_<開始頁>` | 31巻・28巻とも 200 |
| 電気学会論文誌C（ieejeiss） | `ieejeiss/<巻>/<号>/<巻>_<開始頁>` | 133巻9号は 200。128巻9号（`128_1462`）は 500 |
| 人工知能学会第二種研究会資料（jsaisigtwo） | `jsaisigtwo/<年>/<FIN-0xx>/<年>_<開始頁>` | 7件とも 200 |
| 人工知能学会論文誌（tjsai） | `tjsai/36/5/36_AG21-A` | 500 |

J-STAGE は存在しない（誤った）パスに 404 ではなく **500**（本文に "500 error"）を返す。500 は URL の型の誤りか一時的な障害かを区別できなかったので、該当論文は CiNii の抄録で確認した。

### 2.7 失敗と制限の実態

| 事象 | 件数 | 内容 |
|---|---:|---|
| NDL の HTTP 429 | 39 | 本文は「Too Many Requests／同時アクセス数の上限に達したため、リクエストの制限を行っています」。待機を60秒に延ばしても連続して 429 になる例があり（同一 URL で最多7回）、成功の直後の要求が 429 になる例も、続けて通る例もあって、規則は読み取れなかった |
| NDL のタイムアウト（40〜120秒で打ち切り） | 3 | 最初の動作確認（#2・#3）と Nison の検索（#43） |
| CiNii の HTTP 202 | 3 | §2.5。WAF の判定 |
| J-STAGE の HTTP 500 | 8 | §2.6 |

作業側の誤りも記録する。NDL の取得キューを誤って二重に起動し、06:30〜06:35 UTC ごろ（取得 #59〜#93 付近）は同種の検索が2本並走した。NDL の「同時アクセス数」制限を悪化させた可能性があり、429 の件数に含まれる。発見後に二重のキューを停止した。

## 3. 取得ログの集計

### 3.1 ホスト別・HTTP 状態別（計130件、確認日 2026-11-11）

| ホスト | 要求数 | 200 | 202 | 429 | 500 | 000（タイムアウト） |
|---|---:|---:|---:|---:|---:|---:|
| ndlsearch.ndl.go.jp | 78 | 36 | 0 | 39 | 0 | 3 |
| cir.nii.ac.jp | 32 | 29 | 3 | 0 | 0 | 0 |
| www.jstage.jst.go.jp | 20 | 12 | 0 | 0 | 8 | 0 |
| 合計 | 130 | 77 | 3 | 39 | 8 | 3 |

- NDL の内訳: OpenSearch 70、SRU の試行 7、書誌ページ 1。CiNii の内訳: OpenSearch 29、書誌 JSON 3。J-STAGE の内訳: 論文ページ 20。
- 一意な URL は 89 件。最後まで 200 を得られなかった URL は、§5 に挙げた。
- ログ CSV の列: `n, url, utc, http_status, bytes, sha256, file, note`（#1〜#3 は取得スクリプトを直す前の試行で、時刻と状態は当時の端末出力から復元した。#69 は応答ヘッダだけを見た手動の確認で、本文は保存していない）。

### 3.2 用途別の取得物

- NDL の分野探索（題名検索）: [PB-003][PB-004][PB-005][PB-006][PB-007][PB-008][PB-009][PB-010][PB-011][PB-012][PB-013][PB-029]。出版者×NDC の一覧: [PB-014][PB-015]。
- NDL の邦訳確認（創作者・題名検索）: [PB-002][PB-016][PB-017][PB-018][PB-019][PB-020][PB-021][PB-022][PB-023][PB-024][PB-026][PB-027]。宗久関連: [PB-025]。動作確認と書誌ページ: [PB-001][PB-028]。
- CiNii の論文探索: [PB-040][PB-041][PB-042][PB-043][PB-044][PB-045][PB-046][PB-047][PB-048][PB-049][PB-050][PB-051][PB-052][PB-053][PB-054][PB-055][PB-056][PB-057][PB-058][PB-059][PB-060]。結果が 0〜1 件で論文表に使わなかった検索（#53・#56・#57・#58・#60・#74・#79・#92）は、出典表に載せていない。
- J-STAGE の論文ページ 12 件と CiNii 抄録の出典は、03_japanese_literature.md の出典表（PB-201 以降）にある。

## 4. 訂正・追記ログ

| 対象文書・箇所 | 旧記述（要点） | 一次資料での確認結果 | 対応（訂正／追記／変更なし） |
|---|---|---|---|
| 04_learning/02_books_japanese.md 要約・§1・限界 | 日本語書籍の書誌は検索で確認できた冊数が0、定番13点は記憶ベース | NDL の書誌で LR-043〜LR-056 と LR-111〜114 を照合（LR-045 は一部）。§2.4・§2.5 を追加 | 訂正（要約・§1・限界を更新） |
| 同 §2.1 LR-043 | 日本経済新聞出版（社）、年は未確認 | 編者 日本テクニカルアナリスト協会、出版者 日本経済新聞社、2004.8、685頁、ISBN 4-532-13281-9（書誌ページ #130 と OpenSearch #11） | 訂正（版元表記・年を確定） |
| 同 LR-044 版元 | 経済変動総研 | 出版者は経済変動研究所 | 訂正 |
| 同 LR-044 巻数・年 | 全七巻と記憶、年は未確認 | NDL の蔵書は6冊（1975.3、週間編 1975.3、完結編 1976.7、綜合編 1979.6、綜合編 後編 1980.5、真技能編 1981.12）。7冊目は見当たらない | 訂正（「全七巻」は確認できず）／追記（刊行年） |
| 同 LR-044 著者 | 細田悟一（一目山人） | NDL の著者標目は「一目山人, 1898-1982」。細田悟一の名は取得項目に現れない | 変更なし（二次資料に基づく同一視を残し、NDL で未確認と注記） |
| 同 LR-045 | 全集の版元・年は未確認。『宗久翁相場全集』（1910）・『相場罫線術講義』（1904）の著者・版元も未確認 | 『徳川時代経済秘録全集』安達太郎 編、松山房、1941（複製 1973、玉栄宝資友の会）。『宗久翁相場全集』本間宗久 著・早坂二菊 注、信義堂、1910.4。『相場罫線術講義』は 429 で未確認。全集の所収内容は取得項目に現れない | 追記（書誌）／一部未確認（行の区分は ✅S のまま） |
| 同 LR-046〜LR-051・LR-054・LR-055 | 邦題・版元は記憶（パンローリング等） | すべて NDL の記載と一致。副題・訳者・刊行年・原タイトルを追記 | 変更なし（✅P に変更し、副題・訳者・年を追記） |
| 同 LR-051 | 原著は1989年と記憶 | NDL の取得項目に原著の刊行年はない | 変更なし（未確認のまま） |
| 同 LR-052 | 出版社未確認 | 金融財政事情研究会（きんざい発売）、2019.12、長尾慎太郎・鹿子木亨紀 監訳、大和アセットマネジメント 訳 | 訂正（空欄を補完） |
| 同 LR-053 | 日本経済新聞出版、版数は未確認 | 版ごとに 日本経済新聞社（1993〜2004）、日本経済新聞出版社（2007〜2019）、日経BP 日本経済新聞出版（2023.5）。NDL 注記で原著第7〜13版との対応を確認 | 訂正（版元は版により異なる）／追記（版数） |
| 同 LR-056 | 文庫版の有無は未確認 | ハヤカワ文庫NF 410・411（2014.6）が存在 | 追記 |
| 同 §2.2 末尾 | Nison・Bulkowski・Pring・Weinstein・Darvas・Aronson などの邦訳の有無は確認できていない | Pring・Weinstein・Darvas・Aronson・Edwards & Magee・Bollinger・Elder・Pardo ほかの邦訳を確認。Nison は書籍の邦訳が NDL で確認できない（講義 DVD の記録はある、下記）。Bulkowski は 429 で未確認 | 訂正・追記（§2.4 に表を新設） |
| 同 §1 | 『日本テクニカル分析大全』・細田悟一『一目均衡表』・ニソン著作の邦訳は書誌を確認できなかった | 前2者は NDL に存在。ニソンは書籍の邦訳が見当たらない（講義 DVD『ローソク足のツボ』の記録はある）。この DVD は取りまとめ役が [PB-007] の応答から見つけて追記した | 訂正 |
| 同 LR-111 | 日経文庫、2019年8月刊とされる | 日本経済新聞出版社、日経文庫 1410、2019.8、ISBN 978-4-532-11410-7 | 変更なし（一致） |
| 同 LR-112 | 版元・年は未確認 | 日本経済新聞社（日経文庫）、2005.1、ISBN 4-532-11045-9 | 追記 |
| 同 LR-113 | 林康史 著、日本経済新聞社（古書の出品情報） | 林康史「編著」、日本経済新聞社、1997.9 | 訂正（著→編著） |
| 同 LR-114 | かんき出版（古書の出品情報） | かんき出版、2000.5、ISBN 4-7612-5848-9 | 変更なし（一致）／追記（年） |
| 04_learning/04_organizations_journals_certifications.md §2 日本テクニカルアナリスト協会 | 会報・機関誌の有無は未確認 | 機関誌『テクニカルアナリストジャーナル』（Technical analysts journal、発行 日本テクニカルアナリスト協会、東京）の論文記録が CiNii にある（第2号 2015〜第8号 2021） | 追記 |
| 同 §4 証券アナリストジャーナル | 日本証券アナリスト協会発行と記憶（⚠M） | 発行 日本証券アナリスト協会（東京）、ISSN 0287-7929、CiNii に 45巻6号（2007）〜64巻6号（2026-06）の記録 | 追記（LR-091 を ✅P に変更） |
| 同 §4 会社四季報・日経マネー | 発行元は記憶（⚠M） | 『会社四季報』は東洋経済新報社（NDL、[1936]-）、『日経マネー』は日経BP（CiNii、1985-、ISSN 0911-9361）。日経ヴェリタス・ダイヤモンドZAi は未確認 | 追記（根拠行 PB-102・PB-103 を新設。LR-092 は ⚠M のまま） |
| 03_evidence/02_methodology_behavioral_japan_ml.md §C-6 | 日本語文献は未確認（CiNii・J-STAGE を直接検索する必要） | CiNii・J-STAGE で日本語論文を確認し、03_japanese_literature.md にまとめた | 追記が必要（02 側は担当外のため未編集） |
| README.md §5 限界2 | 日本語書籍の定番13点は記憶ベース、日本語の学術文献も未確認 | 上記のとおり確認済み | 追記が必要（README はリード担当のため未編集） |

## 5. 取得できなかった・確認できなかったもの

- **NDL の 429 で未確認**: Bulkowski の邦訳（`creator=Bulkowski, Thomas N` を7回）、『相場罫線術講義』（1904年。`title=相場罫線術` を3回）、`idx=201` によるページ送り（取得 #128）、題名「需給」の検索（取得 #129）。同じ URL の再試行は2回までという方針を、Bulkowski の検索（7回）では超えてしまった。取りまとめ役の指示で打ち切り、これらは未確認のまま（✅S／⚠M のまま）にした。
- **CiNii の書誌 JSON**: WAF の判定（202）で取得不可（§2.5）。
- **J-STAGE の 500**: 行動経済学の2・3・4巻（`3_114`・`3_1`・`4_75`・`4_51`・`2_93`）、人工知能学会論文誌 36(5)（`36_AG21-A`）、電気学会論文誌C 128(9)（`128_1462`）。URL の型の誤りか障害か不明。
- **内容は未確認**: 書籍の本文・目次、論文の本文。全集（徳川時代経済秘録全集）に宗久名義の秘録が所収されるか。一目山人と細田悟一の同一性。
- **邦訳の検索を行っていない原著**: Kirkpatrick & Dahlquist、Grimes、Morris、Achelis、Williams、Villahermosa、Ehlers、Chan、Davey、Lo & MacKinlay、Lo。
- **書籍の邦訳が見当たらなかった原著**: Nison（創作者検索のヒットは英語原著2点と仏語訳1点[PB-016]）。ただし、題名「ローソク足」の検索応答（取得 #23、[PB-007]）に、パンローリングの講義 DVD『スティーブ・ニソンの「ローソク足のツボ」』（2006、67分、ISBN 978-4-7759-6181-0）の記録があり、標目の表記ゆれによる漏れは実際に起きていた。取りまとめ役が片仮名で再検索したが（`creator=ニソン` は72件で大半が別人の姓、`creator=スティーブ・ニソン` と `any=スティーブ・ニソン` は0件）、書籍の邦訳の有無は決着していない。

## 6. 再現用コマンド（例）

```
# NDL: 創作者の原綴りで邦訳を引く（蔵書限定、40件）
curl -sS -L -m 60 -A "research-fetch/1.0" -o out.xml \
  "https://ndlsearch.ndl.go.jp/api/opensearch?creator=Elder%2C%20Alexander&dpid=iss-ndl-opac&cnt=40"
# CiNii Research: 論文を題名語で検索（JSON）
curl -sS -L -m 60 -A "research-fetch/1.0" -o out.json \
  "https://cir.nii.ac.jp/opensearch/articles?q=%E5%87%BA%E6%9D%A5%E9%AB%98%20%E6%A0%AA%E4%BE%A1&count=50&format=json"
# J-STAGE: 論文ページ（行動経済学 10巻 22頁）
curl -sS -L -m 60 -A "research-fetch/1.0" -o page.html \
  "https://www.jstage.jst.go.jp/article/jbef/10/0/10_22/_article/-char/ja/"
```

- 429 のときは60秒以上空け、同じ URL は2回までにとどめる。
- 解析は `python -I` で、XML は `xml.etree.ElementTree`（名前空間 `dc`＝`http://purl.org/dc/elements/1.1/`、`dcndl`＝`http://ndl.go.jp/dcndl/terms/`、`dcterms`＝`http://purl.org/dc/terms/`）、CiNii は `json`、J-STAGE は正規表現で `<meta name="citation_*">` と `<meta name="abstract">` を読む。

## 関連文書

- [04_learning/02_books_japanese.md](../04_learning/02_books_japanese.md): 日本語書籍と邦訳の確認表（§2.4）、専門書の書誌（§2.5）
- [04_learning/04_organizations_journals_certifications.md](../04_learning/04_organizations_journals_certifications.md): 協会・雑誌（発行元の確認を追記）
- [03_evidence/03_japanese_literature.md](../03_evidence/03_japanese_literature.md): 日本語の学術文献
- [03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md): 日本語文献は §C-6 で未確認としていた箇所
- [01_jpx_primary.md](01_jpx_primary.md): 同じ方式で JPX を確認した文書

## この文書の限界

- 取得したのは書誌レコード・抄録・論文ページで、書籍・論文の本文は読んでいない。✅P は書誌と抄録の確認である。
- NDL は応答の約半数が 429（同時アクセス制限）で、未確認の項目が残った（§5）。作業側の二重起動が 429 を増やした可能性がある。件数や並び順（題名の読み順に近い）から、上位の取りこぼしがありうる。
- CiNii の書誌 JSON は WAF の判定で取得できず、抄録は OpenSearch 応答の `description` に頼った。抄録が目次や導入だけの論文がある。
- J-STAGE の URL の型は誌ごとの試行で、500 の原因は特定できていない。
- NDL の蔵書に載らない資料（納本されない出版物）、CiNii・J-STAGE に載らない論文は対象外である。
- 件数と収録は確認日 2026-11-11 の値で、日々変わる。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| PB-001 | NDLサーチ OpenSearch: 題名「テクニカル分析」（5件、動作確認） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%83%86%E3%82%AF%E3%83%8B%E3%82%AB%E3%83%AB%E5%88%86%E6%9E%90&cnt=5 | ✅P | 取得日 2026-11-11／sha256:11b07d43f880／取得 #4（12,818 バイト）／確認箇所: 応答は RSS 2.0＋dcndl。totalResults=400（dpid なし）。item に link・dc:title・dc:publisher・dc:identifier（ISBN）・注記（原タイトル）がある。Pring の邦訳（1985）の注記を確認 |
| PB-002 | NDLサーチ OpenSearch: 創作者 Murphy, John J（50件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Murphy%2C%20John%20J&cnt=50 | ✅P | 取得日 2026-11-11／sha256:5a86b00ce311／取得 #7（994,854 バイト）／確認箇所: totalResults=1829、応答 995 KB。同姓の別人・記事が混ざり過広。Murphy 邦訳（2017.12、練習帳 2018.4、先行書 1990.5）の注記を確認 |
| PB-003 | NDLサーチ OpenSearch: 題名「テクニカル分析」、蔵書限定（dpid=iss-ndl-opac、100件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%83%86%E3%82%AF%E3%83%8B%E3%82%AB%E3%83%AB%E5%88%86%E6%9E%90&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:c98e364457e9／取得 #11（301,495 バイト）／確認箇所: totalResults=94（映像資料を含む）。LR-043・LR-111〜114、Weinstein・Wilder・Aronson・Schwager 邦訳の書誌 |
| PB-004 | NDLサーチ OpenSearch: 題名「一目均衡表」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E4%B8%80%E7%9B%AE%E5%9D%87%E8%A1%A1%E8%A1%A8&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:34353778ac58／取得 #18（47,661 バイト）／確認箇所: totalResults=20。一目山人『一目均衡表』6冊（経済変動研究所、1975.3〜1981.12）、川口一晃・三世一目山人ほか |
| PB-005 | NDLサーチ OpenSearch: 題名「チャート分析」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%83%81%E3%83%A3%E3%83%BC%E3%83%88%E5%88%86%E6%9E%90&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:8f1bad3769d5／取得 #20（191,907 バイト）／確認箇所: totalResults=62。林康史・藤本壱・小次郎講師・Weis 邦訳ほか |
| PB-006 | NDLサーチ OpenSearch: 題名「酒田五法」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E9%85%92%E7%94%B0%E4%BA%94%E6%B3%95&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:daf348b66359／取得 #21（23,578 バイト）／確認箇所: totalResults=10。日本証券新聞社『酒田五法は風林火山』の版違い（1969・1987.9・2004.5・2019.12）ほか |
| PB-007 | NDLサーチ OpenSearch: 題名「ローソク足」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%83%AD%E3%83%BC%E3%82%BD%E3%82%AF%E8%B6%B3&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:853f98056146／取得 #23（36,766 バイト）／確認箇所: totalResults=12。伊藤智洋・小澤實・伊本晃暉ほか |
| PB-008 | NDLサーチ OpenSearch: 題名「罫線」、蔵書限定（先頭100件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E7%BD%AB%E7%B7%9A&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:47e52b8d98ad／取得 #24（215,984 バイト）／確認箇所: totalResults=514。昭和期以前の株式罫線書が多数。鏑木繁『先物罫線』の2版 |
| PB-009 | NDLサーチ OpenSearch: 題名「出来高」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E5%87%BA%E6%9D%A5%E9%AB%98&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:bb779210f61b／取得 #25（100,624 バイト）／確認箇所: totalResults=35（出来高払い制など無関係を含む）。荒井正和・岩本祐介ほか |
| PB-010 | NDLサーチ OpenSearch: 題名「移動平均」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E7%A7%BB%E5%8B%95%E5%B9%B3%E5%9D%87&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:421937bbc47a／取得 #28（102,136 バイト）／確認箇所: totalResults=43（時系列解析の学位論文などを含む）。小次郎講師・野坂晃一ほか |
| PB-011 | NDLサーチ OpenSearch: 題名「システムトレード」、NDC 338.183、2005年以降 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E3%83%88%E3%83%AC%E3%83%BC%E3%83%89&ndc=338.183&from=2005&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:a6f3302072c8／取得 #29（79,518 バイト）／確認箇所: totalResults=26。斉藤正章・若林良祐ほか |
| PB-012 | NDLサーチ OpenSearch: 題名「Python 株」、蔵書限定 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=Python%20%E6%A0%AA&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:c4723c06caaf／取得 #32（14,998 バイト）／確認箇所: totalResults=4。宮部保雄・片渕彼富の書誌 |
| PB-013 | NDLサーチ OpenSearch: 題名「信用取引」、NDC 338.15 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E4%BF%A1%E7%94%A8%E5%8F%96%E5%BC%95&ndc=338.15&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:7c44a0abe9cc／取得 #36（43,969 バイト）／確認箇所: totalResults=16。東証公式株式サポーター 信用取引編の各版ほか |
| PB-014 | NDLサーチ OpenSearch: 出版者パンローリング、NDC 338.183（先頭200件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?publisher=%E3%83%91%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%AA%E3%83%B3%E3%82%B0&ndc=338.183&dpid=iss-ndl-opac&cnt=200 | ✅P | 取得日 2026-11-11／sha256:7b4c246ca5a8／取得 #37（740,918 バイト）／確認箇所: totalResults=215、200件を取得（残り15件は idx 指定が 429 で未取得）。注記に「原タイトル」を持つ邦訳 103 件 |
| PB-015 | NDLサーチ OpenSearch: 出版者パンローリング、NDC 338.15（先頭200件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?publisher=%E3%83%91%E3%83%B3%E3%83%AD%E3%83%BC%E3%83%AA%E3%83%B3%E3%82%B0&ndc=338.15&dpid=iss-ndl-opac&cnt=200 | ✅P | 取得日 2026-11-11／sha256:5097f155e307／取得 #39（565,848 バイト）／確認箇所: totalResults=162。Edwards & Magee・Bollinger・Schwager・Aronson・Clenow・Weis ほかの邦訳 |
| PB-016 | NDLサーチ OpenSearch: 創作者 Nison, Steve | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Nison%2C%20Steve&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:ba8f3c93cc44／取得 #44（6,829 バイト）／確認箇所: totalResults=3（英語原著2点と仏語訳1点）。邦訳は見当たらない |
| PB-017 | NDLサーチ OpenSearch: 創作者 Kaufman, Perry J | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Kaufman%2C%20Perry%20J&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:510a9fac3012／取得 #51（13,450 バイト）／確認箇所: totalResults=4。邦訳2点（別書）と英語原著2点。Trading Systems and Methods の邦訳は見当たらない |
| PB-018 | NDLサーチ OpenSearch: 創作者 Elder, Alexander | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Elder%2C%20Alexander&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:9e360e7a2ae5／取得 #70（44,665 バイト）／確認箇所: totalResults=12。投資苑・投資苑2・投資苑3・ザ・トレーディングほか |
| PB-019 | NDLサーチ OpenSearch: 創作者 Darvas, Nicholas | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Darvas%2C%20Nicholas&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:2d73dcccf4a7／取得 #86（22,500 バイト）／確認箇所: totalResults=7。『私は株で200万ドル儲けた』の4版（1962・2003・2008・2017）ほか |
| PB-020 | NDLサーチ OpenSearch: 創作者 Malkiel, Burton Gordon | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Malkiel%2C%20Burton%20Gordon&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:9d827de46c7c／取得 #93（83,344 バイト）／確認箇所: totalResults=18。『ウォール街のランダム・ウォーカー』の8版（1993〜2023） |
| PB-021 | NDLサーチ OpenSearch: 創作者 Taleb, Nassim | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Taleb%2C%20Nassim&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:0c0c258d1da4／取得 #102（61,123 バイト）／確認箇所: totalResults=8。『まぐれ』（2008.1）ほか |
| PB-022 | NDLサーチ OpenSearch: 題名「ファイナンス機械学習」 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E3%83%95%E3%82%A1%E3%82%A4%E3%83%8A%E3%83%B3%E3%82%B9%E6%A9%9F%E6%A2%B0%E5%AD%A6%E7%BF%92&dpid=iss-ndl-opac&cnt=20 | ✅P | 取得日 2026-11-11／sha256:4bdfd487f643／取得 #114（10,284 バイト）／確認箇所: totalResults=2。『ファイナンス機械学習』（2019.12）、『アセットマネージャーのためのファイナンス機械学習』（2020.12） |
| PB-023 | NDLサーチ OpenSearch: 全項目「Systematic trading Carver」 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?any=Systematic%20trading%20Carver&dpid=iss-ndl-opac&cnt=20 | ✅P | 取得日 2026-11-11／sha256:2bd3b015be2f／取得 #119（7,536 バイト）／確認箇所: totalResults=2（うち1件が該当）。『システマティックトレード』（2016.7） |
| PB-024 | NDLサーチ OpenSearch: 創作者 Douglas, Mark・題名「ゾーン」 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Douglas%2C%20Mark&title=%E3%82%BE%E3%83%BC%E3%83%B3&dpid=iss-ndl-opac&cnt=20 | ✅P | 取得日 2026-11-11／sha256:d513d300d766／取得 #120（16,652 バイト）／確認箇所: totalResults=4。『ゾーン : 相場心理学入門』（2002.4）ほか |
| PB-025 | NDLサーチ OpenSearch: 題名「宗久翁」 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E5%AE%97%E4%B9%85%E7%BF%81&dpid=iss-ndl-opac&cnt=20 | ✅P | 取得日 2026-11-11／sha256:d55bd035c4ce／取得 #122（21,951 バイト）／確認箇所: totalResults=8。徳川時代経済秘録全集（1941・複製1973）、宗久翁相場全集（1910）、宗久翁秘録の現代訳ほか |
| PB-026 | NDLサーチ OpenSearch: 題名「禁断の市場」 | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E7%A6%81%E6%96%AD%E3%81%AE%E5%B8%82%E5%A0%B4&dpid=iss-ndl-opac&cnt=20 | ✅P | 取得日 2026-11-11／sha256:3ee38fea3ab1／取得 #124（8,560 バイト）／確認箇所: totalResults=1。『禁断の市場』（2008.6） |
| PB-027 | NDLサーチ OpenSearch: 創作者 Kahneman, Daniel | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?creator=Kahneman%2C%20Daniel&dpid=iss-ndl-opac&cnt=40 | ✅P | 取得日 2026-11-11／sha256:21afff294e0e／取得 #125（64,498 バイト）／確認箇所: totalResults=12。『ファスト&スロー』上・下（2012.11）、文庫（2014.6）ほか |
| PB-028 | NDLサーチ書誌ページ: 日本テクニカル分析大全（HTML） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/books/R100000002-I000007436982 | ✅P | 取得日 2026-11-11／sha256:736b473460f2／取得 #130（446 KB のサーバー描画 HTML）／確認箇所: 国立国会図書館書誌ID 000007436982・著者 日本テクニカルアナリスト協会 編・出版者 日本経済新聞社・出版年 2004.8・685p・NDC 338.155 |
| PB-029 | NDLサーチ OpenSearch: 題名「株価チャート」、蔵書限定（先頭100件） | 国立国会図書館（NDLサーチ） | 2026 | https://ndlsearch.ndl.go.jp/api/opensearch?title=%E6%A0%AA%E4%BE%A1%E3%83%81%E3%83%A3%E3%83%BC%E3%83%88&dpid=iss-ndl-opac&cnt=100 | ✅P | 取得日 2026-11-11／sha256:24d3e35bb5f6／取得 #26／確認箇所: totalResults=706。先頭100件の大半が『会社四季報』各号の書誌（東洋経済新報社、[1936]-）で占められた。戸松信博『1時間でわかる株価チャートの読み方』（2019.11）の書誌を使用 |
| PB-040 | CiNii Research OpenSearch（論文）: q=「テクニカル分析 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%86%E3%82%AF%E3%83%8B%E3%82%AB%E3%83%AB%E5%88%86%E6%9E%90%20%E6%A0%AA%E4%BE%A1&count=20&format=json | ✅P | 取得日 2026-11-11／sha256:21d8470c0a61／取得 #50／確認箇所: total=33。テクニカル分析と株価予測の論文（佐藤賀一ほか） |
| PB-041 | CiNii Research OpenSearch（論文）: q=「一目均衡表」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E4%B8%80%E7%9B%AE%E5%9D%87%E8%A1%A1%E8%A1%A8&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:979ae914a7cc／取得 #54／確認箇所: total=20。実務誌の連載と『テクニカルアナリストジャーナル』の論文、畑仲優輝（2024） |
| PB-042 | CiNii Research OpenSearch（論文）: q=「ローソク足 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%AD%E3%83%BC%E3%82%BD%E3%82%AF%E8%B6%B3%20%E6%A0%AA%E4%BE%A1&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:d217be1628dd／取得 #55／確認箇所: total=7。池田欽一（2019・2021）、後藤公一ほか（1988） |
| PB-043 | CiNii Research OpenSearch（論文）: q=「値幅制限」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E5%80%A4%E5%B9%85%E5%88%B6%E9%99%90&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:109e79b9153f／取得 #61／確認箇所: total=23。人工市場の研究（水田孝信ほか）、廖美華、食糧（米）関連の記事を含む |
| PB-044 | CiNii Research OpenSearch（論文）: q=「モメンタム 日本」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%A2%E3%83%A1%E3%83%B3%E3%82%BF%E3%83%A0%20%E6%97%A5%E6%9C%AC&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:0551fa832305／取得 #62／確認箇所: total=98（先頭50件）。徳永俊史・岩永安浩・加藤明ほか。工学・社会科学の同名語を多数含む |
| PB-045 | CiNii Research OpenSearch（論文）: q=「リターン・リバーサル」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%AA%E3%82%BF%E3%83%BC%E3%83%B3%E3%83%BB%E3%83%AA%E3%83%90%E3%83%BC%E3%82%B5%E3%83%AB&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:03c053ae77d3／取得 #63／確認箇所: total=4。翟林瑜（2022）、徳永俊史（2008） |
| PB-046 | CiNii Research OpenSearch（論文）: q=「テクニカル分析 有効性」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%86%E3%82%AF%E3%83%8B%E3%82%AB%E3%83%AB%E5%88%86%E6%9E%90%20%E6%9C%89%E5%8A%B9%E6%80%A7&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:208cbc4ba4b7／取得 #65／確認箇所: total=10。北島孝博（2011）、伊藤博志（2010）、東田啓（1996）、佐藤賀一（2017）ほか |
| PB-047 | CiNii Research OpenSearch（論文）: q=「売買ルール 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E5%A3%B2%E8%B2%B7%E3%83%AB%E3%83%BC%E3%83%AB%20%E6%A0%AA%E4%BE%A1&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:8628138ca3be／取得 #66／確認箇所: total=1。間普真吾ほか（2008） |
| PB-048 | CiNii Research OpenSearch（論文）: q=「ディスポジション効果」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%87%E3%82%A3%E3%82%B9%E3%83%9D%E3%82%B8%E3%82%B7%E3%83%A7%E3%83%B3%E5%8A%B9%E6%9E%9C&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:40130a753664／取得 #73／確認箇所: total=5。閻石（2010〜2011）、米澤忠幸・中井孝（2012）、高橋陽二ほか（2009） |
| PB-049 | CiNii Research OpenSearch（論文）: q=「アンカリング 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%82%A2%E3%83%B3%E3%82%AB%E3%83%AA%E3%83%B3%E3%82%B0%20%E6%A0%AA%E4%BE%A1&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:5731c3d7258e／取得 #75／確認箇所: total=2。松村尚彦（2010） |
| PB-050 | CiNii Research OpenSearch（論文）: q=「データ・スヌーピング」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%87%E3%83%BC%E3%82%BF%E3%83%BB%E3%82%B9%E3%83%8C%E3%83%BC%E3%83%94%E3%83%B3%E3%82%B0&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:bba16bc7c225／取得 #76／確認箇所: total=1。北島孝博（2011） |
| PB-051 | CiNii Research OpenSearch（論文）: q=「出来高 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E5%87%BA%E6%9D%A5%E9%AB%98%20%E6%A0%AA%E4%BE%A1&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:4678ebfd2309／取得 #77／確認箇所: total=27。三輪宏太郎・植田一博（2009・2010）、岩田年浩（2001）ほか |
| PB-052 | CiNii Research OpenSearch（論文）: q=「空売り規制」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E7%A9%BA%E5%A3%B2%E3%82%8A%E8%A6%8F%E5%88%B6&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:dfbbca47c1c4／取得 #78／確認箇所: total=66（先頭50件）。足立光生（2016）ほか。法学・実務誌の記事が多い |
| PB-053 | CiNii Research OpenSearch（論文）: q=「バックテスト」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%90%E3%83%83%E3%82%AF%E3%83%86%E3%82%B9%E3%83%88&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:4300f24c1351／取得 #80／確認箇所: total=35。Bailey・López de Prado・松村陽平（2022）、野村至紀（2016）、水田孝信ほか（2022）。無関係（板金のスプリングバック試験など）を含む |
| PB-054 | CiNii Research OpenSearch（論文）: q=「株式市場 アノマリー 日本」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E6%A0%AA%E5%BC%8F%E5%B8%82%E5%A0%B4%20%E3%82%A2%E3%83%8E%E3%83%9E%E3%83%AA%E3%83%BC%20%E6%97%A5%E6%9C%AC&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:796e6e225f0a／取得 #82／確認箇所: total=25。岩澤誠一郎・内山朋規、桂眞一ほか。『証券アナリストジャーナル』64巻6号（2026-06）の特集記事 |
| PB-055 | CiNii Research OpenSearch（論文）: q=「曜日効果」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E6%9B%9C%E6%97%A5%E5%8A%B9%E6%9E%9C&count=50&format=json | ✅P | 取得日 2026-11-11／sha256:9db3f6dd5d48／取得 #83／確認箇所: total=25。砂田洋志（1996）、高岡慎（2002）、阿部圭司（1998）ほか |
| PB-056 | CiNii Research OpenSearch（論文）: q=「ボリンジャーバンド」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%9C%E3%83%AA%E3%83%B3%E3%82%B8%E3%83%A3%E3%83%BC%E3%83%90%E3%83%B3%E3%83%89&count=30&format=json | ✅P | 取得日 2026-11-11／sha256:acf5d23d7f85／取得 #87／確認箇所: total=7。Bollinger の邦訳（2004）の記録、新茂則（2007） |
| PB-057 | CiNii Research OpenSearch（論文）: q=「投資部門別」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E6%8A%95%E8%B3%87%E9%83%A8%E9%96%80%E5%88%A5&count=30&format=json | ✅P | 取得日 2026-11-11／sha256:143b8d2987cc／取得 #88／確認箇所: total=13。徳永俊史（2005）、三宅一弘・米沢康博（1993）ほか |
| PB-058 | CiNii Research OpenSearch（論文）: q=「順張り」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E9%A0%86%E5%BC%B5%E3%82%8A&count=30&format=json | ✅P | 取得日 2026-11-11／sha256:5f30f4f10b2b／取得 #89／確認箇所: total=17。『日経マネー』『テクニカルアナリストジャーナル』の記事、水田孝信ほか |
| PB-059 | CiNii Research OpenSearch（論文）: q=「ランダムウォーク 株価」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%A9%E3%83%B3%E3%83%80%E3%83%A0%E3%82%A6%E3%82%A9%E3%83%BC%E3%82%AF%20%E6%A0%AA%E4%BE%A1&count=40&format=json | ✅P | 取得日 2026-11-11／sha256:037e53e7ee4c／取得 #90／確認箇所: total=12。佐々木豊史・宮崎浩一（2012）、田中美栄子・徳岡聖二ほか |
| PB-060 | CiNii Research OpenSearch（論文）: q=「トレンドフォロー」 | CiNii Research（国立情報学研究所） | 2026 | https://cir.nii.ac.jp/opensearch/articles?q=%E3%83%88%E3%83%AC%E3%83%B3%E3%83%89%E3%83%95%E3%82%A9%E3%83%AD%E3%83%BC&count=30&format=json | ✅P | 取得日 2026-11-11／sha256:a950ff0b459f／取得 #91／確認箇所: total=12。山本竜市・平田英明（2011）ほか |
