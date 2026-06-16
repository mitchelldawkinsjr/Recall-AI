# Accessibility Audit — Final Report

**Target:** `http://127.0.0.1:8000` (Recall AI / AskMyVideo local dev server)  
**Date:** 2026-06-16  
**Auditor:** axe-core 4.11.4 via `@axe-core/playwright`  
**Standards:** WCAG 2.0 AA, WCAG 2.1 AA, WCAG 2.2 AA, best-practice  

> **Note on Ponytail:** [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) is an AI coding-style ruleset (anti-over-engineering), **not** a web accessibility scanner. This audit used **axe-core** — the industry-standard equivalent for automated WCAG 2.1/2.2 checks — per the failure-mode guidance in the audit prompt.

---

## Executive Summary

A baseline accessibility audit of four public Recall AI routes found **10 node-level violations across 5 issue types** (1 critical, 1 high, 3 medium). All issues were remediated in Django templates with minimal visual impact: form label associations, landmark semantics, heading hierarchy, sidebar contrast, and auth-page footer structure. A post-fix re-audit confirmed **zero violations** on all four pages. Playwright e2e tests and a GitHub Actions workflow were added to gate future PRs.

---

## Summary Table (Before → After)

| Issue ID | Severity | Description | Pages | Before | After |
|----------|----------|-------------|-------|--------|-------|
| `label` | **critical** | Form inputs missing programmatic labels | public_enhanced | 4 | **0** |
| `color-contrast` | **high** | Sidebar tagline below 4.5:1 contrast ratio | home, public_enhanced | 2 | **0** |
| `region` | medium | Footer content outside landmarks | login, register | 2 | **0** |
| `landmark-unique` | medium | Duplicate `<aside>` without unique names | public_enhanced | 1 | **0** |
| `page-has-heading-one` | medium | Page missing `<h1>` | public_enhanced | 1 | **0** |
| **Total violations** | | | | **7 rule hits / 10 nodes** | **0** |

---

## Remediation Details

### 1. `label` — Form elements must have labels (critical)

**Cause:** Filter controls in `enhanced_search.html` had visible text but no `for`/`id` association; checkbox toggle used a nested label without linking to the input.

**Fix:** Added `for` attributes on all filter labels; restructured diversify toggle as a single `<label for="diversifyResults">`.

**Files:** `video_processor/templates/video_processor/enhanced_search.html`

### 2. `color-contrast` — Insufficient contrast (high)

**Cause:** Sidebar tagline used `text-primary-fixed-dim/60` (#6587ba on #002753 = 4.04:1, below 4.5:1 required for 12px text).

**Fix:** Increased opacity to `/80` for ≥4.5:1 contrast while preserving visual hierarchy.

**Files:** `video_processor/templates/video_processor/includes/sidebar.html`

**Risk:** None — minor visual brightening of secondary text only.

### 3. `region` — Content not in landmarks (medium)

**Cause:** Auth pages placed copyright footer in a plain `<div>` outside `<main>`.

**Fix:** Changed footer wrapper to semantic `<footer>` element; marked decorative background `aria-hidden="true"`.

**Files:** `video_processor/templates/video_processor/auth_base.html`

### 4. `landmark-unique` — Duplicate landmarks (medium)

**Cause:** Sidebar and filter panel both used `<aside>` without distinguishing accessible names.

**Fix:** Added `aria-label="Main navigation"` and `aria-label="Advanced search filters"`.

**Files:** `sidebar.html`, `enhanced_search.html`

### 5. `page-has-heading-one` — Missing h1 (medium)

**Cause:** Enhanced search pages used `<h3>` for primary content title; public page lacked any `<h1>`.

**Fix:** Public page profile header promoted to `<h1>`; authenticated page gets sr-only `<h1>`; results section demoted to `<h2>`.

**Files:** `public_enhanced_search.html`, `enhanced_search.html`

---

## Verification

```bash
cd a11y-audit
npm ci && npx playwright install chromium
node audit.mjs          # baseline (see summary-before.json)
node audit.mjs --after  # post-fix (summary-after.json)
npx playwright test     # 4/4 passed
```

---

## CI Instructions

Workflow: `.github/workflows/a11y-audit.yml`

Triggers on PRs touching templates/static/a11y-audit. Starts Django, runs `audit.mjs`, then Playwright tests. Reports uploaded as artifacts.

Local PR check:
```bash
cd a11y-audit && npm run audit:after && npm run test:a11y
```

---

## Recommended Monitoring

1. Run `npm run test:a11y` in CI on every PR touching UI templates.
2. Re-audit authenticated routes (`/library/`, `/enhanced/`, `/upload/`) after login flow is testable in CI.
3. Quarterly manual keyboard + screen reader pass (VoiceOver/NVDA) on search → play flow.
4. Suppress axe rules only with inline comment documenting rationale.

---

## Artifacts

| File | Description |
|------|-------------|
| `a11y-audit/summary-before.json` | Baseline aggregate |
| `a11y-audit/summary-after.json` | Post-fix aggregate |
| `a11y-audit/report-*.json` | Per-page raw axe output |
| `a11y-audit/report-*.md` | Human-readable per-page reports |
| `a11y-audit/a11y.spec.mjs` | Playwright e2e tests |
| `a11y-audit/audit.mjs` | Audit runner script |
