# OpenRAN Security Implementation Guide

## Overview

This document outlines the security measures implemented in the OpenRAN deployment to address the critical vulnerabilities identified in the security audit.

## Implemented Security Fixes

### 1. ✅ Container Security Contexts

All radio pods (gNB and UE) now run with restrictive security contexts:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

# Per-container security
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  capabilities:
    drop:
    - ALL
```

**Benefits:**
- Eliminates root container execution
- Prevents privilege escalation
- Restricts filesystem access
- Applies seccomp filtering

### 2. ✅ Network Segmentation

Comprehensive NetworkPolicy implementation:

- **Default Deny**: All traffic denied by default
- **Granular Rules**: Only necessary communication allowed
- **Monitoring Access**: Prometheus can scrape metrics
- **Inter-component**: gNB and UE can communicate on required ports

**Key Policies:**
- `gnb-netpol`: Restricts gNB pod communications
- `ue-netpol`: Restricts UE pod communications  
- `monitoring-netpol`: Allows metrics collection
- `default-deny`: Blocks all other traffic

### 3. ✅ Service Account Security

Minimal privilege service accounts:

- **Radio Components**: No service account token mounting
- **Monitoring**: Minimal RBAC (pods, services, configmaps read-only)
- **Principle of Least Privilege**: Only necessary permissions granted

### 4. ✅ Resource Governance

Resource quotas and limits prevent resource exhaustion:

```yaml
# Namespace limits
pods: "10"
requestsCpu: "4" 
requestsMemory: "8Gi"
limitsCpu: "8"
limitsMemory: "16Gi"

# Container limits
defaultCpu: "500m"
defaultMemory: "512Mi"
maxCpu: "2"
maxMemory: "4Gi"
```

### 5. ✅ Pod Security Standards

Kubernetes Pod Security Standards enforced:

- **Level**: `restricted` (highest security)
- **Enforcement**: Block non-compliant pods
- **Audit/Warn**: Log violations

### 6. ✅ Prometheus Configuration Fix

Fixed duplicate global sections in Prometheus config:

```yaml
serverFiles:
  prometheus.yml:
    global:  # Single global section
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
      # Properly structured scrape jobs
```

### 7. ✅ Strong Authentication

Grafana security improvements:

- **No Default Passwords**: Empty password triggers random generation
- **Secret Management**: Credentials stored in Kubernetes secrets
- **Future**: Ready for OIDC/LDAP integration

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Kubernetes Namespace                    │
│  ┌─────────────┐ Pod Security ┌─────────────────────┐   │
│  │ Standards   │ ────────────► │ NetworkPolicies     │   │
│  │ (restricted)│               │ (default deny)      │   │
│  └─────────────┘               └─────────────────────┘   │
│                                                         │
│  ┌─────────────┐               ┌─────────────────────┐   │
│  │ gNB Pod     │ ◄──ZMQ────── │ UE Pod              │   │
│  │ (non-root)  │               │ (non-root)          │   │
│  │ User: 1000  │               │ User: 1000          │   │
│  └─────────────┘               └─────────────────────┘   │
│       │                                │                │
│       │ metrics (9091)                 │ metrics (9092) │
│       ▼                                ▼                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Prometheus (monitoring service account)             │ │
│  │ RBAC: pods/services/configmaps (read-only)         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Resource Quotas & Limits                            │ │
│  │ • Max 10 pods, 8 CPU cores, 16Gi memory           │ │
│  │ • Container limits enforced                         │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Security Validation

### Deployment Security Check

```bash
# Verify security contexts
kubectl get pods -o jsonpath='{.items[*].spec.securityContext.runAsUser}'

# Check network policies
kubectl get networkpolicies

# Verify resource limits
kubectl describe limitrange

# Check RBAC
kubectl get rolebindings

# Validate Pod Security Standards
kubectl get namespace -o yaml | grep pod-security
```

### Monitoring Security

```bash
# Check for privileged containers
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].securityContext.privileged}'

# Verify service account tokens
kubectl get pods -o jsonpath='{.items[*].spec.automountServiceAccountToken}'

# Check image policies
kubectl get configmap openran-image-policy -o yaml
```

## Configuration Options

### Enable/Disable Security Features

```yaml
# values.yaml
networking:
  networkPolicy:
    enabled: true

resourceQuota:
  enabled: true

podSecurity:
  enabled: true
  enforce: "restricted"

imageSecurity:
  enabled: false  # Requires admission controller
```

### Customizing Security Levels

```yaml
# Less restrictive for development
podSecurity:
  enforce: "baseline"  # instead of "restricted"

# More permissive network policies
networking:
  networkPolicy:
    enabled: false
```

## Compliance Status

| Standard | Status | Implementation |
|----------|--------|----------------|
| Pod Security Standards | ✅ Implemented | Restricted level enforced |
| Network Segmentation | ✅ Implemented | Comprehensive NetworkPolicies |
| RBAC | ✅ Implemented | Minimal privilege service accounts |
| Resource Management | ✅ Implemented | Quotas and limits enforced |
| Container Security | ✅ Implemented | Non-root, read-only filesystem |
| Secret Management | ✅ Implemented | No hardcoded credentials |

## Next Steps

### High Priority (Week 1)
1. **Image Scanning**: Implement vulnerability scanning pipeline
2. **Admission Controllers**: Deploy OPA/Gatekeeper for policy enforcement
3. **Monitoring**: Deploy Falco for runtime security monitoring

### Medium Priority (Week 2-4)
1. **mTLS**: Implement service mesh (Istio/Linkerd)
2. **External Secrets**: Integrate with HashiCorp Vault
3. **Audit Logging**: Enable Kubernetes audit logs
4. **Backup Security**: Implement encrypted backups

### Long Term (Month 2+)
1. **OIDC Integration**: Replace basic auth with enterprise SSO
2. **Certificate Management**: Automated certificate rotation
3. **Security Scanning**: Container image signing and verification
4. **Compliance Automation**: Automated policy compliance checking

## Troubleshooting

### Common Issues

1. **Pod Security Violations**
   ```bash
   # Check PSS violations
   kubectl get events --field-selector reason=FailedCreate
   ```

2. **Network Policy Blocking Traffic**
   ```bash
   # Temporary disable for debugging
   kubectl label namespace default name-
   ```

3. **Resource Quota Exceeded**
   ```bash
   # Check current usage
   kubectl describe quota
   ```

## Security Testing

### Penetration Testing Checklist

- [ ] Container escape attempts
- [ ] Network segmentation bypass
- [ ] Privilege escalation tests
- [ ] Resource exhaustion attacks
- [ ] Service discovery enumeration
- [ ] Credential extraction attempts

### Continuous Security

- [ ] Automated vulnerability scanning
- [ ] Policy compliance monitoring
- [ ] Security audit log analysis
- [ ] Incident response procedures
- [ ] Security training for operators

This security implementation provides a robust foundation for the OpenRAN deployment while maintaining operational functionality.
