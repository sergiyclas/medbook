# MedBook – web client

React + TypeScript single-page app built with Vite. It talks only to the REST
API under `/api/v1` – in development Vite proxies it to `http://localhost:8000`,
in the Docker image nginx does the same (see `nginx.conf`).

```bash
npm install
npm run dev      # http://localhost:5173, backend must run on :8000
npm run build    # type-check (tsc -b) + production bundle in dist/
npm run lint     # oxlint
```

Structure: `src/api` (typed client), `src/auth` (session), `src/components`
(talon, slot picker, dialogs), `src/pages/{public,patient,doctor,admin}`.
