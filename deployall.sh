#!/bin/bash

set -e  # Exit on error

echo "======================================"
echo "🚀 DEPLOY PARISH SECRETARY SYSTEM"
echo "======================================"
echo ""

# 1. Deploy main email processing function
echo "📧 [1/2] Deploying main email processing function..."
gcloud functions deploy process-parish-emails-pubsub \
  --gen2 \
  --runtime=python311 \
  --region=europe-west1 \
  --entry-point=process_gmail_notification \
  --trigger-topic=gmail-notifications \
  --memory=512Mi \
  --timeout=300s \
  --env-vars-file=.env.yaml \
  --service-account=parish-secretary-sa@ordinal-gear-472720-h5.iam.gserviceaccount.com

echo "✅ Main function deployed!"
echo ""

# 2. Deploy scheduled event recap function
echo "🎫 [2/2] Deploying scheduled event recap function..."
gcloud functions deploy daily-event-recap \
  --gen2 \
  --runtime=python311 \
  --region=europe-west1 \
  --entry-point=daily_event_recap \
  --trigger-topic=daily-recap \
  --memory=256Mi \
  --timeout=180s \
  --env-vars-file=.env.yaml \
  --service-account=parish-secretary-sa@ordinal-gear-472720-h5.iam.gserviceaccount.com

echo "✅ Scheduled function deployed!"
echo ""

# 3. Update Cloud Scheduler (if needed)
echo "📅 Updating Cloud Scheduler..."

# Elimina job esistente (se c'è)
gcloud scheduler jobs delete daily-event-recap-job --location=europe-west1 --quiet 2>/dev/null || true

# Crea nuovo job
gcloud scheduler jobs create pubsub daily-event-recap-job \
  --location=europe-west1 \
  --schedule="0 10 * * *" \
  --topic=daily-recap \
  --message-body='{"task":"daily_recap"}' \
  --time-zone="Europe/Rome" \
  --description="Invia recap eventi del giorno successivo alle 10:00"

echo "✅ Cloud Scheduler configured!"
echo ""
echo "======================================"
echo "✅ DEPLOY COMPLETED!"
echo "======================================"
echo ""
echo "📊 Summary:"
echo "   - Main function: process-parish-emails-pubsub"
echo "   - Scheduled function: daily-event-recap"
echo "   - Scheduler job: daily-event-recap-job (10:00 AM daily)"
echo ""
echo "🧪 Test scheduled job manually:"
echo "   gcloud scheduler jobs run daily-event-recap-job --location=europe-west1"
echo ""
