---
title: "feat: 錄音最低秒數前端提示"
type: feat
status: completed
date: 2026-03-31
---

# feat: 錄音最低秒數前端提示

## Overview

後端要求音訊樣本 ≥ 3 秒，但前端沒有任何提示。使用者可以錄 1 秒就按送出，直到收到 HTTP 400 錯誤才知道太短。本計畫在前端加入最低秒數檢查：錄音不足 3 秒時 disable 送出按鈕並顯示提示文字。

## Problem Frame

使用者錄音後按「送出」，後端 `voice.py:267` 檢查 `duration_secs < 3.0` 並回傳錯誤訊息「音訊樣本太短，至少需要 3 秒。」這個體驗不理想 — 使用者應該在按送出之前就知道錄音不夠長。

## Requirements Trace

- R1. 錄音停止後若 `recordingSeconds < 3`，送出按鈕維持 disabled
- R2. 錄音停止後若 `recordingSeconds < 3`，在已錄製狀態旁顯示提示文字「錄音至少需要 3 秒」

## Scope Boundaries

- 不改後端驗證（後端驗證作為最後防線保留）
- 不新增檔案、元件、hook 或常數
- 不改錄音流程、計時器邏輯、或音檔上傳邏輯
- 不加倒數提示或計時器變色等額外功能

## Context & Research

### Relevant Code and Patterns

- `VoiceCloner.jsx:214` — 現有 `isDisabled` 條件：`!audioBlob || !text.trim() || loading || isRecording || isAcquiringMic`
- `VoiceCloner.jsx:63` — `recordingSeconds` state，計時器每秒遞增
- `VoiceCloner.jsx:254-268` — 錄音停止後顯示「✓ 已錄製 MM:SS」和預覽播放器
- `voice.py:267` — 後端 `if duration_secs < 3.0:` 回傳 HTTP 400
- `index.css:197-201` — `.recorded-status` 樣式（綠色文字）
- `index.css:78-86` — `.error-message` 樣式（紅色文字），可參考配色

## Key Technical Decisions

- **直接寫死 `3` 而不抽常數**：後端也是寫死的，只有一處用到。抽常數增加間接性但沒有實質好處。
- **用 `recordingSeconds` 而非解析 blob 長度**：`recordingSeconds` 已存在且即時更新，無需額外計算。計時器精度（整數秒）足夠用於 ≥ 3 秒的門檻判斷。
- **提示文字直接內嵌在 `recorded-status` 區塊旁**：保持 UI 結構簡單，不需要新的條件渲染區塊。

## Open Questions

### Resolved During Planning

- **要用 `<` 還是 `<=`？** — 用 `< 3`，即錄滿 3 整秒（`recordingSeconds === 3`）即可送出。後端用浮點數 `< 3.0`，前端用整數秒計時，錄滿 3 秒實際已超過 3.0 秒。

### Deferred to Implementation

- 無

## Implementation Units

- [x] **Unit 1: 加入最低秒數檢查與提示文字**

**Goal:** 錄音不足 3 秒時 disable 送出按鈕並顯示警語

**Requirements:** R1, R2

**Dependencies:** 無

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx`
- Modify: `frontend/src/index.css`

**Approach:**
- 在 `isDisabled` 條件加入 `recordingSeconds < 3`（沒有 blob 時 `!audioBlob` 已經 disable，所以此條件只在有 blob 時才是決定性的）
- 在 `audioBlob && !isRecording` 的條件區塊內，當 `recordingSeconds < 3` 時顯示提示文字
- 為提示文字加一個簡單的 CSS class，用與 `.error-message` 相近的紅色配色
- 提示文字加上 `role="alert"` 讓螢幕閱讀器自動播報（沿用現有 `recording-timer` 的 `aria-live` 無障礙模式）

**Patterns to follow:**
- 現有的 `recorded-status` span 和條件渲染模式
- `.error-message` 的紅色配色（`color: #b91c1c`）

**Test scenarios:**
- Happy path: 錄音 5 秒 → 停止 → 輸入文字 → 送出按鈕 enabled，無警語
- Happy path: 錄音恰好 3 秒 → 停止 → 送出按鈕 enabled，無警語
- Edge case: 錄音 1 秒 → 停止 → 送出按鈕 disabled，顯示「錄音至少需要 3 秒」
- Edge case: 錄音 2 秒 → 停止 → 送出按鈕 disabled，顯示警語 → 重新錄音 5 秒 → 停止 → 送出按鈕 enabled，警語消失
- Edge case: 尚未錄音 → 送出按鈕 disabled（既有行為不變）

**Verification:**
- 錄音 < 3 秒時送出按鈕不可點擊且有可見的提示文字
- 錄音 ≥ 3 秒時行為與修改前完全一致

## System-Wide Impact

- **Interaction graph:** 純前端 UI 變更，不影響任何 API 呼叫、hook 或後端行為
- **Error propagation:** 後端 3 秒驗證保留作為最後防線，前端只是增加早期反饋
- **Unchanged invariants:** 錄音流程、計時器邏輯、blob 組裝、API 提交邏輯皆不變

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| 計時器整數精度可能導致邊界誤判（例如錄了 2.9 秒但 `recordingSeconds` 顯示 2） | 用 `< 3` 而非 `<= 3`；後端驗證作為最終防線 |
