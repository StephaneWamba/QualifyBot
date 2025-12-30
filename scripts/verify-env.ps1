# PowerShell script to verify environment variables

Write-Host "Checking environment variables..." -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ .env file exists" -ForegroundColor Green
Write-Host ""

# Check required variables
$requiredVars = @(
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "TWILIO_WEBHOOK_URL",
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "SALESFORCE_USERNAME",
    "SALESFORCE_PASSWORD",
    "SALESFORCE_SECURITY_TOKEN"
)

$missingVars = @()

foreach ($var in $requiredVars) {
    $line = Select-String -Path .env -Pattern "^${var}="
    if ($line) {
        $value = ($line.Line -split '=', 2)[1]
        if ([string]::IsNullOrWhiteSpace($value) -or $value -like "your-*" -or $value -like "https://your-*") {
            Write-Host "⚠️  $var is set but appears to be a placeholder" -ForegroundColor Yellow
            $missingVars += $var
        } else {
            Write-Host "✅ $var is set" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ $var is missing" -ForegroundColor Red
        $missingVars += $var
    }
}

Write-Host ""

if ($missingVars.Count -eq 0) {
    Write-Host "✅ All required environment variables are set!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Missing or incomplete variables:" -ForegroundColor Red
    foreach ($var in $missingVars) {
        Write-Host "   - $var" -ForegroundColor Red
    }
    exit 1
}


