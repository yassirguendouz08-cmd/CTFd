# CyberDune club identity

The CTF theme shares the visual identity of https://cyberdune.online, inspected on 11 October 2026. CTF navigation, forms, challenges and event configuration remain specific to the platform.

`CTFd/themes/cyberdune/static/css/club.css` loads after the existing theme styles. It provides the club's black and zinc surfaces, red borders, Geist Sans and Geist Mono typography, navigation pill, red/pink gradient hero button, community photograph, subtle grid and responsive layout. Other pages use the same colors, controls and cards.

The bundled community photograph and font binaries come from the club website. Geist's official SIL Open Font License files are included alongside the fonts. Assets are served locally by CTFd rather than fetched from the club website at runtime.

Deploy on the existing Ubuntu VPS:

```bash
cd ~/CTFd
git pull --ff-only origin master
~/ctfd-compose restart ctfd
```

This deployment mounts the repository into CTFd. A Docker image rebuild is unnecessary for these theme changes. Refresh the browser after deployment.

Validation: isolated CTFd rendering, login, registration, challenge submissions and team flows; browser checks for homepage, challenge board and login at 1440px and 390px widths, including local font loading and horizontal overflow.
