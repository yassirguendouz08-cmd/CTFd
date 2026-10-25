# Account protection and email verification

Registration and authentication protection uses atomic Redis counters shared by all CTFd workers. Redis outages block protected operations with 503; public browsing remains available. HTML errors keep the CYBERDUNE theme, API errors are JSON, and throttled responses include Retry-After.

| Operation | Limits |
| --- | --- |
| Signup | 30 attempts/minute and 300/hour per IP; 3/hour per email |
| Login | 100/minute and 600/15 minutes per IP; 20/15 minutes per normalized account |
| Confirmation resend | 1/minute and 3/15 minutes per user; 100/15 minutes per IP |
| Password reset | 50/15 minutes per IP; 3/hour per normalized email |
| Instance changes | 12/minute per user and 600/minute per IP |
| Instance status | 120/minute per authenticated user |
| ZIP upload | 5/5 minutes per admin |
| Team creation/join | 100/5 minutes per IP |

Counters hash identities instead of storing raw email addresses in Redis key names. Rejected requests do not extend the expiration. Login counters include successful attempts, and limits can affect shared networks; tune `rules()` for a large bootcamp. Limits reduce abuse; they do not guarantee that a determined distributed attacker cannot create accounts.

Nginx additionally limits the site to 20 requests/second/IP (burst 100), auth pages to 2 requests/second/IP (burst 12), and auth request bodies to 64 KB. The proxy replaces forwarding headers with the actual client IP. CTFd remains bound to VPS loopback. Cookie Secure/HttpOnly/SameSite=Lax and HTTPS security headers are enabled on this HTTPS deployment. New passwords must be at least 12 characters; existing passwords remain valid.

## Email activation (pending provider configuration)

No SMTP or Mailgun provider was configured when these changes were installed. **Email verification remains disabled until real email delivery has been tested**, so existing users can continue using the platform. No account was silently marked verified or deleted.

1. Create a Brevo account and activate transactional sending. Authenticate `cyberdune.online` by adding the exact DNS records supplied by Brevo. Add a sender such as `noreply@cyberdune.online`.
2. In Brevo SMTP & API settings, create an SMTP key and copy the displayed SMTP login. Do not use the Brevo account password or an API key as the SMTP password.
3. Open https://ctf.cyberdune.online/admin/config#email and enter:
   - From address: the verified sender.
   - SMTP server: `smtp-relay.brevo.com`.
   - Port: `587`.
   - Authentication: enabled.
   - Username: the SMTP login displayed by Brevo.
   - Password: the SMTP key, entered privately.
   - TLS/STARTTLS: enabled; SSL: disabled.
4. Save. Using your own test account, go to `/confirm?flow=init` and request a verification email. Confirm it arrives, uses an HTTPS link, and the link confirms the account. Check Brevo delivery logs if delivery fails.
5. Only after that test succeeds, open Admin -> Config -> Accounts and enable **Verify Emails**. Unverified existing users will also need to confirm their email; admins retain access.
6. Test one new registration and a password reset using your own email. The confirmation token expires after 30 minutes and is removed after successful use. Test mail before announcing registration publicly.

Required verification covers CTFd core protected pages and the instance manager API (including token-authenticated requests after CTFd resolves the user). Registration stops with a helpful message if verification is required but there is no mail configuration. Delivery failures never claim success; an already-created account can retry from the confirmation page. SMTP TLS now validates certificates and correctly handles SSL=False on port 587.

Sources: https://docs.ctfd.io/docs/settings/emails/ and https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP

## Deployment and recovery

Run `sudo python3 install-account-security.py` beside `account-security.zip` in the Ubuntu user's home directory. The installer only updates the named files, backs up originals and the small set of changed non-secret config keys, validates Nginx before reloading, and restarts CTFd. It does not enable verification or configure credentials. Keep the emitted backup path for recovery. The security plugin is required for the additional controls; SAFE_MODE disables custom plugins.

No claim is made that the entire platform has passed a comprehensive penetration test. These changes address account/email spam and the exposed authentication/instance flows.

## Validation on 2026-10-12

- 30 automated security, verification, instance-lifecycle, and ZIP-upload tests passed against disposable databases and mocked email delivery.
- Live Redis: 100 concurrent calls with a limit of 7 admitted exactly 7 and throttled 93; disposable keys were removed.
- Live CTFd: a nonexistent-account login probe using a synthetic IP admitted 10 attempts and returned a themed 429 with Retry-After on attempt 11. Probe counters were removed.
- Public HTTPS home, login, register, and scoreboard returned 200. Secure/HttpOnly/SameSite=Lax cookies, HSTS, no-store auth responses, nosniff, frame protection, and referrer policy were checked.
- Nginx configuration validated before reload.
- Installed backup: `/home/ubuntu/cyberdune-security-backups/20261012T154339Z`.
- Real SMTP delivery remains untested and verification is disabled pending provider setup. Existing users/data were retained; GitHub synchronization is still pending independently of this live deployment.
