# Smart Code Checker

Smart Code Checker is a small web app that lets users paste or upload code, sends it to a deployed Vertex AI Agent Engine for analysis, and displays the agent's recommendations.

### IMPORTANT: the SmartCodeChecker web app expects that you have already deployd to Vertex AI Enging (Google AI Platform) an agent base on steps 1-5&7 of the following [Google CodeLab](https://codelabs.developers.google.com/adk-code-reviewer-assistant/instructions#0)


### Interface (with partial output from checking code)
<img width="1358" height="1400" alt="image" src="https://github.com/user-attachments/assets/c6b1fcbe-e94c-46e3-9421-d81813d52479" />




## Project layout:

- frontend/
  - index.html
  - style.css
  - script.js
- backend/
  - app.py
  - requirements.txt
  - Dockerfile
  - .env.example

## Local development

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows PowerShell
```

2. Install requirements:

```bash
pip install -r backend/requirements.txt
```

3. Copy `.env.example` to `.env` and update if necessary:

```
cp backend/.env.example backend/.env
# then edit backend/.env to ensure values are correct
```

4. Run the Flask app for development:

```bash
cd backend
FLASK_ENV=development python app.py   OR python app.py
```

The app serves the frontend statically; open `http://localhost:8080`.

## Environment variables

- `AGENT_RESOURCE_NAME` - resource name of deployed Vertex AI Agent Engine (provided in `.env.example`).
- `GOOGLE_CLOUD_PROJECT` - GCP project id.
- `GOOGLE_CLOUD_LOCATION` - region (e.g. `us-central1`).
- `PORT` - port to run the app on (defaults to 8080).

## Deploy to Cloud Run

Build and push the container, then deploy with `gcloud` (example):

```bash
# build and push (Cloud Build or Docker)
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/smart-code-checker

# deploy to Cloud Run
gcloud run deploy smart-code-checker \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/smart-code-checker \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

Ensure the Cloud Run service account has permissions to call Vertex AI and that the Cloud Run runtime has access to required APIs.

## Notes
- The backend uses `vertexai.agent_engines` if available. Depending on the installed `vertexai` package version, the client API may differ. If the app cannot initialize the agent client, confirm you have a compatible `vertexai` SDK and your environment is authenticated (e.g., `gcloud auth application-default login` or service account on Cloud Run).
