#!/bin/bash

gcloud run deploy audio-transcribor-1 \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets="/secrets/cookies.txt=youtube-cookies:latest" \
  --no-cpu-throttling \
  --min-instances 1
