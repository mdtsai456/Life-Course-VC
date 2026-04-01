# Proposal: simplify-semaphore-try-finally

## Problem

`backend/app/routes/voice.py` L296-322 的 semaphore acquire/release 分散在兩個獨立的 `try` block 中：

1. **第一個 try (L296-302)**：acquire semaphore，附帶一個 `except HTTPException: raise` —— 這是 no-op，沒有實際效果。
2. **第二個 try (L303-322)**：執行 XTTS 推論，`finally` 中 release semaphore。

程式碼正確，但冗餘的 `try/except` 增加了閱讀負擔，讓人需要推理才能確認 acquire/release 配對無誤。

## Solution

刪除第一個 `try/except HTTPException: raise`，讓 acquire 裸露在 try 外面：

```python
async with admission_lock:
    if semaphore.locked():
        raise 503
    await semaphore.acquire()

try:
    async with xtts_lock:
        result = ...
except OOMError:
    ...
finally:
    semaphore.release()
```

結構保證：acquire 失敗 → 不進 try → 不 release；acquire 成功 → finally 保證 release。不需要額外的 flag 或狀態追蹤。

## Scope

- **In scope**: 移除 `voice.py` 中冗餘的 `try/except HTTPException: raise` wrapper
- **Out of scope**: 併發控制邏輯本身不變（admission_lock、semaphore、xtts_lock 的語意與用途不動）

## Risks

- **低風險**：純結構簡化，不改變任何執行路徑或異常處理語意
