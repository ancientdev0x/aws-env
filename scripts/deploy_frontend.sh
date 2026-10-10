#!/usr/bin/env bash
# Publish frontend/ (index.html + data/ overlays) to the stack's S3 static website bucket.
# Usage: scripts/deploy_frontend.sh            (always uses the hackathon profile "baadh", never the shell default)
set -euo pipefail
export AWS_PROFILE=baadh
REGION=ap-south-1
STACK=${STACK:-baadhdrishti}
cd "$(dirname "$0")/.."
out() { aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
          --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API=$(out ApiUrl); BUCKET=$(out FrontendBucketName); URL=$(out FrontendUrl)
printf '{"apiUrl": "%s"}\n' "$API" > frontend/config.json
aws s3 sync frontend/ "s3://$BUCKET/" --region "$REGION" --exclude ".*" --delete --only-show-errors
echo "API      $API"
echo "Frontend $URL"
