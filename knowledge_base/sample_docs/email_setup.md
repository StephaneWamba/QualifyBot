# Email Setup and Configuration

## Setting Up Email on Different Devices

### Outlook Desktop Setup

**Steps:**
1. Open Outlook and go to File > Add Account
2. Enter your email address
3. Choose "Let me set up my account manually"
4. Select IMAP or POP3 (IMAP recommended)
5. Enter server settings:
   - Incoming: mail.company.com (port 993 for IMAP, 995 for POP3)
   - Outgoing: smtp.company.com (port 587)
6. Enter username and password
7. Test connection

### Mobile Email Setup (iOS/Android)

**Steps:**
1. Go to Settings > Mail/Accounts
2. Add Account > Other
3. Enter email and password
4. Configure server settings:
   - IMAP: mail.company.com, port 993, SSL enabled
   - SMTP: smtp.company.com, port 587, TLS enabled
5. Save and test

### Common Email Issues

#### Cannot Send Emails

**Solutions:**
- Verify SMTP server settings are correct
- Check port 587 is not blocked by firewall
- Ensure "My server requires authentication" is enabled
- Try port 465 with SSL if 587 doesn't work
- Check if account is locked (too many failed attempts)

#### Cannot Receive Emails

**Solutions:**
- Verify IMAP/POP3 server settings
- Check port 993 (IMAP) or 995 (POP3) is open
- Ensure SSL/TLS is enabled
- Check email account isn't full (storage quota)
- Verify password hasn't expired

#### Emails Going to Spam

**Solutions:**
- Check sender's email reputation
- Verify SPF/DKIM records are configured
- Add sender to contacts/whitelist
- Check email content (avoid spam trigger words)
- Contact email administrator if persistent

## Password Reset

If you need to reset your email password:
1. Go to company password portal
2. Enter your username
3. Follow password reset instructions
4. Wait 15 minutes for changes to propagate
5. Update password in all email clients

## Escalation Criteria

Escalate to IT support if:
- Server settings are unknown
- Account is locked
- Multiple users affected
- Email server appears down
- Authentication errors persist after password reset

