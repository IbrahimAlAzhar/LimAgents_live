# LimGen – Free Deployment Guide (Total Cost: $0)

## Architecture
```
User's Browser
     │
     ├──(frontend)──→  Vercel / Netlify  (free static hosting)
     │                   serves index.html
     │
     └──(API calls)──→  Render.com  (free Python backend)
                          runs app.py → calls OpenAI API
```

---

## Step 1: Push code to GitHub (5 min)

Both Render and Vercel/Netlify deploy from GitHub.

1. Create a GitHub account (if you don't have one): https://github.com
2. Create a **new repository** called `limgen`
3. Upload the project files with this structure:

```
limgen/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── Procfile
└── frontend/
    └── index.html
```

You can do this via GitHub's web UI (drag & drop) or via git:
```bash
cd limgen-free
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/limgen.git
git push -u origin main
```

---

## Step 2: Deploy Backend on Render (5 min)

1. Go to https://render.com and sign up (free, use GitHub login)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo (`limgen`)
4. Configure:
   - **Name:** `limgen-backend`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. Click **"Create Web Service"**
6. Wait 2-3 minutes for it to build
7. You'll get a URL like: `https://limgen-backend.onrender.com`
8. Test it: visit `https://limgen-backend.onrender.com/api/health`
   - Should show: `{"status":"ok"}`

---

## Step 3: Deploy Frontend on Vercel (3 min)

### Option A: Vercel (recommended)
1. Go to https://vercel.com and sign up (free, use GitHub login)
2. Click **"Add New Project"** → Import your `limgen` repo
3. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** `Other`
4. Click **"Deploy"**
5. You'll get a URL like: `https://limgen.vercel.app`

### Option B: Netlify (alternative)
1. Go to https://netlify.com and sign up
2. Drag & drop the `frontend/` folder onto the Netlify dashboard
3. Done — you get a URL like: `https://limgen.netlify.app`

---

## Step 4: Connect Frontend to Backend (1 min)

Open `frontend/index.html` and find this line near the top of the `<script>`:

```javascript
const API_URL = '';
```

Change it to your Render URL:

```javascript
const API_URL = 'https://limgen-backend.onrender.com';
```

Commit and push — Vercel/Netlify will auto-redeploy.

---

## Done! 🎉

Your site is live at your Vercel/Netlify URL. Share it with anyone.

---

## Important Notes

### Free tier limits
| Service | Free Limits | What happens |
|---------|------------|--------------|
| Render  | 750 hrs/month, sleeps after 15min idle | First request after sleep takes ~30sec to wake up |
| Vercel  | 100GB bandwidth/month | More than enough |
| Netlify | 100GB bandwidth/month | More than enough |

### The "cold start" issue
On Render's free tier, the backend sleeps after 15 minutes of no requests.
The first user after a sleep period waits ~30 seconds for it to wake up.

**Fix (optional):** Use a free cron service like https://cron-job.org to ping
`https://limgen-backend.onrender.com/api/health` every 14 minutes.
This keeps it awake during business hours.

### Security
- OpenAI API keys are sent from the user's browser → your Render backend → OpenAI
- Keys are never stored or logged
- For production, you should add HTTPS (both Vercel and Render provide it automatically)

### Custom domain (optional, free)
- Get a free domain from https://freedns.afraid.org or buy one (~$10/year)
- Add it in Vercel dashboard → Settings → Domains
- Both Vercel and Render provide free SSL certificates automatically

---

## Upgrading Later

If your app gets popular and the free tier isn't enough:

| Upgrade | Cost | Benefit |
|---------|------|---------|
| Render Starter | $7/mo | No sleep, faster, more RAM |
| Your own VPS | $5-6/mo | Full control, use deploy.sh |
| Railway.app | $5/mo | Easy alternative to Render |
