"""Generate Google-Ads landing pages: /<SITE>/leads/<city>-<trade>.html

These keyword-matched landers drive paid + organic traffic into the app.
They are NOT produced by build_board.py, so the permit pipeline never
overwrites them. City totals/freshness mirror the live DATA (Oct 13, 2026 pull).

Usage:  python3 scripts/build_landers.py [site_dir]     # default: prototype3
Out:     <site_dir>/leads/index.html + one page per city×trade below.
Board data is read from <site_dir>/index.html, and links use ../ so landers
are relocatable between prototype2/ and prototype3/.

Regenerate whenever the board data refreshes — run right after build_board.py
writes the board pages for the target site.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SITE = sys.argv[1] if len(sys.argv) > 1 else "prototype3"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / SITE / "leads"
BASE = "https://businesslocalrecords.com/{}/leads".format(SITE)
PULLED = "Oct 13, 2026"

# Real per-city weekly totals from the live DATA blob.
CITIES = {
    "los-angeles": {"name": "Los Angeles", "n": 2522, "range": "Sep 29 – Oct 10, 2026"},
    "chicago":      {"name": "Chicago",      "n": 1262, "range": "Sep 29 – Oct 12, 2026"},
    "austin":       {"name": "Austin",       "n": 1974, "range": "Sep 29 – Oct 13, 2026"},
    "philadelphia": {"name": "Philadelphia", "n": 1047, "range": "Sep 29 – Oct 6, 2026"},
    "phoenix":      {"name": "Phoenix",      "n": 626,  "range": "Sep 29 – Oct 12, 2026"},
    "san-francisco": {"name": "San Francisco", "n": 547, "range": "Sep 29 – Oct 9, 2026"},
}
ORDER = ["los-angeles", "chicago", "austin", "philadelphia", "phoenix", "san-francisco"]

# High-intent lead-gen trades (subset of DATA.trades).
TRADES = {
    "roofing": {
        "label": "Roofing",
        "scope": "re-roofs, tear-offs & new roofs",
        "why": "Roofers close more jobs when they call on an address the week the permit drops — before the homeowner has three quotes.",
        "sample": [
            ("Residential re-roof — full tear-off", 148000),
            ("Re-roof 3-story townhome, architectural shingle", 76500),
            ("New roof — dwelling addition", 41200),
            ("Roof repair, structural sheathing", 15800),
            ("Commercial membrane re-roof", None),
        ],
    },
    "electrical": {
        "label": "Electrical",
        "scope": "panel upgrades, EV chargers & new circuits",
        "why": "Electricians and EV-charger installers reach the job first and win the work that never makes it to a referral.",
        "sample": [
            ("Service upgrade 100A → 200A", 12400),
            ("EV charger install, Level 2 + panel add", 9800),
            ("New 20A circuits, kitchen remodel", 6300),
            ("Whole-home rewire, 2,400 sq ft", 28400),
            ("Commercial subpanel + feeders", None),
        ],
    },
    "plumbing": {
        "label": "Plumbing",
        "scope": "repipes, water heaters & gas lines",
        "why": "Plumbers and suppliers see every permitted job in the city, not just the ones that happen to call you.",
        "sample": [
            ("Repipe — replace galvanized supply", 21600),
            ("Water heater replacement, 50 gal tankless", 7400),
            ("New gas line to range + dryer", 3900),
            ("Bathroom addition, full rough-in", 34500),
            ("Commercial backflow + repipe", None),
        ],
    },
    "solar": {
        "label": "Solar",
        "scope": "PV installs, batteries & panel additions",
        "why": "Solar installers target the highest-value rooftops the week the permit is issued, while intent is hot.",
        "sample": [
            ("PV rooftop array, 8.6 kW + battery", 31200),
            ("Solar + battery backup, whole home", 46800),
            ("Rooftop PV array, detached garage", 18900),
            ("Panel addition, service upgrade", 11400),
            ("Commercial rooftop PV, 120 kW", None),
        ],
    },
}
TRADE_ORDER = ["roofing", "electrical", "plumbing", "solar"]


def e(s: str) -> str:
    return html.escape(str(s), quote=True)


def money(n):
    return "Not published" if n is None else "${:,.0f}".format(n)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pretty(iso):
    parts = str(iso).split("-")
    if len(parts) == 3:
        try:
            return "{} {}".format(MONTHS[int(parts[1]) - 1], int(parts[2]))
        except (ValueError, IndexError):
            return str(iso)
    return str(iso)


_DATA = None


def load_board_data():
    """Parse the embedded `const DATA = {...}` from the generated index.html so the
    lander preview uses the SAME real records the board shows. Falls back to {}
    if the board file isn't present (landers still generate)."""
    global _DATA
    if _DATA is not None:
        return _DATA
    idx = OUT.parent / "index.html"
    try:
        m = re.search(r"const DATA = (\{.*\});\s*\nconst SECTION",
                      idx.read_text(encoding="utf-8"), re.S)
        _DATA = json.loads(m.group(1))
    except Exception:
        _DATA = {}
    return _DATA


