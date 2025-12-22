gcloud run deploy video-downloader \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account="$SERVICE_ACCOUNT_EMAIL" \
