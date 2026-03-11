# ResearchClaw Website

Vite + React static docs/landing site for ResearchClaw.

## Prerequisites

- Node.js 18+
- pnpm (recommended) or npm

## Install

```bash
pnpm install
# or
npm install
```

## Development

```bash
pnpm run dev
```

Dev server: `http://localhost:5173`.

## Build

```bash
pnpm run build
```

Build pipeline includes:

1. docs search index generation (`scripts/build-search-index.mjs`)
2. Vite production build
3. SPA fallback page generation (`scripts/spa-fallback-pages.mjs`)

Output: `dist/`.

## Preview

```bash
pnpm run preview
```

## Docs Content

- Markdown docs live in `public/docs` as `*.en.md` and `*.zh.md`.
- Keep bilingual docs in sync.
- If you add a new docs page slug, update `src/pages/Docs.tsx` sidebar/title mappings.

## Deployment Docs Entry

The deployment guide is now part of docs:

- `public/docs/deployment.en.md`
- `public/docs/deployment.zh.md`
