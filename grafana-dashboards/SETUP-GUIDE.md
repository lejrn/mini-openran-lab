# OpenRAN Grafana Dashboard Setup Guide

## 1. Access Grafana
- Open your browser to: http://localhost:3001
- Login with credentials: `admin` / `admin`

## 2. Configure Prometheus Data Source
1. Click the gear icon (⚙️) in the left sidebar → "Data sources"
2. Click "Add data source"
3. Select "Prometheus"
4. Configure:
   - **Name**: `Prometheus`
   - **URL**: `http://openran-radio-prometheus-server.openran-radio.svc.cluster.local`
   - **Access**: `Server (default)`
5. Click "Save & test" - you should see "Data source is working"

## 3. Import OpenRAN Dashboard
1. Click the "+" icon in the left sidebar → "Import"
2. Click "Upload JSON file" 
3. Select `/home/lrn/Repos/mini-openran-lab/grafana-dashboards/openran-overview.json`
4. Click "Load"
5. Select "Prometheus" as the data source
6. Click "Import"

## 4. Available Metrics in Your OpenRAN Lab

### gNB (Base Station) Metrics:
- `gnb_connected_ues_total` - Number of connected user devices
- `gnb_active_bearers_total` - Active data connections
- `gnb_ul_throughput_mbps` - Uplink data rate
- `gnb_dl_throughput_mbps` - Downlink data rate  
- `gnb_cpu_usage_percent` - Resource utilization
- `gnb_memory_usage_percent` - Memory usage

### UE (User Equipment) Metrics:
- `ue_connection_state` - Connection status (0=disconnected, 1=connected)
- `ue_signal_strength_dbm` - Radio signal quality
- `ue_uptime_seconds` - How long device has been running
- `ue_data_throughput_mbps` - Data transmission rate
- `ue_battery_level_percent` - Simulated battery level

## 5. Dashboard Panels Explained

### Connection Status Panel
- Shows if UE is connected to gNB
- Green = Connected, Red = Disconnected

### Throughput Charts
- Real-time data rates between gNB and UE
- Separate uplink/downlink measurements

### Signal Quality Gauge
- Radio signal strength in dBm
- Green: Good signal (-60 to -40 dBm)
- Yellow: Fair signal (-80 to -60 dBm)  
- Red: Poor signal (-100 to -80 dBm)

### Resource Monitoring
- gNB CPU and memory usage over time
- Helps identify performance bottlenecks

## 6. Customizing Your Dashboard

### Adding New Panels
1. Click "Add panel" → "Add a new panel"
2. In the query field, enter any of the metrics above
3. Choose visualization type (Graph, Stat, Gauge, etc.)
4. Configure display options and thresholds

### Example Custom Queries
```
# Average throughput over 5 minutes
avg_over_time(gnb_dl_throughput_mbps[5m])

# UE connection uptime in hours
ue_uptime_seconds / 3600

# Total data transferred (approximate)
gnb_dl_throughput_mbps * ue_uptime_seconds / 8
```

## 7. Troubleshooting

### No Data Showing
- Verify Prometheus data source configuration
- Check that port-forward is running: `kubectl port-forward svc/openran-radio-grafana 3001:80 -n openran-radio`
- Confirm pods are running: `kubectl get pods -n openran-radio`

### Metrics Not Available
- Check gNB metrics: `kubectl exec -n openran-radio deployment/openran-radio-gnb -- curl -s http://localhost:9091/metrics`
- Check UE metrics: `kubectl exec -n openran-radio deployment/openran-radio-ue -- curl -s http://localhost:9092/metrics`

## 8. Next Steps

### Phase 3 - RIC Integration
Your current setup is ready for RIC (RAN Intelligent Controller) integration:
- xApps will connect to collect these metrics
- Machine learning algorithms can analyze patterns
- Automated optimization based on performance data

### Advanced Monitoring
- Set up alerting for connection failures
- Create SLA dashboards for uptime tracking
- Add geo-location simulation for mobility scenarios