def city_trade_rows(data, city_id, trade_label, limit=30):
    """Real rows for one city + trade, sorted by job value (nulls last)."""
    if not data or "rows" not in data:
        return [], 0
    cities = data.get("cities", [])
    trades = data.get("trades", [])
    ti = trades.index(trade_label) if trade_label in trades else -1
    if ti < 0:
        return [], 0
    ci = next((i for i, c in enumerate(cities) if c.get("id") == city_id), -1)
    if ci < 0:
        return [], 0
    mask = 1 << ti
    matched = [r for r in data["rows"] if r[1] == ci and (r[5] & mask)]
    total = len(matched)
    matched.sort(key=lambda r: (r[7] is None, -(r[7] or 0)))
    return matched[:limit], total


def preview_rows(rows, free_n=6):
    """Render rows server-side (matches the board): first `free_n` fully visible,
    the rest blurred/gated. JS re-applies the gate after sort/filter."""
    out = []
    for i, r in enumerate(rows):
        value, issued = r[7], r[0]
        addr = r[8] or "—"
        scope = r[9] or "—"
        gated = "" if i < free_n else " row-gated"
        out.append(
            "          <tr class=\"pv-row{g}\" data-value=\"{dv}\" data-issued=\"{di}\">"
            "<td class=\"mono\">{id}</td>"
            "<td class=\"addr\">{ad}</td>"
            "<td class=\"scope\">{sc}</td>"
            "<td class=\"mono\">{mvv}</td>"
            "</tr>".format(
                g=gated, dv=("" if value is None else value), di=e(issued),
                id=pretty(issued), ad=e(addr), sc=e(scope), mvv=money(value))
        )
    return "\n".join(out)


def faq_jsonld(city_name, trade_label, slug):
    items = [
        ("What is {} {} lead data?".format(city_name, trade_label.lower()),
         "It is the list of permits {c} issued this week tagged to {t}. Each lead shows the issue date, address, scope of work, and where published, the job value — so you can prioritise the biggest jobs first.".format(c=city_name, t=trade_label.lower())),
        ("Where does the data come from?",
         "Public building-permit files published by {c} and other cities. Records are pulled on a schedule and refreshed weekly — the latest pull above shows the current date.".format(c=city_name)),
        ("Can I see it before paying?",
         "Yes. Open the live index for {c} and scan this week's permits free. Sign in opens the full list, downloads, and every other city on the index.".format(c=city_name)),
        ("How much does it cost?",
         "$9.99/month. It unlocks every city on the index, the full records past the free preview, and downloads for every city. Cancel anytime."),
    ]
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in items
        ],
    }, ensure_ascii=False)


def head(slug, title, desc, canonical, ld_json, city="", trade=""):
    meta = json.dumps({"slug": slug, "city": city, "trade": trade}, ensure_ascii=False)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#0b2545">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta name="blr:lead" content='{meta}'>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/tokens.css">
<link rel="stylesheet" href="../assets/landing.css">
<link rel="stylesheet" href="../assets/preview.css">
<script type="application/ld+json">{ld}</script>
<script src="/uet.js" async></script>
<script src="/gtag.js" async></script>
</head>""".format(title=e(title), desc=e(desc), canonical=e(canonical), meta=meta, ld=ld_json)


def header():
    return """
<header class="site-header">
  <div class="bar">
    <a class="brand" href="../index.html"><span class="mark">B</span><span>Business Local Records<small>Local project leads</small></span></a>
    <nav>
      <a class="hlink" href="../index.html">Open the index</a>
      <a class="hlink" href="../coverage.html">Coverage</a>
      <a class="hlink" href="../methodology.html">Methodology</a>
      <a class="btn btn-primary" href="../checkout.html" data-track="subscribe_click" data-label="header">Subscribe</a>
    </nav>
  </div>
