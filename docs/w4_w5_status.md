# W4・W5・FIX-05 の実装状況と実行手順

**実装とテスト（合成データ）は完了。J-Quants の実データでの実行は未実施**（データはローカル PC にある）。結果が出るまで、採否・モデルの既定変更はしない。

## 実装したもの
| 項目 | 場所 | 内容 |
|---|---|---|
| W4 追記専用の予測台帳（FIX-08） | `forecastlib/ledger.py`（`AppendOnlyLedger`） | ハッシュ連鎖（書き換えを検出。壊れた台帳には追記しない）。J-Quants 正本（`source="jquants"`）以外は拒否。データ目録・コード版・設定のハッシュが必須。採点は別の行で追記（予測の行は変えない）。置き場は `data/jquants/ledger/` |
| FIX-05 外側評価 | `forecastlib/outer.py` | 各ブロックの前に確定した損失だけで採用モデルを選び（余白 h 日）、そのモデルの外側の損失を連結。基準 B1・B0 との比較、全期間で選んだ場合との差（楽観の大きさ）を出す |
| W5 パネル・特徴量 | `selectlib/panel.py`、`features.py` | リバランス日（21 営業日ごと）、ラベル（T+1 始値→T+22 始値−TOPIX）、対象銘柄（内国普通株・市場区分・流動性・履歴）。SEL-A（9 特徴量）・SEL-B（6 特徴量）。先読みがないことをテスト |
| W5 モデル | `selectlib/model.py` | リッジ（α=1.0 固定、平均損失の形で標本数に依存しない）、LightGBM（任意）。k−1 期のラベルは k で使わない（テスト） |
| W5 執行台帳 | `selectlib/portfolio.py` | 現物・買いのみ・100 株単位・全売却→再購入。分割をまたぐ換算、ストップ高で買えない、ストップ安・売買なしの売却繰り延べ（最大 5 日、強制評価）。円単位で整合（3 ケースのテスト） |
| W5 評価 | `selectlib/evalsel.py` | 逆ボラ重み（上限 2 倍）、TOPIX ボラの現金ゲート、年率超過収益、上位 3 期間を除く頑健性、暦年別、採用ゲートの機械的な判定、DSR、PBO（CSCV） |
| 実行 | `scripts/w5/run_selection.py`、`scripts/w5/forecast_tools.py` | 下記 |

## ローカルでの実行（`git pull` のあと、リポジトリのフォルダで）
```
python -m pip install pandas numpy pyarrow lightgbm
python scripts/w5/run_selection.py                    # W5。試行は data/jquants/ledger/trials.jsonl に追記。集計は data/jquants/results/w5/summary.json
python scripts/w5/forecast_tools.py outer --n 30      # FIX-05。流動性上位 30 銘柄（約 10〜30 分）
python scripts/w5/forecast_tools.py forecast 7203 5802   # W4。最新日の予測を台帳へ
python scripts/w5/forecast_tools.py score 7203 5802      # 期日後の採点
```
出力は集計のみ。結果を貼ってください（生の表は不要）。

## 注意（結果の読み方）
- **評価期間が短い**: 既定は 2022-04-04 以降のプライム・スタンダードだけ（旧区分の案は未確定）。リバランスは約 50 回で、学習の最初の 12 回を除くと約 40 回。統計的な力は弱く、DSR・PBO も不安定。旧区分の案を使うと期が増えるが、仕様変更の確定が先。
- σ̂ の簡易版: 逆ボラの σ̂ は、forecastlib の S3 ではなく、EWMA と 22 日 GKYZ の幾何平均の簡易版。
- 全売却→再購入のため、同じ銘柄を続けて持つ場合もコストを 2 回払う（保守的）。
- 採用の判断は利用者。ゲートの機械的な判定は参考。
- FIX-09 (3): リッジ罰則は平均損失の形で標本数に依存しない（テスト済み）。パネルでの検証（標本数・欠損・日付の重みが変わったときの実効的な強さ）は、上の実行結果を見てから。
- FIX-09 (2): 標本内残差の過小評価は、外側評価の結果と並べて診断する（未実施）。

