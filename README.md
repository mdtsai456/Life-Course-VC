# Life Course: Voice-Cloning

## Docker

以容器啟動前後端（含可選 NVIDIA GPU）的步驟見 [docs/docker.md](docs/docker.md)。

快速範例（與 [docs/docker.md](docs/docker.md) 一致）：

- CPU 開發：`docker compose --profile dev up --build`
- GPU 開發：`docker compose --profile dev-gpu up --build`
- 類上線（nginx + 後端映像、無原始碼 bind）：`docker compose --profile prod-like up --build`（需 NVIDIA 驅動與 NVIDIA Container Toolkit；無 GPU 請用 `--profile dev`）
