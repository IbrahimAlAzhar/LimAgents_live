# LimGen – Multi-Agent Paper Limitation Generator

Upload a research paper and 6 specialist AI agents analyze it for limitations across novelty, methodology, experiments, generalization, clarity, and ethics.

## Deploy Free on Render.com (10 minutes)

### Step 1: Upload to GitHub
1. Go to https://github.com → click **"New repository"** → name it `limgen`
2. Click **"uploading an existing file"** → drag all 4 files → click **"Commit changes"**

Your repo should look like:
```
limgen/
├── app.py
├── index.html
├── requirements.txt
└── Procfile
```

### Step 2: Deploy on Render
1. Go to https://render.com → sign up free with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your `limgen` repo
4. Fill in:
   - **Name:** `limgen`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. Click **"Create Web Service"**
6. Wait 2-3 minutes for build

### Step 3: Use it
- Visit your URL: `https://limgen.onrender.com`
- Enter your OpenAI API key
- Upload a PDF
- Get limitations

That's it. One URL, everything works.

## Notes

- **Free tier:** Backend sleeps after 15 min idle. First request after sleep takes ~30 sec.
- **Keep alive (optional):** Use https://cron-job.org to ping `https://limgen.onrender.com/api/health` every 14 min.
- **Cost:** $0 for hosting. Users provide their own OpenAI API key.
- **Upgrade:** Render Starter plan ($7/mo) removes the sleep limitation.
