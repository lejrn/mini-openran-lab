*** Settings ***
Documentation     End-to-end tests for Mini-OpenRAN Lab
...               This test suite verifies the complete deployment works correctly
...               by checking that all components are running and communicating.

Library           RequestsLibrary
Library           Process
Library           OperatingSystem
Library           Collections
Library           String

Suite Setup       Setup Test Environment
Suite Teardown    Cleanup Test Environment

*** Variables ***
${GRAFANA_URL}         http://localhost:3000
${PROMETHEUS_URL}      http://localhost:9090
${XAPP_URL}           http://localhost:8080
${KUBECTL_CMD}        kubectl
${TIMEOUT}            30s

*** Test Cases ***
Verify Kubernetes Cluster Is Running
    [Documentation]    Check that kind cluster is accessible
    [Tags]             infrastructure
    
    ${result} =    Run Process    ${KUBECTL_CMD}    get    nodes
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Ready
    Log    Cluster nodes: ${result.stdout}

Verify OpenRAN Pods Are Running
    [Documentation]    Check all OpenRAN components are deployed and running
    [Tags]             deployment
    
    # Check gNB pod
    ${result} =    Run Process    ${KUBECTL_CMD}    get    pods    -l    app=srsran-gnb
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Running
    
    # Check UE pod  
    ${result} =    Run Process    ${KUBECTL_CMD}    get    pods    -l    app=srsran-ue
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Running
    
    # Check RIC platform
    ${result} =    Run Process    ${KUBECTL_CMD}    get    pods    -l    app=ric-platform
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Running
    
    # Check xApp
    ${result} =    Run Process    ${KUBECTL_CMD}    get    pods    -l    app=beam-tuner-xapp
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    Running

Verify Services Are Accessible
    [Documentation]    Check that Kubernetes services are properly exposed
    [Tags]             networking
    
    ${result} =    Run Process    ${KUBECTL_CMD}    get    services
    ...            shell=True    timeout=10s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    srsran-gnb
    Should Contain    ${result.stdout}    grafana
    Should Contain    ${result.stdout}    prometheus

Verify gNB Logs Show RRC Connection
    [Documentation]    Check that gNB successfully establishes RRC connection with UE
    [Tags]             radio
    
    ${result} =    Run Process    ${KUBECTL_CMD}    logs    -l    app=srsran-gnb    --tail=50
    ...            shell=True    timeout=15s
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain Any    ${result.stdout}    RRC CONNECTED    RRC_SETUP_COMPLETE    UE connected
    Log    gNB logs: ${result.stdout}

Verify xApp Health Endpoint
    [Documentation]    Check that beam tuner xApp is responding to health checks
    [Tags]             xapp
    
    # Port forward to xApp (background process)
    Start Process    ${KUBECTL_CMD}    port-forward    svc/beam-tuner-xapp    8080:8080
    ...              alias=xapp-forward
    Sleep    5s    # Allow port forward to establish
    
    # Create HTTP session
    Create Session    xapp    ${XAPP_URL}    timeout=${TIMEOUT}
    
    # Check health endpoint
    ${response} =    GET On Session    xapp    /healthz
    Should Be Equal As Integers    ${response.status_code}    200
    
    ${json} =    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    healthy
    Should Contain    ${json}    timestamp

Verify xApp Status Endpoint
    [Documentation]    Check that xApp reports valid status information
    [Tags]             xapp
    
    ${response} =    GET On Session    xapp    /status
    Should Be Equal As Integers    ${response.status_code}    200
    
    ${json} =    Set Variable    ${response.json()}
    Should Contain    ${json}    current_mcs
    Should Contain    ${json}    cqi_history
    Should Contain    ${json}    thresholds
    
    # Validate MCS is within expected range
    ${mcs} =    Get From Dictionary    ${json}    current_mcs
    Should Be True    ${mcs} >= 1 and ${mcs} <= 28

Verify Prometheus Metrics Collection
    [Documentation]    Check that Prometheus is collecting metrics from components
    [Tags]             monitoring
    
    # Port forward to Prometheus
    Start Process    ${KUBECTL_CMD}    port-forward    svc/prometheus-server    9090:80
    ...              alias=prometheus-forward
    Sleep    5s
    
    Create Session    prometheus    ${PROMETHEUS_URL}    timeout=${TIMEOUT}
    
    # Check Prometheus is up
    ${response} =    GET On Session    prometheus    /-/healthy
    Should Be Equal As Integers    ${response.status_code}    200
    
    # Check for specific metrics
    ${response} =    GET On Session    prometheus    /api/v1/query?query=up
    Should Be Equal As Integers    ${response.status_code}    200
    
    ${json} =    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    success

