# 実験履歴

## 2026-08-05: baseline-0.1

- 戦略: 初期NW 5x5区画でCARROTを購入・植付・給水・収穫する決定的ルールベース
- 動物、雇用、土地購入、市場売却最適化は未実装
- 公式SDKシミュレーションと複数エピソード評価をCIで実行する
- Kaggle実提出: 競技固有の公式提出形式確認待ち

### ローカル実行結果

実行コマンド: `python scripts/simulate.py --episodes 3`

| Episode | Agent reward | Random reward |
| ---: | ---: | ---: |
| 0 | 2600.0 | 0.0 |
| 1 | 2600.0 | 0.0 |
| 2 | 2600.0 | 0.0 |

注: OpenSpielの未登録ゲームに関する警告がstderrへ出力されたが、Kaggricultureの実行と終了ステータスは正常だった。

## 2026-08-05: strong-replay-analysis

- 対象: `90041552.json`, `90073673.json`
- 共通所見: 約300回のHIRE、土地2回拡張、牛8・羊6、WHEAT/STRAWBERRY/MELONの併用、動物のFEED/CARE、肥料回収・施肥。
- 結論: 現行版の作物ルート微調整では差が埋まらない。人員・土地・動物・飼料・肥料を含む段階的な経済ループを実装する。
- 実装計画: [strong-policy-plan.md](strong-policy-plan.md)

## 2026-08-05: replay-analysis-90134794-90135506

- 対象: `90134794.json`（自分 22,184、相手 40,096）、`90135506.json`（自分 31,453、相手 18,455）。
- 自分の2試合の行動は同一で、NW区画のみ、MELONのみ、HIRE 180、BUY_SEED:MELON 60、SELL:MELON 136、HARVEST 40。`BUY_LAND`、動物、WHEAT、FEED、CARE、FERTILIZEは0回。
- 敗戦相手は土地を拡張せず、HIRE 253、牛4・ガチョウ1、WHEAT種62、WHEAT購入36、FEED 101、CARE 98、COLLECT_FERTILIZER 93、HARVEST 135を実行していた。
- 勝利した試合の相手は、初期からSTRAWBERRYと土地を購入したが、3区画開放後も`BUY_LAND`を17日目以降に196回繰り返し、WHEATを売って直後に買う循環も続けていた。これは拡張路線の失敗例であり、採用しない。
- 次の実装順を確定した: (1) NW内でWHEAT・動物・肥料の循環、(2) 10人雇用と役割分担、(3) 資金・残日数・未開放区画を条件にした土地拡張、(4) 拡張後の作物面積利用。
- 土地は「未開放区画があり、必要現金を残して購入できる場合に各区画1回だけ」とし、購入後に観測で`unlocked_quadrants`が変わらなければ再注文しない。
- 飼料WHEATは販売対象から除外し、動物数と残日数に基づく予備在庫を確保する。

## 2026-08-06: submission-guard-fix

- GitHub Actions run `30990317238` では、pytest・5エピソード評価・パッケージ生成まで成功した。
- 提出直前に `kaggle competitions list --search kaggriculture` が大会を返さず、安全チェックが停止した。`KAGGLE_API_TOKEN`未設定や提出コマンド失敗ではなく、シミュレーション大会の一覧検索を必須にしていた実装上の問題だった。
- `scripts/submit.py` は、公式確認済みの設定締切・提出履歴・重複コミット・サイズを検査し、アクセス可否は実際の `kaggle competitions submit` に委ねるよう修正する。

## 2026-08-06: economic-policy-prototype

- 実装したもの: 需要ベースの最大10人雇用、WHEAT予備を考慮した売却、役割別の作物・動物・肥料・建設ジョブ、条件付き土地/動物購入、終端3ターンの回収優先。
- 初回結果: 31,113点まで上がったが、動物を売却対象にしていた不具合を発見。
- 不具合修正後: 23,764〜23,785点へ低下。動物の購入・配置が作物ルートを圧迫し、FEED/COLLECT_FERTILIZERも成立していなかった。
- 判断: この統合版は採用せず、安定版（26,907〜28,371点）へ戻した。次回は動物ループを独立した小さな状態機械として検証してから、作物ルートへ統合する。
- `hamburger` Anchor Exactの大量コードをそのまま移植せず、まず経済フェーズと終端回収を個別に再現する。

