---
name: code-review-ui
description: Use when reviewing frontend, UI, or component code. Covers accessibility (WCAG AA), state management, bundle size, keyboard navigation, hydration, and rendering performance. Load instead of the general code-review skill for UI-focused reviews.
metadata:
  type: skills
  scope: ["TypeScript", "JavaScript", "React", "Vue", "HTML", "CSS"]
  when: "Reviewing React/Vue/Svelte components, CSS, HTML templates, state management, or any frontend rendering code"
---

# Code Review — UI / Frontend Layer

Focus on accessibility, performance, and correctness at the rendering boundary.

---

## Accessibility (WCAG AA)

- [ ] **Missing `alt` text on images** — every `<img>` needs an `alt` attribute. Decorative images use `alt=""`. Never `alt="image"` or `alt="photo"`.
- [ ] **Interactive element is not keyboard-accessible** — a `<div onClick>` or `<span onClick>` is not focusable by default. Use `<button>` or add `role`/`tabIndex` and keyboard event handlers.
- [ ] **Color contrast** — text must meet 4.5:1 contrast ratio (3:1 for large text). Check with a contrast analyzer before approving color changes.
- [ ] **Missing form labels** — every `<input>` needs a visible `<label>` or `aria-label`. Placeholder text is not a substitute.
- [ ] **Inaccessible error messages** — form validation errors must be associated with the input (`aria-describedby`) and announced to screen readers.
- [ ] **Focus management after state change** — modals, dialogs, and popups must move focus to the new content on open and restore it on close.
- [ ] **Missing ARIA role on custom widget** — a custom dropdown, slider, or menu must declare its ARIA role and maintain ARIA state (`aria-expanded`, `aria-selected`, etc.).

---

## State Management

- [ ] **Server state stored in client state** — data fetched from an API stored in `useState`/`useReducer`/Vuex instead of a server state cache (React Query, SWR, Apollo). Leads to stale reads and manual invalidation bugs.
- [ ] **Derived state stored explicitly** — `const [fullName, setFullName] = useState(...)` when `fullName = firstName + lastName` is derivable. Store the minimum, compute the rest.
- [ ] **State updated without immutability** — mutating a React/Vue state object directly (`state.items.push(...)`) instead of returning a new reference. Breaks change detection.
- [ ] **Global state for local data** — adding to a global store (Redux, Zustand, Pinia) something only one component uses. Use `useState` / component-local state first.
- [ ] **Missing loading / error states** — async data fetch with no handling of the pending or error case. The UI silently shows nothing or crashes.

---

## Rendering & Performance

- [ ] **Missing key on list items** — rendering a list without a stable, unique `key` prop. React/Vue uses `key` for reconciliation; missing or array-index keys cause incorrect re-renders.
- [ ] **Unnecessary re-renders** — a component re-renders on every parent update because a prop (often an inline object or callback) is recreated each render. Stabilize with `useMemo`/`useCallback`/`memo`.
- [ ] **Blocking the main thread** — expensive computation in a render method or event handler without `requestIdleCallback`, a Web Worker, or `useDeferredValue`.
- [ ] **Waterfall data fetching** — child components that each fetch their own data serially. Hoist fetches to a parent or use parallel queries.
- [ ] **Layout thrashing** — reading and writing DOM properties (e.g., `element.offsetHeight`) in a loop causes repeated reflows. Batch reads before writes.

---

## Bundle Size

- [ ] **Unguarded heavy import** — `import * as moment from 'moment'` (300 kB) when only one function is needed. Use a lighter alternative (`date-fns`) or a named import.
- [ ] **Missing code splitting** — a rarely-used heavy route imported eagerly. Use `React.lazy` / dynamic `import()` for route-level or feature-flag-gated code.
- [ ] **Polyfill included unconditionally** — polyfills for features that target browsers already support. Check `browserslist` config.
- [ ] **Duplicate dependency** — two packages that provide the same thing (e.g., `lodash` and `lodash-es`, or both `axios` and `fetch` wrappers). Pick one.

---

## Hydration & SSR

- [ ] **Hydration mismatch** — rendering different content on the server vs. client (using `window`, `Date.now()`, or random values during SSR). Wrap in `useEffect` or a client-only boundary.
- [ ] **Missing Suspense boundary** — a lazy-loaded component or async data source with no `<Suspense>` fallback. Crashes or shows nothing during loading.
- [ ] **Client-only APIs accessed in SSR** — `localStorage`, `document`, `window` accessed outside a lifecycle hook or `useEffect`. Will throw during server rendering.

---

## See Also

- `.claude/skills/code-review/SKILL.md` — general review checklist for all layers
- `.claude/skills/react-best-practices/SKILL.md` — React-specific patterns and hooks rules
- `.claude/skills/accessibility/SKILL.md` — detailed WCAG 2.2 accessibility guidance
