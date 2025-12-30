# Railway Environment Variables Guide

## Quick Setup

After creating PostgreSQL and Redis services in Railway, you only need to set these environment variables:

### Required Variables

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

## Auto-Configured by Railway

Railway automatically sets these when you add services - **DO NOT set them manually**:

✅ `DATABASE_URL` - Set automatically when you add PostgreSQL service
✅ `REDIS_URL` - Set automatically when you add Redis service  
✅ `PORT` - Set automatically by Railway

## What NOT to Set

❌ **Don't set these** - Railway handles them automatically:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `REDIS_PASSWORD`

The application code automatically detects and uses `DATABASE_URL` and `REDIS_URL` when they're available.

## Redis with RediSearch

**Important**: Railway's **standard Redis service** doesn't include RediSearch module, which is required by `langgraph-checkpoint-redis`.

### Option 1: Use Railway's Redis Stack Template (Recommended)

Railway offers a **Redis Stack** template that includes RediSearch:

1. In Railway, click "New" → "Template"
2. Search for "Redis Stack" 
3. Deploy the Redis Stack template
4. Railway automatically sets `REDIS_URL` with RediSearch enabled
5. This includes RediSearch, RedisJSON, RedisTimeSeries, and RedisBloom modules

**If you already added standard Redis:**
- Remove the standard Redis service
- Add Redis Stack template instead
- Railway will automatically update `REDIS_URL`

### Option 2: Use Upstash Redis

1. Go to https://upstash.com
2. Create a Redis database with **RediSearch** enabled
3. Copy the Redis URL
4. In Railway, add environment variable:
   ```
   REDIS_URL=rediss://your-upstash-redis-url
   ```
5. This will override Railway's default Redis URL

### Option 3: Use Memory Checkpointer (Not for Production)

If you don't set `REDIS_URL` or Railway's Redis doesn't have RediSearch, the app will fall back to memory checkpointer. This works for testing but **not recommended for production** as state is lost on restart.

## Verification

After setting environment variables:

1. Check Railway logs for:
   - `Database initialized` ✅
   - `Redis checkpointer initialized` ✅ (or `Using memory checkpointer` ⚠️)

2. Test health endpoints:
   - `/health` - Should return `{"status": "healthy"}`
   - `/health/ready` - Shows database and Redis connection status

3. Check `/health/ready` response:
   ```json
   {
     "status": "ready",
     "database": "connected",
     "redis": "connected"
   }
   ```

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` is set (check Railway service → Variables)
- Check logs for connection errors
- Ensure PostgreSQL service is running

### Redis Connection Issues

- Verify `REDIS_URL` is set (check Railway service → Variables)
- If using Railway's Redis and seeing `FT._LIST` errors, switch to Upstash Redis with RediSearch
- Check logs for Redis connection errors

### Missing Environment Variables

- All required variables must be set before the app can handle calls
- Check Railway logs for validation errors
- Use `/health/ready` to see which services are connected

