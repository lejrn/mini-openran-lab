#!/bin/bash

# Debug script for diagnosing Kind/WSL2/Docker issues
# This script collects system information to help troubleshoot cluster creation problems

set -e

echo "🔍 OpenRAN Lab Environment Diagnostics"
echo "========================================"
echo

# Check if running in WSL2
echo "📍 Environment Detection:"
if grep -qi microsoft /proc/version; then
    echo "  ✅ Running in WSL2"
    WSL_VERSION=$(wsl.exe --list --verbose 2>/dev/null | grep -E '\*.*Running' | awk '{print $3}' || echo "Unknown")
    echo "  📋 WSL Version: $WSL_VERSION"
else
    echo "  ℹ️  Not running in WSL2"
fi

# System resources
echo
echo "💻 System Resources:"
echo "  📊 CPU cores: $(nproc)"
echo "  📊 Memory: $(free -h | grep '^Mem:' | awk '{print $2}') total, $(free -h | grep '^Mem:' | awk '{print $7}') available"
echo "  📊 Disk space: $(df -h / | tail -1 | awk '{print $4}') available"

# Docker status
echo
echo "🐳 Docker Status:"
if command -v docker >/dev/null 2>&1; then
    echo "  ✅ Docker binary found: $(docker --version)"
    
    if docker info >/dev/null 2>&1; then
        echo "  ✅ Docker daemon is running"
        
        # Docker system info
        DOCKER_MEMORY=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "Unknown")
        DOCKER_CPUS=$(docker system info --format '{{.NCPU}}' 2>/dev/null || echo "Unknown")
        echo "  📊 Docker allocated CPUs: $DOCKER_CPUS"
        echo "  📊 Docker allocated memory: $(numfmt --to=iec $DOCKER_MEMORY 2>/dev/null || echo $DOCKER_MEMORY)"
        
        # Check Docker storage driver
        STORAGE_DRIVER=$(docker system info --format '{{.Driver}}' 2>/dev/null || echo "Unknown")
        echo "  📊 Storage driver: $STORAGE_DRIVER"
        
        # Check for running containers
        CONTAINER_COUNT=$(docker ps -q | wc -l)
        echo "  📊 Running containers: $CONTAINER_COUNT"
        
        if [ $CONTAINER_COUNT -gt 0 ]; then
            echo "  📋 Running containers:"
            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
        fi
        
    else
        echo "  ❌ Docker daemon is not running or not accessible"
        echo "  💡 Try: sudo systemctl start docker (Linux) or restart Docker Desktop"
    fi
else
    echo "  ❌ Docker binary not found"
fi

# Kind status
echo
echo "🔧 Kind Status:"
if command -v kind >/dev/null 2>&1; then
    echo "  ✅ Kind binary found: $(kind version)"
    
    # List existing clusters
    CLUSTERS=$(kind get clusters 2>/dev/null || echo "")
    if [ -n "$CLUSTERS" ]; then
        echo "  📋 Existing clusters:"
        echo "$CLUSTERS" | sed 's/^/    /'
        
        # Check cluster health for each
        for cluster in $CLUSTERS; do
            echo "  🔍 Checking cluster: $cluster"
            if kubectl cluster-info --context "kind-$cluster" >/dev/null 2>&1; then
                echo "    ✅ Cluster $cluster is responsive"
            else
                echo "    ❌ Cluster $cluster is not responsive"
            fi
        done
    else
        echo "  ℹ️  No existing Kind clusters found"
    fi
else
    echo "  ❌ Kind binary not found"
fi

# Kubectl status
echo
echo "⚙️  Kubectl Status:"
if command -v kubectl >/dev/null 2>&1; then
    echo "  ✅ Kubectl binary found: $(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null | head -1)"
    
    # Check contexts
    CONTEXTS=$(kubectl config get-contexts -o name 2>/dev/null || echo "")
    if [ -n "$CONTEXTS" ]; then
        echo "  📋 Available contexts:"
        echo "$CONTEXTS" | sed 's/^/    /'
        
        CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "None")
        echo "  📍 Current context: $CURRENT_CONTEXT"
    else
        echo "  ℹ️  No kubectl contexts configured"
    fi
else
    echo "  ❌ Kubectl binary not found"
fi

# Network diagnostics
echo
echo "🌐 Network Diagnostics:"
echo "  📍 Default gateway: $(ip route | grep default | awk '{print $3}' | head -1)"

# Test DNS resolution
if nslookup registry-1.docker.io >/dev/null 2>&1; then
    echo "  ✅ DNS resolution working (registry-1.docker.io)"
