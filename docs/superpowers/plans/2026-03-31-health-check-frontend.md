# Health Check 前端狀態顯示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 頁面載入時檢查後端 health 狀態，模型未就緒時 disable 送出按鈕並顯示「服務準備中…」。

**Architecture:** 新增 `checkHealth` API function + `useHealthCheck` hook 進行 polling，VoiceCloner 整合 hook 結果控制按鈕狀態。

**Tech Stack:** React hooks, fetch API, Vite proxy config

**Spec:** `docs/superpowers/specs/2026-03-31-health-check-frontend-design.md`

---

### File Map

| 檔案 | 動作 | 職責 |
|------|------|------|
| `frontend/vite.config.js` | 修改 | 加入 `/health` proxy 規則 |
| `frontend/src/services/api.js` | 修改 | 新增 `checkHealth()` function |
| `frontend/src/hooks/useHealthCheck.js` | 新增 | polling 邏輯，回傳 `serviceReady` |
| `frontend/src/components/VoiceCloner.jsx` | 修改 | 整合 `useHealthCheck`，控制按鈕狀態與文字 |

---

### Task 1: 加入 health proxy 規則與 checkHealth API function

**Files:**
- Modify: `frontend/vite.config.js:6-13`
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: 在 vite.config.js 加入 `/health` proxy**

後端 health endpoint 在 `/health`，但 Vite dev proxy 只轉發 `/api/*`。需要加入 `/health` 規則。

```js
server: {
  proxy: {
    '/api': {
      target: process.env.VITE_API_TARGET || 'http://localhost:8000',
      changeOrigin: true,
    },
    '/health': {
      target: process.env.VITE_API_TARGET || 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

- [ ] **Step 2: 在 api.js 新增 checkHealth function**

在 `frontend/src/services/api.js` 底部加入：

```js
export async function checkHealth() {
  const response = await fetch('/health')
  return response.ok
}
```

不需要讀 response body，只要知道是否 200。網路錯誤會 throw，呼叫端 catch 後視為未就緒。

- [ ] **Step 3: 驗證 proxy 設定**

啟動 dev server，在瀏覽器開 devtools 確認 `fetch('/health')` 有正確代理到後端。

Run: `cd frontend && npm run dev`

在瀏覽器 console 執行 `fetch('/health').then(r => r.json()).then(console.log)` 確認回傳 `{ status: "ok"|"loading", checks: { xtts_v2: true|false } }`。

- [ ] **Step 4: Commit**

```bash
git add frontend/vite.config.js frontend/src/services/api.js
git commit -m "feat: add checkHealth API function and /health proxy"
```

---

### Task 2: 建立 useHealthCheck hook

**Files:**
- Create: `frontend/src/hooks/useHealthCheck.js`

- [ ] **Step 1: 建立 useHealthCheck.js**

```js
import { useEffect, useState } from 'react'
import { checkHealth } from '../services/api'

const POLL_INTERVAL_MS = 3000

export default function useHealthCheck() {
  const [serviceReady, setServiceReady] = useState(false)

  useEffect(() => {
    let timerId = null
    let cancelled = false

    async function poll() {
      try {
        const ok = await checkHealth()
        if (cancelled) return
        if (ok) {
          setServiceReady(true)
          return // stop polling
        }
      } catch {
        // network error — keep polling
      }
      if (!cancelled) {
        timerId = setTimeout(poll, POLL_INTERVAL_MS)
      }
    }

    poll()

    return () => {
      cancelled = true
      clearTimeout(timerId)
    }
  }, [])

  return serviceReady
}
```

關鍵設計：
- 用 `setTimeout` 遞迴而非 `setInterval`，確保上一次 fetch 完成後才排下一次
- 收到 200 後不再排 timeout，自然停止 polling
- `cancelled` flag 防止 unmount 後 setState
- cleanup 清除 pending timeout

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useHealthCheck.js
git commit -m "feat: add useHealthCheck hook with 3s polling"
```

---

### Task 3: 整合到 VoiceCloner

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx`

- [ ] **Step 1: 加入 import**

在 `VoiceCloner.jsx` 第 6 行 `import LoadingButton` 之前加入：

```js
import useHealthCheck from '../hooks/useHealthCheck'
```

- [ ] **Step 2: 在元件內呼叫 hook**

在 `VoiceCloner` function 內，第 77 行 `const { execute, ... } = useAsyncSubmit()` 之後加入：

```js
const serviceReady = useHealthCheck()
```

- [ ] **Step 3: 將 serviceReady 加入 disabled 條件**

修改第 227 行的 `isDisabled`：

```js
const isDisabled = !serviceReady || !audioBlob || !text.trim() || loading || isRecording || isAcquiringMic || tooShort || tooLong
```

在最前面加上 `!serviceReady`。

- [ ] **Step 4: 修改送出按鈕的 children 文字**

修改第 337-345 行的 `LoadingButton`：

```jsx
<LoadingButton
  type="submit"
  className="submit-button"
  disabled={isDisabled}
  loading={loading}
  loadingText="處理中…"
>
  {!serviceReady ? '服務準備中…' : '送出'}
</LoadingButton>
```

將固定的 `送出` 改為根據 `serviceReady` 顯示不同文字。

- [ ] **Step 5: 手動驗證**

1. 啟動後端（模型載入需要時間）和前端
2. 頁面載入後確認按鈕顯示「服務準備中…」
3. 模型載入完成後，按鈕自動切換為「送出」
4. 錄音 + 輸入文字後可正常送出

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/VoiceCloner.jsx
git commit -m "feat: show service loading status on submit button"
```
