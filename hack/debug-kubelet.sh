#!/bin/bash
# Debug script to check kubelet status inside kind container

set -euo pipefail

CLUSTER_NAME="openran"

echo "🔍 Debugging kubelet in kind cluster..."

# Start cluster creation in background and try to debug while it's running
echo "🚀 Starting cluster creation..."
kind create cluster --config hack/kind-config.yaml --wait 30s &
CREATE_PID=$!

# Wait a bit for the container to start
sleep 10

echo "📋 Checking if container is running..."
if docker ps --filter "name=${CLUSTER_NAME}-control-plane" --format "table {{.Names}}" | grep -q "${CLUSTER_NAME}-control-plane"; then
    echo "✅ Container is running, attempting to debug kubelet..."
    
    echo ""
    echo "🔍 Checking systemd status inside container..."
    docker exec ${CLUSTER_NAME}-control-plane systemctl status kubelet || echo "❌ systemctl status kubelet failed"
    
    echo ""
    echo "🔍 Checking kubelet logs..."
    docker exec ${CLUSTER_NAME}-control-plane journalctl -xeu kubelet --no-pager -l || echo "❌ journalctl failed"
    
    echo ""
    echo "🔍 Checking running containers inside kind node..."
    docker exec ${CLUSTER_NAME}-control-plane crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps -a | grep kube | grep -v pause || echo "❌ crictl failed"
    
    echo ""
    echo "🔍 Checking if kubelet binary exists and is executable..."
    docker exec ${CLUSTER_NAME}-control-plane ls -la /usr/bin/kubelet || echo "❌ kubelet binary check failed"
    
    echo ""
    echo "🔍 Checking kubelet configuration..."
    docker exec ${CLUSTER_NAME}-control-plane cat /var/lib/kubelet/config.yaml || echo "❌ kubelet config check failed"
    
    echo ""
    echo "🔍 Checking cgroup configuration..."
    docker exec ${CLUSTER_NAME}-control-plane cat /proc/cgroups || echo "❌ cgroups check failed"
    
    echo ""
    echo "🔍 Checking systemd cgroup driver..."
    docker exec ${CLUSTER_NAME}-control-plane systemctl show --property=DefaultControlGroup || echo "❌ systemd cgroup check failed"
    
else
    echo "❌ Container not running yet, waiting for creation to finish..."
fi

# Wait for the creation process to finish
wait $CREATE_PID
echo "📊 Creation process finished with exit code: $?"

# Clean up
kind delete cluster --name $CLUSTER_NAME || true
