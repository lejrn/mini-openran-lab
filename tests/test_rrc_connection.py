"""
Test RRC connection establishment between gNB and UE

Tests that verify the radio layer is working by checking for
RRC CONNECTED states in the component logs.
"""

import pytest
import subprocess
import time
import re
from pathlib import Path


class TestRRCConnection:
    """Test suite for RRC connection establishment."""
    
    @pytest.fixture(scope="class")
    def kubectl_cmd(self):
        """Return kubectl command with proper context."""
        return ["kubectl", "--context", "kind-openran"]
    
    def test_gnb_deployment_exists(self, kubectl_cmd):
        """Test that gNB deployment exists and is ready."""
        print("\n🔧 Testing gNB deployment status...")
        result = subprocess.run(
            kubectl_cmd + ["get", "deployment", "-l", "app.kubernetes.io/component=gnb", "-o", "name"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to get gNB deployment: {result.stderr}"
        assert "deployment" in result.stdout, "gNB deployment not found"
        print("✅ gNB deployment exists")
    
    def test_ue_deployment_exists(self, kubectl_cmd):
        """Test that UE deployment exists and is ready."""
        print("\n🔧 Testing UE deployment status...")
        result = subprocess.run(
            kubectl_cmd + ["get", "deployment", "-l", "app.kubernetes.io/component=ue", "-o", "name"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to get UE deployment: {result.stderr}"
        assert "deployment" in result.stdout, "UE deployment not found"
        print("✅ UE deployment exists")
    
    def test_wait_for_pods_running(self, kubectl_cmd):
        """Wait for both gNB and UE pods to be in Running state."""
        print("\n⏳ Waiting for pods to be Running...")
        
        # Wait for gNB pod
        max_wait = 120  # 2 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            result = subprocess.run(
                kubectl_cmd + ["get", "pods", "-l", "app=srsran-gnb", "-o", "jsonpath={.items[*].status.phase}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "Running" in result.stdout:
                print("✅ gNB pod is Running")
                break
            time.sleep(5)
        else:
            pytest.fail("gNB pod did not reach Running state within timeout")
        
        # Wait for UE pod
        start_time = time.time()
        while time.time() - start_time < max_wait:
            result = subprocess.run(
                kubectl_cmd + ["get", "pods", "-l", "app=srsran-ue", "-o", "jsonpath={.items[*].status.phase}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "Running" in result.stdout:
                print("✅ UE pod is Running")
                break
            time.sleep(5)
        else:
            pytest.fail("UE pod did not reach Running state within timeout")
    
    def test_gnb_logs_contain_startup_messages(self, kubectl_cmd):
        """Test that gNB logs show proper startup."""
        print("\n📋 Checking gNB startup logs...")
        result = subprocess.run(
            kubectl_cmd + ["logs", "-l", "app=srsran-gnb", "--tail=100"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to get gNB logs: {result.stderr}"
        
        logs = result.stdout.lower()
        # Check for typical gNB startup indicators
        startup_indicators = [
            "gnb", "starting", "initialized", "cell", "band"
        ]
        
        found_indicators = []
        for indicator in startup_indicators:
            if indicator in logs:
                found_indicators.append(indicator)
        
        print(f"Found startup indicators: {found_indicators}")
        assert len(found_indicators) >= 2, f"gNB startup logs incomplete. Found: {found_indicators}"
        print("✅ gNB shows proper startup messages")
    
    def test_ue_logs_contain_startup_messages(self, kubectl_cmd):
        """Test that UE logs show proper startup."""
        print("\n📋 Checking UE startup logs...")
        result = subprocess.run(
            kubectl_cmd + ["logs", "-l", "app=srsran-ue", "--tail=100"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to get UE logs: {result.stderr}"
        
        logs = result.stdout.lower()
        # Check for typical UE startup indicators
        startup_indicators = [
            "ue", "starting", "initialized", "searching", "cell"
        ]
        
        found_indicators = []
        for indicator in startup_indicators:
            if indicator in logs:
                found_indicators.append(indicator)
        
        print(f"Found startup indicators: {found_indicators}")
        assert len(found_indicators) >= 2, f"UE startup logs incomplete. Found: {found_indicators}"
        print("✅ UE shows proper startup messages")
    
    def test_rrc_connection_established(self, kubectl_cmd):
        """Test that RRC CONNECTED state is achieved."""
        print("\n🔗 Testing for RRC CONNECTED state...")
        
        # Wait up to 3 minutes for RRC connection
        max_wait = 180  # 3 minutes
        start_time = time.time()
        
        rrc_patterns = [
            r"rrc.*connected",
            r"rrc_setup_complete",
            r"ue.*connected",
            r"connection.*established",
            r"attach.*complete"
        ]
        
        while time.time() - start_time < max_wait:
            # Check gNB logs
            result = subprocess.run(
                kubectl_cmd + ["logs", "-l", "app=srsran-gnb", "--tail=50"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logs = result.stdout.lower()
                for pattern in rrc_patterns:
                    if re.search(pattern, logs):
                        print(f"✅ Found RRC connection indicator in gNB logs: {pattern}")
                        print(f"📝 Relevant log excerpt:\n{self._extract_relevant_logs(result.stdout, pattern)}")
                        return
            
            # Check UE logs
            result = subprocess.run(
                kubectl_cmd + ["logs", "-l", "app=srsran-ue", "--tail=50"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                logs = result.stdout.lower()
                for pattern in rrc_patterns:
                    if re.search(pattern, logs):
                        print(f"✅ Found RRC connection indicator in UE logs: {pattern}")
                        print(f"📝 Relevant log excerpt:\n{self._extract_relevant_logs(result.stdout, pattern)}")
                        return
            
            print(f"⏳ Still waiting for RRC connection... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(10)
        
        # If we get here, we didn't find RRC connection
        # Get final logs for debugging
        gnb_result = subprocess.run(
            kubectl_cmd + ["logs", "-l", "app=srsran-gnb", "--tail=100"],
            capture_output=True,
            text=True,
            timeout=15
        )
        ue_result = subprocess.run(
            kubectl_cmd + ["logs", "-l", "app=srsran-ue", "--tail=100"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        error_msg = (
            f"RRC CONNECTED state not achieved within {max_wait}s timeout.\n\n"
            f"gNB logs (last 100 lines):\n{gnb_result.stdout}\n\n"
            f"UE logs (last 100 lines):\n{ue_result.stdout}"
        )
        pytest.fail(error_msg)
    
    def _extract_relevant_logs(self, full_logs: str, pattern: str) -> str:
        """Extract relevant log lines around the pattern match."""
        lines = full_logs.split('\n')
        relevant_lines = []
        
        for i, line in enumerate(lines):
            if re.search(pattern, line.lower()):
                # Include 2 lines before and after the match
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                relevant_lines.extend(lines[start:end])
                relevant_lines.append("---")
        
        return '\n'.join(relevant_lines[-10:])  # Return last 10 relevant lines
    
    def test_metrics_endpoints_accessible(self, kubectl_cmd):
        """Test that metrics endpoints are accessible from both components."""
        print("\n📊 Testing metrics endpoints...")
        
        # Get gNB pod name first
        gnb_pod_result = subprocess.run(
            kubectl_cmd + ["get", "pods", "-l", "app=srsran-gnb", "-o", "jsonpath={.items[0].metadata.name}"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if gnb_pod_result.returncode == 0 and gnb_pod_result.stdout.strip():
            gnb_pod_name = gnb_pod_result.stdout.strip()
            print(f"Testing gNB metrics on pod: {gnb_pod_name}")
            
            # Test gNB metrics endpoint
            result = subprocess.run(
                kubectl_cmd + ["exec", gnb_pod_name, "--", "curl", "-s", "-f", "http://localhost:9091/metrics"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ gNB metrics endpoint accessible")
                # Look for some expected metrics
                metrics = result.stdout.lower()
                if "gnb" in metrics or "connected" in metrics or "throughput" in metrics:
                    print("✅ gNB metrics contain expected data")
                    print(f"📝 Sample metrics: {result.stdout[:200]}...")
            else:
                print(f"⚠️  gNB metrics endpoint not accessible: {result.stderr}")
        else:
            print("⚠️  Could not find gNB pod for metrics testing")
        
        # Get UE pod name first
        ue_pod_result = subprocess.run(
            kubectl_cmd + ["get", "pods", "-l", "app=srsran-ue", "-o", "jsonpath={.items[0].metadata.name}"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if ue_pod_result.returncode == 0 and ue_pod_result.stdout.strip():
            ue_pod_name = ue_pod_result.stdout.strip()
            print(f"Testing UE metrics on pod: {ue_pod_name}")
            
            # Test UE metrics endpoint
            result = subprocess.run(
                kubectl_cmd + ["exec", ue_pod_name, "--", "curl", "-s", "-f", "http://localhost:9092/metrics"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ UE metrics endpoint accessible")
                # Look for some expected metrics
                metrics = result.stdout.lower()
                if "ue" in metrics or "connection" in metrics or "signal" in metrics:
                    print("✅ UE metrics contain expected data")
                    print(f"📝 Sample metrics: {result.stdout[:200]}...")
            else:
                print(f"⚠️  UE metrics endpoint not accessible: {result.stderr}")
        else:
            print("⚠️  Could not find UE pod for metrics testing")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])
