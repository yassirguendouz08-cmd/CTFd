# CyberDune website identity and challenge completion

The active public theme pairs the owner's original Hack technical typography with
Geist Sans for descriptions, forms and content headings. It retains the animated
background, glass navigation and red chamfered cards. See
[Original UI restoration](ORIGINAL-UI-RESTORATION.md) for the archived source,
animation provenance, accessibility behavior and validation. Fonts are served locally.

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