else
    echo "  ❌ DNS resolution failed (registry-1.docker.io)"
fi

# Test container registry connectivity
if timeout 10 curl -s https://registry-1.docker.io/v2/ >/dev/null 2>&1; then
    echo "  ✅ Docker registry connectivity working"
else
    echo "  ❌ Docker registry connectivity failed"
fi

# Kind-specific diagnostics
echo
echo "🧪 Kind-Specific Diagnostics:"

# Check for common WSL2 issues
if grep -qi microsoft /proc/version; then
    echo "  🔍 WSL2-specific checks:"
    
    # Check systemd
    if systemctl is-system-running >/dev/null 2>&1; then
        echo "    ✅ systemd is running"
    else
        echo "    ⚠️  systemd may not be properly configured"
    fi
    
    # Check cgroup v2
    if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
        echo "    ✅ cgroup v2 is available"
    else
        echo "    ⚠️  cgroup v2 may not be available"
    fi
    
    # Check memory overcommit
    OVERCOMMIT=$(cat /proc/sys/vm/overcommit_memory)
    echo "    📊 Memory overcommit setting: $OVERCOMMIT"
    
    # Check swap
    SWAP_TOTAL=$(free | grep Swap | awk '{print $2}')
    if [ "$SWAP_TOTAL" -gt 0 ]; then
        echo "    📊 Swap is enabled: $(free -h | grep Swap | awk '{print $2}')"
    else
        echo "    ℹ️  Swap is disabled"
    fi
fi

# Configuration files
echo
echo "📄 Configuration Files:"
KIND_CONFIG="$(dirname "$0")/kind-config.yaml"
if [ -f "$KIND_CONFIG" ]; then
    echo "  ✅ Kind config found: $KIND_CONFIG"
    echo "  📋 Node count: $(grep -c 'role:' "$KIND_CONFIG" || echo "Unknown")"
    echo "  📋 Port mappings: $(grep -c 'hostPort:' "$KIND_CONFIG" || echo "0")"
else
    echo "  ❌ Kind config not found: $KIND_CONFIG"
fi

# Recent Docker/Kind logs
echo
echo "📝 Recent System Logs:"
echo "  🔍 Checking for recent Docker/Kind errors..."

# Check journalctl for Docker issues (if available)
if command -v journalctl >/dev/null 2>&1; then
    DOCKER_ERRORS=$(journalctl -u docker --since "10 minutes ago" --no-pager -q | grep -i error | wc -l)
    if [ "$DOCKER_ERRORS" -gt 0 ]; then
        echo "    ⚠️  Found $DOCKER_ERRORS Docker errors in last 10 minutes"
        echo "    💡 Run: journalctl -u docker --since '10 minutes ago' --no-pager"
    else
        echo "    ✅ No recent Docker errors found"
    fi
fi

# Check dmesg for OOM or resource issues
OOM_KILLS=$(dmesg | grep -i "killed process" | tail -5 | wc -l)
if [ "$OOM_KILLS" -gt 0 ]; then
    echo "    ⚠️  Found $OOM_KILLS recent OOM kills"
    echo "    💡 System may be running low on memory"
else
    echo "    ✅ No recent OOM kills found"
fi

echo
echo "🎯 Summary and Recommendations:"
echo "==============================="

# Provide specific recommendations based on findings
if grep -qi microsoft /proc/version; then
    echo "📍 WSL2 Environment Detected:"
    echo "  💡 Ensure Docker Desktop is running with WSL2 integration enabled"
    echo "  💡 Consider increasing Docker Desktop memory limit (Settings > Resources)"
    echo "  💡 If cluster creation hangs, try restarting Docker Desktop"
    echo
fi

if [ "$CONTAINER_COUNT" -gt 5 ]; then
    echo "📍 Many containers running ($CONTAINER_COUNT):"
    echo "  💡 Consider stopping unused containers to free resources"
    echo "  💡 Run: docker container prune"
    echo
fi

# Check available memory
AVAILABLE_MB=$(free -m | grep '^Mem:' | awk '{print $7}')
if [ "$AVAILABLE_MB" -lt 2048 ]; then
    echo "📍 Low available memory (${AVAILABLE_MB}MB):"
    echo "  💡 Kind clusters need at least 2GB available memory"
    echo "  💡 Close other applications or increase system memory"
    echo
fi

echo "✅ Diagnostics complete!"
echo "💡 If issues persist, share this output when asking for help"
