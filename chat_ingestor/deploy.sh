#!/bin/bash

gcloud run deploy chat-ingestor-1 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 2Gi \
  --max-instances 1 \
  --min-instances 0 \
  --port 8080


  ## chmod +x deploy.sh to give executable permission
  ## ./deploy.sh to run the script
