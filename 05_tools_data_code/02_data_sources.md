# データ源（日本株・海外・マクロ）と、調整後株価・生存者バイアス・暦の落とし穴
> 要約: 日本株の主要データ源（J-Quants API、EDINET、TDnet、JPX の統計、Yahoo 系、BOJ・e-Stat）と海外の API（Alpha Vantage、Massive 旧 Polygon.io、Tiingo、Finnhub、Twelve Data、EODHD、Nasdaq Data Link、FRED、yfinance 等）を、調整済み価格・分足・無料枠・規約の観点で整理した。
> 本セッションでは Web 検索の上限に達し各社の公式ページを読めていない。確認できたのは PyPI／npm 上のクライアントの README 経由の情報に限り、それ以外は記憶（⚠M）か「未確認」とした。料金・無料枠・規約は必ず公式で確認すること（確認日 2026-11-09）。ただし J-Quants・JPX 関連の記述は 2026-11-11 に JPX の公式ページで照合した（jpx-jquants.com は 403 で取得不可）。
> 後半は、分割・配当の調整、生存者バイアスと上場廃止、時差と日米データの結合、休場カレンダーの落とし穴を式と実装上の注意で扱う。
> 最終更新: 2026-11-11

## 1. 読み方

- 検証 ✅S の根拠は、クライアントライブラリ（PyPI／npm）の JSON・README と学術論文の書誌・要旨である。サービス本体の公式ページは読んでいない（JPX 側の J-Quants 紹介ページ・告知・統計・TDnet の案内は 2026-11-11 に取得して ✅P とした。jpx-jquants.com は 403 で取得不可）。「公式ドキュメント」の URL は README に書かれていたものを転記しただけで、内容は未確認。
- 確認日: 2026-11-09。料金・無料枠・レート制限・規約は変更されるため、数値は載せず「要公式確認」とした。「未確認」は調べても材料が得られなかったことを意味し、「無い」ことを意味しない。

## 2. 日本株・日本のデータ源