## 2026-08-06: baseline-stability-20-seeds

- 対象: 動物ループ統合版を破棄した後の現行安定版。
- 評価: `python scripts/simulate.py --episodes 20`
- 結果: 平均 28,808.2、中央値 28,371、最低 26,907、最高 31,453。
- 20回中19回が28,000点以上で、ランダム相手には全試合で勝利した。
- スコアは26,907 / 28,371 / 29,333 / 31,453に集中しており、実装は安定している一方、動物・土地・複数作物による上振れ余地をまだ使えていない。

## 2026-08-06: hamburger-anchor-reproduction

- `kaggriculture-hamburger.ipynb` の `Anchor Exact` をNotebook内のgzip/base64 blobからメモリ上へ抽出し、現在の `kaggle-environments==1.32.4` で実行した。
- 5シードの報酬は 176,135 / 186,287 / 181,913 / 182,757 / 189,406。Notebookの評価だけでなく、ローカルSDKでも大幅な優位を再現できた。
- 共通行動: HIRE 306、BUY_LAND 2、牛8・羊6、BUY_SEEDはMELON21/WHEAT66/STRAWBERRY44、BUY_PRODUCT WHEAT約967、FEED319、CARE308、COLLECT_FERTILIZER318、FERTILIZE107、HARVEST338。
- 現行版との差は、土地購入そのものではなく、`PICKUP -> PLACE -> FEED/CARE -> COLLECT_FERTILIZER -> FERTILIZE -> HARVEST -> DROP/SELL` の物流状態機械と、日単位の役割・経済フェーズである。
- 次の移植単位は、Anchorの固定行動列をコピーすることではなく、(1)ジョブ台帳、(2)運搬中在庫を含む状態、(3)動物のサービス期限、(4)市場注文の上限10件、(5)step 718までの終端回収を分離実装する。

## 2026-08-06: anchor-state-policy-prototype

- Anchorの行動統計をもとに、状態依存の市場注文、10人雇用、混成作物、土地拡張、牛・羊、飼料、牧場、肥料回収を1つの小型状態機械へ統合した。
- SDKでの検証結果は1〜5点で、同一タイルへの行動集中と市場注文上限10件の干渉により、作物が枯れ、資金も使い切った。
- この候補は提出版へ採用せず、コードは現在のエントリポイントから切り離した。固定行動列を部分移植する場合も、役割分担と搬送状態を先にテストする必要がある。

## 2026-08-06: baseline-ten-hands

- 採用候補: 既存の決定論的作物ルートを維持し、雇用上限を6人から10人へ拡張。雇用費のFibonacci列も10人分へ正確化した。
- `python -m pytest -q`: 6 passed。
- `python scripts/simulate.py --episodes 3`: 31,603 / 31,603 / 30,348点、相手は全て0点。
- 追加の10エピソード評価: 平均30,617.7、中央値31,603、最低28,944、最高31,603。10/10で相手を上回った。
- 20シードの安定版中央値28,371点を全3試合で上回ったため、今回の区切りではこの安全な改善版を提出候補とする。動物・肥料ループは未統合のまま、次の実験へ分離する。

## 2026-08-06: submission-34

- GitHub Actions Run `31071666989` / job `92520688039` が成功。
- 提出コミット: `5f58aaabb9df2e999c6b52d4e35d218cc5874baf`。
- パッケージSHA-256: `c4473d3566db7b4a8efdda7d94166d6b71b960f650fe247237229eb02191b5ed`。
- Actions Summary: `3 submissions remaining today`、`Successfully submitted to Kaggriculture`。
- Kaggleの最終スコアは反映待ち。Actions上の提出成功とKaggle画面の採点結果は別タイミングで確認する。
