# FinAlly frontend

Next.js + TypeScript + Tailwind, built as a static export. `npm run build` writes
`out/`, which the Dockerfile copies into the backend's `static/` directory.

```
npm install
npm run dev     # http://localhost:3000, API at NEXT_PUBLIC_API_BASE (.env.development)
npm run build   # static export to out/
npm run lint
npm test
```

`NEXT_PUBLIC_API_BASE` is empty in production (same origin as the backend).
