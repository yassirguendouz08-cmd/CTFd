# Cyber Odyssey Reference Design Specification

Inspected from the rendered page at `https://cyberodyssey.akasec.ma/` in Chromium on 2026-11-03. CSS measurements below are computed values from the live page where available. Screenshot dimensions vary slightly because the browser reserves space for its scrollbar.

## Typography

| Use | Observed style |
| --- | --- |
| Body and controls | Inter (variable 100–900 on the reference), 16px / 24px, weight 400, normal letter spacing |
| Main hero headline | Anton, uppercase, 1px tracking, 600 weight; 96px / 96px at 1920px, 72px / 72px at 1440px, 60px / 60px at 768px, 48px / 48px at 390px |
| Section headlines | Anton, uppercase, 60px / 60px, weight 700, 1px tracking at desktop; 48px at 768px |
| Day labels | Anton, 36px / 40px, weight 400 |
| Small section kicker | Inter, 16px / 24px, weight 700, uppercase, 0.9px tracking, red |
| Card/support copy | Inter, generally 14–18px / 20–28px; muted secondary lines are smaller |

The reference loads Inter and Anton as web fonts. The CyberDune adaptation uses the existing locally stored Inter files and requests Anton from Google Fonts with condensed local fallbacks.

## Palette and background

- Page background: near-black, sampled CSS `lab(2.75% 0 0)` (approximately `#080808`).
- Main text: near-white, `lab(98.26% 0 0)` (approximately `#f5f5f5`).
- Card base: `lab(7.78% 0 0)` (approximately `#141414`).
- Muted text: `lab(66.13% 0 0)` (approximately `#a7a7a7`).
- Border: white at 10% opacity.
- Red accent: reference token `--akasec-red-500` (`lab(51.59% 74.04 53.77)`, near `#ed1c24`); secondary pink is near `#e51651`.
- Interior page sections use a very low contrast repeating scallop pattern over black. The hero uses a darkened event photograph/video instead.
- Glass panels use black/translucent fills, 4px backdrop blur, a thin translucent border, and an inset red glow focused toward the right/top edge.

## Layout and spacing

- Desktop page content reaches a 1536px outer container at 1920px, with 64px inner horizontal padding (1408px usable width). At 1440px, the outer container is 1280px wide with the same 64px horizontal padding. At 768px, outer width is 753px with 24px horizontal padding. At 390px, the scrollable content width is 375px and the inner content is 327px after 24px padding.
- Main section spacing is generally 96px from the top on desktop (`pt-24`); tablet/mobile reduce it to 64px (`pt-16`).
- Facts cards use 24px grid gaps at desktop. Their measured sizes are 452×236px at 1920px, 368×288px at 1440px and 219×268px at 768px. Cards use about 64px horizontal padding and roughly 56–64px vertical padding at desktop.
- Speaker portraits are 334×400px at 1920px and 270×400px at 1440px, with 16px corners and a dark bottom gradient behind the text.
- FAQ rows are about 1152×78px at 1920px, with 16px corners, a 1px border, 24px inline padding and 16px semibold question text.
- Day selector cards are about 347×167px at 1920px with 32px padding and 25px corners. Schedule cards are about 1036×186px, with a red border, 24px vertical / 64px right / 28px left padding, and a 40px internal gap.
- The intro glass panel is 961×639px at 1920px; its descriptive text is centered with a constrained reading width.

## Responsive behavior

Breakpoints observed from the responsive grid classes are 640px (`sm`), 768px (`md`), 1024px (`lg`), 1280px (`xl`) and 1536px (`2xl`). Facts use 1/2/3 columns at the small/medium/desktop steps. Speaker cards use 1 column on mobile, 2 columns at tablet, and 4 from 1280px. Agenda switches from one column to a selector/content split at 1024px. At 390px, the hero headline wraps to four lines, facts cards are full width, and card/panel inline padding reduces to 32px.

## Components, controls, motion

- Navigation is a compact translucent pill group, with the brand separated at the left and account actions at the right. Active navigation uses a red tinted fill and thin red outline.
- Primary actions use a saturated red-to-pink treatment, white text, about 48px height, and a 6–8px radius. Secondary actions use a near-white fill with dark text.
- Large information cards use 25px corners; image cards and FAQ accordions use 16px; inputs use tighter 6–8px corners.
- Hover/selection effects are restrained: red edge/glow emphasis and a small lift or fade. Reduced-motion preferences should suppress transforms and transitions.
- Preserve CyberDune's existing logo, footage, challenge data and interaction flows; the adaptation uses the reference's typography, dark pattern, spacing, glass panels, red highlights and hierarchy.

## Inspected sections

The full rendered page was inspected from top to bottom: full-screen hero; introduction glass panel; two-row facts grid; speaker portrait grid; sticky day selector and schedule; previous-edition carousel; sponsor and CTF statistics; FAQ accordion; social footer. The supplied screenshots were also used to verify the visual treatment of the hero, results list, intro, stats, speaker cards, CTF stats, FAQ and footer.
