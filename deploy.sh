#!/bin/bash
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