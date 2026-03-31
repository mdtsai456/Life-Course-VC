---
date: 2026-03-31
topic: example-text-suggestions
---

# 文字預設範例

## Problem Frame

使用者面對空白的 textarea 時，不確定該輸入什麼長度或內容的文字。提供可一鍵填入的範例句子，降低使用門檻，同時展示功能預期用法。

## Requirements

- R1. 在 textarea 下方或上方顯示 2 個範例句子按鈕，點擊後填入 textarea
- R2. 範例風格混合：一句日常對話風、一句正式朗讀風
- R3. 若 textarea 已有內容，點擊範例按鈕直接覆蓋（不追加）
- R4. 範例按鈕在錄音中或處理中時 disabled

## Success Criteria

- 使用者能在 1 次點擊內填入範例文字並送出

## Scope Boundaries

- 不做可自訂範例功能
- 不做隨機/多組輪替範例
- 不需後端改動

## Next Steps

→ `/ce:plan` for structured implementation planning
