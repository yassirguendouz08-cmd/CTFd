# Original CyberDune UI restoration

The visual reference is the previously supplied theme preserved locally in
`releases/core-theme-vps.zip`, its first integration commit `d2fe57a8`, and the
saved `supplied-home-1440.png` preview. No new ZIP accompanied the current request.

The archive's `templates/pagehome.html` contains the original encrypted description:
the alphabet `!@#$%^&*()0123456789ABC]HIJKLMefghijklmnopq]vwxyz`, a 30 ms update
interval, 30 reveal steps, and a 30% chance of scrambling each unrevealed character.
`original-ui.js` adapts that logic to titles, navigation labels, the launch button
and challenge cards. It paints an `aria-hidden` overlay while leaving the original
text and layout intact, supports keyboard focus, and cancels on departure.

The original animated background is **`static/img/bg-1.gif`**, referenced by the
archive's compiled `main.e9ec7884.css`; it is not a Canvas or particle generator.
Its SHA-256 is `896f514d821224f82150a91ec837108b8a6bf335c3835f2d0f6aa2d537bb1a3f`.
The existing `cyberdune-background.webm` is the same footage previously converted
to VP9 at 15 fps (2.5 MB instead of the 22 MB GIF). A new 77 KB poster is extracted
from that GIF's first frame. The shared base template uses one decorative,
muted, looping, inline video with this poster across all public theme pages.

The restored visual layer uses the original Hack family, glass navigation pills,
red active states, two-column homepage panels, DUNE typing/cursor, the 45-second
text ticker, and the red chamfered challenge-card polygon. Hack regular/bold files
are hosted locally with their upstream license. Existing responsive forms, error
messages, modal behavior, navigation routes and original event settings remain.
The current developer credit is preserved. The obsolete full-screen boot loader
and sample sponsor carousel are omitted; the platform stays immediately usable.

The footer has no motion-status badge or effects button. Reduced-motion users
receive a still poster without loading the video. The full CYBERDUNE heading
scrambles on hover or keyboard focus, pausing its DUNE typing until the reveal ends.
This deliberately triggered brand reveal takes 240 ms with reduced motion,
compared with the normal 900 ms; other scramble effects honor the OS preference. Hidden
tabs pause playback and text timers. Video playback failure leaves the poster.
Solved cards retain the requested green state and checkmarked label; admin-only
hidden flag previews remain separate from scored submissions.

Profile rendering exposed two existing frontend issues: category statistics were
read before their request completed, and zero attempts produced `NaN` percentages.
The four public/private user/team graph components now handle those initial and
empty states. Source bundles and the Vite manifest are rebuilt together.

Validation:

- Node regression checks cover pending, empty and populated user/team categories
  and percentages; production Vite build succeeds.
- Browser checks cover the restored homepage, challenges, login/registration,
  scoreboard, private/public user/team profiles, notifications and rules at phone,
  tablet and desktop widths; navigation and nested Escape/ArrowDown behavior.
- A disposable CTFd database confirms login, a correct flag, immediate Solved state,
  refresh persistence, teammate completion and administrator preview.
- Playback advances, scramble overlays disappear with original labels intact,
  the motion badge is absent, and reduced-motion pages omit the video source.
  The local fixture explicitly enables normal motion for one test because the
  browser host itself requests reduced motion; this override is never deployed.
- Six isolated CTFd visibility checks cover hidden/admin challenges, signed file
  access and scheduled visibility. No production users, solves or flags are reset.

`redesign.css` remains the responsive layout foundation. `original-ui.css` and
`original-ui.js`, loaded last in `base.html`, define the restored visual identity.