| データ源 | 対象 | 調整済み価格 | 分足 | 無料枠（要公式確認） | 利用規約上の注意 | 出典 |
|---|---|---|---|---|---|---|
| J-Quants API V2 | 上場銘柄一覧、株価日足・午前終値、指数・TOPIX・先物・オプション、投資部門別売買状況、信用取引残高、空売り比率・報告、売買内訳、財務サマリー・詳細、配当、決算発表予定日、適時開示インデックス、営業日カレンダー、EDINET 由来の大株主等 | 日足に調整後の列（`AdjC`・`AdjVo`）がある。調整の範囲は、分割・併合のみで配当は対象外とする説明を別文書 [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md) の 5 章が公式ページの検索要約から確認している（本稿では未確認）。JPX の紹介ページも「過去の分割等を考慮した調整済み株価と調整前の株価データ」を提供すると記す [TL-612]（配当の扱いは jpx-jquants.com が取得不可で未確認） | あり（1 分足、5・15 分足は分足から算出）。取得可能範囲はプランで異なる | プラン（JPX総研の2025-08-22告知を2026-11-11に取得して確認、✅P。現行は jpx-jquants.com が正で未取得、要公式確認）: 無料（過去2年分・12週間遅延）／ライト 月額1,650円（過去5年分）／スタンダード 月額3,300円（過去10年分）／プレミアム 月額16,500円（提供期間すべて。前場・後場データを含む）（いずれも税込）。株価四本値は無料・ライト・スタンダードが日通しのみ、プレミアムが前後場・日通し [TL-611]。データセットの有無はプラン別で、投資部門別情報・TOPIX四本値はライト以上、指数四本値・日経225オプション四本値・信用取引週末残高・業種別空売り比率・空売り残高報告・日々公表信用取引残高はスタンダード以上、売買内訳・前場四本値・配当金情報・財務諸表・先物／オプション四本値はプレミアム（表は [08文書の§3.7](../08_primary_sources/01_jpx_primary.md)）。アドオンとして Tick・分足（日次配信でリアルタイムではない）と適時開示書類データ（日中配信）がある [TL-612]。法人向けは別サービス（J-Quants Pro）[PJ-059]。README の「現在は有償版サービス」は、無料プランを含む4プランとする JPX 告知と食い違う（README が古い可能性） | 個人投資家向けサービス。API キー認証。レートリミットがあり超過で HTTP 429（`_range` 系は並列で叩く）。再配布・商用の可否は要確認 | [TL-101] |
| JPX の公開統計・データ | 投資部門別売買状況（週次）、信用取引残高（銘柄別は日次、二市場合計は週次）、空売り集計（日次・月間）、空売り残高（日次）、裁定取引・プログラム売買、東証上場銘柄一覧、株価情報（過去分。月次 PDF）など（JPX の統計ページを 2026-11-11 に確認、✅P） | 非該当 | 非該当 | 無料。PDF・Excel・CSV。公表時刻の目処は [08文書の§3.8](../08_primary_sources/01_jpx_primary.md) の表（例: 銘柄別信用残 16:00、空売り集計 16:30、空売り残高 17:00、投資部門別 15:30） | 株価情報（過去分）は手動取得が基本で自動取得はご遠慮、掲載ファイルの転載は禁止と明記 [PJ-061]。その他の統計の再配布条件は要確認 | [PJ-060] [PJ-061] |
| EDINET API（金融庁） | 有価証券報告書・四半期報告書・大量保有報告書・公開買付関連などの開示書類（CSV 変換、inline XBRL、XBRL インスタンス） | 非該当 | 非該当 | 無料の API キーが必要（第三者ライブラリ edinet-tools の README） | 利用条件は公式で要確認 | [TL-102] |
| TDnet（適時開示） | 決算短信・業績予想修正・配当予想修正などの開示と XBRL。第三者ライブラリ tdnet の README: 既定の取得元は**非公式**の「やのしん WEB-API」で、不通時は release.tdnet.info に切り替える。J-Quants V2 にも適時開示の一覧・ファイル・一括取得がある | 非該当 | 非該当 | 未確認（tdnet ライブラリは API キー不要と README に記載） | README: XBRL／PDF は release.tdnet.info 上で約 30〜40 日で削除され、JPX の恒久 URL へ自動で切り替わる。既定は 1 秒に 1 リクエスト。非公式 API の可用性と規約は未確認。JPX の公式ページ: 適時開示情報閲覧サービスは開示日を含め 31 日分を掲載し、安定稼働のためスクレイピング等による自動取得を控えるよう求める [PJ-066]。開示時刻は報道機関への公開時刻と同時 [PJ-067] | [TL-103] [TL-101] [PJ-066] [PJ-067] |
| Yahoo 系（Yahoo!ファイナンス、yfinance） | 日米等の株価。日本株のティッカーは `.T` の接尾辞と記憶（⚠M） | yfinance は既定で配当調整済み（`auto_adjust=True`）。生の終値が欲しいときは設定を変える | 取得可（保持期間は要確認） | 無料。非公式 | README: yfinance は Yahoo と無関係の非公式ツールで研究・教育目的、Yahoo の API は個人利用のみ。Yahoo!ファイナンス（日本）の規約は未確認 | [TL-106] |
| Stooq | 日本株の接尾辞は `.jp` と記憶（⚠M） | 未確認 | 未確認 | 未確認 | pandas-datareader 0.11.1 の README は Stooq を挙げておらず、PyPI に `stooq` の名前は見つからなかった。現行の取得可否は未確認 | [TL-107] |
| 日本銀行 時系列統計データ検索サイトの API | 日銀の時系列統計。Code API（系列コード指定）・Layer API（階層指定）・Metadata API の 3 種（第三者ライブラリ boj-api の README） | 非該当 | 非該当 | 認証キーの記述は README になし | README は「このサービスは日銀の API 機能を使用しており、内容は日銀が保証したものではない」旨のクレジット文言を掲載。日銀側で表記が義務かは未確認 | [TL-104] |
| e-Stat API（総務省統計局） | 政府統計全般。応答はコードとラベルが別領域に分かれた JSON（第三者ライブラリ pyestat の README） | 非該当 | 非該当 | 無料。アプリケーション ID の取得が必要と記憶（⚠M） | クレジット表記等の条件は未確認 | [TL-105] [TL-127] |
| 証券会社の API／連携 | kabuステーション API（三菱UFJ eスマート証券、旧 auカブコム証券）、立花証券 e支店、楽天証券 MARKETSPEED II の Excel 連携など（⚠M） | 未確認 | 未確認 | 口座・条件・料金は要公式確認 | 個人向け自動売買は各社の規約に従う。PyPI に `kabusapi` の名前は見つからなかった | [TL-127] |
| 日経平均・TOPIX の指数値 | 指数値の再配布には指数提供元の権利が及ぶと考えられる（⚠M） | 非該当 | 非該当 | 要公式確認 | 再配布・商用利用は提供元の条件を確認 | [TL-127] |

