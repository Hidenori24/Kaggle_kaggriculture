Exit code: 0
Wall time: 1.3 seconds
Output:
# Kaggriculture Agent

Kaggriculture向けの、公式 `kaggle-environments` SDKで実行できるルールベースエージェントです。

## 現在の状態

- 公式SDKのローカルシミュレーションに対応
- 作物中心の決定的ベースライン
- 単体テストとCIを用意
- 実Kaggle提出は、競技固有の提出形式を公式ページで確認するまで安全停止

## 環境構築

Python 3.11以上を使用します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## テストとシミュレーション

```powershell
python -m pytest
python scripts/simulate.py --episodes 3
```

公式環境は `kaggle_environments.make("kaggriculture")` で作成し、エージェント対 `random` の複数対戦を実行します。

## 提出

Kaggle規約同意とGitHub Actions Secret登録はユーザー操作が必要です。提出形式が確定した後、`submission` ブランチへのpushを提出トリガーにします。現段階のActionsは、未確認の提出形式で誤提出しないよう停止します。

## 構成

- `src/kaggriculture_agent/`: エージェントと戦略
- `tests/`: 単体テスト・SDKシミュレーションテスト
- `scripts/`: シミュレーション・提出ゲート
- `configs/`: 戦略設定
- `docs/`: 仕様・実験履歴
- `.github/workflows/`: CIと提出ワークフロー

公式仕様: [Kaggle EnvironmentsのKaggriculture](https://github.com/Kaggle/kaggle-environments/tree/master/kaggle_environments/envs/kaggriculture)

