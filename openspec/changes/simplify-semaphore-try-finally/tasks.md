# Tasks: simplify-semaphore-try-finally

## Tasks

- [x] 1. 移除 `voice.py` L296-302 冗餘的 `try/except HTTPException: raise`，讓 semaphore acquire 裸露在第二個 try block 外面
- [x] 2. 執行既有測試確認無 regression
