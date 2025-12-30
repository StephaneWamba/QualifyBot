# Setting Up Redis Stack in Railway

## After Deploying Redis Stack Service

When you deploy Redis Stack as a separate service in Railway, you need to connect it to your main API service.

## Option 1: Use Railway Service References (Recommended)

Railway automatically provides environment variables for connected services.

### Steps:

1. **In your main API service** (not the Redis Stack service):
   - Go to your API service → **Variables** tab
   - Railway should automatically provide these variables:
     - `REDIS_HOST` - The Redis Stack service hostname
     - `REDIS_PORT` - The Redis port (usually 6379)
     - `REDIS_PASSWORD` - The Redis password (if set)
     - `REDIS_URL` - The full connection URL (if Railway generates it)

2. **If Railway doesn't auto-generate `REDIS_URL`**, construct it manually:
   ```
   redis://default:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}
   ```
   
   Or if you have the private domain:
   ```
   redis://default:${REDIS_PASSWORD}@${RAILWAY_PRIVATE_DOMAIN}:6379
   ```

3. **Check available variables**:
   - In your API service → Variables tab
   - Look for variables prefixed with the Redis Stack service name
   - Railway often names them like: `REDIS_STACK_HOST`, `REDIS_STACK_PORT`, etc.

## Option 2: Manual Connection String

If you have the connection string from the Redis Stack service:

1. **Get the connection details** from Redis Stack service:
   - Go to Redis Stack service → **Variables** tab
   - Note the values (they might be shown as `${{ REDIS_PASSWORD }}` etc.)

2. **In your API service** → Variables tab:
   - Add: `REDIS_URL=redis://default:YOUR_ACTUAL_PASSWORD@YOUR_ACTUAL_HOST:6379`
   - Replace placeholders with actual values

3. **To get actual values**:
   - Click on the Redis Stack service
   - Check the **Connect** or **Variables** section
   - Railway shows the actual values there

## Option 3: Use Railway Private Network

Railway services in the same project can communicate via private network:

1. **In your API service** → Variables:
   - Set: `REDIS_URL=redis://default:${REDIS_PASSWORD}@${REDIS_HOST}:6379`
   - Railway will resolve `${REDIS_HOST}` and `${REDIS_PASSWORD}` automatically

2. **Or use the private domain**:
   - Set: `REDIS_URL=redis://default:${REDIS_PASSWORD}@${RAILWAY_PRIVATE_DOMAIN}:6379`
   - `RAILWAY_PRIVATE_DOMAIN` is automatically available in Railway services

## Verification

After setting `REDIS_URL`:

1. **Check Railway logs** for your API service:
   - Look for: `Redis checkpointer initialized` ✅
   - If you see: `Using memory checkpointer` ⚠️ - Redis connection failed

2. **Test the connection**:
   - Check `/health/ready` endpoint
   - Should show: `"redis": "connected"`

3. **If connection fails**:
   - Verify `REDIS_URL` format is correct
   - Check that Redis Stack service is running
   - Ensure password is correct (if set)
   - Check Railway logs for Redis Stack service

## Common Issues

### Issue: Variables show as `${{ REDIS_PASSWORD }}`

**Solution**: These are Railway template variables. To use them:
- Railway resolves them automatically in the same service
- For cross-service, use the actual variable names Railway provides
- Or manually copy the actual values

### Issue: Connection refused

**Solution**: 
- Ensure Redis Stack service is running
- Check that you're using the correct hostname/port
- Verify services are in the same Railway project

### Issue: Authentication failed

**Solution**:
- Check the password matches between services
- Verify `REDIS_PASSWORD` is set correctly
- Some Redis Stack configs don't require a password - try without it:
  ```
  redis://${REDIS_HOST}:6379
  ```