</header>"""


def footer():
    return """
<footer class="site-footer">
  <div class="ft wrap">
    <a class="brand" href="../index.html"><span class="mark">B</span><span>Business Local Records<small>Local project leads</small></span></a>
    <nav aria-label="Footer">
      <a href="../about.html">About</a>
      <a href="../coverage.html">Coverage</a>
      <a href="../methodology.html">Methodology</a>
      <a href="../terms.html">Terms</a>
      <a href="../privacy.html">Privacy</a>
    </nav>
  </div>
  <div class="copyline"><p>&copy; 2026 Business Local Records · 55 Church St, New York, NY 10007 · sales@businesslocalrecords.com</p></div>
</footer>
<div class="sticky-cta">
  <a class="btn btn-ghost" href="../index.html?city=%CITY%&trade=%TRADELBL%" data-track="open_index" data-label="sticky">Open free index</a>
  <a class="btn btn-primary" href="../checkout.html?city=%CITY%" data-track="subscribe_click" data-label="sticky">Unlock all leads — $9.99/mo</a>
</div>
<script src="../assets/landing.js" defer></script>
<script src="../assets/preview.js" defer></script>"""


def build_lander(city_id, city_name, total, week, trade_key):
    t = TRADES[trade_key]
    slug = "{}-{}".format(city_id, trade_key)
    title = "{t} leads in {c} — new permit projects | Business Local Records".format(t=t["label"], c=city_name)
    desc = ("Every {t} permit {c} issued this week — address, scope of work, and job value — ranked so the biggest jobs "
            "surface first. {n:,} permits pulled. Filter free; sign in to view and download the full list.").format(
        t=t["label"].lower(), c=city_name, n=total)
    canonical = "{}/{}.html".format(BASE, slug)
    ld = faq_jsonld(city_name, t["label"], slug)
    idx = "../index.html?city={c}&trade={t}".format(c=city_id, t=e(t["label"]))
    idx_big = "../index.html?city={c}&trade={t}&size=4".format(c=city_id, t=e(t["label"]))
    co = "../checkout.html?city={c}".format(c=city_id)
    signup = "../signup.html?city={c}".format(c=city_id)
    mail = "mailto:sales@businesslocalrecords.com?subject={}".format(
        e("Done-for-you {t} leads in {c}".format(t=t["label"], c=city_name)).replace(" ", "%20"))

    # Real, interactive preview rows from the live board DATA.
    data = load_board_data()
    pv_rows, pv_total = city_trade_rows(data, city_id, t["label"])
    pv_rows_html = preview_rows(pv_rows)

    faq_pairs = [
        ("What is {c} {t} lead data?".format(c=city_name, t=t["label"].lower()),
         "It is the list of permits {c} issued this week tagged to {t}. Each lead shows the issue date, address, scope of work, and where published, the job value — so you can prioritise the biggest jobs first.".format(c=city_name, t=t["label"].lower())),
        ("Where does the data come from?",
         "Public building-permit files published by {c}. Records are refreshed on a schedule — the latest pull is {p}.".format(c=city_name, p=PULLED)),
        ("Can I see it before paying?",
         "Yes. Open the live {c} index and scan this week's {t} permits free. Sign in opens the full list, downloads, and every other city on the index.".format(c=city_name, t=t["label"].lower())),
        ("How much does it cost?",
         "$9.99/month. It unlocks every city on the index, the full records past the free preview, and downloads for every city. Cancel anytime."),
    ]
    faq_html = "\n".join(
        "    <details><summary>{q}<span class=\"chev\">▾</span></summary><p>{a}</p></details>".format(q=e(q), a=e(a))
        for q, a in faq_pairs
    )

    body = head(slug, title, desc, canonical, ld, city=city_name, trade=t["label"])
    body += header()
    body += """
