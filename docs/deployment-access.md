# Deployment & access model

Goal: teammates can reach a real, live deployment to test against, without
getting access to the underlying server, SSH keys, Docker host, or any of
my other personal infrastructure.

## How it's structured

This project is a **self-contained Compose stack** (`docker-compose.yml` at
the repo root) with no dependency on anything else running on the host.
That's deliberate - it means:

- Anyone who clones the repo *could* run `docker compose up --build`
  themselves, on their own machine or any server. The project itself is
  not locked to my infrastructure.
- In practice, **only I deploy it**, on my own home server, on its own
  subdomain (e.g. `ws-demo.<my-domain>`), fully separate from any other
  service running there.

## What teammates get

- A public HTTPS URL (e.g. `https://ws-demo.<my-domain>`) they can open in
  a browser like any other live website.
- No SSH access, no Docker/Compose access, no Cloudflare Tunnel or reverse
  proxy config access, no credentials of any kind.
- They can still run the *whole stack themselves* locally if they want to
  develop or test independently - the repo is fully portable - they just
  can't touch my deployment of it.

## Why not give them real deploy access?

- Keeps a uni group project cleanly separated from personal infrastructure
  (SSH keys, other self-hosted services, DNS, tunnel config).
- Avoids "who broke prod" problems on infra that also runs unrelated
  personal services.
- If something needs to change, they open a PR / hand me the diff, I deploy.
  This is also just... how most real-world deployments to a shared
  environment work, so it doubles as a reasonable thing to mention in a
  uni report if access-control reasoning is in scope.

## If the course requires "the team can deploy"

If a grading requirement is that all team members must be *able* to deploy
(not just me), the cleanest fix without opening up my personal server is:

- Each person deploys the **same Compose stack** to their own free-tier
  environment (e.g. a student cloud credit, or just running it locally and
  demoing from their own laptop during presentation).
- Or: spin up one shared, project-only VM/account (not tied to my personal
  domain or server) that the team manages together, separate from my
  Horst-Lichter setup entirely.

Either of those satisfies "everyone can deploy" while still keeping my
personal infrastructure out of it.