## 追加（2026-11-14 承認）: チャート規則の一斉検証・診断・前向きの記録
仕様は `docs/w5_protocol.md` の「追加の事前固定」。実装とテスト（合成データ）は完了、実データでの実行はローカル PC で行う。
```
python scripts/w5/diagnose.py        # 段階 0（特徴量ごとの IC・係数の安定性）と H0（理想と実現の差の分解）。診断のみ
python scripts/w5/rule_study.py      # 段階 1〜3（49 規則 × 2 期間、条件つき、3 つの型）。約 20〜60 分
python scripts/w5/forward.py record  # 前向きの記録（最新日の引け後。データ更新のたびに）
python scripts/w5/forward.py score   # 結果が出た記録の採点
python scripts/w5/forward.py summary # 21 営業日以上あけた記録だけで集計
```
- 規則は 49 個（signal_frame 41 ＋ ローソク足 8）。事前に「45 個・53 個・106 検定」と書いていたのは数え間違いで、実際は 41 個・49 個・98 検定（文書を訂正済み）。
- 確認期間（2022-04 以降）は、発見期間の通過規則だけを 1 度読み、読んだ記録を台帳（`confirmation_read`）に残す。
- 前向きの記録は、データを更新する（J-Quants の追加取得 → `build_processed.py`）たびに、`forward.py record` を実行する。独立な記録は 21 営業日（約 1 か月）あけて数える。12 期たまるまで結論は出さない。
- 実行しない: 単元未満株（H1）、上位 50 銘柄（H3）、緩衝帯（H2）、進捗率の特徴量（H4）は未承認。

## 追加（2026-11-14）: 底打ち・上昇しやすい局面（12 検定）と下がり方の特徴（探索的）
```
python scripts/w5/bottom_study.py     # 約 10〜20 分。家族 1（6 規則 × h{5, 21}）と家族 2（下げ状態 × 10 特徴）
```
仕様は `docs/w5_protocol.md`。家族 2 の yes / no の水準は、`data/jquants/results/bottom/summary.json` の `family2_descriptive_levels_discovery`。

## 追加（2026-11-14）: 市場の内部指標と、Standard 固有データ
```
python scripts/w5/breadth_study.py                       # 市場の内部指標 M1〜M5 の極端な日（20 検定）。約 10 分
python scripts/jquants/backfill_extra.py                 # 計画（通信なし）
python scripts/jquants/backfill_extra.py --execute       # 信用残・空売り比率・投資部門別の取得（約 25〜30 分、再開可）
python scripts/jquants/build_processed.py                # 加工（上の 3 表が processed に入る）
```
取得できる Standard 固有データ: 信用取引週末残高（週次・銘柄別、公表日つき）、業種別空売り比率（日次・33 業種）、投資部門別売買状況（週次）。売買内訳データは Premium 限定で不可。モデルの入力にするのは、事前固定した除去実験を通してから。

## 追加（2026-11-14）: 信用残・空売り比率の目印（K1〜K5、10 検定）
```
python scripts/w5/margin_study.py     # 約 10〜15 分（要: backfill_extra.py と build_processed.py の完了）
```
仕様は `docs/w5_protocol.md`。出力に、目印ごとのデータのある割合（coverage）と、yes / no の水準（記述）も出る。

## 追加（2026-11-14）: 探索マップ（記述。発見期間のみ）
```
python scripts/w5/explore_map.py      # 約 10〜15 分。検定ではなく、8 つの見方の集計（保有期間別の IC、買い側と売り側、流動性・買える銘柄、決算発表日の値動き、夜間と日中、暦、業種）
```
確認期間（2022-04-04 以降）のデータには触れない（境界以降のデータを壊しても出力が変わらないことをテストで確認）。試行台帳には書かない。

## 追加（2026-11-14）: 季節性（毎年同じ時期の上げ下げ）と、広い母集団
```
python scripts/w5/seasonal_study.py   # 約 10 分。S1 同じ月の持続、S2 配当の権利取り、S3 決算発表前の上昇（5 検定）
```
母集団は、内国普通株の全市場（TOKYO PRO・その他を除く）、売買代金 60 営業日平均 ≥ 2,000 万円、履歴 ≥ 250 営業日。流動性の段階（A ≥ 5 億円、B 5,000 万〜5 億円、C それ未満）別の結果と、段階ごとのコスト（片道 15・30・60 bps）を引いた値も出る。仕様は `docs/w5_protocol.md`。

## 追加（2026-11-14）: パターン図鑑（条件の組み合わせの網羅）
```
python scripts/w5/pattern_atlas.py    # 約 10〜20 分。条件（流動性・株価・下落・リターン・ボラ・割安・修正・ROE・信用残・トレンド・業種・市場・月）の 1〜3 個の組み合わせをすべて数え、買い側の上位 30・避ける側の上位 15 を、暦年ごとの成績つきで出す
```
確認期間は、報告した 45 個だけを 1 度読む。検討した組み合わせの総数と、補正後の q 値を併記する。仕様は `docs/w5_protocol.md`。

