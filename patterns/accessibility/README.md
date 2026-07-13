# Accessibility Patterns

Cross-framework accessibility baseline, written from
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) and the
[WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
fundamentals — not adapted from any one codebase's internal APIs. The
target is **WCAG 2.2 Level AA**. This doc calls out the decisions and the
handful of rules that catch the most real defects; it doesn't re-teach
the full spec (follow the two links for that).

## The first rule of ARIA: don't use ARIA

A native element (`<button>`, `<a href>`, `<input>`, `<label>`, `<nav>`,
`<table>`) brings keyboard behavior, focus, and the correct role/state
for free. Reach for `role="button"` + `tabindex` + key handlers only when
no native element fits — a `<div role="button">` you built by hand is a
liability you now own forever. Semantic HTML first; ARIA to *fill gaps*,
never to *replace* semantics.

```html
<!-- Good -->
<button type="button" onclick="save()">Save</button>

<!-- Avoid: reinvents everything the native button already does -->
<div role="button" tabindex="0" onclick="save()" onkeydown="...">Save</div>
```

## Perceivable

- **Text alternatives.** Every meaningful image needs an `alt` describing
  its *purpose*; decorative images take empty `alt=""` so screen readers
  skip them. Icon-only controls need an accessible name
  (`aria-label`/visually-hidden text).
- **Contrast.** Body text ≥ **4.5:1**; large text (≥ 24px, or 18.66px
  bold) and meaningful UI components/graphics ≥ **3:1**. Verify the
  computed colors, don't eyeball them.
- **Don't rely on color alone.** A red border *and* an error message/icon
  — not red alone — so it survives color-blindness and grayscale.

## Operable

- **Keyboard.** Everything interactive must be reachable and operable by
  keyboard alone, in a logical order, with **no keyboard trap**. If you
  add `tabindex`, use `0` (in natural order) or `-1` (focusable only
  programmatically) — never positive values.
- **Visible focus.** Never `outline: none` without a clearly visible
  replacement focus style; keyboard users navigate by it.
- **Skip link.** A "skip to main content" link as the first focusable
  element on pages with repeated nav.
- **Target size.** Interactive targets ≥ **24×24 px** (WCAG 2.2's
  2.5.8), with spacing if smaller.

## Understandable

- **Label every input.** A programmatically associated `<label for>` (or
  `aria-labelledby`) — placeholder text is not a label.
- **Identify errors in text.** On validation failure, describe what's
  wrong and how to fix it, associate it with the field
  (`aria-describedby`), and set `aria-invalid="true"`.
- **Consistent navigation** and predictable behavior — focus doesn't jump
  or submit on its own.

## Robust

- **Name, Role, Value** for every custom widget. If you build a custom
  control, follow the matching
  [ARIA APG pattern](https://www.w3.org/WAI/ARIA/apg/patterns/) exactly —
  its documented roles, states (`aria-expanded`, `aria-selected`,
  `aria-checked`), and keyboard interactions. A half-implemented ARIA
  widget is worse than a native element.
- **Announce dynamic changes.** Content that updates without a page load
  (toasts, async results, validation) needs an `aria-live` region
  (`polite` for status, `assertive` only for genuinely urgent) or a
  `role="alert"`.

## Testing: automated catches a minority

Automated tooling ([axe-core](https://github.com/dequelabs/axe-core),
Lighthouse) reliably catches only ~30–50% of WCAG issues — contrast,
missing labels/alt, invalid ARIA. It cannot judge whether `alt` text is
*meaningful*, whether focus order makes sense, or whether a custom widget
is actually operable. So:

1. Run an automated check in CI (fail on new violations).
2. **Tab through every flow by keyboard** — reach, operate, see focus,
   escape.
3. Test with a screen reader (VoiceOver/NVDA) for anything custom.

See [`patterns/testing/PLAYWRIGHT_UI_TESTING.md`](../testing/PLAYWRIGHT_UI_TESTING.md)
for wiring automated checks and keyboard-navigation assertions into the
UI test suite.