<main>
  <section class="hero">
    <div class="wrap inner">
      <nav class="crumbs"><a href="../index.html">Records</a><span class="sep">/</span><a href="index.html">Leads</a><span class="sep">/</span><span>{c}</span></nav>
      <div class="hero-grid">
        <div>
          <span class="eyebrow"><span class="badge"><span class="dot"></span>Fresh for the week of {wk}</span></span>
          <h1>{c} <span class="hl">{t}</span> leads<br>before your competitors call.</h1>
          <p class="sub">See every {t} permit {c} issued this week — {sc} — with the address, scope of work, and job value. Ranked so the {big} surface first.</p>
          <div class="cta-row">
            <a class="btn btn-primary btn-lg" href="{idx}" data-track="open_index" data-label="hero">Scan this week's {t} leads — free</a>
            <a class="btn btn-cta btn-lg" href="{co}" data-track="subscribe_click" data-label="hero">Unlock the full list</a>
          </div>
          <p class="micro">Free preview in the browser · No card to scan · Newsletter unsubscribe anytime</p>
        </div>
        <div class="hero-card">
          <div class="hrow">
            <div class="hero-stat"><div class="n tnum">{total:,}</div><div class="k">permits pulled this week</div></div>
            <div class="hero-stat"><div class="n tnum">{pulled}</div><div class="k">last data refresh</div></div>
          </div>
          <div class="hero-card" style="border:0;background:none;padding:{s4} 0 0">
            <a class="btn btn-ghost btn-block" href="{idx_big}" data-track="open_index_high_value" data-label="hero_card">Show only $100k+ {t} jobs ▸</a>
          </div>
          <div class="foot"><span class="dot"></span>Full list, downloads &amp; every city with a $9.99/mo membership.</div>
        </div>
      </div>
    </div>
  </section>

  <section class="section alt">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow center">How it works</span>
        <h2>From public permits to your next booked job</h2>
        <p>No cold lists. No guessing. Just the permits {c} actually issued, ranked by value.</p>
      </div>
      <div class="steps">
        <div class="step"><div class="num">1</div><h3>Pick city &amp; trade</h3><p>{c} is already selected for {t}. Filter by permit type, size band, or search an address instantly.</p></div>
        <div class="step"><div class="num">2</div><h3>Scan ranked leads free</h3><p>Newest and biggest jobs first. Read address, scope of work, and job value in the free preview.</p></div>
        <div class="step"><div class="num">3</div><h3>Unlock &amp; download</h3><p>Sign in for the full list, one-click CSV/Excel, and alerts when a new {t} permit matches.</p></div>
      </div>
    </div>
  </section>

  <section class="section" id="preview">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow center">This week's records · live preview</span>
        <h2>{c} {t} permits, ranked by value</h2>
        <p>Real records {c} issued this week. Sort and filter below — the biggest jobs rise to the top. <strong>Sign in to read all {pvtot}.</strong></p>
      </div>
      <div class="live-preview" data-total="{pvtot}">
        <div class="pv-bar">
          <div class="pv-chips" role="group" aria-label="Quick filters">
            <span class="pv-lbl">Filter</span>
            <button type="button" class="pv-chip on" data-filter="all">All</button>
            <button type="button" class="pv-chip" data-filter="100k">$100k+</button>
            <button type="button" class="pv-chip" data-filter="10-50k">$10k–$50k</button>
          </div>
          <div class="pv-sorts" role="group" aria-label="Sort">
            <span class="pv-lbl">Sort</span>
            <button type="button" class="pv-sort on" data-sort="value">Job value</button>
            <button type="button" class="pv-sort" data-sort="issued">Newest</button>
          </div>
        </div>
        <div class="scroller">
          <table class="sample pv-table">
            <thead><tr><th>Issued</th><th>Address</th><th>Scope of work</th><th>Job value</th></tr></thead>
            <tbody id="pv-body">
{pvrows}
            </tbody>
          </table>
        </div>
        <div class="pv-gate" id="pv-gate">
          <span class="pv-gate-txt">You're previewing the top jobs. Sign in to view every {t} permit {c} issued this week.</span>
          <div class="pv-gate-actions">
            <a class="btn btn-primary" href="{signup}" data-track="subscribe_click" data-label="preview_gate">Sign in to view all {pvtot}</a>
            <a class="btn btn-ghost" href="{idx}" data-track="open_index" data-label="preview_open">Open full index</a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section alt">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow center">Why {t} teams use it</span>
        <h2>{why}</h2>
      </div>
      <div class="fits">
        <div class="fit"><div class="ic">🔨</div><h4>{t} contractors</h4><p>Bid earlier. Call the address the week it's permitted, not months later.</p></div>
        <div class="fit"><div class="ic">🚚</div><h4>Suppliers</h4><p>Know which jobs need material before the PO lands.</p></div>
        <div class="fit"><div class="ic">📞</div><h4>Sales &amp; reps</h4><p>Route by size band and geography for tighter territories.</p></div>
        <div class="fit"><div class="ic">🏢</div><h4>Service firms</h4><p>Find properties with active, funded work already approved.</p></div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow center">Choose your access</span>
        <h2>Scan free, then unlock everything</h2>
      </div>
      <div class="offers">
        <div class="offer">
          <span class="tag">Free</span>
          <div class="price">$0</div>
          <ul>
            <li>Scan {c}'s {t} permits in the browser</li>
            <li>Address, scope, and job value preview</li>
            <li>Filter by size, type, and search</li>
          </ul>
          <a class="btn btn-ghost" href="{idx}" data-track="open_index" data-label="offer_free">Scan free now</a>
        </div>
        <div class="offer featured">
          <span class="tag">Membership</span>
          <div class="price">$9.99<small>/month</small></div>
          <ul>
            <li>Every city on the index</li>
            <li>Full records past the free preview</li>
            <li>CSV / Excel downloads for every city</li>
            <li>Email alerts when a {t} permit matches</li>
          </ul>
          <a class="btn btn-primary" href="{co}" data-track="subscribe_click" data-label="offer_subscribe">Unlock full list</a>
        </div>
        <div class="offer">
          <span class="tag">Done-for-you</span>
          <div class="price">Talk to us</div>
          <ul>
            <li>We build &amp; deliver your lead list</li>
            <li>Tailored trades, zones &amp; value bands</li>
            <li>Set up once, delivered weekly</li>
          </ul>
          <a class="btn btn-ghost" href="{mail}" data-track="contact_dfy" data-label="offer_dfy">Get a quote</a>
        </div>
      </div>
    </div>
  </section>

  <section class="section alt">
    <div class="wrap">
      <div class="section-head">
        <span class="eyebrow center">FAQ</span>
        <h2>Questions, answered</h2>
      </div>
      <div class="faq">
{faq}
      </div>
    </div>
  </section>

  <section class="section alt" id="newsletter">
    <div class="wrap nl-wrap">
      <div class="nl-copy">
        <span class="eyebrow">Free weekly digest</span>
        <h2>Get the week's new {t} permits in {c}.</h2>
        <p>One short email each week with the newest, biggest {t} permits {c} issued. No spam — unsubscribe anytime.</p>
      </div>
      <form class="nl-form" id="nl-form" data-city="{cid}" data-trade="{t}" novalidate>
        <input type="email" name="email" required placeholder="you@company.com" aria-label="Work email">
        <button class="btn btn-primary" type="submit">Send this week's leads</button>
        <p class="nl-note" id="nl-note" role="status" hidden></p>
      </form>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="cta-band">
        <h2>{c}'s {t} permits are public.<br>Your competitors just aren't reading them.</h2>
        <p>This week's {total:,} records are live now. Scan them free, and unlock the full list when you're ready.</p>
        <div class="cta-row">
          <a class="btn btn-primary btn-lg" href="{co}" data-track="subscribe_click" data-label="final">Unlock everything — $9.99/mo</a>
          <a class="btn btn-ghost btn-lg" href="{idx}" data-track="open_index" data-label="final" style="background:transparent;color:#fff;border-color:rgba(255,255,255,.4)">Or scan free first</a>
        </div>
      </div>
    </div>
  </section>