## 追加（2026-11-14）: S2（配当の権利取り）の深掘り診断
S2 は、発見期間と確認期間の両方で再現した（上位 1/5 の超過 +1.84% → +1.35%、IC 0.115 → 0.123）。採用する仕様は変えず、中身を確認する。
```
python scripts/w5/s2_deep_dive.py     # 約 5〜10 分。権利月別、利回り 5 段階、流動性の段階別と年別、感度の一覧、実行できる形（段階 A・上位 15 銘柄）
```

## 追加（2026-11-14）: S2（配当の権利取り）の前向きの記録
```
python scripts/w5/forward_s2.py record     # データ更新のたびに（買いの予定日が約 3 か月以内の権利月の候補を、台帳に記録）
python scripts/w5/forward_s2.py score      # 権利付き最終日を過ぎたものを採点（買いの日より前の記録だけを使う）
python scripts/w5/forward_s2.py summary    # 12 か月以上たまるまで、結論を出さない
```
台帳: `data/jquants/ledger/forward_s2.jsonl`（追記専用のハッシュ連鎖）。仕様は変えない（40 営業日前の始値で買い、権利付き最終日の始値で売り、予想配当利回りの上位 1/5）。

## 追加（2026-11-14）: パターン図鑑 v2
```
python scripts/w5/pattern_atlas.py    # v2: 市場区分を新旧をまたぐ 3 区分に、観測が 9 割以上重なる候補を除去。結果は results/atlas_v2/
```
確認期間は v1 で 1 度読んでいるので、v2 の確認は 2 度目の読み（v1 とは独立な証拠にならない）。

## 追加（2026-11-14）: 除外フィルターの検証
```
python scripts/w5/exclusion_study.py   # 約 5〜10 分。信用残の「避ける状態」（X1〜X4）が効くか（検証 A）、順位予測の上位 15 から除くと良くなるか（検証 B）。結果は results/exclusion/
```
仕様は docs/w5_protocol.md「除外フィルターの検証」（事前固定）。主たる族は X1・X2・U12（定義が発見期間だけから決まったもの）。X3・X4・U1234 は、パターン図鑑で確認期間を見た後に選んだ由来なので、記述のみ（判定に使わない）。確認期間は 1 度だけ読み、台帳に記録する。事前に、信用残（`processed/margin_interest.parquet`）が必要。

## 追加（2026-11-14）: S2 の実行可能性（口座での売買の模擬）
```
python scripts/w5/s2_portfolio.py      # 約 3〜5 分。1,000 万円・現物・100 株単位・コスト込みで、S2 が口座にいくら残るか。結果は results/s2_portfolio/
```
仕様は docs/w5_protocol.md「S2 の実行可能性」（事前固定）。試行は 2 本（主: 段階 B のみ、副: 段階 A＋B）。確認期間は S2 で既読なので、新しい証拠ではなく、目減りの計算。

## 追加（2026-11-14）: 型破りの探索（強制的な売買と、会社の癖）
```
python scripts/w5/unconventional_study.py   # 約 5〜10 分。12 検定（市場の昇格、貸借銘柄の選定、株式分割、ストップ高・安、権利落ち後の戻り、進捗率、自社株買い）。結果は results/unconventional/
```
仕様は docs/w5_protocol.md「型破りの探索」（事前固定。予測の向きを先に書いた）。発見期間で BH を通り、予測と同じ向きのものだけ、確認期間を 1 度読む。

## 追加（2026-11-14）: 修正した「買える日」での測り直し
PowerShell で、環境変数を設定してから、各スクリプトを実行する（結果は `results/<名前>_execopen/` に出る。元の結果は残る）。
```
$env:JQ_EXEC = "open"
python scripts/w5/rule_study.py        # 約 30〜60 分
python scripts/w5/pattern_atlas.py     # 約 10〜20 分
python scripts/w5/explore_map.py       # 約 10〜15 分
python scripts/w5/bottom_study.py
python scripts/w5/breadth_study.py
python scripts/w5/earnings_study.py
python scripts/w5/margin_study.py
Remove-Item Env:JQ_EXEC                # 終わったら、元に戻す
```
仕様は docs/w5_protocol.md「修正した『買える日』での測り直し」。**まず rule_study・pattern_atlas・explore_map の 3 つ**（結論に使った主なもの）。残りは、必要なら。

## 追加（2026-11-14）: 前向きの記録の更新（月 1 回）と、信用売りの実行可能性
```
powershell -ExecutionPolicy Bypass -File scripts\update_and_record.ps1    # 追加取得 → 加工 → 順位予測・S2 の記録 → 採点・集計。キーは実行時に入力（画面に出ない）
python scripts/w5/short_feasibility.py                                    # ストップ高の翌朝の空売りの、コスト・貸借・踏み上げの計算（--rt-cost 0.004 --borrow 0.0115 を、証券会社の条件に合わせて変更）
```
初回の `update_and_record.ps1` は、追加取得が、取得済みの日をチェックポイントで飛ばすか確かめるため、出力を貼る。独立な記録は 21 営業日あけて数える。12 期たまるまで結論は出さない（S2 は 12 か月）。

