# Grafana Dashboard Setup - Quick Steps

## Current Status
You're in the Grafana query builder interface. Here's how to proceed:

## Option 1: Manual Metric Entry (Try This First)
1. **In the "Select metric" field**: Type `gnb_connected_ues_total`
2. **Click "Run queries"** (blue button)
3. **If you see data**: Great! You can now add more panels
4. **If "No data"**: Continue to Option 2

## Option 2: Check/Fix Data Source
1. **Go to Data Sources**:
   - Click the gear icon (⚙️) in left sidebar → "Data sources"
   - Click on "Prometheus" (if it exists) or "Add data source"

2. **Configure Prometheus URL**:
   - **Name**: `Prometheus`
   - **URL**: `http://openran-radio-prometheus-server.openran-radio.svc.cluster.local`
   - **Access**: `Server (default)`
   - Click "Save & test"

## Option 3: Import Complete Dashboard
1. **Go to Dashboard Import**:
   - Click "+" in left sidebar → "Import"
   - Click "Upload JSON file"
   - Upload: `/home/lrn/Repos/mini-openran-lab/grafana-dashboards/openran-overview.json`

## Available OpenRAN Metrics to Try:
- `gnb_connected_ues_total` - Number of connected devices
- `gnb_dl_throughput_mbps` - Download speed  
- `gnb_ul_throughput_mbps` - Upload speed
- `ue_connection_state` - UE connection status
- `ue_signal_strength_dbm` - Signal quality

## Next Steps After Getting Metrics:
1. **Change visualization type**: Time series, Stat, Gauge
2. **Add more queries**: Multiple metrics per panel
3. **Customize**: Colors, thresholds, units
4. **Save dashboard**: Give it a name and save

---
**Current OpenRAN Status**: ✅ gNB: 2 UEs connected, ✅ UE: Active, ✅ Throughput: ~62 Mbps DL