## 3. 海外・グローバルのデータ源

| データ源 | 対象・特記 | 調整済み価格 | 分足 | 無料枠（要公式確認） | 利用規約上の注意 | 出典 |
|---|---|---|---|---|---|---|
| Alpha Vantage | 株式・指標・オプション・コモディティ・経済指標など（クライアント README）。無料 API を謳い、キー必須、`get_intraday` あり | 未確認 | あり | 要公式確認（README に数値なし）。クライアントは 2024-07 以降リリースなし | 要公式確認 | [TL-108] |
| Massive（旧 Polygon.io） | 株式・オプション・指数・先物・FX・暗号資産（npm クライアントの説明）。PyPI `massive` の概要が「formerly Polygon.io」と明記し、旧 `polygon-api-client` の最終版は 2025-10-30 | 未確認 | REST／WebSocket（概要）。分足の可否は未確認 | 要公式確認 | 日本株の取扱いは未確認 | [TL-109] [TL-110] [TL-111] |
| Tiingo | 日次（日・週・月・年）と、IEX 由来のイントラデイ（`30Min`・`1Hour` など）。README に調整後終値等のフィールド言及 | あり（README） | あり（IEX 由来） | 要公式確認 | 対象市場は米国中心と記憶（⚠M）。日本株は未確認 | [TL-112] |
| Finnhub | 株式・FX・暗号資産。クライアントに `market_holiday`・`market_status`（取引所指定）がある | 未確認 | 未確認 | 要公式確認 | 日本株は未確認 | [TL-113] |
| Twelve Data | API キー必須。`exchange` で上場先を指定、`timezone`（UTC／Exchange／IANA）を選べる。ファンダメンタルは「全世界の市場」と README | 未確認 | 未確認 | 要公式確認（料金ページへ誘導） | 日本株は未確認 | [TL-114] |
| EODHD | 公式クライアント README: 無料登録で API キー、一部データは有料。イントラデイ履歴、対応取引所一覧、Exchange API（取引時間・休場・**シンボル変更履歴**） | 未確認 | あり | 要公式確認 | 日本株の対応は取引所一覧で要確認 | [TL-115] |
| Nasdaq Data Link（旧 Quandl） | 公式クライアント 1.0.4（2022-08 以降リリースなし）。旧 `quandl` は 2021-11 | 未確認 | 未確認 | データセットごとに異なる（未確認） | 要公式確認 | [TL-116] |
| FRED／ALFRED | マクロ時系列。fredapi README: 無料 API キー。ALFRED の**ビンテージ**（`realtime_start`・`realtime_end`）で過去時点の値を再現できる | 非該当 | 非該当 | 無料（キー必要） | 先読み防止に有用。系列ごとの再配布条件は要確認 | [TL-117] |
| Interactive Brokers API | 公式 `ibapi` の license 欄は「IB API Non-Commercial License または Commercial License」。ib_async（2025-12）・ib-insync（2023-07 以降更新なし）は別の非同期ラッパー | 未確認 | あり（記憶 ⚠M） | 口座・市場データ購読が前提（⚠M） | 非商用／商用でライセンスが分かれる | [TL-120] [TL-121] |