## 追加（2026-11-14）: 個別株の弾力性、気になった銘柄の診断と記録
```
python scripts/w5/elasticity_study.py                 # 約 5〜10 分。下げた後に戻る癖（3 定義 × 5・21 日 = 6 検定）。結果は results/elasticity/
python scripts/w5/stock_profile.py --code 7203        # 気になった銘柄の診断（集計だけを画面に出す。1 件ごとの表は results/profile/<コード>.json にだけ）
python scripts/w5/watchlist.py add --code 7203 --cause 一過性 --view 戻る --note "理由のメモ"   # 指定の記録（原因: 一過性/構造的/需給/連想/不明、予想: 戻る/戻らない）
python scripts/w5/watchlist.py score                  # 22 営業日目の始値までそろったものを採点
python scripts/w5/watchlist.py summary                # 原因の分類ごとの集計（12 件未満は結論を出さない）
```
仕様は docs/w5_protocol.md「個別株の弾力性の検証」「気になった銘柄の診断と、指定の前向きの記録」（事前固定）。

## 追加（2026-11-15）: 期待と実態の不一致（割安 × 財務の強さ）、材料のない下げ、財務危機
```
python scripts/w5/mismatch_study.py                   # 約 10 分。9 検定（割安 × F、材料なしの下げ、財務危機）。結果は results/mismatch/
python scripts/w5/watchlist.py add --code 7203 --cause 一過性 --view 戻る --type 業績回復 --check "次の決算" --exit "下方修正が出たら撤回"
```
`stock_profile.py` の出力に、財務の強さ F（8 項目）・財務危機・簿価利回りの順位・直近の開示の有無が加わった。`watchlist.py` は、投資の型・確認時期・反証条件を記録し、21・63・126 営業日で採点する。
出力の `columns_available` で、決算データの列（売上・営業利益・純利益・総資産・純資産・営業 CF・株式数・BPS）が読めているかを確かめる。false があれば、その項目は計算されていない。

## 追加（2026-11-15）: 全銘柄での極端な出来事の漂流、信用売りの精査
```
git pull
python scripts/w5/extreme_events.py        # 約 10 分。6 出来事 × 5 段階 × 2 保有 = 60 検定（売買代金 500 万円以上の全銘柄）。結果は results/extremes/
python scripts/w5/short_feasibility.py     # 約 2〜3 分。売り残の重さ・流動性で分け、逆日歩の感度・資金配分の計算を加えた（要: 信用残 processed/margin_interest.parquet）
```
仕様は docs/w5_protocol.md「全銘柄での極端な出来事の漂流と、信用売りの精査」（事前固定）。`extreme_events.py` の画面の出力は、通過したセルと、通過しなかったセルの発見期間の値だけ（全セルは results/extremes/summary.json）。

## 追加（2026-11-15）: ボラを合わせた比較（C）、極端な動きの回避フィルター（B）
```
git pull
python scripts/w5/vol_matched_study.py         # 約 10 分。極端な出来事の後の弱さが、高ボラ株の低リターンで説明されるか。結果は results/vol_matched/
python scripts/w5/extreme_filter_study.py      # 約 5〜10 分。順位予測の上位 15 から、直近 5 営業日に極端な動きがあった銘柄を除くと良くなるか。結果は results/extreme_filter/
```
仕様は docs/w5_protocol.md「極端な動きの回避フィルターと、ボラを合わせた比較」（事前固定）。`vol_matched_study.py` の `verdict_counts` と、`cells` の `verdict`（ボラでは説明できない／一部／ボラで説明される）を見る。

## 追加（2026-11-15）: 指数レベルの逆張りと、日次の前向きの記録
```
git pull
python scripts/w5/index_contrarian.py            # 1 分ほど。TOPIX 3 定義 × 5・21 日、33 業種 2 定義 × 5・21 日 = 10 検定。結果は results/index_contrarian/
python scripts/w5/forward_events.py record       # データを更新するたびに（最新日の引け後）。信用売りの候補（紙の上）と、指数の状態を記録
python scripts/w5/forward_events.py score        # 結果がそろったものを採点
python scripts/w5/forward_events.py summary      # 集計（候補 30 件、指数 10 エピソード たまるまで、結論を出さない）
```
`update_and_record.ps1` に、`forward_events.py record/score/summary` を足してある。記録は、データの更新が毎日でなくてもよい（記録しなかった日は、結果と無関係に抜けるだけ）。実際の売買はしない（紙の上）。
