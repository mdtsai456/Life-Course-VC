# Proposal: api-network-error-chinese-messages

## Problem

`frontend/src/services/api.js` 的 `postForBlob()` 只處理了 HTTP 回應錯誤（status not ok），但 `fetch()` 本身拋出的網路層錯誤（斷線、伺服器掛了、DNS 失敗等）會以瀏覽器原生英文訊息直接顯示給使用者，例如 "Failed to fetch"（Chrome）、"Load failed"（Safari）。

同樣地，`response.blob()` 如果連線中途斷掉也會 throw，目前也沒有被攔截。

## Solution

在 `postForBlob()` 中，用 try/catch 包住 `fetch()` 和 `response.blob()`，將非 `AbortError` 的網路錯誤統一 map 成一句中文訊息：「無法連線到伺服器，請檢查網路連線後重試。」

不嘗試區分具體錯誤原因——各瀏覽器的 error message 不同且無法可靠辨識。

## Scope

- **In scope**: `postForBlob()` 中 `fetch()` 與 `response.blob()` 的網路錯誤中文化
- **Out of scope**: HTTP 回應錯誤處理（已有中文 fallback 機制）、`checkHealth()` 的錯誤處理（呼叫端已靜默處理）

## Risks

- **低風險**：只新增 catch 邏輯，不改變既有 HTTP 錯誤處理路徑
