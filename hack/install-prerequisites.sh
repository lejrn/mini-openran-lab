#!/bin/bash
# hack/install-prerequisites.sh - Install all prerequisites for mini-OpenRAN lab

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running in WSL2
is_wsl2() {
    [[ -f /proc/version ]] && grep -qi microsoft /proc/version
}

# Install kind
install_kind() {
    local kind_version="v0.22.0"
    local kind_url="https://kind.sigs.k8s.io/dl/${kind_version}/kind-linux-amd64"
    
    log_info "Installing kind ${kind_version}..."
    
    if command -v kind &> /dev/null; then
        local current_version=$(kind version | head -1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
        if [[ "$current_version" == "$kind_version" ]]; then
            log_success "kind ${kind_version} is already installed"
            return 0
        else
            log_warning "kind ${current_version} is installed, upgrading to ${kind_version}"
        fi
    fi
    
    # Download and install kind
    curl -Lo ./kind "$kind_url"
    chmod +x ./kind
    sudo mv ./kind /usr/local/bin/kind
    
    # Verify installation
    if kind version &> /dev/null; then
        log_success "kind installed successfully: $(kind version | head -1)"
    else
        log_error "Failed to install kind"
        exit 1
    fi
}

# Install kubectl
install_kubectl() {
    log_info "Installing kubectl..."
    
    if command -v kubectl &> /dev/null; then
        log_success "kubectl is already installed: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
        return 0
    fi
    
    # Get latest stable version
    local kubectl_version=$(curl -L -s https://dl.k8s.io/release/stable.txt)
    local kubectl_url="https://dl.k8s.io/release/${kubectl_version}/bin/linux/amd64/kubectl"
    
    # Download and install kubectl
    curl -LO "$kubectl_url"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
    
    # Verify installation
    if kubectl version --client &> /dev/null; then
        log_success "kubectl installed successfully: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    else
        log_error "Failed to install kubectl"
        exit 1
    fi
}

# Install Helm
install_helm() {
    local helm_version="v3.15.0"
    
    log_info "Installing Helm ${helm_version}..."
    
    if command -v helm &> /dev/null; then
        local current_version=$(helm version --short | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+')
        if [[ "$current_version" == "$helm_version" ]]; then
            log_success "Helm ${helm_version} is already installed"
            return 0
        else
            log_warning "Helm ${current_version} is installed, upgrading to ${helm_version}"
        fi
    fi
    
    # Download and install Helm
    local helm_url="https://get.helm.sh/helm-${helm_version}-linux-amd64.tar.gz"
    curl -sSL "$helm_url" | tar xz
    sudo mv linux-amd64/helm /usr/local/bin/
    rm -rf linux-amd64
    
    # Verify installation
    if helm version &> /dev/null; then
        log_success "Helm installed successfully: $(helm version --short)"
    else
        log_error "Failed to install Helm"
        exit 1
    fi
}

# Check and setup Docker for WSL2
check_docker_wsl2() {
    log_info "Checking Docker setup for WSL2..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker command not found."
        log_info "For WSL2 users:"
        log_info "  1. Install Docker Desktop on Windows"
        log_info "  2. Enable WSL2 integration in Docker Desktop settings"
        log_info "  3. Restart WSL2: wsl --shutdown (run from Windows)"
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not accessible."
        log_info "For WSL2 users:"
        log_info "  1. Make sure Docker Desktop is running on Windows"
        log_info "  2. Check WSL2 integration is enabled in Docker Desktop"
        log_info "  3. Try restarting Docker Desktop"
        exit 1
    fi
    
    log_success "Docker is properly configured: $(docker version --format '{{.Client.Version}}' 2>/dev/null)"
}

# Install Docker for native Linux
install_docker_linux() {
    log_info "Installing Docker for Linux..."
    
    if command -v docker &> /dev/null; then
        log_success "Docker is already installed"
        return 0
    fi
    
    # Update package index
    sudo apt update
    
    # Install Docker
    sudo apt install -y docker.io
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    # Start and enable Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker installed successfully"
    log_warning "Please log out and log back in for group changes to take effect"
}

# Install Poetry
install_poetry() {
    log_info "Checking Poetry installation..."
    
    if command -v poetry &> /dev/null; then
        log_success "Poetry is already installed: $(poetry --version)"
        return 0
    fi
    
    log_info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Verify installation
    if command -v poetry &> /dev/null; then
        log_success "Poetry installed successfully: $(poetry --version)"
        log_info "Add the following to your shell profile (~/.bashrc or ~/.zshrc):"
        log_info "export PATH=\"\$HOME/.local/bin:\$PATH\""
    else
        log_error "Failed to install Poetry"
        exit 1
    fi
}

# Main installation function
main() {
    log_info "🚀 Setting up mini-OpenRAN lab prerequisites..."
    echo ""
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        exit 1
    fi
    
    # Detect environment
    if is_wsl2; then
        log_info "Detected WSL2 environment"
        check_docker_wsl2
    else
        log_info "Detected native Linux environment"
        install_docker_linux
    fi
    
    # Install development tools
    install_kind
    install_kubectl
    install_helm
    install_poetry
    
    echo ""
    log_success "🎉 All prerequisites installed successfully!"
    echo ""
    log_info "Next steps:"
    log_info "  1. If this is your first time, restart your terminal session"
    log_info "  2. Run: cd $(dirname $SCRIPT_DIR)"
    log_info "  3. Run: poetry install"
    log_info "  4. Run: ./hack/kind-up.sh"
    log_info "  5. Run: poetry run pytest tests/test_kind_cluster.py -v"
    echo ""
}

# Run main function
main "$@"
