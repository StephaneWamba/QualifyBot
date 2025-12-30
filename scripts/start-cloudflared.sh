#!/bin/bash
# Start cloudflared tunnel for Twilio webhooks in development

echo "Starting cloudflared tunnel..."
echo "This will expose your local server at http://localhost:10000 to the internet"
echo ""
echo "Once started, you'll get a public URL like: https://xxxx-xx-xx-xx-xx.trycloudflare.com"
echo "Use this URL in your .env file as TWILIO_WEBHOOK_URL"
echo ""

# Start cloudflared tunnel pointing to localhost:10000 (Docker port)
cloudflared tunnel --url http://localhost:10000


