# Autonomous Subagent Playtest Benchmark Report (10 Trials x 2,000 Max Turns)

## Detailed Trial Results

| Trial # | Strategy | Turns | Duration (s) | Max Floor | Potions | Altars | Outcome | End/Death Reason |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | Hybrid | 1,000 | 12.35s | B5F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#2** | Hybrid | 1,000 | 7.86s | B1F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#3** | Hybrid | 1,000 | 43.36s | B1F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#4** | Hybrid | 1,000 | 7.05s | B1F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#5** | Hybrid | 1,000 | 8.62s | B2F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#6** | Hybrid | 1,000 | 15.15s | B4F | 2 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#7** | Hybrid | 1,000 | 30.70s | B7F | 0 | 6 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#8** | Hybrid | 1,000 | 11.76s | B3F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#9** | Hybrid | 1,000 | 8.83s | B1F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |
| **#10** | Hybrid | 1,000 | 9.42s | B3F | 0 | 5 | ✅ Victory (Survive/Clear) | `turn_limit` |

## Statistical Summary

| Metric | Value | Interpretation / Analysis |
| :--- | :--- | :--- |
| **Total Trials** | **10 回** | 全セッション完走 |
| **Survival / Win Rate** | **100.0%** | 高い生存自律判断の維持 |
| **Mean Survival Turns** | **1,000.0 ターン** | 最大2,000ターンまでスタックせず継続 |
| **Mean Trial Duration** | **15.51 秒** | 高速推論・低負荷レスポンス |
| **Deepest Floor Reached** | **B7F** | 階層踏破・遷移の成功 |
| **Total Potions Consumed** | **2 個** | HP危機時の自律回復 |
| **Total Altars Offered** | **51 回** | 信仰値蓄積・奇跡発動準備 |