</main>
 """.format(
        c=city_name, t=t["label"], sc=e(t["scope"]), big="biggest jobs", wk=e(week), cid=city_id,
        total=total, pulled=PULLED, idx=idx, idx_big=idx_big, co=co, mail=mail, signup=signup,
        pvrows=pv_rows_html, pvtot="{:,}".format(pv_total), why=e(t["why"]), faq=faq_html,
        s4="var(--s4)", s5="var(--s5)",
    )
    body += footer().replace("%CITY%", city_id).replace("%TRADELBL%", e(t["label"]))
    body += "\n</body>\n</html>\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (slug + ".html")).write_text(body, encoding="utf-8")
    return slug


def build_hub():
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Local construction & trade leads by city",
        "description": "Fresh, public building-permit leads by city and trade — scanned free, fully unlocked with a $9.99/mo membership.",
    }
    title = "Local construction leads by city & trade | Business Local Records"
    desc = "Fresh permit leads by city and trade. Roofing, electrical, plumbing & solar permits, ranked by job value. Scan free, unlock the full list for $9.99/mo."
    body = head("index", title, desc, BASE + "/index.html", json.dumps(ld, ensure_ascii=False))
    body += """
<header class="site-header">
  <div class="bar">
    <a class="brand" href="../index.html"><span class="mark">B</span><span>Business Local Records<small>Local project leads</small></span></a>
    <nav>
      <a class="hlink" href="../index.html">Open the index</a>
      <a class="hlink" href="../coverage.html">Coverage</a>
      <a class="hlink" href="../methodology.html">Methodology</a>
      <a class="btn btn-primary" href="../checkout.html" data-track="subscribe_click" data-label="hub_header">Subscribe</a>
    </nav>
  </div>
