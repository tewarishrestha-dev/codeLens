# Deploying CodeLens to Render (Free Live Web Link)

This guide walks you through deploying **CodeLens** to Render so you have a public, shareable web link accessible anywhere.

---

## Architecture Overview

```
                      ┌────────────────────────────────┐
                      │    Render Static Site (Free)   │
                      │     React + Vite Frontend      │
                      │  https://codelens.onrender.com │
                      └──────────────┬─────────────────┘
                                     │
                     REST API Calls  │ (VITE_API_URL)
                                     ▼
                      ┌────────────────────────────────┐
                      │   Render Web Service (Free)    │
                      │        FastAPI Backend         │
                      │ https://codelens-api.onrender  │
                      └──────────────┬─────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
         Cloud LLM (Gemini / Groq)           Local / Remote Ollama
         Configured via Settings/Env            (Default local)
```

---

## Option 1: Automatic Blueprint Deployment (Recommended — 2 Minutes)

We have included a `render.yaml` file in the root of the repository that configures both the backend and frontend automatically.

### Steps:

1. **Commit and push your changes to GitHub**:
   ```bash
   git add .
   git commit -m "Add multi-language analysis, cloud LLM support, and Render deployment"
   git push origin main
   ```

2. **Open Render Dashboard**:
   - Visit [https://dashboard.render.com](https://dashboard.render.com) and log in (or create a free account).

3. **Deploy via Blueprint**:
   - Click the **New +** button in the top right corner.
   - Select **Blueprint**.
   - Connect your GitHub repository: `tewarishrestha-dev/CodeLens`.
   - Render will detect `render.yaml` and show:
     - `codelens-backend` (Web Service, Python 3.12, Free)
     - `codelens-frontend` (Static Site, Free)
   - Click **Apply**.

4. **Add your AI API Key (Optional for Cloud AI)**:
   - In the Render Dashboard, open `codelens-backend` -> **Environment**.
   - Add one of the following free API keys:
     - `GEMINI_API_KEY`: Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey)
     - `GROQ_API_KEY`: Get a free key at [Groq Console](https://console.groq.com/keys)
   - *Note: Users can also enter their own API key directly in the web app under the **Settings** tab!*

5. **Done!**
   - Render will build and deploy both services.
   - Click your `codelens-frontend` URL (e.g. `https://codelens-frontend.onrender.com`) to open your live web application.

---

## Option 2: Manual Deployment on Render

If you prefer to configure each service manually in Render:

### Step 1: Deploy Backend Web Service

1. On the Render Dashboard, click **New +** -> **Web Service**.
2. Connect `tewarishrestha-dev/CodeLens`.
3. Configure the settings:
   - **Name**: `codelens-backend`
   - **Region**: Oregon (or closest to you)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.12.4`
   - `CODELENS_DATA_DIR`: `/tmp/codelens_data`
   - `CODELENS_CORS_ORIGINS`: `*`
   - *(Optional)* `GEMINI_API_KEY` or `GROQ_API_KEY` for instant cloud AI.
5. Click **Create Web Service**. Note down the URL (e.g. `https://codelens-backend-xxxx.onrender.com`).

### Step 2: Deploy Frontend Static Site

1. On the Render Dashboard, click **New +** -> **Static Site**.
2. Connect `tewarishrestha-dev/CodeLens`.
3. Configure the settings:
   - **Name**: `codelens-frontend`
   - **Branch**: `main`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`
4. In **Environment Variables**, add:
   - `VITE_API_URL`: Your backend URL from Step 1 (e.g. `https://codelens-backend-xxxx.onrender.com`)
5. In **Redirects / Rewrites**:
   - **Type**: `Rewrite`
   - **Source**: `/*`
   - **Destination**: `/index.html`
6. Click **Create Static Site**.

---

## Verifying the Deployment

1. Visit your frontend URL.
2. Under **Command Center**:
   - Try the **C — Quick Demo** buttons (e.g. `Pallets / Click` or `Express / Router`) to verify repository ingestion, multi-language AST parsing, and dependency mapping.
   - Or drop a `.zip` of any project.
3. In **Code Explorer**:
   - Inspect files across Python, JavaScript, and TypeScript.
   - Use the **Copy Code** button and test the **⬇ Export Report** feature.
   - Switch to **Graph Studio** to explore dependency graphs and execution flows.
4. In **Ask CodeLens**:
   - Ask questions about the mapped codebase.
   - If using cloud hosting, enter a free Gemini or Groq key in **Settings** to get instant answers.
