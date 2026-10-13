# CYBERDUNE frontend redesign

The existing CTFd theme now follows the public Securinets Quals interface's navigation, typography hierarchy, split authentication layout, button geometry, spacing and restrained surfaces, using CYBERDUNE's existing logo/background and its own black/red/white identity.

## Reference review

Inspected desktop and mobile screenshots of https://quals.securinets.tn/ and public login, registration, scoreboard, teams, users and rules pages with Playwright. The reference uses a 73px desktop header, 7px button corners, 36px compact navigation actions, 48px main actions, monospace action labels, bold sans headings and a split authentication layout. Its challenges redirect to login; no protected reference pages were accessed. No reference logos, photos, branding or files were copied. Fonts come from the separately licensed Fontsource packages and are self-hosted; license notices are included.

## Changes

- `templates/base.html`, shared navbar/footer/auth-brand and homepage: one page shell, slim navigation, keyboard-accessible mobile/account menus, platform hero, original CYBERDUNE assets and consistent footer. Event details only render through the existing explicitly configured presentation mode.
- `static/assets/redesign.css`: reusable palette/spacing/control tokens, primary/secondary/danger/loading/disabled/focus states, forms, alerts, cards, tables, profiles, modals, resources, settings and instance states; mobile/tablet/desktop layouts.
- `static/assets/redesign.js`: navigation/account behavior and current-page indication.
- Auth, challenge board, scoreboard, settings, profile and team templates: shared styling, clear action labels, category filters using actual categories, usable long titles/descriptions/URLs/code/files/hints, and useful empty states.
- Removed competing embedded visual styles, glitch input decorations, the animated background/video loader and the old fixed homepage HUD. Original assets remain in the repository.
- `assets/scss/main.scss`, package manifests, Vite copy rules and generated manifest/assets: clean compiled base CSS with self-hosted Inter, JetBrains Mono and Montserrat. The language preference cookie now applies across all platform routes.
- Theme source and production artifacts are included. Rebuild with `npm ci` then `npm run build` inside `CTFd/themes/core-theme`.

## Validation

- Theme production build passed. Existing ECharts chunk-size warning remains; charts are loaded on chart pages.
- 30 existing security, verification, instance and ZIP-upload tests passed with isolated databases/mock email and manager.
- Playwright main flows passed with no JavaScript errors or missing resources: login, registration, team creation/join, flag attempts and scoring, hints/files, instance launch/copy/extend/restart/stop and failure/recovery.
- Responsive routes/modal checks passed at 320, 375, 430, 768, 1024, 1280 and 1440 pixels.
- Authentication checks passed at all seven widths; team edit dialogs passed at 320, 768 and 1440.
- Explicit checks passed for fonts, mobile menu/Escape, language selection and category filtering. Before/reference/after images are in `cyberdune-preview/redesign` beside the repository; these use synthetic local accounts/content.

## Deployment and limits

The deployment installer changes only the theme and this report/license notices, backs up every replaced file, compiles templates, then restarts CTFd. It does not update CTFd core, security/email settings, manager services, database records or admin templates. Keep its printed backup path for rollback.

Private reference layouts were extrapolated from its public components. Production has no configured challenges or teams at the pre-deployment snapshot, so comprehensive authenticated challenge/team/instance tests use the disposable local fixture; no sample challenges or users are created in production. Database/config counts are compared before and after deployment. GitHub synchronization remains separate from direct deployment.

## Live verification (2026-10-13)

The redesigned theme is live at https://ctf.cyberdune.online/. Public home/login/register/scoreboard checks passed at 375, 768, 1024 and 1440 pixels with no JavaScript errors, missing assets/images, duplicate IDs or horizontal overflow. Mobile menu/Escape and the final CSS cache version were checked live. The final generated bundle also passed the local main-flow checks after the language-cookie fix.

Theme backup: `/home/ubuntu/cyberdune-theme-backups/redesign-20261013T171847Z`. The pre/post snapshot remained 2 users, 0 teams, 0 challenges, 0 flags, 0 submissions and 1 page; required email verification remained enabled. Existing admin/core/security/manager files were not part of the package. No competition or sample content was added to production.

Recovery: restore backed-up files to their same paths under `~/CTFd`, remove only the additions listed in the backup's `new-files.txt`, then restart `ctfd-ctfd-1`. Keep old asset bundles until browser caches expire.
