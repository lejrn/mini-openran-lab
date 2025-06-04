#!/bin/bash
# hack/load-images.sh - Load Docker images into kind cluster

set -euo pipefail

CLUSTER_NAME="openran"

echo "📦 Loading Docker images into kind cluster..."

#!/bin/bash
# hack/load-images.sh - Load Docker images into kind cluster

set -euo pipefail

CLUSTER_NAME="openran"

echo "📦 Loading Docker images into kind cluster..."

# Check if cluster exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "❌ Kind cluster '$CLUSTER_NAME' not found. Run ./hack/kind-up.sh first."
    exit 1
fi

# Build and load beam-tuner xApp
echo "🔨 Building beam-tuner image..."
docker build -t beam-tuner:latest xapps/beam_tuner/

echo "📤 Loading beam-tuner into kind cluster..."
kind load docker-image beam-tuner:latest --name "$CLUSTER_NAME"

echo "✅ Images loaded successfully!"
echo "📋 Verify with: docker exec -it ${CLUSTER_NAME}-control-plane crictl images"
