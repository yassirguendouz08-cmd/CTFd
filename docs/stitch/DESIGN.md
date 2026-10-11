# CYBERDUNE CTF — Premium Redesign

Uploaded to Google Stitch and used to create the shared design system on 11 October 2026.

## Identity

A serious competition workspace from a student cybersecurity community in the
Moroccan Sahara. Confident, legible and precise. Use the actual CyberDune logo.
Avoid decorative hacker imagery, fake system telemetry, excessive glow and
repetitive marketing phrases. Competition tasks and real information lead.

## Proposed tokens

| Role | Value |
| --- | --- |
| Background | #080A0F |
| Surface | #11141C |
| Elevated surface | #191E29 |
| Primary action | #E11D48 |
| Accent | #FF304F |
| Primary text | #F8FAFC |
| Secondary text | #94A3B8 |

Use Inter for body/forms, Space Grotesk for headings, JetBrains Mono for flags,
points and small technical labels. Include an Arabic-compatible font fallback.
Check actual contrast for all labels and controls rather than assuming token
colors pass everywhere. Red must not be the only distinction for an error or state.

## Layout and interaction

- Spacious public landing page, practical challenge workspace and readable standings.
- Compact consistent navigation with clear active state and accessible mobile menu.
- Grid with restrained borders; consistent cards and controls; short readable line lengths.
- Challenge points, category, solved status and solve count have distinct hierarchy.
- Keep challenge attachments, paid hints, flag input and validation easy to find.
- Show accurate schedule states, real countdown and legitimate empty states.
- Keyboard focus, descriptive labels, 44px touch targets and reduced-motion behavior.
- English, French and Arabic; fully mirrored RTL layout, LTR flags/commands.
- Use subtle interaction transitions; no large looping decorative animations.

## Screen set

Landing, challenge board, challenge details (default/success/error), standings,
login, registration, recovery, player profile, team profile/enrollment, event guide,
announcements and safe admin appearance refinements. Include mobile/tablet layouts.

Explore at least two structural directions for landing and challenge board before
selecting a shared design. Keep sample data clearly a design fixture; production
screens must bind real authorized CTFd data.

## Stitch project
Project ID: 10465941215322521387
Controls have subtly rounded 6px corners; cards 10px; modals 12px. Use precise thin borders and restrained elevation. Keep a spacious hero and compact task surfaces.

