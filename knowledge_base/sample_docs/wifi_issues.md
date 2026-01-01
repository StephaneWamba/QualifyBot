# WiFi Connection Troubleshooting

## Basic WiFi Troubleshooting Steps

### Cannot Connect to WiFi

**Quick Fixes:**
1. Turn WiFi off and on again
2. Forget network and reconnect
3. Restart device
4. Move closer to router
5. Check if WiFi is enabled (airplane mode off)

### Slow WiFi Connection

**Solutions:**
1. Check signal strength (move closer to router)
2. Reduce interference (move away from microwaves, Bluetooth devices)
3. Change WiFi channel (use 5GHz if available)
4. Limit devices using WiFi simultaneously
5. Update WiFi drivers
6. Restart router

### WiFi Keeps Disconnecting

**Symptoms:**
- Connection drops frequently
- Need to reconnect often
- Intermittent connectivity

**Solutions:**
1. Update WiFi drivers
2. Check router firmware is up to date
3. Change WiFi channel (avoid crowded channels)
4. Disable power saving mode for WiFi adapter
5. Check for interference from other devices
6. Reset network settings (last resort)

## Advanced Troubleshooting

### Windows WiFi Issues

**Command Line Fixes:**
```cmd
netsh wlan show profiles
netsh wlan delete profile name="NetworkName"
netsh winsock reset
ipconfig /release
ipconfig /renew
ipconfig /flushdns
```

### macOS WiFi Issues

**Terminal Commands:**
```bash
sudo ifconfig en0 down
sudo ifconfig en0 up
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### Network Reset Steps

1. Forget the WiFi network
2. Restart device
3. Re-enter WiFi password
4. Check router settings if issue persists
5. Contact network administrator

## Router-Specific Issues

### Cannot Access Router Admin

**Default Steps:**
1. Connect via Ethernet cable
2. Access 192.168.1.1 or 192.168.0.1
3. Use default admin credentials (check router label)
4. Reset router if password changed and unknown

### Router Needs Reset

**Steps:**
1. Locate reset button on router
2. Hold for 10-30 seconds (check manual)
3. Wait for router to restart
4. Reconfigure WiFi settings
5. Update default password

## Security Best Practices

1. Use WPA2 or WPA3 encryption
2. Change default router password
3. Use strong WiFi password (12+ characters)
4. Enable MAC address filtering if needed
5. Disable WPS if not needed
6. Keep router firmware updated

## Escalation Criteria

Escalate to IT support if:
- Multiple users affected
- Router appears to be down
- Network infrastructure issue suspected
- Security breach suspected
- Solutions above don't resolve after 2 attempts

