#!/bin/bash

gcloud run deploy audio-transcribor-1 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --max-instances 1 \
  --min-instances 0 \
  --port 8080