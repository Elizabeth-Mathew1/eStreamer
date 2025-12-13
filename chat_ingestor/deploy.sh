#!/bin/bash

gcloud run deploy chat-ingestor-1 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars CLIENT_ID="${CLIENT_ID}" \
  --set-env-vars CLIENT_SECRET="${CLIENT_SECRET}" \
  --set-env-vars REFRESH_TOKEN="${REFRESH_TOKEN}" \
  --set-env-vars KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS}" \
  --set-env-vars KAFKA_API_KEY="${KAFKA_API_KEY}" \
  --set-env-vars KAFKA_API_SECRET="${KAFKA_API_SECRET}" \
  --set-env-vars KAFKA_TOPIC="${KAFKA_TOPIC}" \
  --set-env-vars REST_API_KEY="${REST_API_KEY}" \
  --cpu 1 \
  --memory 2Gi \
  --max-instances 1 \
  --min-instances 0 \
  --port 8080


  ## chmod +x deploy.sh to give executable permission
  ## ./deploy.sh to run the script
