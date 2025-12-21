#!/bin/bash

# Simple deployment script for YouTube Stream Frontend
# Prerequisites:
#   - npm installed
#   - gsutil installed and authenticated
#   - Environment variable GCS_BUCKET_NAME set, or edit BUCKET_NAME below


echo "Loading environment variables..."
if [ -f .env ]; then
  set -a
  . .env
  set +a
fi

echo "Building frontend application..."
npm install
npm run build

if [ $? -ne 0 ]; then
    echo "Build failed."
    exit 1
fi


BUCKET_NAME="${GCS_BUCKET_NAME}"
echo "Uploading to Google Cloud Storage bucket: ${BUCKET_NAME}"
gsutil -m rsync -r dist/ gs://${BUCKET_NAME}/

if [ $? -ne 0 ]; then
    echo "Upload failed."
    exit 1
fi


echo "Configuring bucket for static website hosting..."
gsutil web set -m index.html -e index.html gs://${BUCKET_NAME}


echo "Deployment complete."
echo "Your site should be available at: https://storage.googleapis.com/${BUCKET_NAME}/index.html"


