# VPN Connection Troubleshooting

## Connecting to Company VPN

### Initial Setup

**Windows:**
1. Go to Settings > Network & Internet > VPN
2. Click "Add a VPN connection"
3. Enter VPN name and server address
4. VPN type: IKEv2 or L2TP/IPSec
5. Enter username and password
6. Save and connect

**macOS:**
1. System Preferences > Network
2. Click "+" to add new connection
3. Interface: VPN, VPN Type: IKEv2
4. Enter server address and account name
5. Click Authentication Settings and enter password
6. Connect

**Mobile (iOS/Android):**
1. Download company VPN app or configure manually
2. Enter server address and credentials
3. Install certificate if required
4. Connect

## Common VPN Issues

### Cannot Connect to VPN

**Symptoms:**
- Connection timeout
- Authentication failed
- Server not reachable

**Solutions:**
1. Verify internet connection is working
2. Check VPN server address is correct
3. Verify username and password
4. Check if VPN service is running (contact IT)
5. Try different VPN protocol (IKEv2 vs L2TP)
6. Disable firewall temporarily to test
7. Restart network adapter
8. Clear DNS cache (ipconfig /flushdns on Windows)

### VPN Connects But No Internet

**Symptoms:**
- VPN shows connected
- Cannot access internet or company resources
- DNS resolution fails

**Solutions:**
1. Check if split tunneling is enabled (may need to disable)
2. Verify DNS settings (use company DNS servers)
3. Check routing table (route print on Windows)
4. Restart VPN connection
5. Try different VPN server if available
6. Check if corporate firewall is blocking

### Slow VPN Connection

**Symptoms:**
- High latency
- Slow file transfers
- Laggy remote desktop

**Solutions:**
1. Check local internet speed
2. Try different VPN server location
3. Disable unnecessary VPN features
4. Check for background downloads
5. Use wired connection instead of WiFi
6. Contact IT to check server load

### VPN Disconnects Frequently

**Symptoms:**
- Connection drops after few minutes
- Need to reconnect repeatedly
- Timeout errors

**Solutions:**
1. Check VPN keepalive settings
2. Verify network stability
3. Update VPN client software
4. Check for conflicting network software
5. Increase connection timeout settings
6. Contact IT to check server logs

## Security Best Practices

1. Always use VPN when accessing company resources remotely
2. Don't share VPN credentials
3. Disconnect VPN when not in use
4. Report suspicious connection attempts
5. Keep VPN client updated

## Escalation Criteria

Escalate to IT support if:
- VPN server appears down
- Certificate errors
- Multiple users affected
- Security concerns (suspicious activity)
- Solutions above don't resolve after 2 attempts

