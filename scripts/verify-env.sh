#!/bin/bash
# Verify environment variables are loaded correctly

echo "Checking environment variables..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

echo "✅ .env file exists"
echo ""

# Check required variables
required_vars=(
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "TWILIO_PHONE_NUMBER"
    "TWILIO_WEBHOOK_URL"
    "OPENAI_API_KEY"
    "ELEVENLABS_API_KEY"
    "SALESFORCE_USERNAME"
    "SALESFORCE_PASSWORD"
    "SALESFORCE_SECURITY_TOKEN"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" .env; then
        value=$(grep "^${var}=" .env | cut -d '=' -f2-)
        if [ -z "$value" ] || [ "$value" = "your-"* ] || [ "$value" = "https://your-"* ]; then
            echo "⚠️  $var is set but appears to be a placeholder"
            missing_vars+=("$var")
        else
            echo "✅ $var is set"
        fi
    else
        echo "❌ $var is missing"
        missing_vars+=("$var")
    fi
done

echo ""

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo "✅ All required environment variables are set!"
    exit 0
else
    echo "❌ Missing or incomplete variables:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    exit 1
fi


