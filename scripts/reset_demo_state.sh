#!/usr/bin/env bash
# Empty the officer-state tables (road overrides + staging hubs) before a demo take.
# Usage: AWS_PROFILE=baadh scripts/reset_demo_state.sh [stack-name]
set -euo pipefail
STACK=${1:-baadhdrishti}
for pair in "road_overrides:edge_id" "staging_hubs:hub_id"; do
  table="$STACK-${pair%%:*}"; key=${pair##*:}
  for id in $(aws dynamodb scan --table-name "$table" --projection-expression "$key" --query "Items[].$key.S" --output text); do
    aws dynamodb delete-item --table-name "$table" --key "{\"$key\":{\"S\":\"$id\"}}"
  done
  echo "$table: $(aws dynamodb scan --table-name "$table" --select COUNT --query Count) items"
done
