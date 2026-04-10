---
date: 2026-04-10
topic: docker-gpu-compose
---

# Docker Compose 與 GPU 後端執行環境

## Problem Frame

貢獻者與部署環境需要可重現的容器化流程；後端語音推論依賴 PyTorch 與 Coqui XTTS（見 `backend/app/main.py`、`backend/requirements.txt`），在 NVIDIA GPU 上可顯著降低延遲。需釐清：**是否一定要掛載 Volume**、**是否必須使用「NVIDIA 官方 Image」才能正常用 GPU**，並約束 repo 內 Docker 相關檔案的落點，讓後續規劃（`/ce:plan`）不需再猜產品邊界。

## Requirements

**檔案與目錄約定**

- R1. Repo 根目錄至少包含 `docker-compose.yml`。若團隊慣用其他 Compose 檔名，須在 Key Decisions 中固定一種；預設仍為 `docker-compose.yml`。
- R2. `backend/` 下至少包含 `Dockerfile` 與 `docker-entrypoint.sh`。
- R3. `frontend/` 下至少包含 `Dockerfile`。

**GPU 與執行環境（概念層）**

- R4. 當目標為在容器內使用 **NVIDIA GPU** 推論時，執行環境須滿足：主機安裝相容的 NVIDIA 驅動、容器執行時可將 GPU 設備傳入容器（常見為 NVIDIA Container Toolkit / `nvidia-docker` 生態），且容器內的 PyTorch 建置須與該 CUDA 執行環境相容（CPU-only 的 torch wheel 無法使用 GPU）。
- R5. **不要求**基底映像檔必須來自 `nvidia/` 命名空間；允許任一滿足 R4 的做法（例如官方 PyTorch 映像、或於 Debian/Ubuntu 基底上安裝帶 CUDA 的 PyTorch）。產品需求是「GPU 可用且相容」，不是「品牌為 NVIDIA 的 Dockerfile FROM 行」。
- R6. 提供一條明確的 **CPU 後備路徑**（與現行程式行為一致：`cuda` 若不可用則 `cpu`），使無 GPU 的開發者仍能啟動後端；Compose 可透過 profile、覆寫服務或文件說明區分 GPU / CPU 啟動方式（具體機制交由規劃決定）。

**Volume 掛載**

- R7. **不**將「所有服務一律必須掛載 volume」列為硬性需求；改為依目標分類：
  - **開發體驗**：建議對原始碼掛載 bind mount，避免每次改碼都重建映像。**已拍板**：以 Compose **profile**（或語意等同的兩組服務／覆寫）區分 **dev**（預設 bind mount 原始碼）與 **prod-like**（不掛原始碼、以映像內建程式為準，用於貼近上線驗證）。
  - **模型與快取**：建議為 Coqui/TTS 等下載的模型與快取目錄提供持久化，避免容器重建後重複下載大型檔案。**已拍板**：Compose **預設使用具名 volume**；操作說明須包含如何改為 **bind 主機目錄**（供備份、清快取、多專案共用等進階用途）。
  - **持久化業務資料**：若後端將上傳或任務產物寫入磁碟（見 `get_storage_root` 等設定），需透過 volume 或等同機制滿足跨重啟持久化；若僅記憶體或外部儲存則不在此強制。

## Success Criteria

- 新進開發者依 repo 內操作說明（路徑於規劃階段敲定，例如根目錄 `README` 或 `docs/` 下專章）可在 **有 NVIDIA GPU + Toolkit** 的機器上啟動後端並確認推論走 GPU（例如日誌出現 `device: cuda` 或等效驗證方式）。
- 無 GPU 的開發者仍可啟動同一套（或文件標明的 CPU）流程，功能可測（可能較慢）。
- `docker-compose.yml` 與各 `Dockerfile` 的職責清楚，且符合 R1–R3 的檔案落點。

## Scope Boundaries

- 本需求不涵蓋 **Apple Silicon / MPS** 專用映像或 Compose 變體（若未來需要，另開主題）；目前後端邏輯以 `torch.cuda.is_available()` 為準。
- 不規定雲端供應商（EKS、GKE、ECS 等）的正式上線拓樸；僅約束 repo 內開發／本機與類本機 Compose 的產品行為與檔案約定。

## Key Decisions

- **映像檔來源**：以「CUDA 相容 + PyTorch GPU build」為判準，不強制 `FROM nvidia/cuda:*`。
- **Volume**：視為強烈建議（開發、模型快取、持久化資料），而非單一句「一定要掛 volume」的全域硬性規則；細項依 R7。
- **開發 vs prod-like**：採 **Compose profile**（或等效）分開 dev（bind mount 原始碼）與 prod-like（不掛原始碼），由規劃決定實際 profile 名稱與啟動指令。
- **模型／快取持久化**：預設 **具名 volume**；文件說明如何改 **bind 主機路徑**。

## Dependencies / Assumptions

- 主機須具備與所選基底映像／PyTorch CUDA 版本相容的 NVIDIA 驅動；版本矩陣由規劃階段對照官方文件敲定。
- 現有後端依 `backend/requirements.txt` 安裝 `torch`；容器內須使用 **GPU 變體**的安裝方式（具體 index URL 或基底映像由規劃決定）。

## Outstanding Questions

### Resolve Before Planning

- 目前無須在規劃前強制拍板的未決議題。
- （選填）若產品方要推翻 R5（僅允許 `nvidia/cuda` 基底）或 R7（禁止 bind mount 原始碼），請在進入規劃前回覆以便更新需求。

### Deferred to Planning

- [Needs research][技術] 選定的 CUDA 次要版本與 PyTorch wheel 的對應表，以及是否在 CI 使用 CPU-only 映像以降低成本。
- [技術] `docker-entrypoint.sh` 是否負責遷移、環境變數展開、或僅啟動 uvicorn；與現有 `backend` 啟動指令對齊。

## Next Steps

→ `/ce:plan`（建議傳入本文件路徑）以產出具體 `Dockerfile`、`docker-compose.yml` 服務定義、GPU deploy 片段、開發用 volume 策略，以及滿足 Success Criteria 的 repo 內操作說明（含 GPU／CPU 啟動與 GPU 驗證步驟）。