- 米国個別株のイントラデイを日本時間で扱う際の時差は 4.3 節。日本株の取扱いは、各社の対応取引所一覧（公式）で必ず確認する。

## 4. データの落とし穴

### 4.1 調整後株価（分割・併合・配当）

- 系列は 3 種ある: ① 未調整（取引所で付いた価格）、② 分割・併合のみ調整、③ 分割・併合＋配当を調整（トータルリターン型）。**チャート分析の価格水準**（支持線・抵抗線、「1,000 円以下」の条件、呼値・値幅制限の判定）は ①②、**リターン評価**は ③ が基本。③ は過去の価格水準を人工的に下げるので、水準依存の判定に使うと誤る。
- 調整の式（比例方式の一例）:

```
分割:  1 株が r 株に分割 → 係数 f = 1 / r（併合 10 株→1 株なら r = 0.1, f = 10）
        権利落ち日より前の 価格 × f、出来高 ÷ f
配当:  1 株配当 D、直前営業日終値 P → f = 1 − D / P
調整後価格_t = 未調整価格_t × Π f_k   （k は t より後に権利落ちが起きたイベント）
```

  差し引き方式（`価格 − Σ配当`）もあり、絶対額は保つが価格が負になりうる。リターンを保つのは比例方式。ベンダーがどちらかは確認する。
- yfinance は**既定で配当調整済み**（`auto_adjust=True`、README [TL-106]）。J-Quants は日足に `AdjC`・`AdjVo`（調整後終値・調整後出来高とみられる）を持つ（README の出力例 [TL-101]）。いずれも「いつ時点の調整か」を記録する。調整係数は将来の分割で書き換わるため、**未調整＋調整係数表を別に保存**すると再現性が高い。
- 日本固有: 権利落ち日に基準値段が配当相当額だけ調整され、値幅制限の基準も動く（JPX の公式サポーター: 終値 1,100 円で 5 円の配当落ちなら基準値段は 1,095 円。✅P [PJ-012]）。分割後は出来高も増える。詳細は [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md)。

### 4.2 生存者バイアスと上場廃止銘柄

- 現在上場している銘柄だけのデータでは、倒産・TOB・MBO・合併・完全子会社化で消えた銘柄が欠け、成績が上方に偏る。米国では CRSP の**上場廃止時のリターン欠落**が大きな偏りを生むことが示され [TL-123]、COMPUSTAT のみを使うと係数が過大になる例が報告されている [TL-124]。インドの小型株指数では、現在構成銘柄のみのバックテストが年率リターンを 4.94 ポイント、シャープレシオを 0.097 押し上げた（プレプリント）[TL-125]。南アフリカ（JSE）でも現在上場銘柄のみのポートフォリオは有意に高いリターンを示した [TL-126]。日本市場での定量値は本調査では未確認。
- 対策: ① 日付時点の上場銘柄一覧（point-in-time）を持つ、② 上場廃止銘柄を含む供給元を使う、③ 上場廃止時の価格（TOB 価格への収束、整理銘柄期間、最終売買価格）を扱う規則を決める。EODHD の Exchange API はシンボル変更履歴を持つ（README [TL-115]）。J-Quants の銘柄一覧が過去日付に対応するかは未確認。
- 日本固有: 市場区分の再編（2022 年 4 月）、銘柄コードの変更・再利用、英数字を含む銘柄コードの存在（edinet-tools の README は数字と英数字のティッカーを検索できると記載 [TL-102]）。J-Quants の `Code` は 5 桁（例 13010。README のサンプル出力 [TL-101]）で、4 桁コードとの対応付けが要る。

### 4.3 タイムゾーンと日米データの結合