</header>
<main>
  <section class="hero">
    <div class="wrap inner">
      <div class="hero-grid">
        <div>
          <span class="eyebrow"><span class="badge"><span class="dot"></span>Updated {pulled}</span></span>
          <h1>Local construction leads,<br><span class="hl">sorted by the city you serve.</span></h1>
          <p class="sub">Public building-permit records for {ncities} cities, tagged to roofing, electrical, plumbing and solar. Ranked by job value so the biggest projects rise to the top.</p>
          <div class="cta-row">
            <a class="btn btn-primary btn-lg" href="../index.html" data-track="open_index" data-label="hub_hero">Open the live index</a>
            <a class="btn btn-cta btn-lg" href="../checkout.html" data-track="subscribe_click" data-label="hub_hero">Unlock full list — $9.99/mo</a>
          </div>
          <p class="micro">Scan free in the browser · Cancel anytime</p>
        </div>
        <div class="hero-card">
          <div class="hrow">
            <div class="hero-stat"><div class="n tnum">{citiescount}</div><div class="k">cities indexed</div></div>
            <div class="hero-stat"><div class="n tnum">4</div><div class="k">high-intent trades</div></div>
          </div>
          <div class="foot"><span class="dot"></span>Pick your city below to scan this week's permits free.</div>
        </div>
      </div>
    </div>
  </section>
  <section class="section">
    <div class="wrap">
      <div class="section-head"><span class="eyebrow center">Pick your city</span><h2>Leads by city</h2></div>
      <div class="offers">
""".format(pulled=PULLED, ncities=len(ORDER), citiescount=len(ORDER))
    cards = []
    for cid in ORDER:
        c = CITIES[cid]
        links = " ".join(
            '<a class="btn btn-ghost" style="min-height:38px;font-size:var(--step--1)" href="{cid}-{tk}.html" data-track="open_landing" data-label="hub_{cid}_{tk}">{lbl}</a>'.format(
                cid=cid, tk=tk, lbl=e(TRADES[tk]["label"])) for tk in TRADE_ORDER)
        cards.append(
            '        <div class="offer"><span class="tag">{name}</span>'
            '<div class="price tnum">{n:,}<small> permits / week</small></div>'
            '<p style="color:var(--muted)">Week of {wk}</p>'
            '<div style="display:flex;flex-wrap:wrap;gap:var(--s2);margin:var(--s3) 0">{links}</div>'
            '<a class="btn btn-cta" href="../index.html?city={cid}" data-track="open_index" data-label="hub_open">Open {name} index</a></div>'.format(
                name=e(c["name"]), n=c["n"], wk=e(c["range"]), links=links, cid=cid))
    body += "\n".join(cards)
    body += """
      </div>
    </div>
  </section>
</main>
"""
    body += footer().replace("%CITY%", "").replace("%TRADELBL%", "")
    body += "\n</body>\n</html>\n"
    (OUT / "index.html").write_text(body, encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    made = 0
    for cid in ORDER:
        c = CITIES[cid]
        for tk in TRADE_ORDER:
            build_lander(cid, c["name"], c["n"], c["range"], tk)
            made += 1
    build_hub()
    write_seo_files()
    print("Wrote {} city×trade landers + index + sitemap/robots to {}".format(made, OUT))


def write_seo_files():
    """Emit sitemap.xml + robots.txt for the landers (board app stays noindex)."""
    urls = [BASE + "/index.html"]
    for cid in ORDER:
        for tk in TRADE_ORDER:
            urls.append("{}/{}-{}.html".format(BASE, cid, tk))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += ["  <url><loc>{}</loc><changefreq>weekly</changefreq></url>".format(u) for u in urls]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")

    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        "# Board app pages are noindex; only the /leads/ landers are crawlable.\n"
        "Sitemap: {}/sitemap.xml\n".format(BASE)
    )
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")


if __name__ == "__main__":
    main()
