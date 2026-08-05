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