- 東証は日本標準時（UTC+9、夏時間なし）。米国の終値は東部時間 16:00（標準時は翌朝 6:00 JST、夏時間は 5:00 JST）に確定する。
- **暦日で結合すると先読みになる**: 東京の D 日の引けの時点では、米国の D 日の終値はまだ存在しない。使えるのは米国の D−1 日（東部時間）の終値で、東京の D 日の寄付前に確定している。逆に、米国 D 日の終値を東京 D+1 日の始値で取引する設計は因果的に成立する。
- 米国の祝日と東京の祝日はずれる。結合後に欠損を前方補完するのは、約定可否と無関係な価格を持ち越すので慎重に扱う。
- Twelve Data は `timezone`（UTC／Exchange／IANA）を選べる（README [TL-114]）。ベンダーの日足の日付が現地日付か UTC かは必ず確認する。分足はバー時刻が開始か終了か、11:30〜12:30 の休憩の扱いも確認する。exchange_calendars はオークション時間を閉場扱いにする（README [TL-118]）。

### 4.4 休場カレンダー

- jpholiday は**国民の祝日のみ**（内閣府データ、2026 年まで確認済みと README [TL-119]）。README の例では 2017-01-02 が「元日 振替休日」、2017-01-03 は祝日なしと判定される一方、東証は年末年始（12 月 31 日、1 月 1〜3 日）に休業する（JPX の休業日一覧で確認、✅P [PJ-054]）。祝日ライブラリだけでは東証の営業日にならない。デリバティブには祝日にも取引する日（祝日取引、2022 年 9 月 23 日開始）があり、現物の休場日にも日経225先物の価格が付く [PJ-052]。
- exchange_calendars には XTKS（東京証券取引所）があるが、各カレンダーは利用者の貢献で維持されると README が明記する [TL-118]。臨時休場や半日取引、取引時間変更の反映は公式と照合する（2020-10-01 のシステム障害による終日売買停止で J-Quants が四本値を Null 収録するとの記述が 02_japan/04 にある。JPX の障害報告で、全銘柄を 9:00 の立会開始から停止し 11:45 に終日停止を決定したことを確認 [PJ-056]）。J-Quants V2 には営業日カレンダーの API がある（README [TL-101]）。pandas_market_calendars は exchange_calendars のミラー [TL-122]。
- 営業日の判定は、取引所カレンダーを正とし、データの有無（出来高ゼロ日・欠損）とも突き合わせる。

### 4.5 その他

- **出来高の定義**: 東証のみか、PTS を含む合算か、ベンダーで異なりうる（⚠M、要確認）。JPX の東証日報は立会市場と ToSTNeT 市場を別欄で載せ（立会市場の合計欄は過誤訂正売買分・デルタニュートラル取引分を含む）、説明に PTS の記載はない。ToSTNeT の単一銘柄取引で売買代金 50 億円以上の超大口取引は、立会日の翌日売買分の日報に含めて四本値・売買高を載せるとされ、日報の値が翌日に補われうる [PJ-068]。
- **約定のない日**: 売買が成立しない日の 4 本値の扱い（前日終値で埋めるか、欠損か）を統一する。ストップ高・安に張り付く日は約定不能（[05_backtesting_frameworks.md](05_backtesting_frameworks.md)）。
- **ベンダー間差**: 始値・終値の定義（気配か約定か）、特別気配、訂正データの反映時期が異なる。複数供給元で突き合わせる。
- **記録すべきメタデータ**: 取得日時、ベンダーと版、調整方式と調整時点、タイムゾーン、ユニバースの決定日。

## 関連文書

