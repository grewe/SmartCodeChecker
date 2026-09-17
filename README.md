# Smart Code Checker

Smart Code Checker is a small web app that lets users paste or upload code, sends it to a deployed Vertex AI Agent Engine for analysis, and displays the agent's recommendations.

### IMPORTANT: the SmartCodeChecker web app expects that you have already deployd to Vertex AI Enging (Google AI Platform) an agent base on steps 1-5&7 of the following [Google CodeLab](https://codelabs.developers.google.com/adk-code-reviewer-assistant/instructions#0)


#### Interface (with partial output from checking code)
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

```bash
cp backend/.env.example backend/.env          # macOS / Linux
Copy-Item backend\.env.example backend\.env  # Windows PowerShell
```

Then edit `backend/.env` so the values are correct (see the highlighted guide below).

> [!IMPORTANT]
> ## Filling in `backend/.env` (read this carefully)
>
> Open **`backend/.env`** (not `.env.example`) and replace every placeholder with your real values. The Flask app loads this file on startup; it **must** live at `backend/.env`.

> [!TIP]
> **Finished file example** — use *your* values, not these samples:
>
> ```
> AGENT_RESOURCE_NAME=projects/my-gcp-project/locations/us-central1/reasoningEngines/7917477678498709504
> GOOGLE_CLOUD_PROJECT=my-gcp-project
> GOOGLE_CLOUD_LOCATION=us-central1
> PORT=8080
> ```

> [!WARNING]
> **Common mistakes**
>
> - No spaces around `=`
> - Do not leave placeholder text (`YOURGOOGLE_CLOUDPROJECT`, `XXXXXXXX`, etc.)
> - On the location line, do **not** keep the example comment. Use only the region, e.g. `us-central1` — not `YOURLOCATION  (like us-central1)`

> [!NOTE]
> ### 1. `GOOGLE_CLOUD_PROJECT` — your GCP Project ID
>
> This is the **Project ID** (a short string like `cs-class-fall-2026`), **not** the project display name. Use the **same project** you used for CodeLab steps 1–5 and 7.
>
> **How to get it (pick one):**
>
> 1. Open [Google Cloud Console](https://console.cloud.google.com).
> 2. At the **top of the page**, click the **project picker** (the project name next to “Google Cloud”).
> 3. In the list, find your project. Copy the value in the **ID** column (not the Name column).
> 4. Paste it into `.env` as: `GOOGLE_CLOUD_PROJECT=your-project-id`
>
> **Other ways:**
>
> - Console **Dashboard** → **Project info** card → copy **Project ID**.
> - In a terminal: `gcloud config get-value project`

> [!NOTE]
> ### 2. `GOOGLE_CLOUD_LOCATION` — the region of your deployed agent
>
> This is a region name such as `us-central1`. It must match the `locations/...` part of `AGENT_RESOURCE_NAME`.
>
> **How to get it:**
>
> 1. If you followed the CodeLab defaults, use **`us-central1`**.
> 2. If you chose a different region when you deployed the agent, use that same region.
> 3. Confirm by looking at your `AGENT_RESOURCE_NAME`. Example: if the name contains `locations/us-central1`, then set:
>    `GOOGLE_CLOUD_LOCATION=us-central1`
>
> Do **not** write `YOURLOCATION  (like us-central1)`. The value must be only the region, with no extra text.

> [!NOTE]
> ### 3. `AGENT_RESOURCE_NAME` — full path of the deployed Vertex AI agent
>
> This is the long resource path, **not** just the numeric engine ID. Shape:
>
> `projects/<PROJECT_ID_OR_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>`
>
> **How to get it (best method):**
>
> 1. Go back to the terminal where you ran CodeLab **Module 7** (`./deploy.sh agent-engine` or `adk deploy agent_engine`).
> 2. Find the success message. It looks like:
>
>    ```
>    ✅ Deployment successful!
>       Agent Engine ID: 7917477678498709504
>       Resource Name: projects/123456789/locations/us-central1/reasoningEngines/7917477678498709504
>    ```
>
> 3. Copy the **Resource Name** line **exactly** (the whole `projects/.../reasoningEngines/...` string).
> 4. Paste it into `.env` as: `AGENT_RESOURCE_NAME=projects/.../reasoningEngines/...`
>
> **If you lost that terminal output:**
>
> 1. Open [Google Cloud Console](https://console.cloud.google.com).
> 2. Make sure the correct project is selected at the top.
> 3. Go to **Vertex AI** → **Agent Engine** (sometimes listed as **Reasoning Engines**).
> 4. Open the agent you deployed in the CodeLab.
> 5. Copy its **resource name** (the full `projects/.../reasoningEngines/...` path).
>
> **Or from a terminal:**
>
> ```bash
> gcloud ai reasoning-engines list --project=YOUR_PROJECT_ID --region=us-central1
> ```
>
> Copy the full resource name from that list.
>
> Extra notes:
>
> - The first segment may be a project **ID** (`my-gcp-project`) or a numeric **project number** (`123456789`). Both are valid; prefer the exact string from deploy output.
> - The CodeLab may mention `AGENT_ENGINE_ID` (only the last number). This app needs the **full** `AGENT_RESOURCE_NAME`, not just the ID.
> - Do **not** invent the `XXXXXXXX` part from `.env.example`.

> [!NOTE]
> ### 4. `PORT` — local port for this web app
>
> This is only for running Smart Code Checker on your computer. It is **not** from Google Cloud.
>
> **How to set it:**
>
> 1. Leave it as **`8080`** unless that port is already in use.
> 2. In `.env` it should look like: `PORT=8080`
> 3. After you start the app (step 4 below), open `http://localhost:8080` in your browser.

> [!CAUTION]
> **Authenticate — `.env` does not log you in**
>
> Before running the app, run this once on your machine:
>
> ```bash
> gcloud auth application-default login
> ```
>
> Use the Google account that has access to that GCP project. Without this, the agent client often fails even if `.env` is correct.

> [!TIP]
> **Quick check before step 4**
>
> 1. All four lines have real values (no placeholders)
> 2. Project ID in `GOOGLE_CLOUD_PROJECT` matches the project in `AGENT_RESOURCE_NAME`
> 3. Region in `GOOGLE_CLOUD_LOCATION` matches `locations/...` in the resource name
> 4. You ran `gcloud auth application-default login`
>
> If those are wrong, the app may still start, but `/analyze` returns **Agent not initialized** and the terminal shows a missing-env or auth/Vertex error.

4. Run the Flask app for development:

```bash
cd backend
FLASK_ENV=development python app.py   OR python app.py
```

The app serves the frontend statically; open `http://localhost:8080`.

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
