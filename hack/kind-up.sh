#!/bin/bash
# hack/kind-up.sh - Create kind cluster for mini-OpenRAN lab

set -euo pipefail

CLUSTER_NAME="openran"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIND_CONFIG_FILE="$SCRIPT_DIR/kind-config.yaml"

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v kind &> /dev/null; then
        missing_tools+=("kind")
    fi
    
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    elif ! docker ps &> /dev/null; then
        echo "❌ Docker daemon is not accessible."
        echo "   For WSL2: Make sure Docker Desktop is running on Windows"
        echo "   For native Linux: Start Docker with 'sudo systemctl start docker'"
        exit 1
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        echo "❌ Missing required tools: ${missing_tools[*]}"
        echo ""
        echo "🔧 Auto-install option available!"
        echo "   Run: $SCRIPT_DIR/install-prerequisites.sh"
        echo ""
        echo "Or install manually:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                kind)
                    echo "   kind: curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
                    ;;
                kubectl)
                    echo "   kubectl: curl -LO \"https://dl.k8s.io/release/\$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\" && sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"
                    ;;
                helm)
                    echo "   helm: curl -sSL https://get.helm.sh/helm-v3.15.0-linux-amd64.tar.gz | tar xz && sudo mv linux-amd64/helm /usr/local/bin/"
                    ;;
                docker)
                    echo "   docker: For WSL2 install Docker Desktop on Windows, for Linux: sudo apt install -y docker.io"
                    ;;
            esac
        done
        exit 1
    fi
    
    echo "✅ Prerequisites check passed"
    echo "  - kind: $(kind version | head -1)"
    echo "  - kubectl: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    echo "  - helm: $(helm version --short)"
    echo "  - docker: $(docker version --format '{{.Client.Version}}' 2>/dev/null || echo 'available')"
}

# Function to handle cleanup on failure
cleanup_on_failure() {
    echo "❌ Setup failed. Cleaning up..."
    kind delete cluster --name $CLUSTER_NAME || true
    exit 1
}

# Set up trap for cleanup
trap cleanup_on_failure ERR

check_prerequisites

echo "🚀 Creating kind cluster '$CLUSTER_NAME'..."
echo "📋 Using config: $KIND_CONFIG_FILE"

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "⚠️  Cluster '$CLUSTER_NAME' already exists. Deleting first..."
    kind delete cluster --name $CLUSTER_NAME
fi

kind create cluster --config $KIND_CONFIG_FILE --wait 5m

echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

echo "🎯 Installing Calico CNI..."
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.0/manifests/calico.yaml

echo "⏳ Waiting for Calico to be ready..."
kubectl wait --for=condition=Ready pods -l k8s-app=calico-node -n kube-system --timeout=300s

echo "📦 Creating namespaces..."
kubectl create namespace openran --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace xapps --dry-run=client -o yaml | kubectl apply -f -

echo "🏷️  Labeling nodes for CPU pinning..."
kubectl label nodes openran-control-plane openran.io/cpu-isolation=enabled --overwrite

echo "🔍 Verifying cluster setup..."
# Verify all namespaces exist
for ns in openran monitoring xapps; do
    if kubectl get namespace $ns &> /dev/null; then
        echo "  ✅ Namespace '$ns' exists"
    else
        echo "  ❌ Namespace '$ns' missing"
        exit 1
    fi
done

# Verify nodes are ready
if kubectl get nodes | grep -q "Ready"; then
    echo "  ✅ Nodes are ready"
else
    echo "  ❌ Nodes are not ready"
    exit 1
fi

echo "✅ Kind cluster '$CLUSTER_NAME' is ready!"
echo "📋 Cluster info:"
kubectl cluster-info --context kind-$CLUSTER_NAME
echo ""
echo "📊 Cluster status:"
kubectl get nodes -o wide
echo ""
echo "🔗 Next steps:"
echo "  1. Run: ./hack/load-images.sh"
echo "  2. Run: helm install openran ./charts/openran -f charts/openran/values-kind.yaml"
echo "  3. Port-forward: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
echo ""
echo "🧪 To run tests: pytest tests/test_kind_cluster.py -v"
