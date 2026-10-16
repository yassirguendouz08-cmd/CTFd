# CyberDune website identity and challenge completion

The public CTF theme uses the club website's Geist Sans/Geist Mono fonts, charcoal
surfaces and red accents. Sans typography carries headings, navigation and challenge
titles; monospace is reserved for small technical details. Fonts are served locally with
their SIL Open Font License in `static/webfonts/Geist-OFL.txt`.

A small, hand-authored `static/img/network-field.svg` supplies the shared background:
quiet grid lines, angled network traces and a few red connection points around the
content. The static drawing replaces the hero's bitmap backdrop and also appears
on the login panel. Cards use neutral borders, comfortable spacing and a modest
hover lift; reduced-motion users do not receive that movement.

The challenge heading, category filters and category rows are centered. Incomplete
rows remain centered on desktop; cards wrap to two columns on tablets and one
column on phones.

A solved challenge has a green background, green border and a checkmarked
**Solved** label. Correct submissions update the card immediately, and recorded
solves remain visible after a refresh. Team completion uses CTFd's account-level
solve state.

Admin checks on hidden challenges are marked **Solved · preview**. Preview status
is stored only in the current browser session, scoped to the admin account and
challenge, and is ignored if the challenge becomes visible. Previews do not add
solves, failed submissions or points. Storage failures do not prevent flag checks.

The theme's JavaScript source and built bundle/manifest are updated together.
The CSS cache version is bumped in `templates/base.html` for deployment.

Validation used an isolated CTFd database and real browser interactions: correct
flag submission, persistence after reload, admin preview, teammate solve state,
category filtering, mobile navigation, and layouts at 375, 768 and 1280 pixels.
