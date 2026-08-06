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
