# Business Local Records

Funnel website that delivers constant, reliable value as a foot in the door —
leaving potential customers wanting more of the wider service. Not because the
wheel was reinvented, but because of how much time the index saves them and how
easy it makes finding local project leads.

## What this is

A B2B lead-gen funnel that sells access to **local building-permit records**
(building permits, occupancy, and sign permits) for contractors, suppliers, and
trades. Guests scan a city's ranked permit "tape" free; members unlock the full
list, downloads, and alerts.

## Two co-existing prototypes

| Path | What | Status |
| --- | --- | --- |
| `index.html`, `occupancy.html`, `signs.html`, `checkout/signup/portal/account.html`, `about/coverage/methodology/privacy/terms.html`, `chrome.css`, `chrome.js` (repo root) | **Prototype 2** — the current live funnel, served at `/prototype2/` | **Live. Do not modify** without intent to change production. |
| `prototype3/**` | **Prototype 3** — the new CPC-optimized full production, served at `/prototype3/` | New. Isolated from Prototype 2. |

Prototype 3 is **self-contained** (its own board, landers, assets, conversion +
legal pages) under `prototype3/`. It reuses the shared backend `/api/index.php`,
the PayPal plan/client id, and the Google (`gtag`) + Microsoft (`uetq`) pixels —
all domain-wide, so membership state carries across both. It ships prebuilt
board HTML with embedded `DATA` (CI never rebuilds the board).

Prototype 3 adds: a conversion hero above the board, city×trade **Google-Ads
landers with a live, interactive preview** (real records, sort/filter, gated
rows), three-tier offers incl. done-for-you, a newsletter/digest capture,
`thanks.html` onboarding + upsell, `sitemap.xml`/`robots.txt`, and conversion
events (`open_index`, `subscribe_click`, `newsletter_signup`, `contact_dfy`).

## Repo → live mapping

Deploy targets: repo root → `public_html/prototype2/`; `prototype3/` →
`public_html/prototype3/`. Everything else (`/api/`, `/uet.js`, `/gtag.js`,
per-city archive boards) lives outside this repo.

## Data pipeline (offline)

Board pages are generated offline by `build_board.py` from external per-city
`data/<city>/{permits.csv,meta.json}` + a shared `build_site.py` (outside the
repo). **CI never rebuilds the board** — it deploys committed HTML. To refresh:
run the pipeline so it writes the board for the target prototype, then commit.

## Landing pages (Prototype 3)

Keyword-matched city×trade landers with a **live interactive preview** (real
records from the board `DATA`, sortable/filterable, gated rows that unlock to a
full-page sign-in). Regenerate — and re-run right after any board-data refresh:

```bash
python3 scripts/build_landers.py          # default: prototype3
python3 scripts/build_landers.py prototype2   # or any other site dir
```

Output: `<site>/leads/` (hub + one page per city×trade) + `sitemap.xml` +
`robots.txt`. Board pages stay `noindex`; only `/leads/` landers are crawlable.
Edit `CITIES`/`TRADES`/per-trade copy at the top of `scripts/build_landers.py`
to add cities or trades.

## Deploy (push → GitHub Actions → Network Solutions)

**A commit alone does NOT update the host** — the GitHub **Actions** deploy
workflows do (they FTP the files to the target directory; you then see them in
the cPanel File Manager under that folder). Two workflows:

- `.github/workflows/deploy.yml` — root → `public_html/prototype2/` (Prototype 2, unchanged).
- `.github/workflows/deploy-prototype3.yml` — `prototype3/` → `public_html/prototype3/` (Prototype 3). Triggered by pushes that touch `prototype3/**`.

Required GitHub **Secrets**: `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`.
Optional **Variables**: `FTP_SERVER_DIR` (default `public_html/prototype2/`),
`FTP_SERVER_DIR_P3` (default `public_html/prototype3/`).

**Manual fallback** (one-off push or IP-blocked runners):

```bash
export FTP_SERVER=ftp.businesslocalrecords.com FTP_USER=... FTP_PASS=...
FTP_SERVER_DIR=public_html/prototype3/ bash scripts/deploy.sh   # Prototype 3
# omit FTP_SERVER_DIR to deploy the root (Prototype 2)
```

If GitHub Actions IPs are blocked by the host, use the manual script or the SFTP
variant noted in the workflow.

## Pricing / offers

- **Free** — scan a city's ranked permits in the browser.
- **Membership $9.99/mo** — every city, full records, CSV/Excel downloads, alerts. Cancel anytime.
- **Done-for-you** — we build & deliver your tailored lead list (`sales@businesslocalrecords.com`).

## Design system

`prototype3/assets/tokens.css` is the single source of truth (palette, type,
spacing, radii, elevation, buttons, cards). `landing.css`/`preview.css` +
`landing.js`/`preview.js` build the landers and the interactive preview on top
of it; `board.css` overlays the board's inline styles. Conversion events fire to
`gtag`/`uetq` only when present and never break the page.
