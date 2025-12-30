# Railway Troubleshooting Guide

## Redis Connection Issues

### Issue: Variables not expanding in REDIS_URL

**Symptom**: `REDIS_URL` contains literal `${REDIS_PASSWORD}` instead of the actual password.

**Solution**:
1. **Remove quotes** from `REDIS_URL`:
   - ❌ Wrong: `REDIS_URL="redis://default:${REDIS_PASSWORD}@..."`
   - ✅ Correct: `REDIS_URL=redis://default:${REDIS_PASSWORD}@...`

2. **Check Railway variable names**:
   - Go to your API service → Variables tab
   - Look for variables from Redis Stack service
   - Railway might use different names:
     - `REDISHOST` / `REDIS_HOST`
     - `REDISPORT` / `REDIS_PORT`
     - `REDISPASSWORD` / `REDIS_PASSWORD`

3. **If variables still don't expand**, use actual values:
   - Go to Redis Stack service → Variables tab
   - Copy the actual password and hostname
   - Set: `REDIS_URL=redis://default:actual_password@actual_hostname:6379`

### Issue: Connection refused to Redis

**Check**:
1. Redis Stack service is running (green status in Railway)
2. Services are in the same Railway project
3. Using correct hostname:
   - For Railway internal network: `service-name.railway.internal`
   - Or use `RAILWAY_PRIVATE_DOMAIN` if available
4. Port is correct (usually 6379)

### Issue: Authentication failed

**Solutions**:
1. Check password matches between services
2. Some Redis Stack configs don't require password - try:
   ```
   REDIS_URL=redis://${REDIS_HOST}:6379
   ```
3. Verify `REDIS_PASSWORD` is set in Redis Stack service

## Database Connection Issues

### Issue: DATABASE_URL format

Railway auto-generates `DATABASE_URL` correctly. Your format looks good:
```
DATABASE_URL=postgresql://postgres:password@postgres.railway.internal:5432/railway
```

**Note**: The code automatically converts `postgresql://` to `postgresql+asyncpg://` for SQLAlchemy.

## Verifying Connections

### Check Railway Logs

Look for these messages in your API service logs:

**Success**:
```
Database initialized ✅
Redis checkpointer initialized ✅
```

**Issues**:
```
Failed to initialize database ❌
Using memory checkpointer ⚠️ (Redis connection failed)
```

### Test Endpoints

1. **Basic health**: `https://your-app.railway.app/health`
   - Should return: `{"status": "healthy"}`

2. **Readiness check**: `https://your-app.railway.app/health/ready`
   - Should return:
     ```json
     {
       "status": "ready",
       "database": "connected",
       "redis": "connected"
     }
     ```

## Common Variable Issues

### Railway Variable Expansion

Railway expands variables like `${VAR_NAME}` at runtime, but:
- ✅ Works: `REDIS_URL=redis://${REDIS_PASSWORD}@...`
- ❌ Doesn't work: `REDIS_URL="${REDIS_PASSWORD}"` (quotes prevent expansion)
- ❌ Doesn't work: `REDIS_URL=redis://$REDIS_PASSWORD@...` (missing braces)

### Finding Actual Variable Names

1. Go to your service → Variables tab
2. Look for variables prefixed with service name
3. For Redis Stack, might be:
   - `REDIS_STACK_HOST`
   - `REDIS_STACK_PORT`
   - `REDIS_STACK_PASSWORD`
   - Or just `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

## Quick Fix Checklist

If Redis isn't connecting:

- [ ] Remove quotes from `REDIS_URL`
- [ ] Verify Redis Stack service is running
- [ ] Check variable names match Railway's actual variables
- [ ] Try using actual values instead of variables
- [ ] Check Railway logs for connection errors
- [ ] Verify services are in the same project
- [ ] Test `/health/ready` endpoint

