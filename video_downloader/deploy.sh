#!/bin/bash

if [ ! -f ".env" ]; then
    echo "Error: .env file not found! Cannot read configuration."
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile not found!"
    exit 1
fi

echo "Reading configuration from .env..."

PROJECT_ID=$(grep "^GCP_PROJECT_ID=" .env | cut -d '=' -f2 | tr -d '\r')
SERVICE_NAME=$(grep "^SERVICE_NAME=" .env | cut -d '=' -f2 | tr -d '\r')
REGION=$(grep "^REGION=" .env | cut -d '=' -f2 | tr -d '\r')
SECRET_NAME=$(grep "^SECRET_NAME=" .env | cut -d '=' -f2 | tr -d '\r')

if [[ -z "$PROJECT_ID" || -z "$SERVICE_NAME" || -z "$REGION" || -z "$SECRET_NAME" ]]; then
    echo "Error: Missing required config keys in .env (GCP_PROJECT_ID, SERVICE_NAME, REGION, SECRET_NAME)"
    exit 1
fi

IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME"



gcloud secrets create $SECRET_NAME --project=$PROJECT_ID --replication-policy="automatic" 2>/dev/null

gcloud secrets versions add $SECRET_NAME --project=$PROJECT_ID --data-file=.env

if [ $? -ne 0 ]; then
    echo "Failed to upload secret. Aborting."
    exit 1
fi

gcloud builds submit --project=$PROJECT_ID --tag $IMAGE_TAG .

if [ $? -ne 0 ]; then
    echo "Build failed! Aborting."
    exit 1
fi


gcloud run deploy $SERVICE_NAME \
  --project=$PROJECT_ID \
  --image $IMAGE_TAG \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets="/app/.env=$SECRET_NAME:latest"
