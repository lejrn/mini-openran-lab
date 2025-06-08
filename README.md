# Mini-OpenRAN Lab 🔬📡

[![CI](https://github.com/username/mini-openran-lab/workflows/CI/badge.svg)](https://github.com/username/mini-openran-lab/actions)

**A zero-cost, laptop-only "mini-OpenRAN lab" that demonstrates a full 4G/5G cell-site with O-RAN RIC, xApps, and modern DevOps—all inside WSL 2.**

> **🎯 Learn both telecom engineering (4G/5G protocols) and modern DevOps (Kubernetes, monitoring, CI/CD) in one integrated project!**

## 📋 **What You'll Build**

- **📡 Radio Access Network**: srsRAN gNB + UE with software-defined radio
- **🧠 Intelligence Layer**: O-RAN RIC + xApps making real-time network decisions  
- **📊 Observability Stack**: Prometheus + Grafana monitoring the entire network
- **🚀 DevOps Pipeline**: Everything containerized, tested, and deployed with Helm

## 🚀 Quick Start (WSL 2)

```bash
# Prerequisites (one-time setup)
# For WSL2 users: Ensure Docker Desktop is installed and running on Windows 11
# with WSL2 integration enabled in Docker Desktop settings

sudo apt update && sudo apt install -y curl make git

# Install kind
curl -Lo /usr/local/bin/kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64 && sudo chmod +x /usr/local/bin/kind

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl -sSL https://get.helm.sh/helm-v3.15.0-linux-amd64.tar.gz | tar xz && sudo mv linux-amd64/helm /usr/local/bin/

# Install Poetry for Python dependency management
curl -sSL https://install.python-poetry.org | python3 -

# Run the lab
git clone https://github.com/<you>/mini-openran-lab && cd mini-openran-lab
poetry install                    # Install Python dependencies
make kind-up                       # 2-3 min
helm repo add local ./charts
helm install openran local/openran -f charts/openran/values-kind.yaml
kubectl port-forward svc/grafana 3000:3000 -n monitoring
# view dashboard at http://localhost:3000  (admin/admin)
poetry run pytest -q && robot robot/e2e.robot
```

## 📚 Understanding the Stack

### 🎯 **Project Overview**

The Mini-OpenRAN Lab implements a **complete cellular network simulation** in Kubernetes, covering:

- **📡 Radio Access Network (RAN)**: gNB + UE communicating via software radio
- **🧠 Intelligence Layer**: RIC + xApps making smart decisions
- **📊 Observability Stack**: Prometheus + Grafana showing what's happening
- **🚀 DevOps Pipeline**: Everything packaged with Helm, tested with PyTest

**Perfect for learning both telecom engineering (4G/5G protocols) and modern DevOps (Kubernetes, monitoring, CI/CD)!**

### 📦 **What is a "Chart" (Helm Chart)**

A **Helm Chart** is like a "recipe" or "template" for deploying applications to Kubernetes. Think of it as:

- **Template Package**: Contains YAML templates that describe how to deploy your app
- **Configurable**: Uses variables (values) so you can customize deployments
- **Reusable**: Can deploy the same app multiple times with different settings
- **Versioned**: Like a software package with version numbers

In your case, the `charts/openran/` directory contains templates for:
- **gNB** (base station)
- **UE** (user equipment/phone simulator)  
- **RIC** (radio intelligence controller)
- **Monitoring stack** (Prometheus + Grafana)

### ⚙️ **What is Helm**

**Helm** is the "package manager for Kubernetes" - like `apt` for Ubuntu or `brew` for macOS, but for Kubernetes applications.

```bash
# Helm commands you'll use:
helm install openran ./charts/openran    # Deploy the whole lab
helm upgrade openran ./charts/openran    # Update deployment
helm uninstall openran                   # Remove everything
```

Helm takes your templates + values and generates the actual Kubernetes YAML files.

### 📊 **What is Prometheus**

**Prometheus** is a **metrics collection and storage system**. It:

- **Scrapes metrics**: Pulls data from `/metrics` endpoints every few seconds
- **Stores time-series data**: Keeps track of values over time
- **Provides alerts**: Can notify when things go wrong
- **Query language (PromQL)**: Search and analyze metrics

In your lab, Prometheus collects:
- **Radio metrics**: Signal quality (CQI), throughput, error rates
- **System metrics**: CPU, memory usage of pods
- **Custom metrics**: From your xApp and RIC

### 📈 **What is Grafana**

**Grafana** is a **visualization and dashboarding tool**. It:

- **Connects to Prometheus**: Reads the metrics data
- **Creates beautiful dashboards**: Graphs, charts, alerts
- **Real-time monitoring**: Watch your 4G/5G network in action
- **Accessible via web**: `http://localhost:3000` (admin/admin)

In your lab, Grafana will show:
- **Signal Quality**: How good the radio connection is
- **Throughput**: Data transfer rates
- **RRC Connections**: When UE connects to gNB
- **xApp Actions**: When AI makes network optimizations

### 🔄 **How They Work Together**

```
┌─────────┐    metrics    ┌─────────────┐    queries    ┌─────────┐
│ srsRAN  │ ──────────────> │ Prometheus  │ ─────────────> │ Grafana │
│ (gNB/UE)│               │ (storage)   │               │ (charts)│
└─────────┘               └─────────────┘               └─────────┘
```

1. **srsRAN pods** expose metrics on `:9092/metrics`
2. **Prometheus** scrapes these metrics every 15 seconds
3. **Grafana** queries Prometheus and shows live charts
4. **You** watch the dashboard to see your 4G/5G network working!

### 🎪 **Nested Containerization: Docker in Kubernetes in Docker**

Yes, Docker and Kubernetes can definitely be nested! You're actually **already doing this** in your Mini-OpenRAN Lab:

```
┌─────────────────── Your Laptop ───────────────────┐
│  ┌─────────────── Docker Engine ─────────────────┐ │
│  │  ┌─────────── kind Container ─────────────────┐ │ │
│  │  │        Kubernetes Cluster                 │ │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐   │ │ │
│  │  │  │srsran-  │  │srsran-  │  │prometheus│   │ │ │
│  │  │  │gnb      │  │ue       │  │         │   │ │ │
│  │  │  │(container)  │(container)  │(container)   │ │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘   │ │ │
│  │  └─────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**What's happening:**
1. **Docker Engine** runs on your laptop
2. **kind** creates a Docker container that runs Kubernetes
3. **Kubernetes** runs your application containers inside that container
4. This gives you a full cluster experience on a single machine!

### 🖥️ **Kubernetes Cluster vs Regular PC**

| Aspect | **Regular PC** | **Kubernetes Cluster** |
|--------|----------------|-------------------------|
| **Scale** | 1 machine | Many machines (or 1 machine pretending to be many) |
| **Process Communication** | Localhost, pipes, shared memory | Network calls, services, DNS |
| **Failure Handling** | Process crashes = manual restart | Pod crashes = automatic restart |
| **Resource Sharing** | Shared CPU/RAM | Isolated CPU/RAM per container |
| **Networking** | `127.0.0.1:port` | `service-name:port` |
| **Process Management** | `systemd`, `ps`, `kill` | `kubectl`, deployments, pods |

### 🏠 **Regular PC Example**
```bash
# On your laptop:
firefox &                 # Process 1234
code &                    # Process 1235
python app.py &           # Process 1236

# They communicate via:
curl http://localhost:8080      # Same machine
```

### ☁️ **Kubernetes Example**
```bash
# In the cluster:
kubectl get pods
# NAME                         READY   STATUS    RESTARTS
# openran-gnb-12345           1/1     Running   0
# openran-ue-67890            1/1     Running   0
# prometheus-11111            1/1     Running   0

# They communicate via:
# UE -> gNB:     http://openran-gnb:2000
# Prometheus -> UE: http://openran-ue:9092
```

### 🧠 **Why Use Kubernetes Instead of Just Running Processes?**

**1. Self-Healing**
```bash
# Regular PC:
kill 1234        # Firefox dies, stays dead

# Kubernetes:
kubectl delete pod openran-gnb-12345
# Kubernetes immediately starts openran-gnb-67891
```

**2. Scaling**
```bash
# Regular PC:
# Hard to run 10 copies of same app

# Kubernetes:
kubectl scale deployment openran-ue --replicas=10
# Now you have 10 UE simulators!
```

**3. Resource Isolation**
```yaml
# Each container gets guaranteed resources:
resources:
  requests:
    memory: "512Mi"    # Guaranteed 512MB RAM
    cpu: "500m"        # Guaranteed 0.5 CPU cores
  limits:
    memory: "1Gi"      # Max 1GB RAM
    cpu: "1000m"       # Max 1 CPU core
```

### 🔗 **Communication Example from Your UE Template**

```yaml
# UE waits for gNB to be ready:
initContainers:
- name: wait-for-gnb
  command: ['sh', '-c', 'until nc -z openran-gnb 2000; do sleep 5; done']
  # Uses Kubernetes DNS: "openran-gnb" resolves to gNB pod IP

# UE connects to gNB:
env:
- name: GNB_ADDRESS
  value: "openran-gnb"  # Service name, not IP address!
```

**Summary**: Kubernetes is like a **"distributed operating system"** that makes many computers look like one big computer, with automatic networking, healing, and scaling!

## 🔬 Science & Technology Background

| Domain | Key Idea | Implementation |
|--------|----------|----------------|
| **Radio PHY** | OFDM + HARQ: srsRAN gNB & UE loop bits through an OFDM pipeline, complete with CQI feedback | `charts/openran/templates/gnb.yaml` (env vars choose QPSK / 16-QAM) |
| **Open RAN** | Near-RT RIC & E2 interface: gNB sends real-time stats to the controller; xApps push policy back | `charts/openran/templates/ric-plt.yaml`, `xapps/beam_tuner/app.py` |
| **Control Theory / ML** | Beam-tuner xApp: watches CQI; if median drops, issues "adjust MCS" E2 message | `xapps/beam_tuner/logic.py` |
| **Observability** | KPIs scraped by Prometheus → Grafana panels show throughput jump when xApp kicks in | `charts/openran/values-kind.yaml` (prom scrape config) |
| **DevOps** | CI builds every image, runs PyTest+Robot, publishes Helm chart; Terraform can replay on AWS | `.github/workflows/ci.yml`, `terraform/main.tf` |

## 📂 Repository Structure

```
mini-openran-lab/
├─ charts/openran/          # Helm bundle: gNB, UE, RIC, xApp, Prom, Grafana
├─ xapps/beam_tuner/        # FastAPI + (later) scikit-learn
├─ hack/                    # kind-up.sh, load-images.sh helpers
├─ tests/                   # pytest unit + Robot E2E
├─ terraform/               # spin 1 × t3.micro + k3s (optional)
├─ grafana/dashboards/      # Dashboard JSON configs
└─ .github/workflows/ci.yml # build, test, push, chart-lint
```

## ✅ Development Roadmap

| Phase | Task | Status |
|-------|------|--------|
| **0. Bootstrap** | Repo, licence, README stub | ✅ |
| | Add CI badge in README | ✅ |
| **1. kind cluster** | hack/kind-up.sh script | ✅ |
| | CI job runs kind create cluster | ✅ |
| **2. Radio pods** | Helm template for srsran-gnb | ✅ |
| | Helm template for srsran-ue | ✅ |
| | PyTest: log contains "RRC CONNECTED" | ✅ |
| | Namespace separation implementation | ✅ |
| | Security audit and documentation | ✅ |
| **3. RIC** | Add RIC chart dependency | ◻ |
| | Verify E2 link (grep log) | ◻ |
| | Update architecture diagram | ◻ |
| **4. xApp skeleton** | FastAPI server returns /healthz=200 | ◻ |
| | Dockerfile builds under CI | ◻ |
| | Helm values enable pod | ◻ |
| **5. Observability** | Prometheus scrape config | ◻ |
| | Grafana dashboard JSON (CQI, Throughput) | ◻ |
| | Robot test checks HTTP 200 on Grafana | ◻ |
| **6. CI/CD** | GitHub Actions: build images, push to ghcr.io | ◻ |
| | Chart lint + helm template smoke in CI | ◻ |
| **7. Terraform (optional)** | main.tf t3.micro + user-data installs k3s | ◻ |
| | make deploy-cloud wrapper | ◻ |
| | terraform destroy cleans all | ◻ |
| **8. ML upgrade (stretch)** | Collect CSV CQI samples | ◻ |
| | Train simple scikit-learn regressor | ◻ |
| | Replace rule-based logic | ◻ |
| **9. Release v1.0** | Tag rel/v1.0 | ◻ |
| | Attach chart .tgz + screenshot | ◻ |
| | Write changelog | ◻ |

### 🎯 Phase 1 Deep Dive: WSL2 Kind Cluster Mastery

**Challenge**: Creating a stable Kubernetes-in-Docker environment on WSL2 that can reliably host telecom workloads.

**Key Issues Solved**:
- **Cgroup Driver Mismatch**: Fixed kubelet/container runtime incompatibility by switching from `cgroupfs` to `systemd` driver
- **Deprecated K8s Flags**: Removed `--pod-eviction-timeout` flag that was deprecated in newer Kubernetes versions  
- **WSL2 Resource Constraints**: Optimized timeout values and swap handling for WSL2 environment
- **Systematic Debugging**: Used `systemctl status kubelet` and `journalctl -xeu kubelet` for root cause analysis

**Technical Implementation**:
- **Poetry**: Modern Python dependency management with virtual environments
- **Comprehensive Testing**: 10 pytest tests with real-time output streaming and proper cleanup
- **CI/CD Integration**: GitHub Actions using Poetry instead of traditional pip workflows
- **WSL2 Optimization**: Specialized configuration for Windows Subsystem for Linux v2 compatibility

**Results**: Fully functional single-node Kubernetes cluster with:
- ✅ All control plane pods healthy (etcd, kube-apiserver, kube-controller-manager, kube-scheduler)
- ✅ Calico CNI networking operational
- ✅ Required namespaces created (openran, monitoring, xapps)
- ✅ Port mappings configured (3000→Grafana, 9090→Prometheus, 8080→xApp API)
- ✅ Node labels applied for CPU isolation
- ✅ 100% test pass rate in ~2 minutes

## 🗄️ Component Glossary

| Component | Role |
|-----------|------|
| **srsran-gnb** | Open-source 4G/5G base-station (gNodeB). Generates OFDM frames, runs MAC scheduler, exposes E2 metrics |
| **srsran-ue-loop** | Dummy UE that connects to gNB in internal loopback; creates constant traffic so KPIs move |
| **ric-platform** | O-RAN Software Community Near-RT RIC (controller) processing CQI, RB table, etc. |
| **xappmgr** | Side-car inside RIC that loads/manages xApps (plugins) |
| **beam-tuner-xapp** | FastAPI micro-service; subscribes to RIC metrics and pushes policy messages |
| **prometheus** | Scrapes /metrics endpoints; stores time-series data |
| **grafana** | Reads Prometheus and shows dashboards: CQI, throughput, BER, xApp actions |

## 🔒 Pinned Versions

| Tool | Version | Purpose |
|------|---------|---------|
| kind | 0.22.0 | Kubernetes-in-Docker |
| Helm | 3.15.* | Package manager |
| Kubernetes | v1.30.0 | Container orchestration |
| srsRAN | 22.10.* | Radio stack |
| O-RAN RIC | v2.4.* | RAN controller |
| FastAPI | 0.111.* | xApp framework |
| scikit-learn | 1.5.* | ML (future) |

## 🤗 Why Beginner-Friendly

| Factor | Mini-OpenRAN-Lab | Production Alternative |
|--------|------------------|------------------------|
| **Radio** | Software loopback (no hardware) | Real RF needs USRP-B210, antennas, timing cards |
| **RIC** | O-RAN SC "RIC-in-Docker" | 20+ microservices, Kafka, multus CNI |
| **Infrastructure** | kind on WSL (zero cost) | Multi-node K8s (EKS/GKE) with load balancers |
| **Debug** | docker logs + localhost Grafana | Remote RF logs, interference, hardware failures |

## 🔒 Network Security & Isolation

**Your Mini-OpenRAN Lab is completely isolated and secure** - no external threats can reach your virtual radio network.

### 🛡️ **3-Layer Security Model**

```
┌──────────── Internet ─────────────┐
│                                   │ ❌ No Direct Access
│  ┌─────── Your Laptop ──────────┐ │
│  │                              │ │
│  │  ┌─── Docker Bridge ───────┐ │ │ 🔒 Private Network
│  │  │   kind cluster          │ │ │    (Bridge + NAT)
│  │  │                         │ │ │
│  │  │  ┌─ Pod Network ─────┐  │ │ │ 🔒 Internal Only
│  │  │  │  srsRAN gNB      │  │ │ │    (Pod-to-Pod)
│  │  │  │  srsRAN UE       │  │ │ │
│  │  │  │  Prometheus      │  │ │ │
│  │  │  └──────────────────┘  │ │ │
│  │  └─────────────────────────┘ │ │
│  └──────────────────────────────┘ │
└───────────────────────────────────┘
```

### 📡 **Network Architecture**

| Network Layer | IP Range | Access Level | Purpose |
|---------------|----------|--------------|---------|
| **Pod Network** | `10.244.0.0/16` | Internal only | srsRAN gNB ↔ UE communication |
| **Service Network** | `10.96.0.0/12` | Cluster internal | Service discovery (DNS names) |
| **Docker Bridge** | `172.18.0.0/16` | Host + containers | kind cluster networking |
| **Localhost Only** | `127.0.0.1:3000,9090,8080` | Your machine | Dashboard access |

### 🚫 **What's NOT Exposed**
- ❌ **Radio interfaces**: Virtual RF between gNB/UE stays internal
- ❌ **Pod IPs**: No external routing to individual containers  
- ❌ **Management APIs**: Kubernetes API server not externally accessible
- ❌ **Internal metrics**: Prometheus endpoints only reachable within cluster

### ✅ **What IS Accessible** 
- ✅ **Grafana Dashboard**: `http://localhost:3000` (localhost-only binding)
- ✅ **Prometheus UI**: `http://localhost:9090` (localhost-only binding)  
- ✅ **xApp API**: `http://localhost:8080` (localhost-only binding)

### 🔐 **Security Features**
- **Docker Bridge Isolation**: Private subnet with NAT-only internet access
- **Kubernetes Network Policies**: Can add pod-to-pod restrictions (currently open for lab use)
- **No External LoadBalancer**: All services use internal ClusterIP or localhost NodePort
- **WSL2 Additional Isolation**: Even more network isolation through Windows Subsystem for Linux

### 🔒 **Enhanced Security Options**

The current configuration uses localhost-only bindings for security. If you need to access 
dashboards from other machines on your network, you can:

```yaml
# In hack/kind-config.yaml, change from:
listenAddress: 127.0.0.1  # Localhost only (current)
# To:
# listenAddress: 0.0.0.0   # All interfaces (less secure)
```

Or use `kubectl port-forward` for temporary external access:
```bash
# Temporary access from any interface
kubectl port-forward --address 0.0.0.0 svc/grafana 3000:3000 &
```

**Bottom Line**: Your virtual cellular network is completely secure and isolated. Dashboard ports are bound to localhost-only, and pod-to-pod radio communications remain completely internal.

## ☁️ AWS Free Tier Deployment (Optional)

```bash
cd terraform
terraform apply       # ≤ 1 min, spins t3.micro with k3s
ssh ec2-user@<ip>
helm repo add openran https://<your-gh-pages>/charts
helm install openran openran/openran -f charts/openran/values-ec2.yaml
# terraform destroy when done (stay within 750 free hours)
```

## 📊 Expected Results

After setup, you'll see:
- **Grafana dashboard** at `http://localhost:3000` showing live CQI/throughput metrics
- **RRC CONNECTED** logs from UE attachment
- **E2 interface** telemetry between gNB and RIC
- **xApp policy changes** affecting radio performance in real-time

## 🔧 Operational Tips

- **CPU pinning**: `taskset -c 0 docker run ... srsran-gnb`
- **Port forwarding**: Open 3000/tcp (Grafana) & 9090/tcp (Prometheus)
- **Cost guard**: AWS Budget at $0.50, cron job stops t3.micro at midnight UTC
- **Debug**: Check `kubectl logs -f deployment/srsran-gnb`

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**🎯 Goal**: Prove you can mix telecom science (CQI, scheduler, beamforming) with modern DevOps (Docker, Helm, GitHub Actions, IaC)—without costing a cent.
