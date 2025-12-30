# PowerShell script to start cloudflared tunnel for Twilio webhooks in development

Write-Host "Starting cloudflared tunnel..." -ForegroundColor Green
Write-Host "This will expose your local server at http://localhost:10000 to the internet" -ForegroundColor Yellow
Write-Host ""
Write-Host "Once started, you'll get a public URL like: https://xxxx-xx-xx-xx-xx.trycloudflare.com" -ForegroundColor Cyan
Write-Host "Use this URL in your .env file as TWILIO_WEBHOOK_URL" -ForegroundColor Yellow
Write-Host ""

# Start cloudflared tunnel pointing to localhost:10000 (Docker port)
cloudflared tunnel --url http://localhost:10000


