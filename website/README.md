# ResearchClaw Website

Static landing page and docs site for ResearchClaw, built with React + Vite.

The site now documents both sides of the product:

- the runtime/control-plane platform
- the Research OS layer for projects, workflows, experiments, claims, evidence, and blockers

## Install

```bash
cd website
corepack pnpm install
```

## Development

```bash
corepack pnpm run dev
```

Dev server: `http://localhost:5173`.

## Build

```bash
corepack pnpm run build
```

The build pipeline does three things:

1. generate docs search index with `scripts/build-search-index.mjs`
2. run the Vite production build
3. generate SPA fallback pages with `scripts/spa-fallback-pages.mjs`

Output goes to `dist/`.

## Preview

```bash
corepack pnpm run preview
```

## Docs Authoring Notes

- docs content lives in `public/docs/`
- every public docs page should have both `*.en.md` and `*.zh.md`
- if you add a new docs slug, update `src/pages/Docs.tsx`
- FAQ pages are parsed from `###` headings, not from `<details>` blocks
- `public/search-index.json` is generated during build, so it may change after doc edits

## Scope

This site is separate from the runtime console:

- `website/` is the public docs and landing site
- `console/` is the authenticated runtime UI served by the backend