- [01_charting_platforms_and_screeners.md](01_charting_platforms_and_screeners.md): チャート／スクリーナー製品
- [03_python_libraries.md](03_python_libraries.md): 各クライアントライブラリの版と依存関係
- [05_backtesting_frameworks.md](05_backtesting_frameworks.md): バックテスト設計上の落とし穴
- [../02_japan/04_tse_market_rules_and_chart_effects.md](../02_japan/04_tse_market_rules_and_chart_effects.md): 取引時間・呼値・値幅制限・配当落ち
- [../02_japan/05_supply_demand_indicators.md](../02_japan/05_supply_demand_indicators.md): 需給系データ（信用・空売り・投資部門別）
- [../08_primary_sources/01_jpx_primary.md](../08_primary_sources/01_jpx_primary.md): JPX 一次資料による照合（J-Quants のプラン表、JPX 統計の公表時刻、取得ログ）
- [../03_evidence/02_methodology_behavioral_japan_ml.md](../03_evidence/02_methodology_behavioral_japan_ml.md): 検証手法の落とし穴

## この文書の限界

- JPX 側のページ（J-Quants API の紹介ページ、プラン告知、統計、TDnet の案内）は 2026-11-11 に取得して確認した（✅P）。一方、jpx-jquants.com（J-Quants の仕様・料金の正本）は 403 で取得できず、API 仕様・レート制限・調整の詳細は未確認である。EDINET・各海外 API の公式ページ、料金、無料枠、利用規約は読めていない。確認できたのはクライアントの README 経由の情報だけで、サービスの現況とは異なる可能性がある。
- 東証の制度に関する記述のうち、出来高の定義（PTS を含むか）、証券会社 API、e-Stat のアプリケーション ID、指数の権利は記憶（⚠M）であり、公式での確認が必要である（休業日・基準値段の調整・JPX 統計は ✅P で確認済み）。
- 日本株を扱えるか、調整が分割のみか配当を含むかは、多くの海外 API と J-Quants について未確認である。
- 学術論文は書誌と要旨のみを確認した。日本市場の生存者バイアスの大きさは未確認。
- 非公式 API（Yahoo 系、やのしん WEB-API 等）の可用性・規約は変わりやすく、将来の動作を保証しない。

## 出典

