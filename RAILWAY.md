# Railway Deployment Guide

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub repository with this code
3. Twilio account with phone number
4. OpenAI API key
5. ElevenLabs API key
6. Salesforce credentials (optional)

## Deployment Steps

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/qualifybot.git
git push -u origin main
```

### 2. Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `qualifybot` repository
5. Railway will automatically detect the Dockerfile and start building

### 3. Add Services

Railway will deploy the main service automatically. You need to add:

#### PostgreSQL Database

1. Click "New" → "Database" → "Add PostgreSQL"
2. Railway will create a PostgreSQL database
3. The `DATABASE_URL` environment variable will be automatically set

#### Redis Database (with RediSearch)

1. Click "New" → "Database" → "Add Redis"
2. **Important**: Railway's default Redis doesn't include RediSearch
3. You have two options:
   - **Option A**: Use Railway's Redis and fall back to memory checkpointer (not recommended for production)
   - **Option B**: Use Upstash Redis with RediSearch module (recommended)
     - Go to https://upstash.com
     - Create a Redis database with RediSearch enabled
     - Copy the Redis URL
     - Add it as `REDIS_URL` environment variable in Railway

### 4. Configure Environment Variables

In Railway, go to your service → Variables tab and add:

#### Required Variables

```bash
# Environment
ENVIRONMENT=production
DEBUG=false

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_URL=https://your-railway-domain.railway.app/api/v1/twilio/webhook

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ElevenLabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Salesforce (optional)
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
SALESFORCE_DOMAIN=login  # or "test" for sandbox

# Sentry (optional)
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=production
```

#### Auto-configured by Railway

Railway automatically sets these when you add services:

- `DATABASE_URL` - Automatically set when you add PostgreSQL service
  - Format: `postgresql://user:password@host:port/dbname`
  - The code automatically converts it to `postgresql+asyncpg://` for SQLAlchemy
- `REDIS_URL` - Automatically set when you add Redis service (if using Railway's Redis)

  - Format: `redis://host:port` or `rediss://host:port` (for SSL)
  - **Important**: Railway's default Redis and Upstash Redis **do NOT support RediSearch**
  - If you see `FT._LIST` errors, you need Redis Stack or Redis Cloud with RediSearch
  - Or the app will fall back to memory checkpointer (not for production)

- `PORT` - Automatically set by Railway (don't set this manually)

#### You DON'T need to set these manually:

- ❌ `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- ❌ `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`

The code will automatically use `DATABASE_URL` and `REDIS_URL` if they're provided by Railway.

### 5. Get Your Railway Domain

1. Go to your service → Settings → Generate Domain
2. Railway will provide a domain like `your-app.up.railway.app`
3. Update `TWILIO_WEBHOOK_URL` to: `https://your-app.up.railway.app/api/v1/twilio/webhook`

### 6. Configure Twilio Webhook

1. Go to Twilio Console → Phone Numbers → Manage → Active Numbers
2. Click on your phone number
3. Under "Voice & Fax", set:
   - **A CALL COMES IN**: `https://your-app.up.railway.app/api/v1/twilio/webhook`
   - **STATUS CALLBACK URL**: `https://your-app.up.railway.app/api/v1/twilio/status`
4. Save

### 7. Deploy

Railway will automatically deploy when you push to GitHub. You can also:

- Click "Deploy" in Railway dashboard
- Or trigger a manual deploy

### 8. Verify Deployment

1. Check logs in Railway dashboard
2. Test health endpoint: `https://your-app.up.railway.app/health`
3. Make a test call to your Twilio number

## Troubleshooting

### Redis Search Error

If you see `unknown command 'FT._LIST'`:

- Railway's default Redis and Upstash Redis **do NOT support RediSearch**
- Options:
  1. Deploy Redis Stack in Railway (template available)
  2. Use Redis Cloud (paid service with RediSearch)
  3. Fall back to memory checkpointer (development only, not for production)

### Port Issues

Railway sets `PORT` automatically. The Dockerfile handles this.

### Database Connection

Railway provides `DATABASE_URL` automatically. The code handles the `postgresql+asyncpg://` driver conversion.

### Webhook URL

Make sure `TWILIO_WEBHOOK_URL` matches your Railway domain exactly.

## Monitoring

- Check Railway logs for errors
- Use Railway's metrics dashboard
- Set up Sentry for error tracking (optional)

## Production Checklist

- [ ] Environment variables set
- [ ] PostgreSQL database added
- [ ] Redis with RediSearch configured (or memory fallback)
- [ ] Twilio webhook URL configured
- [ ] Health check passing
- [ ] Test call successful
- [ ] Sentry configured (optional)
- [ ] Custom domain configured (optional)
