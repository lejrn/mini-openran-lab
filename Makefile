# Mini-OpenRAN Lab Makefile

.PHONY: help setup kind-up kind-down build test deploy-local deploy-cloud clean

# Default target
help:
	@echo "Mini-OpenRAN Lab Commands:"
	@echo "  setup           Install all prerequisites (kind, kubectl, helm, etc.)"
	@echo "  kind-up         Create kind cluster and deploy OpenRAN stack"
	@echo "  kind-down       Delete kind cluster"
	@echo "  build           Build all Docker images"
	@echo "  test            Run pytest and Robot Framework tests"
	@echo "  deploy-local    Deploy to local kind cluster"
	@echo "  deploy-cloud    Deploy to AWS EC2 via Terraform"
	@echo "  clean           Clean up all resources"

# Install prerequisites
setup:
	@echo "🔧 Installing prerequisites..."
	./hack/install-prerequisites.sh
	@echo "📦 Installing Python dependencies..."
	poetry install
	@echo "✅ Setup complete!"

# Create kind cluster and deploy
kind-up:
	@echo "🚀 Setting up kind cluster..."
	./hack/kind-up.sh
	@echo "📦 Loading Docker images..."
	./hack/load-images.sh
	@echo "🎯 Deploying OpenRAN stack..."
	helm repo add local ./charts
	helm dependency update charts/openran
	helm install openran ./charts/openran -f charts/openran/values-kind.yaml
	@echo "✅ Setup complete! Port-forward Grafana with:"
	@echo "   kubectl port-forward svc/grafana 3000:3000 -n monitoring"

# Delete kind cluster
kind-down:
	@echo "🧹 Deleting kind cluster..."
	kind delete cluster --name openran || true

# Build all images
build:
	@echo "🔨 Building xApp images..."
	docker build -t ghcr.io/mini-openran-lab/beam-tuner:latest xapps/beam_tuner/
	@echo "✅ Build complete"

# Run tests
test:
	@echo "🧪 Running unit tests..."
	poetry run pytest tests/ -v
	@echo "🤖 Running E2E tests..."
	poetry run robot tests/robot/

# Run tests for kind cluster setup
test-kind:
	@echo "🧪 Testing kind cluster setup..."
	poetry run pytest tests/test_kind_cluster.py -v

# Code quality checks
lint:
	@echo "🔍 Running code quality checks..."
	poetry run black --check .
	poetry run flake8 .
	poetry run mypy xapps/ --ignore-missing-imports

# Format code
format:
	@echo "🎨 Formatting code..."
	poetry run black .
	poetry run isort .

# Deploy to local kind
deploy-local: kind-up

# Deploy to AWS EC2
deploy-cloud:
	@echo "☁️ Deploying to AWS..."
	cd terraform && terraform init && terraform apply
	@echo "✅ AWS deployment complete"

# Clean up everything
clean: kind-down
	@echo "🧹 Cleaning Docker images..."
	docker rmi ghcr.io/mini-openran-lab/beam-tuner:latest || true
	@echo "🧹 Cleaning Terraform state..."
	cd terraform && terraform destroy -auto-approve || true
	@echo "✅ Cleanup complete"

# Development helpers
dev-logs:
	@echo "📋 Showing recent logs..."
	kubectl logs -l app=srsran-gnb --tail=50
	kubectl logs -l app=beam-tuner-xapp --tail=50

dev-shell:
	@echo "🐚 Opening shell in xApp pod..."
	kubectl exec -it deployment/beam-tuner-xapp -- /bin/bash

dev-forward:
	@echo "🔗 Setting up port forwards..."
	kubectl port-forward svc/grafana 3000:3000 -n monitoring &
	kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "📈 Prometheus: http://localhost:9090"