| ID | 資料名 | 著者・発行元 | 年 | URL | 検証 | メモ |
|---|---|---|---|---|---|---|
| TL-101 | PyPI: jquants-api-client 2.8.0 | J-Quants Project Contributors | 2026 | https://jpx-jquants.com/spec/data-spec | ✅S | README（V2 エンドポイント一覧・有償サービスの記載）。URL は README が案内する公式ドキュメントで内容は未読 |
| TL-102 | PyPI: edinet-tools 0.9.1 | Matt Helmer | 2026 | https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1 | ✅S | 第三者製。URL は README が案内する EDINET API キー登録ページで内容は未読 |
| TL-103 | PyPI: tdnet 0.3.2 | — | 2026 | https://www.release.tdnet.info/ | ✅S | 第三者製（AGPL）。URL は README が示す TDnet 配信サイトで内容は未読 |
| TL-104 | PyPI: boj-api 0.1.2 | — | 2026 | — | ✅S | 第三者製（MIT）。日銀のクレジット文言を README が掲載 |
| TL-105 | PyPI: pyestat 0.3.0 | — | 2026 | https://www.e-stat.go.jp/api/ | ✅S | 第三者製（MIT）。URL は README が示す e-Stat API ページで内容は未読 |
| TL-106 | PyPI: yfinance 1.8.0 | — | 2026 | https://github.com/ranaroussi/yfinance | ✅S | README の Legal 節と調整価格の注記 |
| TL-107 | PyPI: pandas-datareader 0.11.1 | — | 2026 | https://pandas-datareader.readthedocs.io/en/latest/ | ✅S | README のデータ源の説明 |
| TL-108 | PyPI: alpha-vantage 3.0.0 | — | 2024 | https://www.alphavantage.co/ | ✅S | URL は README が示すサービスのサイトで内容は未読 |
| TL-109 | PyPI: massive 2.9.1 | — | 2026 | — | ✅S | 概要に formerly Polygon.io と明記。README は空 |
| TL-110 | PyPI: polygon-api-client 1.16.3 | — | 2025 | — | ✅S | 最終版 1.16.3 |
| TL-111 | npm: @massive.com/client-js 10.8.0 | — | 2026 | https://github.com/massive-com/client-js#readme | ✅S | npm registry の説明文（Stocks, Options, Indices, Futures, Forex, Crypto） |
| TL-112 | PyPI: tiingo 0.16.1 | — | 2025 | — | ✅S | README の頻度・調整後フィールドの記載 |
| TL-113 | PyPI: finnhub-python 2.4.30 | — | 2026 | — | ✅S | README のメソッド例 |
| TL-114 | PyPI: twelvedata 1.4.0 | — | 2026 | https://twelvedata.com/pricing | ✅S | URL は README が示す料金ページで内容は未読 |
| TL-115 | PyPI: eodhd 1.0.32 | — | 2024 | https://eodhd.com/pricing | ✅S | 公式クライアント。URL は README が示す料金ページで内容は未読 |
| TL-116 | PyPI: Nasdaq-Data-Link 1.0.4 | — | 2022 | — | ✅S | README は数行。旧 quandl 3.7.0（2021-11-11） |
| TL-117 | PyPI: fredapi 0.5.2 | — | 2024 | http://api.stlouisfed.org/api_key.html | ✅S | URL は README が示す API キー申請ページで内容は未読 |
| TL-118 | PyPI: exchange_calendars 4.13.2 | Gerry Manoim | 2026 | https://github.com/gerrymanoim/exchange_calendars | ✅S | README の対応取引所表（XTKS）とメンテナンス方針 |
| TL-119 | PyPI: jpholiday 1.0.3 | Vatis | 2025 | https://github.com/Lalcs/jpholiday | ✅S | README の対象範囲と例 |
| TL-120 | PyPI: ibapi 9.81.1.post1 | — | 2020 | — | ✅S | license 欄に非商用／商用ライセンスの記載 |
| TL-121 | PyPI: ib_async 2.1.0 | — | 2025 | — | ✅S | 概要のみ |
| TL-122 | PyPI: pandas_market_calendars 5.6.0 | — | 2026 | https://github.com/rsheftel/pandas_market_calendars | ✅S | README: exchange_calendars のミラー |
| TL-123 | The Delisting Bias in CRSP Data | Tyler Shumway／Journal of Finance | 1997 | — | ✅S | DOI 10.1111/j.1540-6261.1997.tb03818.x。論文検索の書誌・要旨のみ確認 |
| TL-124 | The cross-section of stock returns and survivorship bias: Evidence from delisted stocks | James L. Davis／Quarterly Review of Economics and Finance | 1996 | — | ✅S | DOI 10.1016/s1062-9769(96)90021-6。論文検索の書誌・要旨のみ確認 |
| TL-125 | Survivorship Bias in Emerging Market Small-Cap Indices: Evidence from India's NIFTY Smallcap 250 | Harjot Singh Ranse／arXiv | 2026 | — | ✅S | DOI 10.48550/arxiv.2603.19380。プレプリント（査読前）。論文検索の書誌・要旨のみ確認 |
| TL-126 | Does survivorship bias really matter? An empirical investigation into its effects on the mean reversion of share returns on the JSE (1984–2007) | E. Gilbert, D. Strugnell／Investment Analysts Journal | 2010 | — | ✅S | DOI 10.1080/10293523.2010.11082521。論文検索の書誌・要旨のみ確認 |
| TL-127 | 日本の取引所・公的機関・証券会社サービスに関する一般知識（出来高の定義、kabuステーション API、立花証券 e支店、楽天証券の Excel 連携、e-Stat のアプリケーション ID、指数の権利） | 日本取引所グループ、各社・各機関 | — | — | ⚠M | 記憶のみ。ページ未確認。要公式確認（JPX 統計・東証の休業日・基準値段の調整は PJ-060／PJ-054／PJ-012 で ✅P に置換済み） |
| TL-611 | J-Quants API の料金プランに関するJPX総研の告知（2025-08-22） | JPX総研／JPX | 2025 | https://www.jpx.co.jp/corporate/news/news-releases/6020/20250822-01.html | ✅P | 取得日 2026-11-11／sha256:94fafd4ef3af／確認箇所: 4プランの料金・提供期間・データセット表、無料は12週間遅延 |
| TL-612 | J-Quants API サービスページ | JPX | 2026 | https://www.jpx.co.jp/markets/other-data-services/j-quants-api/ | ✅P | 取得日 2026-11-11／sha256:2d353e697afc／確認箇所: 提供データ例、アドオン（Tick・分足は日次配信）、調整済み株価の記載（2026/05/18更新） |
| PJ-012 | 東証公式株式サポーター 株式取引編 第8版（PDF） | 東京証券取引所 | 2024 | https://www.jpx.co.jp/equities/trading/strengthening/cg27su00000054qm-att/mklp77000000fabh.pdf | ✅P | 取得日 2026-11-11／sha256:f6b08697a42c／Q.8基準値段、Q.9売買単位、Q.18大引け更新値幅2倍、Q.32制限値幅の撤廃 |
| PJ-052 | 祝日取引 | JPX | 2026 | https://www.jpx.co.jp/derivatives/rules/holidaytrading/index.html | ✅P | 取得日 2026-11-11／sha256:5c3d4c78ff98／2026・2027年の実施日、12/31・1/1は実施しない（2026/06/26更新） |
| PJ-054 | 営業時間・休業日一覧 | JPX | 2026 | https://www.jpx.co.jp/corporate/about-jpx/calendar/index.html | ✅P | 取得日 2026-11-11／sha256:cda2f71c21ce／2026/12/31・2027/01/01-03などの休業日（2026/02/06更新） |
| PJ-056 | 10月1日に株式売買システムで発生した障害について（PDF） | 東京証券取引所 | 2020 | https://www.jpx.co.jp/corporate/news/news-releases/0060/nlsgeu0000051l46-att/trading_system.pdf | ✅P | 取得日 2026-11-11／sha256:45bb6614840c／全銘柄を9:00の立会開始から停止、11:45に終日停止を決定 |
| PJ-059 | J-Quants Pro（JPXの紹介ページ） | JPX | 2025 | https://www.jpx.co.jp/markets/other-data-services/j-quants-pro/index.html | ✅P | 取得日 2026-11-11／sha256:3a2dbfded582／法人向け。銘柄別信用取引残高（日次）、空売り残高報告（0.5%以上）など |
| PJ-060 | 統計情報（株式関連） | JPX（東京証券取引所） | 2026 | https://www.jpx.co.jp/markets/statistics-equities/index.html | ✅P | 取得日 2026-11-11／sha256:b6d7071443bc／公開統計の一覧（日報・信用・空売り・投資部門別・裁定・上場銘柄一覧ほか） |
| PJ-061 | 東京証券取引所日報: 株価情報（過去分） | JPX（東京証券取引所） | 2026 | https://www.jpx.co.jp/markets/statistics-equities/daily/03.html | ✅P | 取得日 2026-11-11／sha256:cfdbdf0df36f／月次PDF。手動取得が基本、自動取得はご遠慮、転載禁止 |
| PJ-066 | 適時開示情報閲覧サービス: ご利用案内 | JPX | 2026 | https://www.jpx.co.jp/listing/disclosure/01.html | ✅P | 取得日 2026-11-11／sha256:60b184740a5b／掲載期間31日、スクレイピング等による自動取得はご遠慮 |
| PJ-067 | TDnetの概要 | JPX | 2022 | https://www.jpx.co.jp/equities/listing/disclosure/tdnet/index.html | ✅P | 取得日 2026-11-11／sha256:0119968a7870／TDnet開示時刻＝報道機関への公開時刻、閲覧は31日分 |
| PJ-068 | 東京証券取引所日報: ご利用の手引き | JPX（東京証券取引所） | 2026 | https://www.jpx.co.jp/markets/statistics-equities/daily/01.html | ✅P | 取得日 2026-11-11／sha256:c19fbf99c94b／立会市場とToSTNeT市場の別欄、相場表の四本値、超大口取引は翌日の日報 |
