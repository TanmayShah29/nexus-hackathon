# NEXUS OS — Google Cloud Migration Guide

This guide outlines the steps to migrate NEXUS OS from a local development environment to a production-grade deployment on **Google Cloud Platform (GCP)**.

---

## 1. Architecture Summary

| Component | Local Implementation | Cloud Implementation |
|-----------|----------------------|----------------------|
| **Backend** | `run.sh` (Uvicorn) | **Google Cloud Run** (Docker) |
| **Frontend** | `localhost:8000` | **Firebase Hosting** |
| **Memory** | Supabase (pgvector) | **Supabase** (or AlloyDB AI) |
| **LLM** | Gemini API Key | **Vertex AI API** |

---

## 2. Backend Deployment (Cloud Run)

The project includes a `nexus/Dockerfile` and `nexus/cloudbuild.yaml` optimized for Cloud Run.

### Step 1: Build and Push to Artifact Registry
```bash
gcloud builds submit --config nexus/cloudbuild.yaml .
```

### Step 2: Deploy to Cloud Run
```bash
gcloud run deploy nexus-api \
  --image gcr.io/[PROJECT_ID]/nexus-api \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars="DEMO_MODE=false,GOOGLE_API_KEY=[YOUR_KEY],SUPABASE_URL=[URL],SUPABASE_ANON_KEY=[KEY]"
```
*Note: Save the generated **Service URL** (e.g., `https://nexus-api-xyz.a.run.app`).*

---

## 3. Frontend Deployment (Firebase)

### Step 1: Update API Endpoint
The `frontend/nexus-core.js` is already configured to detect production environments. However, you can explicitly set your backend URL by adding this script tag to your HTML files (before `nexus-core.js`):
```html
<script>
  window.NEXUS_CONFIG = {
    API_BASE: 'https://nexus-api-xyz.a.run.app'
  };
</script>
```

### Step 2: Deploy to Firebase Hosting
```bash
firebase init hosting
# Select 'frontend' as your public directory
firebase deploy
```

---

## 4. Advanced: AlloyDB AI Migration (Optional)

To move from Supabase to **AlloyDB AI** for Track 3 compliance:

1. **Create Instance:** Create an AlloyDB cluster with the "AI Index" enabled in your GCP project.
2. **VPC Connector:** Set up a Serverless VPC Access Connector to allow Cloud Run to communicate with AlloyDB's private IP.
3. **Update Memory Logic:** Modify `nexus/memory/supabase_client.py` (or create `alloydb_client.py`) to use `psycopg2` with the `pgvector` extension.

---

## 5. Security Checklist
- [ ] Set `DEMO_MODE=false` in Cloud Run environment variables.
- [ ] Set `ALLOWED_ORIGINS` to your Firebase Hosting URL in `nexus/cloudbuild.yaml`.
- [ ] Enable **Vertex AI API** in the Google Cloud Console for enterprise-grade LLM access.
