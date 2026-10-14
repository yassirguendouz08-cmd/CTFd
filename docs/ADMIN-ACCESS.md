# Grant or remove admin access

1. Ask the person to register their own account on the platform.
2. Sign in with an existing admin account and open **Admin Panel → Users**.
3. Find the account by username or email and open its details.
4. Click **Manage admin access**. Under **Account role**, select **Admin**.
5. Click **Submit**. The account now has full administrator permissions.
6. Ask the person to refresh the page and open `/admin`.

To revoke access, follow the same steps and select **User** instead.
Role changes clear the cached account permissions. Keep at least one working
admin account, and use separate accounts for each administrator.

Admin grants full access to challenges, flags, users and platform configuration;
CTFd does not provide a limited challenge-editor role here. This is a platform
account permission, independent of GitHub or SSH access.

The existing admin-only user API saves the role. The public registration and
profile settings do not expose this control. No database migration or asset build
is needed for this template update.
