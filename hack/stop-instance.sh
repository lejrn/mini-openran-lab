#!/bin/bash
# hack/stop-instance.sh - Cost guard-rail script for AWS EC2

set -euo pipefail

# Configuration
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_TAG_NAME="mini-openran-lab"

echo "🛡️  Cost guard-rail: Stopping mini-OpenRAN lab instances..."

# Find instances by tag
INSTANCE_IDS=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=tag:Name,Values=$INSTANCE_TAG_NAME" "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text)

if [ -z "$INSTANCE_IDS" ]; then
    echo "✅ No running instances found with tag Name=$INSTANCE_TAG_NAME"
    exit 0
fi

echo "🔍 Found running instances: $INSTANCE_IDS"

# Stop instances
for instance_id in $INSTANCE_IDS; do
    echo "⏹️  Stopping instance: $instance_id"
    aws ec2 stop-instances --region "$REGION" --instance-ids "$instance_id"
done

echo "✅ All instances stopped. AWS charges should now be minimal."
echo "💡 To restart: terraform apply in the terraform/ directory"

# Optional: Send notification
if command -v curl >/dev/null 2>&1 && [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🛡️ Mini-OpenRAN lab instances stopped automatically (cost guard-rail)\"}" \
        "$SLACK_WEBHOOK_URL"
fi
