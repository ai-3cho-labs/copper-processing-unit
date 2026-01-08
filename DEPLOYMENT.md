# $COPPER Cloud Deployment Guide

This guide covers deploying the $COPPER backend and frontend to cloud platforms.

## Architecture

| Component | Service | Purpose |
|-----------|---------|---------|
| Frontend | Cloudflare Pages | Next.js app with global CDN |
| Backend API | Koyeb | FastAPI REST API + WebSocket |
| Celery Worker | Koyeb | Background task processing |
| Celery Beat | Koyeb | Periodic task scheduling |
| Redis | Upstash | Task queue + caching |
| Database | Neon | PostgreSQL (already set up) |

---

## 1. Set Up Upstash Redis

1. Go to [Upstash Console](https://console.upstash.com)
2. Create a new Redis database:
   - Name: `copper-redis`
   - Region: Choose closest to your users
   - TLS: Enabled (required for production)
3. Copy the connection details:
   - `REDIS_URL`: Use the `rediss://` URL (with TLS)
   - `UPSTASH_REDIS_REST_URL`: For REST API access
   - `UPSTASH_REDIS_REST_TOKEN`: REST API token

---

## 2. Deploy Backend to Koyeb

### Option A: Via Koyeb Dashboard (Recommended for first deploy)

1. Go to [Koyeb Console](https://app.koyeb.com)
2. Click "Create App"
3. Select "GitHub" and connect your repository

**Service 1: API**
- Name: `copper-api`
- Branch: `main`
- Dockerfile path: `backend/Dockerfile`
- Port: `8000`
- Instance: Nano ($5.42/mo)
- Scaling: 1-2 instances
- Health check: `GET /api/health`

**Service 2: Worker**
- Name: `copper-worker`
- Dockerfile path: `backend/Dockerfile.worker`
- Instance: Nano
- Scaling: 1 instance
- No port needed

**Service 3: Scheduler**
- Name: `copper-scheduler`
- Dockerfile path: `backend/Dockerfile.beat`
- Instance: Nano
- Scaling: 1 instance
- No port needed

### Environment Variables (set as secrets in Koyeb)

```
ENVIRONMENT=production
DATABASE_URL=<your-neon-url>
REDIS_URL=<your-upstash-url>
HELIUS_API_KEY=<your-helius-key>
COPPER_TOKEN_MINT=<your-token-mint>
CORS_ORIGINS=https://your-project.pages.dev
CREATOR_WALLET_PRIVATE_KEY=<base58-key>
BUYBACK_WALLET_PRIVATE_KEY=<base58-key>
AIRDROP_POOL_PRIVATE_KEY=<base58-key>
TEAM_WALLET_PUBLIC_KEY=<public-key>
```

### Option B: Via CLI

```bash
# Install Koyeb CLI
brew install koyeb/tap/koyeb

# Login
koyeb login

# Deploy using config
cd backend
koyeb app init copper-backend --config koyeb.yaml
```

---

## 3. Deploy Frontend to Cloudflare Pages

### Option A: Via Cloudflare Dashboard (Recommended)

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) > Pages
2. Click "Create a project" > "Connect to Git"
3. Select your repository
4. Configure build settings:
   - Framework preset: `Next.js`
   - Build command: `npm run build && npm run pages:build`
   - Build output directory: `.vercel/output/static`
   - Root directory: `frontend`
5. Add environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://copper-api.koyeb.app
   NEXT_PUBLIC_WS_URL=wss://copper-api.koyeb.app/ws
   NEXT_PUBLIC_SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
   NEXT_PUBLIC_COPPER_TOKEN_MINT=your-token-mint
   CF_PAGES=1
   NODE_VERSION=18
   ```
6. Deploy

### Option B: Via CLI

```bash
cd frontend

# Install dependencies
npm install

# Build for Cloudflare Pages
npm run build
npm run pages:build

# Deploy (first time - creates project)
npm run pages:deploy

# Or use wrangler directly
wrangler pages deploy .vercel/output/static --project-name=copper-frontend
```

---

## 4. Configure Helius Webhook

After backend is deployed, set up the Helius webhook for sell detection:

1. Go to [Helius Dashboard](https://dev.helius.xyz)
2. Create a webhook:
   - URL: `https://copper-api.koyeb.app/api/webhook/helius`
   - Transaction types: `SWAP`, `TOKEN_TRANSFER`
   - Account addresses: Your token mint address
3. Copy the webhook secret to your backend environment variables

---

## 5. DNS & Custom Domain (Optional)

### Backend (Koyeb)
1. In Koyeb, go to your service settings
2. Add custom domain: `api.copper.app`
3. Add CNAME record in Cloudflare DNS

### Frontend (Cloudflare Pages)
1. In Cloudflare Pages, go to Custom Domains
2. Add: `copper.app` and `www.copper.app`
3. Cloudflare handles DNS automatically

---

## Verification Checklist

After deployment, verify everything works:

- [ ] Backend health: `curl https://copper-api.koyeb.app/api/health`
- [ ] Frontend loads: Visit your Pages URL
- [ ] WebSocket connects: Check browser console
- [ ] Wallet connection works
- [ ] API endpoints respond
- [ ] Celery tasks run (check Koyeb logs)

---

## Monitoring & Logs

**Koyeb:**
- Real-time logs in dashboard
- Automatic restart on failure
- CPU/Memory metrics

**Cloudflare:**
- Pages Analytics for traffic
- Real User Monitoring available

**Optional - Sentry:**
Add `SENTRY_DSN` to backend for error tracking

---

## Cost Estimate

| Service | Tier | Cost/Month |
|---------|------|------------|
| Koyeb API | Nano | ~$5 |
| Koyeb Worker | Nano | ~$5 |
| Koyeb Scheduler | Nano | ~$5 |
| Upstash Redis | Free tier | $0 |
| Cloudflare Pages | Free tier | $0 |
| Neon DB | Free tier | $0 |
| **Total** | | **~$15/mo** |

---

## Troubleshooting

**WebSocket not connecting:**
- Ensure CORS_ORIGINS includes your frontend URL
- Check that wss:// is used (not ws://) in production

**Celery tasks not running:**
- Verify REDIS_URL is correct
- Check worker logs in Koyeb

**Build fails on Cloudflare:**
- Ensure NODE_VERSION=18 is set
- Check that CF_PAGES=1 is set for standalone output
