# Docker 與 Compose

本專案使用根目錄 `docker-compose.yml`，後端映像定義於 `backend/Dockerfile`（`runtime-cpu` / `runtime-gpu` 兩個 target），前端正式環境映像為 `frontend/Dockerfile`（nginx 提供靜態檔並反向代理 API）。

## 前置條件

- [Docker](https://docs.docker.com/get-docker/) 與 **Docker Compose v2**
- **GPU 路徑**（`dev-gpu` 或 `prod-like` 後端）：主機安裝 [NVIDIA 驅動](https://www.nvidia.com/Download/index.aspx) 與 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

## Profiles 與指令

| 情境 | 指令 |
|------|------|
| 本機開發（CPU 推論，較慢） | `docker compose --profile dev up --build` |
| 本機開發（NVIDIA GPU） | `docker compose --profile dev-gpu up --build` |
| 類上線：映像內建程式、無原始碼 bind | `docker compose --profile prod-like up --build` |

- **dev / dev-gpu**：後端 `http://localhost:8000`，前端 Vite `http://localhost:5173`。前端透過 `VITE_API_TARGET=http://api:8000` 將 `/api`、`/health` 轉到後端（Compose 網路別名 `api`）。
- **prod-like**：後端僅在 Compose 網路內對 `frontend-prod` 提供 `8000`（主機不對外綁定）；對外入口為 nginx `http://localhost:8080`；後端 CORS 預設為 `http://localhost:8080`。

## 驗證是否使用 GPU

檢視後端日誌應出現：

- GPU：`device: cuda`
- CPU：`device: cpu`

```bash
docker compose --profile dev-gpu logs -f backend-dev-gpu
```

若未裝 Container Toolkit 或無 GPU，請改用 `--profile dev`（CPU）。

## Volume 與快取

預設使用 **具名 volume**（不需額外設定）：

| Volume | 用途 |
|--------|------|
| `tts-cache` | 掛在容器內 `/cache`（`HOME`、`HF_HOME`、`TORCH_HOME`、`XDG_CACHE_HOME`）以持久化模型與下載快取 |
| `job-storage` | 後端 `STORAGE_ROOT`（預設 `/app/storage`），對應 `backend/app/config.py` |
| `frontend-node-modules` | 開發時將 `node_modules` 留在 volume，避免 bind 覆蓋 |

### 改為 bind 主機目錄（模型／快取）

將 `docker-compose.yml` 中後端服務的：

```yaml
- tts-cache:/cache
```

改為例如：

```yaml
- /your/path/coqui-cache:/cache
```

（請自行建立目錄並注意權限。）`HF_HOME`、`TORCH_HOME`、`XDG_CACHE_HOME` 已指向 `/cache` 底下子目錄，無須改環境變數即可一併持久化。

## 僅建映像（不啟動）

```bash
docker build -f backend/Dockerfile --target runtime-cpu ./backend
docker build -f backend/Dockerfile --target runtime-gpu ./backend
docker build -f frontend/Dockerfile ./frontend
```

## prod-like 與無 GPU 主機

`prod-like` 的 `backend-prod` 預設建置為 **runtime-gpu** 並請求 GPU。若僅有 CPU，請改用 **`--profile dev`** 做全端開發，或自行以 `runtime-cpu` target 建置後端映像並調整 compose（非預設路徑）。

## 後端基底映像

- **GPU**：`pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`（與 `torch>=2.6` 對齊；若拉取失敗請至 [Docker Hub Tags](https://hub.docker.com/r/pytorch/pytorch/tags) 選相近 tag）。
- **CPU**：`python:3.12-slim-bookworm` + PyTorch CPU index。

## 相關檔案

- `docker-compose.yml`
- `backend/Dockerfile`、`backend/docker-entrypoint.sh`
- `frontend/Dockerfile`、`frontend/nginx-default.conf`
