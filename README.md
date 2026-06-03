# kubereats-backend

`main` branch 是 Kubereats backend 的 GitOps / deployment 入口。這個 branch 主要保存 Kubernetes manifests、Argo CD 設定、部署文件與維運腳本；各 backend service 的實作原始碼放在 `module/*` 分支。

## 專案定位

- `main`: 集中管理部署狀態，Argo CD 以此 branch 的 `deploy/` 內容作為 Kubernetes desired state。
- `module/*`: 各服務的 source branch，通常包含 `app/`、`Dockerfile`、`pyproject.toml`、測試與 migrations。
- `chore/*`: 監控、SonarQube、autoscaling、observability 等維運或品質工作分支。
- `deploy/*`: 部署階段、endpoint contract 或環境調整分支。
- `feature/*`: 功能開發分支。
- `fix/*`: 修正部署或服務問題的分支。
- `archive/*`: 已封存的舊工作分支。

## Main Branch 專案結構

```text
.
├── README.md
├── deploy/
│   ├── README.md
│   ├── argocd/
│   │   ├── apps/          # Argo CD Applications / root app / app-of-apps
│   │   ├── bootstrap/     # Argo CD 安裝與 bootstrap 腳本
│   │   └── projects/      # Argo CD Project 定義
│   ├── docs/              # 部署與維運補充文件
│   ├── k8s/
│   │   ├── base/          # 各服務共用基底 manifests
│   │   └── overlays/
│   │       ├── dev/       # kubereats-dev 環境
│   │       └── prod/      # production 範例/預備 manifests
│   └── scripts/           # 遠端 kubectl、smoke test、NodePort 驗證腳本
├── docs/
│   └── ops/               # DB access / maintenance / roles runbook
└── scripts/
    └── db/                # DB role 或初始化 SQL
```

## Main Branch 目前管理的服務

`deploy/k8s/base/` 保存服務基底，`deploy/k8s/overlays/dev/` 決定 dev 環境實際同步哪些服務與 image tag。

| Service | Source branch | Dev 狀態 | Dev NodePort / 說明 |
| --- | --- | --- | --- |
| `merchant-service` | `module/merchant` | 已納入 dev overlay | `31081` |
| `committee-service` | `module/fuwei-system` | 已納入 dev overlay | `31082` |
| `verification-service` | `module/verification` | 已納入 dev overlay | `31083` |
| `tagging-service` | `module/tagging` | 已納入 dev overlay | `31084` |
| `finance-service` | `module/finance` | 已納入 dev overlay | `31085` |
| `recommendation-service` | `module/recommend` | 已納入 dev overlay | `31086` |
| `order-scheduler-service` | `module/order-scheduler` | 已納入 dev overlay | `31087` |
| `order-consumer-service` | `module/order-consumer` | 已納入 dev overlay | internal worker，無 NodePort |
| `notification-service` | `module/notification` | 有 base 與 dev overlay 目錄，但目前未放進 dev root kustomization | 需 Redis / worker 等依賴確認 |
| `sonarqube` | `chore/*` 維運用途 | 已納入 dev overlay | `31090`，私人網段 UI |

更完整的部署細節、health endpoint、image build、secret 與 smoke test 流程請看 `deploy/README.md`。

## Kustomize / Argo CD 結構

- `deploy/k8s/base/<service>/`: 每個服務的 Deployment、Service、ConfigMap、Secret example、autoscaling 或監控資源。
- `deploy/k8s/overlays/dev/<service>/`: dev 環境 patch，包含 image tag、replicas、env 與 NodePort。
- `deploy/k8s/overlays/dev/kustomization.yaml`: dev 環境的入口，Argo CD sync 時會從這裡展開 manifests。
- `deploy/k8s/overlays/prod/`: prod manifests，目前偏向範例/預備狀態，正式 promotion 前要再確認 secrets、image tag、replicas 與 ingress/LB 設定。
- `deploy/argocd/apps/root-app.yaml`: app-of-apps 入口。
- `deploy/argocd/apps/backend-dev.yaml`: dev backend Application。
- `deploy/argocd/bootstrap/install-argocd.sh`: 透過 SSH 在 control plane 安裝 Argo CD。

## 分支使用方式

建議工作流：

1. 修改服務原始碼時，checkout 對應的 `module/<service>` 分支。
2. 在該分支完成測試、Docker build 或 CI。
3. image 發布後，更新 `main` branch 的 `deploy/k8s/overlays/dev/<service>/kustomization.yaml` image tag。
4. Argo CD 從 `main` sync dev 環境，讓 Git 保持部署 desired state。

常見分支對應：

| 分支 | 用途 |
| --- | --- |
| `main` | GitOps manifests、Argo CD、部署文件與維運腳本 |
| `module/merchant` | Merchant API source |
| `module/fuwei-system` | Committee service source |
| `module/verification` | Verification / auth service source |
| `module/notification` | Notification service source |
| `module/tagging` | Tagging service source |
| `module/finance` | Finance service source |
| `module/recommend` | Recommendation service source |
| `module/order-scheduler` | Order scheduler service source |
| `module/order-consumer` | Order consumer worker source |
| `chore/*` | SonarQube、metrics、ServiceMonitor、autoscaling、observability 等工作 |
| `deploy/*` | 部署階段或環境契約調整 |
| `feature/*` | 新功能開發 |
| `fix/*` | bugfix 或部署修正 |

## 常用指令

查看目前 branch：

```bash
git branch --show-current
```

查看所有本地與遠端分支：

```bash
git branch --all
```

切到服務 source branch：

```bash
git checkout module/merchant
```

回到 GitOps main branch：

```bash
git checkout main
```

驗證 dev Kustomize 輸出：

```bash
kubectl kustomize deploy/k8s/overlays/dev
```

查看 Argo CD 與 dev pods：

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get applications -n argocd
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/remote-kubectl.sh get pods -n kubereats-dev -o wide
```

執行 NodePort smoke test：

```bash
SSH_KEY=/home/edtsai/tf-cloud-init ./deploy/scripts/verify-nodeport-phase1.sh
```

## 注意事項

- 不要把真實 secrets commit 到 repo；只保留 `secret.example.yaml`。
- `main` 不是單一服務的開發分支，服務程式碼請到對應 `module/*` 分支。
- 修改 deployment manifests 時，先確認 `deploy/k8s/overlays/dev/kustomization.yaml` 是否有納入該服務。
- prod overlay 尚未等同正式 production 狀態，上線前需重新檢查 image、replicas、secret、LB/Ingress 與 health check。
