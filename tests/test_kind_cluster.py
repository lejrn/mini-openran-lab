"""
Integration tests for Kind cluster setup

Tests that the kind cluster is properly configured and functional.
"""

import pytest
import subprocess
import time
import json
import yaml
import queue
import threading
import sys
from pathlib import Path


class TestKindCluster:
    """Test suite for Kind cluster setup and configuration."""
    
    @pytest.fixture(scope="class")
    def cluster_name(self):
        """Return the expected cluster name."""
        return "openran"
    
    @pytest.fixture(scope="class")
    def kind_config_path(self):
        """Return path to kind configuration file."""
        return Path(__file__).parent.parent / "hack" / "kind-config.yaml"
    
    def test_kind_binary_available(self):
        """Test that kind binary is available and working."""
        print("\n🔧 Testing kind binary availability...")
        result = subprocess.run(
            ["kind", "version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ kind command failed: {result.stderr}")
        assert result.returncode == 0, f"kind binary not working: {result.stderr}"
        assert "kind" in result.stdout.lower(), f"Unexpected version output: {result.stdout}"
        print(f"✅ Kind version: {result.stdout.strip()}")
    
    def test_kubectl_binary_available(self):
        """Test that kubectl binary is available."""
        print("\n🔧 Testing kubectl binary availability...")
        result = subprocess.run(
            ["kubectl", "version", "--client"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ kubectl command failed: {result.stderr}")
        assert result.returncode == 0, f"kubectl binary not working: {result.stderr}"
        print("✅ kubectl binary is available")
    
    def test_kind_config_file_exists(self, kind_config_path):
        """Test that kind configuration file exists and is valid YAML."""
        print(f"\n📋 Testing kind config file: {kind_config_path}")
        assert kind_config_path.exists(), f"Kind config file not found: {kind_config_path}"
        
        print("  📄 Reading and validating YAML...")
        with open(kind_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate basic structure
        print("  🔍 Validating config structure...")
        assert config['kind'] == 'Cluster', f"Expected kind=Cluster, got {config.get('kind')}"
        assert config['apiVersion'] == 'kind.x-k8s.io/v1alpha4', f"Unexpected apiVersion: {config.get('apiVersion')}"
        assert config['name'] == 'openran', f"Expected name=openran, got {config.get('name')}"
        assert 'nodes' in config, "nodes section missing from config"
        assert len(config['nodes']) >= 1, "At least one node required"
        assert config['nodes'][0]['role'] == 'control-plane', f"First node should be control-plane, got {config['nodes'][0].get('role')}"
        
        print("  ✅ Config structure is valid")
        print("✅ Kind config file is valid")
    
    def test_cluster_creation_script_exists(self):
        """Test that the cluster creation script exists and is executable."""
        print("\n📜 Testing cluster creation script...")
        script_path = Path(__file__).parent.parent / "hack" / "kind-up.sh"
        print(f"  Script path: {script_path}")
        
        assert script_path.exists(), "kind-up.sh script not found"
        assert script_path.is_file(), "kind-up.sh is not a file"
        
        # Check if script is executable
        import stat
        st = script_path.stat()
        is_executable = bool(st.st_mode & stat.S_IEXEC)
        print(f"  Executable permissions: {oct(st.st_mode)[-3:]}")
        assert is_executable, "kind-up.sh is not executable"
        
        print("✅ kind-up.sh script exists and is executable")
    
    def test_cluster_can_be_created(self, cluster_name):
        """Test that we can create a kind cluster successfully."""
        print(f"\n🧪 Starting cluster creation test for '{cluster_name}'...")
        
        # First, ensure any existing cluster is deleted
        print("🧹 Cleaning up any existing cluster...")
        cleanup_result = subprocess.run(
            ["kind", "delete", "cluster", "--name", cluster_name], 
            capture_output=True,
            text=True
        )
        if cleanup_result.returncode == 0:
            print("  ✅ Existing cluster deleted")
        else:
            print("  ℹ️  No existing cluster to delete")
        
        # Create the cluster using our script
        script_path = Path(__file__).parent.parent / "hack" / "kind-up.sh"
        print(f"🚀 Creating cluster using script: {script_path}")
        print("⏳ This may take 2-3 minutes...")
        
        try:
            # Run the script with real-time output streaming
            process = subprocess.Popen(
                [str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress with timeout and real-time output
            start_time = time.time()
            timeout = 360  # 6 minutes (longer timeout for WSL2)
            all_output = []
            
            print("  📊 Streaming cluster creation output:")
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    print(f"    {line}")
                    all_output.append(line)
                    sys.stdout.flush()  # Force output to appear immediately
                
                # Check if process finished
                if process.poll() is not None:
                    break
                    
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    print(f"\n❌ Cluster creation timed out after {elapsed:.1f} seconds!")
                    print("🔍 Checking for any error patterns in output...")
                    
                    # Look for specific error patterns
                    output_text = '\n'.join(all_output)
                    if "timed out waiting for the condition" in output_text.lower():
                        print("  🚨 Found timeout condition - likely kubelet health issue")
                    if "failed to pull image" in output_text.lower():
                        print("  🚨 Found image pull failure")
                    if "network" in output_text.lower() and "error" in output_text.lower():
                        print("  🚨 Possible network connectivity issue")
                    
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    
                    raise TimeoutError(f"Cluster creation exceeded {timeout} seconds")
            
            # Get the return code
            return_code = process.wait()
            
            if return_code != 0:
                print(f"\n❌ Script failed with return code: {return_code}")
                print("🔍 Analyzing failure output...")
                
                # Analyze the output for common issues
                output_text = '\n'.join(all_output)
                if "kubelet" in output_text.lower() and ("unhealthy" in output_text.lower() or "timeout" in output_text.lower()):
                    print("  🚨 Kubelet health check failure detected")
                    print("  💡 This is often caused by WSL2/Docker resource constraints")
                    print("  💡 Try: increasing Docker memory limit or restarting Docker")
                
                if "failed to create cluster" in output_text.lower():
                    print("  🚨 General cluster creation failure")
                    
                if len(all_output) > 20:
                    print("  📄 Last 20 lines of output:")
                    for line in all_output[-20:]:
                        print(f"      {line}")
                else:
                    print("  📄 Full output:")
                    for line in all_output:
                        print(f"      {line}")
                
                raise AssertionError(f"Failed to create cluster. Return code: {return_code}")
            
            print("\n✅ Kind cluster created successfully!")
            
            # Verify cluster is actually responsive
            print("🔍 Verifying cluster responsiveness...")
            verify_result = subprocess.run(
                ["kubectl", "get", "nodes", "--context", f"kind-{cluster_name}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if verify_result.returncode == 0:
                print("  ✅ Cluster is responsive to kubectl commands")
            else:
                print(f"  ⚠️  Cluster may not be fully ready: {verify_result.stderr}")
            
        except Exception as e:
            print(f"\n❌ Exception during cluster creation: {str(e)}")
            print("🧹 Attempting cleanup...")
            
            # Try to cleanup any partially created resources
            subprocess.run(["kind", "delete", "cluster", "--name", cluster_name], 
                         capture_output=True, timeout=60)
            
            # Also check for any docker containers that might be stuck
            print("🔍 Checking for stuck containers...")
            docker_ps = subprocess.run(["docker", "ps", "-a", "--filter", f"name={cluster_name}"],
                                     capture_output=True, text=True)
            if docker_ps.returncode == 0 and docker_ps.stdout.strip():
                print(f"  Found containers: {docker_ps.stdout}")
            
            raise
    
    def test_cluster_is_running(self, cluster_name):
        """Test that the cluster is running and accessible."""
        print(f"\n🔍 Checking if cluster '{cluster_name}' is running...")
        
        # Check cluster exists
        print("📋 Listing existing clusters...")
        result = subprocess.run(
            ["kind", "get", "clusters"], 
            capture_output=True, 
            text=True
        )
        assert result.returncode == 0, f"Failed to list clusters: {result.stderr}"
        print(f"  Found clusters: {result.stdout.strip().split()}")
        assert cluster_name in result.stdout, f"Cluster '{cluster_name}' not found in: {result.stdout}"
        
        # Check kubectl can connect
        print("🔗 Testing kubectl connectivity...")
        result = subprocess.run(
            ["kubectl", "cluster-info", "--context", f"kind-{cluster_name}"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ kubectl cluster-info failed: {result.stderr}")
        assert result.returncode == 0, f"kubectl cluster-info failed: {result.stderr}"
        assert "Kubernetes control plane" in result.stdout, f"Control plane not found in output: {result.stdout}"
        
        print("✅ Cluster is running and accessible")
    
    def test_required_namespaces_exist(self, cluster_name):
        """Test that required namespaces are created."""
        print(f"\n🏷️  Checking required namespaces in cluster '{cluster_name}'...")
        expected_namespaces = ["openran", "monitoring", "xapps"]
        
        print("📋 Getting all namespaces...")
        result = subprocess.run(
            ["kubectl", "get", "namespaces", "-o", "json", "--context", f"kind-{cluster_name}"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to get namespaces: {result.stderr}")
        assert result.returncode == 0, f"Failed to get namespaces: {result.stderr}"
        
        namespaces_data = json.loads(result.stdout)
        existing_namespaces = [ns['metadata']['name'] for ns in namespaces_data['items']]
        print(f"  Found namespaces: {existing_namespaces}")
        
        for ns in expected_namespaces:
            if ns in existing_namespaces:
                print(f"  ✅ Namespace '{ns}' exists")
            else:
                print(f"  ❌ Namespace '{ns}' missing")
            assert ns in existing_namespaces, f"Namespace '{ns}' not found"
        
        print(f"✅ All required namespaces exist: {expected_namespaces}")
    
    def test_nodes_are_ready(self, cluster_name):
        """Test that all cluster nodes are in Ready state."""
        print(f"\n🖥️  Checking node status in cluster '{cluster_name}'...")
        
        print("📋 Getting node information...")
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json", "--context", f"kind-{cluster_name}"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to get nodes: {result.stderr}")
        assert result.returncode == 0, f"Failed to get nodes: {result.stderr}"
        
        nodes_data = json.loads(result.stdout)
        nodes = nodes_data['items']
        print(f"  Found {len(nodes)} nodes")
        assert len(nodes) >= 1, "No nodes found in cluster"
        
        for node in nodes:
            node_name = node['metadata']['name']
            print(f"  📋 Checking node: {node_name}")
            
            conditions = node['status']['conditions']
            ready_condition = next((c for c in conditions if c['type'] == 'Ready'), None)
            assert ready_condition is not None, f"Ready condition not found for node {node_name}"
            
            status = ready_condition['status']
            reason = ready_condition.get('reason', 'Unknown')
            print(f"    Status: {status}, Reason: {reason}")
            
            if status == 'True':
                print(f"    ✅ Node {node_name} is ready")
            else:
                print(f"    ❌ Node {node_name} is not ready")
                
            assert status == 'True', f"Node {node_name} is not ready. Status: {status}, Reason: {reason}"
        
        print(f"✅ All {len(nodes)} nodes are ready")
    
    def test_port_mappings_configured(self, cluster_name, kind_config_path):
        """Test that port mappings are properly configured."""
        print(f"\n🔌 Testing port mappings configuration...")
        
        print(f"  Reading config from: {kind_config_path}")
        with open(kind_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check that port mappings exist in config
        node = config['nodes'][0]
        print("  📋 Checking for extraPortMappings...")
        assert 'extraPortMappings' in node, "extraPortMappings not found in node config"
        
        port_mappings = node['extraPortMappings']
        expected_ports = [3000, 9090, 8080]  # Grafana, Prometheus, xApp API
        
        mapped_ports = [pm['hostPort'] for pm in port_mappings]
        print(f"  Found port mappings: {mapped_ports}")
        
        for port in expected_ports:
            if port in mapped_ports:
                print(f"    ✅ Port {port} is mapped")
            else:
                print(f"    ❌ Port {port} is NOT mapped")
            assert port in mapped_ports, f"Port {port} not mapped"
        
        print(f"✅ Port mappings configured correctly: {mapped_ports}")
    
    def test_node_labels_applied(self, cluster_name):
        """Test that custom node labels are applied."""
        print(f"\n🏷️  Checking node labels in cluster '{cluster_name}'...")
        
        result = subprocess.run(
            ["kubectl", "get", "nodes", "-o", "json", "--context", f"kind-{cluster_name}"], 
            capture_output=True, 
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to get nodes: {result.stderr}")
        assert result.returncode == 0, f"Failed to get nodes: {result.stderr}"
        
        nodes_data = json.loads(result.stdout)
        nodes = nodes_data['items']
        
        # Check for openran.io/cpu-isolation label
        for node in nodes:
            node_name = node['metadata']['name']
            labels = node['metadata'].get('labels', {})
            print(f"  📋 Checking labels for node: {node_name}")
            
            # Show some relevant labels
            openran_labels = {k: v for k, v in labels.items() if 'openran' in k.lower()}
            if openran_labels:
                print(f"    OpenRAN labels: {openran_labels}")
            
            if 'openran.io/cpu-isolation' in labels:
                label_value = labels['openran.io/cpu-isolation']
                print(f"    ✅ CPU isolation label found: {label_value}")
                assert label_value == 'enabled', f"Expected 'enabled', got '{label_value}'"
            else:
                print(f"    ❌ CPU isolation label not found")
                print(f"    Available labels: {list(labels.keys())}")
                assert False, f"CPU isolation label not found on node {node_name}"
        
        print("✅ Node labels are properly applied")
    
    @pytest.fixture(scope="class", autouse=True)
    def cleanup_cluster(self, cluster_name):
        """Cleanup fixture that runs after all tests."""
        yield
        
        # Cleanup: delete the cluster after tests
        print(f"\n🧹 Cleaning up cluster '{cluster_name}'...")
        result = subprocess.run(
            ["kind", "delete", "cluster", "--name", cluster_name], 
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Cluster cleanup completed successfully")
        else:
            print(f"⚠️  Cleanup had issues: {result.stderr}")
            print("✅ Cluster cleanup completed")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