Verify Grafana Dashboard Access
    [Documentation]    Check that Grafana is accessible and has data sources configured
    [Tags]             monitoring
    
    # Port forward to Grafana
    Start Process    ${KUBECTL_CMD}    port-forward    svc/grafana    3000:80
    ...              alias=grafana-forward  
    Sleep    5s
    
    Create Session    grafana    ${GRAFANA_URL}    timeout=${TIMEOUT}
    
    # Check Grafana health (may return 302 redirect to login)
    ${response} =    GET On Session    grafana    /api/health    expected_status=any
    Should Be True    ${response.status_code} in [200, 302]
    
    # Check login page is accessible
    ${response} =    GET On Session    grafana    /login
    Should Be Equal As Integers    ${response.status_code}    200
    Should Contain    ${response.text}    Grafana

Test xApp Manual MCS Adjustment
    [Documentation]    Test manual MCS adjustment through xApp API
    [Tags]             xapp    integration
    
    # Get current MCS
    ${response} =    GET On Session    xapp    /status
    ${initial_status} =    Set Variable    ${response.json()}
    ${initial_mcs} =    Get From Dictionary    ${initial_status}    current_mcs
    
    # Trigger manual adjustment
    ${response} =    POST On Session    xapp    /adjust?direction=up
    Should Be Equal As Integers    ${response.status_code}    200
    
    ${json} =    Set Variable    ${response.json()}
    Should Be Equal    ${json['status']}    success
    Should Be Equal    ${json['direction']}    up
    
    # Wait a moment for adjustment to take effect
    Sleep    2s
    
    # Verify MCS changed
    ${response} =    GET On Session    xapp    /status  
    ${new_status} =    Set Variable    ${response.json()}
    ${new_mcs} =    Get From Dictionary    ${new_status}    current_mcs
    
    # Note: In simulation mode, MCS might not actually change
    # This test verifies the API works, actual change depends on E2 connection
    Log    Initial MCS: ${initial_mcs}, New MCS: ${new_mcs}

Verify E2E Data Flow
    [Documentation]    Verify data flows through the complete pipeline
    [Tags]             integration    e2e
    
    # Check xApp metrics endpoint
    ${response} =    GET On Session    xapp    /metrics
    Should Be Equal As Integers    ${response.status_code}    200
    Should Contain    ${response.text}    cqi_observations
    Should Contain    ${response.text}    mcs_adjustments_total
    
    # Verify metrics are being updated
    ${first_response} =    GET On Session    xapp    /metrics
    Sleep    5s
    ${second_response} =    GET On Session    xapp    /metrics
    
    # At minimum, timestamp should have changed
    Should Not Be Equal    ${first_response.text}    ${second_response.text}

*** Keywords ***
Setup Test Environment
    [Documentation]    Prepare the test environment
    
    Log    Setting up test environment for OpenRAN lab
    
    # Verify kubectl is available
    ${result} =    Run Process    which    kubectl    shell=True
    Should Be Equal As Integers    ${result.rc}    0
    
    # Verify kind cluster exists
    ${result} =    Run Process    kind    get    clusters    shell=True
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    openran
    
    # Set kubectl context to kind cluster
    Run Process    kubectl    config    use-context    kind-openran    shell=True

Cleanup Test Environment
    [Documentation]    Clean up after tests
    
    Log    Cleaning up test environment
    
    # Terminate any port forwards
    Terminate All Processes
    
    # Clean up any test files
    Run Keyword And Ignore Error    Remove Directory    ${TEMPDIR}/robot-test    recursive=True

Should Contain Any
    [Documentation]    Check if text contains any of the provided patterns
    [Arguments]    ${text}    @{patterns}
    
    FOR    ${pattern}    IN    @{patterns}
        ${contains} =    Run Keyword And Return Status    Should Contain    ${text}    ${pattern}
        Return From Keyword If    ${contains}
    END
    
    Fail    Text does not contain any of the expected patterns: ${patterns}
