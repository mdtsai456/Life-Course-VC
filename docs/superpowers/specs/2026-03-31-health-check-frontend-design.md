# Health Check 前端狀態顯示

## 問題

後端 `/health` endpoint 回報 XTTS v2 模型載入狀態，但前端未使用。模型未就緒時，使用者送出請求只會得到錯誤。

## 設計

### 行為

1. 頁面載入時呼叫 `GET /api/health`
2. 非 200 回應（503 或網路錯誤）：標記 `serviceReady = false`，每 3 秒 poll 一次
3. 收到 200：標記 `serviceReady = true`，停止 polling
4. `serviceReady === false` 時，送出按鈕 disabled，文字顯示「服務準備中…」
5. `serviceReady === true` 後，按鈕恢復正常

### 改動範圍

| 檔案 | 改動 |
|------|------|
| `frontend/src/services/api.js` | 新增 `checkHealth()` function，GET `/api/health` |
| `frontend/src/hooks/useHealthCheck.js` | 新增 hook，管理 polling 邏輯與 `serviceReady` 狀態 |
| `frontend/src/components/VoiceCloner.jsx` | 呼叫 `useHealthCheck()`，將 `serviceReady` 傳給送出按鈕的 disabled 與文字 |

### 設計決策

- **表單內提示**（非全頁遮罩或 banner）：使用者可先錄音、輸入文字，只是不能送出
- **固定 3 秒間隔 polling**：模型載入通常數十秒到數分鐘，3 秒一次負擔極小
- **不區分連線失敗與模型載入中**：對使用者行為無差異，統一顯示「服務準備中…」

### 不做的事

- 不加全頁遮罩或 banner
- 不加指數退避
- 不加 health check 的視覺進度條
- 不區分錯誤類型
