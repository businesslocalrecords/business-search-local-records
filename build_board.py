"""Build the permit-tape prototype from the city CSVs.

The page is a scanner: trade, street, and size range are on the tape.
House number, scope of work, and exact job value stay in the city files.
"""

import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import build_site as b
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "index.html"

HOUSE = re.compile(
    r"^\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?(?:\s+\d/\d(?:-\d/\d)?)?\s+"
)
UNIT = re.compile(r"(?:\s+(?:BLDG|BUILDING|UNIT|APT|STE|SUITE|#)\s*[\w-]+)+$")
BANDS = ["Not published", "Under $10k", "$10k–$50k", "$50k–$100k", "$100k–$500k", "$500k+"]


def street_name(address):
    text = re.sub(r"\s+", " ", (address or "").strip())
    stripped = UNIT.sub("", HOUSE.sub("", text)).strip(" ,")
    if not stripped or stripped == text:
        return ""
    return stripped.upper()


def band_of(value):
    if value is None:
        return 0
    if value < 10_000:
        return 1
    if value < 50_000:
        return 2
    if value < 100_000:
        return 3
    if value < 500_000:
        return 4
    return 5


def short_day(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return d.strftime("%b ") + str(d.day)


def load():
    cities = []
    types, streets = [], []
    type_ix, street_ix = {}, {}
    rows_out = []
    for city_dir in sorted(p for p in DATA.iterdir() if (p / "permits.csv").exists() and (p / "meta.json").exists()):
        meta = json.loads((city_dir / "meta.json").read_text(encoding="utf-8"))
        raw = list(csv.DictReader((city_dir / "permits.csv").open(encoding="utf-8")))
        dates = sorted(r["issue_date"] for r in raw)
        range_text = f"{b.day(dates[0])} to {b.long_day(dates[-1])}".replace(" to ", " \u2013 ")
        ci = len(cities)
        cities.append(
            {
                "id": meta["city"],
                "label": meta["label"],
                "href": f"../{meta['city']}/{dates[0]}/",
                "n": len(raw),
                "range": range_text,
                "pulled": b.long_day(meta["generated"][:10]),
                "weeks": [{"id": dates[0], "range": range_text, "pulled": b.long_day(meta["generated"][:10])}],
            }
        )
        for row in raw:
            value = b.to_float(row["job_value"])
            desc = (row["permit_type"] + " " + row["work_description"]).upper()
            mask = 0
            for bit, (label, word) in enumerate(b.KEYWORDS):
                if word in desc:
                    mask |= 1 << bit
            typ = b.clean_type(row["permit_type"]) or "Permit"
            if typ not in type_ix:
                type_ix[typ] = len(types)
                types.append(typ)
            street = street_name(row["address"])
            if street not in street_ix:
                street_ix[street] = len(streets)
                streets.append(street)
            # date, city, type, street, band, trade mask. No address, value, scope, or permit number.
            scope = re.sub(r"\s+", " ", row["work_description"] or "").strip()
            address = re.sub(r"\s+", " ", (row["address"] or "").strip())
            rows_out.append(
                [
                    row["issue_date"],
                    ci,
                    type_ix[typ],
                    street_ix[street],
                    band_of(value),
                    mask,
                    0,
                    None if value is None else int(round(value)),
                    address,
                    scope,
                ]
            )
            for field in ("address", "permit_number", "work_description", "job_value"):
                if field in rows_out[-1]:
                    raise SystemExit("paid field leaked into a row")
    rows_out.sort(key=lambda r: (r[4], r[0]), reverse=True)
    return {
        "trades": [label for label, _ in b.KEYWORDS],
        "bands": BANDS,
        "cities": cities,
        "types": types,
        "streets": streets,
        "rows": rows_out,
    }


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="__CANON__">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<meta name="theme-color" content="#0b2545">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --bp:#0b2545; --ink:#14181f; --muted:#5c6570; --paper:#f4f6f8; --card:#fff; --line:#d9dee6;
  --sans:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;padding-top:64px;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:var(--bp);text-decoration:none}
a:hover{text-decoration:underline}
button,select{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--bp);outline-offset:2px}
.top{background:var(--bp);color:#fff;border-bottom:1px solid rgba(255,255,255,.08)}
.top-inner,.wrap{width:min(1120px,calc(100% - 2rem));margin:0 auto}
.top-inner{display:flex;align-items:center;gap:.4rem;height:64px}
.top .top-inner{position:fixed;top:0;left:0;right:0;z-index:40;box-sizing:border-box;width:auto;margin:0;padding:0 max(1rem,calc((100vw - 1120px) / 2));background:var(--bp);border-bottom:1px solid rgba(255,255,255,.08)}
.brand{font-weight:600;font-size:18px;letter-spacing:.12em;color:#fff;text-decoration:none;white-space:nowrap}
.top .brand{font-family:inherit;font-size:17px;font-weight:500;letter-spacing:.015em;line-height:1;color:rgba(255,255,255,.72)}
.top .brand:hover{text-decoration:none;color:rgba(255,255,255,.92)}
.sections{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.15rem;width:min(1120px,calc(100% - 2rem));margin:0 auto;padding:0 0 1.1rem}
.sections a{box-sizing:border-box;display:flex;align-items:center;justify-content:center;width:auto;min-height:58px;text-align:center;color:rgba(255,255,255,.92);font-size:16px;font-weight:500;letter-spacing:.01em;line-height:1.3;text-decoration:none;padding:1.05rem 1.75rem;border:1px solid rgba(255,255,255,.88);border-radius:4px}
@media(max-width:760px){
  .top .top-inner{height:auto;min-height:64px;padding:.75rem max(1rem,calc((100vw - 1120px) / 2)) .2rem}
  .sections{grid-template-columns:1fr;justify-items:center;gap:.65rem;padding:1.2rem 0 .9rem}
  .sections a{width:min(280px,100%);min-height:40px;padding:.5rem 1rem;font-size:15px}
}
.sections a:hover{color:#fff;border-color:#fff;text-decoration:none}
.sections a.on{color:#fff;border-color:#fff;background:rgba(255,255,255,.08)}
.head-actions{margin-left:auto;display:flex;align-items:center;gap:.35rem}
#headsub{display:inline-flex;align-items:center;height:36px;padding:0 .7rem;border:0;background:transparent;color:rgba(255,255,255,.78);font-weight:500;font-size:14px;line-height:1;cursor:pointer;text-decoration:none}
#headsub:hover{color:#fff;text-decoration:none}
#headsub[hidden]{display:none}
#signin{display:inline-flex;align-items:center;justify-content:center;height:36px;max-width:220px;padding:0 1rem;border:0;border-radius:8px;background:#fff;color:var(--bp);font-weight:600;font-size:14px;line-height:1;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#signin:hover{background:#f4f7fb}
.cities{display:flex;flex-wrap:wrap;justify-content:center;gap:.2rem 1.15rem;padding:0 1rem .65rem}
.cities a{color:rgba(255,255,255,.72);font-size:13.5px;font-weight:500;text-decoration:none;padding:.05rem 0;border-bottom:2px solid transparent}
.cities a:hover{color:#fff;text-decoration:none}
.cities a.on{color:#fff;border-bottom-color:#fff}
@media(max-width:760px){.cities{display:none}}
#nav-account{display:inline-flex;align-items:center;height:36px;color:rgba(255,255,255,.92);font-size:14px;font-weight:500;line-height:1;text-decoration:none;padding:0 .7rem}
#nav-account[hidden]{display:none}
.start{margin:1.15rem 0 0;font-size:15px;font-weight:600;letter-spacing:-.02em;color:var(--ink)}
.controls{display:grid;gap:.75rem;grid-template-columns:1fr;padding:.45rem 0 .25rem;align-items:end}
@media(min-width:1100px){.controls{grid-template-columns:1.05fr 1.2fr .95fr .9fr .8fr 1.15fr auto}}
label.f{display:flex;flex-direction:column;gap:.35rem;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
label.f select,label.f input{text-transform:none;letter-spacing:0;font-weight:500;font-size:16px;background:#fff;border:1px solid #b7c0cc;border-radius:8px;min-height:48px;padding:0 .75rem;width:100%;box-shadow:0 1px 0 rgba(11,37,69,.04)}
label.f select{padding-right:2rem;appearance:none;background:#fff url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='%230b2545' d='M1 1l5 5 5-5'/></svg>") no-repeat right .9rem center}
.clear{min-height:48px;padding:0 .95rem;border:1px solid #b7c0cc;border-radius:8px;background:#fff;font-weight:600;cursor:pointer}
.clear:hover{border-color:var(--bp);color:var(--bp)}
.board{margin-top:1rem;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.status{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;justify-content:space-between;padding:.7rem .9rem;color:var(--muted);font-size:13px;border-bottom:1px solid var(--line)}
.status b{color:var(--ink);font-weight:600}
.status-actions{display:flex;align-items:center;gap:.75rem}
.filter-wrap{position:relative}
.filter-btn{display:inline-flex;align-items:center;gap:.4rem;min-height:36px;padding:0 .7rem;border:1px solid #b7c0cc;border-radius:8px;background:#fff;color:var(--ink);font-weight:600;font-size:13px;cursor:pointer}
.filter-btn svg{width:14px;height:14px;display:block}
.filter-btn:hover,.filter-btn.on{border-color:var(--bp);color:var(--bp);background:#f4f7fb}
.filter-menu{position:absolute;right:0;top:calc(100% + .35rem);z-index:30;width:250px;padding:.8rem;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 32px rgba(11,37,69,.16)}
.filter-menu[hidden]{display:none}
.filter-menu label.f{margin-bottom:.65rem}
.filter-menu label.f:last-child{margin-bottom:0}
.filter-menu label.f select{min-height:40px;font-size:14px}
.dl-go{width:100%;min-height:40px;margin-top:.15rem;border:0;border-radius:8px;background:var(--bp);color:#fff;font-weight:600;font-size:14px;cursor:pointer}
.dl-go:hover{background:#163a66}
a.dl-go{display:flex;align-items:center;justify-content:center;text-decoration:none}
a.dl-go:hover{color:#fff;text-decoration:none}
.offer-lead{margin:0 0 .75rem;color:var(--ink);font-size:13px;line-height:1.45}
.offer-up{display:block;margin-top:.55rem;text-align:center;color:var(--bp);font-weight:600;font-size:14px;text-decoration:none}
.offer-up:hover{text-decoration:underline}
.alert-menu{width:280px}
.alert-menu .fine{margin:.55rem 0 0;color:var(--muted);font-size:12px;line-height:1.4}
.alert-off{width:100%;min-height:36px;margin-top:.45rem;border:0;background:none;color:var(--muted);font-weight:600;font-size:13px;cursor:pointer}
.alert-off:hover{color:var(--bp)}
#openfull{background:none;border:0;padding:0;color:var(--bp);font-weight:600;font-size:13px;cursor:pointer}
#openfull:hover{text-decoration:underline}
#openfull[hidden]{display:none}
.scroller{overflow:auto}
table{width:100%;border-collapse:collapse;min-width:920px}
th,td{text-align:left;border-top:1px solid var(--line);vertical-align:top}
td{padding:.7rem .85rem}
th{padding:0;background:#f7f8fa}
th button{display:flex;align-items:center;gap:.35rem;width:100%;padding:.7rem .85rem;border:0;background:transparent;cursor:pointer;color:#3d4654;font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:600;text-align:left}
th button:hover{color:var(--bp)}
tr.cols th[aria-sort="ascending"],tr.cols th[aria-sort="descending"]{background:#0b2545}
th[aria-sort="ascending"] button,th[aria-sort="descending"] button,th[aria-sort="ascending"] button:hover,th[aria-sort="descending"] button:hover{color:#fff}
.arr{font-size:12px;min-width:.7em;color:inherit}
td.sorted{background:#e4edf6}
td.mono{font-family:var(--mono);font-size:12px;white-space:nowrap}
td.addr{font-weight:600}
td.scope{font-size:13px;color:#2a313b;white-space:normal}
td.trade{font-size:13px;white-space:normal}
.group td{padding:0;background:#eef2f6;border-top:1px solid #d3dae3}
.group button.fold{display:flex;align-items:center;gap:.55rem;width:100%;padding:.65rem .85rem;border:0;background:transparent;cursor:pointer;font-weight:600;font-size:13px;text-align:left;color:var(--ink)}
.group button.fold:hover{background:#e7edf3}
.group .chev{width:.85em;color:var(--muted);font-size:11px}
.group .n{margin-left:auto;font-variant-numeric:tabular-nums}
tr.cols th{padding:0;background:#fff}
tr.cols th.plain{padding:.7rem .85rem;color:#3d4654;font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:600}
tr.peek{cursor:pointer}
tr.data td{box-sizing:border-box;vertical-align:top}
tr.peek td{filter:blur(5px);user-select:none}
.pager td{padding:.65rem .85rem;background:#f7f8fa}
.pager nav{display:flex;flex-wrap:wrap;gap:.35rem;align-items:center}
.pager button{min-width:36px;min-height:36px;padding:0 .55rem;border:1px solid #b7c0cc;border-radius:8px;background:#fff;color:var(--bp);font-weight:600;cursor:pointer}
.pager button[aria-current="page"]{background:var(--bp);color:#fff;border-color:var(--bp);cursor:default}
.pager .gap{color:var(--muted);padding:0 .15rem}
.pager .hint{border:0;background:none;color:var(--bp);font-weight:600;min-width:0;margin-left:.35rem;cursor:pointer}
.pager .hint:hover{text-decoration:underline}
tr.gate td{padding:.35rem .85rem .55rem;background:#fff}
tr.gate button{border:0;background:none;padding:0;color:var(--bp);font-size:13px;font-weight:600;cursor:pointer}
tr.gate button:hover{color:var(--bp);text-decoration:underline}
.empty{padding:1.4rem .9rem;color:var(--muted)}
.pay{display:flex;flex-wrap:wrap;gap:1rem;align-items:center;justify-content:space-between;padding:1.1rem .95rem;border-top:1px solid var(--line);background:#f7f8fa}
.pay p{margin:0}
.pay .k{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.pay .amt{font-weight:600;font-size:16px;letter-spacing:-.02em;margin-top:.15rem}
.pay .sub{color:var(--muted);font-size:13px;margin-top:.15rem}
.pay button{min-height:44px;padding:0 1.1rem;border:0;border-radius:8px;background:var(--bp);color:#fff;font-weight:600;cursor:pointer}
.pay button:hover{background:#163a66}
.site-footer{margin-top:2rem;border-top:1px solid var(--line);background:#fff}
.ft{display:flex;flex-wrap:wrap;gap:.75rem 1.5rem;align-items:center;justify-content:space-between;padding:1rem 0 .35rem}
.ft .brand{color:var(--ink);font-size:13px;font-weight:600;letter-spacing:.04em}
.ft nav{display:flex;flex-wrap:wrap;gap:.15rem .5rem}
.ft a{color:#243044;font-size:12px;font-weight:500}
.ft nav a{font-size:11px;text-decoration:underline;text-underline-offset:2px}
.copyline{width:min(1120px,calc(100% - 2rem));margin:0 auto;padding:0 0 1.15rem}
.copyline p{margin:0;color:var(--muted);font-size:11px}
.modal{position:fixed;inset:0;z-index:80;display:flex;align-items:center;justify-content:center;padding:1rem;background:rgba(10,20,34,.5)}
.modal[hidden]{display:none}
.sheet{position:relative;width:min(420px,100%);background:#fff;color:var(--ink);border-radius:12px;padding:1.45rem 1.35rem 1.25rem;box-shadow:0 24px 60px rgba(11,37,69,.28)}
.sheet h2{margin:0 0 .35rem;font-size:1.2rem;font-weight:600;letter-spacing:-.03em}
.sheet .lead{margin:0 0 1rem;color:var(--muted);font-size:14px}
.sheet .err{margin:-.2rem 0 .7rem;color:#8d2a2a;font-size:13px}
.sheet .x{position:absolute;top:.7rem;right:.7rem;width:32px;height:32px;border:0;border-radius:6px;background:transparent;color:var(--muted);font-size:20px;cursor:pointer}
.sheet .x:hover{background:#f2f4f7}
.gbtn,.go{width:100%;min-height:46px;border-radius:8px;font-weight:600;cursor:pointer}
.gbtn{border:1px solid #cfd6e0;background:#fff}
.gbtn:hover{background:#f7f8fa}
.or{display:flex;align-items:center;gap:.75rem;margin:.9rem 0;color:var(--muted);font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.or:before,.or:after{content:"";height:1px;background:var(--line);flex:1}
.sheet input{width:100%;min-height:46px;border:1px solid #b7c0cc;border-radius:8px;padding:0 .75rem;margin-bottom:.6rem}
.go{border:0;background:var(--bp);color:#fff}
.go:hover{background:#163a66}
.sort-tip{position:fixed;z-index:50;width:max-content;max-width:220px;padding:.5rem .65rem;background:#e6e8ec;color:#3d4654;border-radius:6px;font-size:13px;font-weight:500;line-height:1.4;box-shadow:0 4px 14px rgba(20,28,40,.12)}
.sort-tip[hidden]{display:none}
.sort-tip a{color:#243044;font-weight:600;text-decoration:underline}
#step-pay[hidden],#step-account[hidden]{display:none}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
<script src="/uet.js" async></script>
<script src="/gtag.js" async></script>
</head>
<body>
<header class="top">
  <div class="top-inner">
    <a class="brand" href="/">Local City Records</a>
    <div class="head-actions">
      <a id="nav-account" href="/prototype2/portal.html" hidden>Account</a>
      <a id="headsub" href="/prototype2/checkout.html">Subscribe</a>
      <button type="button" id="signin">Sign in</button>
    </div>
  </div>
  <nav class="sections" id="sections" aria-label="Sections">
    <a href="./" data-path="./" data-section="permits">Ranked Permit Records</a>
    <a href="occupancy.html" data-path="occupancy.html" data-section="occupancy">Occupancy Records</a>
    <a href="signs.html" data-path="signs.html" data-section="signs">Sign Permit Records</a>
  </nav>
  <nav class="cities" id="cities" aria-label="Cities"></nav>
</header>
<main class="wrap">
  <p class="start">__START__</p>
  <div class="controls">
    <label class="f">City
      <select id="city"></select>
    </label>
    <label class="f">Permit type
      <select id="ptype"></select>
    </label>
    <label class="f">Trade
      <select id="trade"></select>
    </label>
    <label class="f">Week
      <select id="week"></select>
    </label>
    <label class="f">Size
      <select id="size">
        <option value="">Any size</option>
        <option value="5">$500k+</option>
        <option value="4">$100k–$500k</option>
        <option value="3">$50k–$100k</option>
        <option value="2">$10k–$50k</option>
        <option value="1">Under $10k</option>
        <option value="0">Not published</option>
      </select>
    </label>
    <label class="f">Search
      <input id="q" type="search" placeholder="Address, type, or scope" autocomplete="off">
    </label>
    <button type="button" id="clear" class="clear">Clear</button>
  </div>
  <section class="board" id="tape" aria-label="Permit index">
    <div class="status">
      <span id="count"></span>
      <div class="status-actions">
        <div class="filter-wrap">
          <button type="button" id="filter-btn" class="filter-btn" aria-haspopup="dialog" aria-expanded="false" aria-controls="filter-menu">
            <svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M1.5 2.5h13l-5 6.1V13l-3 1.2V8.6l-5-6.1z"/></svg>
            <span>Filter</span>
          </button>
          <div id="filter-menu" class="filter-menu" hidden>
            <label class="f">Filter by
              <select id="filter-field">
                <option value="trade">Trade</option>
                <option value="ptype">Permit type</option>
                <option value="size">Size</option>
                <option value="week">Week</option>
              </select>
            </label>
            <label class="f">Show
              <select id="filter-value"></select>
            </label>
          </div>
        </div>
        <div class="filter-wrap">
          <button type="button" id="download-btn" class="filter-btn" aria-haspopup="dialog" aria-expanded="false" aria-controls="download-menu">
            <svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><path d="M8 2.5v7"/><path d="M5.2 7.2 8 10l2.8-2.8"/><path d="M3 12.5h10"/></svg>
            <span>Download</span>
          </button>
          <div id="download-menu" class="filter-menu" hidden>
            <div id="download-pick">
              <label class="f">Format
                <select id="download-format">
                  <option value="csv">CSV</option>
                  <option value="excel">Excel</option>
                </select>
              </label>
              <button type="button" class="dl-go" id="download-go">Download list</button>
            </div>
            <div id="download-offer" hidden>
              <p class="offer-lead">Download the full list for every city, and read every issued record on the site.</p>
              <button type="button" class="dl-go" id="download-signin">Sign in</button>
              <a class="offer-up" id="download-sub" href="/prototype2/signup.html">Sign Up</a>
            </div>
          </div>
        </div>
        <div class="filter-wrap">
          <button type="button" id="alert-btn" class="filter-btn" aria-haspopup="dialog" aria-expanded="false" aria-controls="alert-menu">
            <svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><path d="M8 2.2a3.2 3.2 0 0 1 3.2 3.2c0 2.4.7 3.4 1.3 4.1H3.5c.6-.7 1.3-1.7 1.3-4.1A3.2 3.2 0 0 1 8 2.2z"/><path d="M6.6 12.2a1.4 1.4 0 0 0 2.8 0"/></svg>
            <span>Alerts</span>
          </button>
          <div id="alert-menu" class="filter-menu alert-menu" hidden>
            <div id="alert-offer">
              <p class="offer-lead">Email a short sample when new records match a city, permit type, trade, or size.</p>
              <button type="button" class="dl-go" id="alert-signin">Sign in</button>
              <a class="offer-up" id="alert-sub" href="/prototype2/signup.html">Sign Up</a>
            </div>
            <form id="alert-form" hidden>
              <label class="f">City
                <select id="alert-city"></select>
              </label>
              <label class="f">Permit type
                <select id="alert-type"></select>
              </label>
              <label class="f">Trade
                <select id="alert-trade"></select>
              </label>
              <label class="f">Size
                <select id="alert-size">
                  <option value="">Any size</option>
                  <option value="5">$500k+</option>
                  <option value="4">$100k–$500k</option>
                  <option value="3">$50k–$100k</option>
                  <option value="2">$10k–$50k</option>
                  <option value="1">Under $10k</option>
                  <option value="0">Not published</option>
                </select>
              </label>
              <label class="f">Email
                <select id="alert-frequency">
                  <option value="twice">Twice a day</option>
                  <option value="daily">Once a day</option>
                  <option value="weekly">Once a week</option>
                  <option value="monthly">Once a month</option>
                </select>
              </label>
              <button type="submit" class="dl-go">Save alert</button>
              <button type="button" class="alert-off" id="alert-off" hidden>Turn off</button>
              <p class="fine" id="alert-note"></p>
            </form>
          </div>
        </div>
        <button type="button" id="openfull" hidden>Open the full index</button>
      </div>
    </div>
    <div class="scroller">
      <table>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <p class="empty" id="empty" hidden>Select a city.</p>
  </section>
</main>
<div class="modal" id="gate" hidden>
  <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="gate-title">
    <button type="button" class="x" id="gate-close" aria-label="Close">×</button>
    <h2 id="gate-title">Sign in</h2>
    <p class="lead">Existing customers</p>
    <form id="login-form">
      <input id="login-email" type="email" required placeholder="Email" autocomplete="username">
      <input id="login-password" type="password" required minlength="8" placeholder="Password" autocomplete="current-password">
      <p class="err" id="login-err" hidden></p>
      <button class="go" type="submit">Sign in</button>
    </form>
    <div class="or">new customer</div>
    <p class="lead">Subscribe to read the full records.</p>
    <button type="button" class="gbtn" id="to-checkout">Continue to checkout</button>
  </div>
</div>
<footer class="site-footer">
  <div class="wrap ft">
    <a class="brand" href="./" style="color:var(--ink)">Business Local Records</a>
    <nav aria-label="Footer">
      <a href="/prototype2/about.html">About</a>
      <a href="/prototype2/coverage.html">Coverage</a>
      <a href="/prototype2/terms.html">Terms</a>
      <a href="/prototype2/privacy.html">Privacy</a>
    </nav>
  </div>
  <div class="copyline"><p>&copy; 2026 Business Local Records</p></div>
</footer>
<script>
const DATA = __DATA__;
const SECTION = "__SECTION__";
const PAGE = "__PAGE__";
const FILESLUG = "__FILESLUG__";
const state = {city:"", ptype:"", trade:"", week:"", size:"", q:"", sort:"issued", dir:"desc"};
const open = new Set();
const PAGE_SIZE = 25;
const FREE_ROWS = 17;
const pageOf = {};
let account = null;
const SORT_LABEL = {issued:"issue date", address:"address", trade:"trade", value:"job value"};
let subscribed = false;
let savedAlert = null;
const $ = (id) => document.getElementById(id);

function pretty(iso){
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", {month:"short", day:"numeric"});
}
function money(n){
  if (n == null) return "Not published";
  return "$" + Math.round(n).toLocaleString("en-US");
}
function matches(row){
  const city = DATA.cities[row[1]];
  if (state.city && city.id !== state.city) return false;
  if (state.ptype && DATA.types[row[2]] !== state.ptype) return false;
  if (state.trade && !(row[5] & (1 << DATA.trades.indexOf(state.trade)))) return false;
  if (state.week !== "" && String(row[6]) !== state.week) return false;
  if (state.size !== "" && String(row[4]) !== state.size) return false;
  if (state.q){
    const blob = (DATA.types[row[2]] + " " + (row[8] || "") + " " + (row[9] || "") + " " + city.label).toLowerCase();
    if (!blob.includes(state.q)) return false;
  }
  return true;
}
function tradeNames(row){
  const names = [];
  for (let i = 0; i < DATA.trades.length; i++){
    if (row[5] & (1 << i)) names.push(DATA.trades[i]);
  }
  names.sort((a, b) => a.localeCompare(b));
  return names.join(", ");
}
function keyOf(row, key){
  if (key === "issued") return row[0];
  if (key === "type") return DATA.types[row[2]];
  if (key === "address") return row[8] || null;
  if (key === "scope") return row[9] || null;
  if (key === "trade") return tradeNames(row) || null;
  return row[7];
}
function cmpKey(a, b, key, dir){
  const ka = keyOf(a, key), kb = keyOf(b, key);
  if (ka == null && kb == null) return 0;
  if (ka == null) return 1;
  if (kb == null) return -1;
  if (ka < kb) return dir === "desc" ? 1 : -1;
  if (ka > kb) return dir === "desc" ? -1 : 1;
  return 0;
}
function cmp(a, b){
  return cmpKey(a, b, state.sort, state.dir) || cmpKey(a, b, "issued", "desc") || cmpKey(a, b, "address", "asc");
}
function pageWindow(page, pages){
  if (pages <= 7) return Array.from({length: pages}, (_, i) => i + 1);
  const keep = new Set([1, pages, page - 1, page, page + 1].filter((n) => n >= 1 && n <= pages));
  const out = [];
  let prev = 0;
  for (let n = 1; n <= pages; n++){
    if (!keep.has(n)) continue;
    if (prev && n - prev > 1) out.push(null);
    out.push(n);
    prev = n;
  }
  return out;
}
function pagerRow(type, page, pages, blurred){
  const tr = document.createElement("tr");
  tr.className = "pager";
  const td = document.createElement("td");
  td.colSpan = 5;
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Table pages");
  pageWindow(page, pages).forEach((n) => {
    if (n === null){
      const gap = document.createElement("span");
      gap.className = "gap";
      gap.textContent = "…";
      nav.appendChild(gap);
      return;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.page = String(n);
    btn.dataset.ptype = type;
    btn.textContent = String(n);
    if (n === page){
      btn.setAttribute("aria-current", "page");
      btn.disabled = true;
    }
    nav.appendChild(btn);
  });
  td.appendChild(nav);
  if (blurred){
    const hint = document.createElement("button");
    hint.type = "button";
    hint.className = "hint";
    hint.dataset.signin = "1";
    hint.textContent = "Sign in to read these rows";
    td.appendChild(hint);
  }
  tr.appendChild(td);
  return tr;
}
function resetPages(){
  Object.keys(pageOf).forEach((key) => { delete pageOf[key]; });
}
function columnHead(){
  const tr = document.createElement("tr");
  tr.className = "cols";
  [["issued", "Issued"], ["address", "Address"], [null, "Scope of work"], ["trade", "Trade"], ["value", "Job value"]].forEach(([key, label]) => {
    const th = document.createElement("th");
    if (!key){
      th.className = "plain";
      th.textContent = label;
      tr.appendChild(th);
      return;
    }
    th.dataset.sort = key;
    const btn = document.createElement("button");
    btn.type = "button";
    const arr = document.createElement("span");
    arr.className = "arr";
    btn.append(document.createTextNode(label + " "), arr);
    th.appendChild(btn);
    tr.appendChild(th);
  });
  return tr;
}
function paintHeads(){
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    const on = th.dataset.sort === state.sort;
    th.setAttribute("aria-sort", on ? (state.dir === "asc" ? "ascending" : "descending") : "none");
    th.querySelector(".arr").textContent = on ? (state.dir === "desc" ? "↓" : "↑") : "";
  });
}
function paintAccount(){
  const btn = $("signin");
  if (account){
    btn.textContent = account.label;
    btn.title = "Sign out";
  } else {
    btn.textContent = "Sign in";
    btn.title = "";
  }
  const accountLink = $("nav-account");
  if (accountLink) {
    accountLink.hidden = !account;
    accountLink.href = memberUrl("portal.html");
  }
  const sub = $("headsub");
  if (sub) {
    sub.hidden = subscribed;
    sub.href = checkoutUrl();
  }
}
function openGate(){
  if (subscribed) return;
  hideSortTip();
  $("login-err").hidden = true;
  $("gate").hidden = false;
}
let sortTip;
function hideSortTip(){
  if (sortTip) sortTip.hidden = true;
}
function showSortTip(th){
  if (!sortTip){
    sortTip = document.createElement("div");
    sortTip.className = "sort-tip";
    sortTip.hidden = true;
    sortTip.innerHTML = '<a href="./#signin">Sign in or sign up</a> for custom sorting.';
    document.body.appendChild(sortTip);
    sortTip.querySelector("a").addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideSortTip();
      openGate();
    });
  }
  const rect = th.getBoundingClientRect();
  sortTip.hidden = false;
  sortTip.style.top = (rect.bottom + 6) + "px";
  sortTip.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - 236)) + "px";
}
function closeGate(){
  $("gate").hidden = true;
}
function memberUrl(file){
  const url = new URL("/prototype2/" + file, location.origin);
  if (state.city) url.searchParams.set("city", state.city);
  if (file === "checkout.html" || file === "signup.html") {
    url.searchParams.set("next", location.pathname + location.search);
  }
  return url;
}
function checkoutUrl(){
  return memberUrl("checkout.html");
}
function pathCity(){
  const parts = location.pathname.split("/").filter(Boolean);
  if (parts.length < 2 || !/^\d{4}-\d{2}-\d{2}$/.test(parts[1]) || parts[0] === "sales-archive") return "";
  const id = parts[0].toLowerCase();
  return DATA.cities.some((c) => c.id === id) ? id : "";
}
function fillWeeks(){
  const sel = $("week");
  const city = DATA.cities.find((c) => c.id === state.city);
  if (!city){
    sel.innerHTML = '<option value="">Latest week</option>';
    state.week = "";
    return;
  }
  let html = "";
  city.weeks.forEach((w, i) => {
    const latest = i === city.weeks.length - 1;
    html += '<option value="' + (latest ? "" : i) + '">' + (latest ? "Latest · " : "Earlier · ") + w.range + "</option>";
  });
  sel.innerHTML = html;
  sel.value = state.week;
}
function esc(s){
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}
function typeNames(){
  const seen = new Set();
  DATA.rows.forEach((row) => {
    const city = DATA.cities[row[1]];
    if (state.city && city.id !== state.city) return;
    if (!state.city && !subscribed) return;
    if (state.week !== "" && String(row[6]) !== state.week) return;
    seen.add(DATA.types[row[2]]);
  });
  return [...seen].sort((a, b) => a.localeCompare(b));
}
function fillTypes(){
  const names = typeNames();
  if (state.ptype && !names.includes(state.ptype)) state.ptype = "";
  $("ptype").innerHTML = '<option value="">All permit types</option>' + names.map((t) => '<option value="' + esc(t) + '">' + esc(t) + "</option>").join("");
  $("ptype").value = state.ptype;
}
function fillFilterValues(){
  const field = $("filter-field").value;
  const sel = $("filter-value");
  let html = "";
  let current = "";
  if (field === "trade"){
    html = '<option value="">All trades</option>' + DATA.trades.map((t) => '<option value="' + esc(t) + '">' + esc(t) + "</option>").join("");
    current = state.trade;
  } else if (field === "ptype"){
    html = '<option value="">All permit types</option>' + typeNames().map((t) => '<option value="' + esc(t) + '">' + esc(t) + "</option>").join("");
    current = state.ptype;
  } else if (field === "size"){
    html = $("size").innerHTML;
    current = state.size;
  } else {
    html = $("week").innerHTML;
    current = state.week;
  }
  sel.innerHTML = html;
  if ([...sel.options].some((opt) => opt.value === current)) sel.value = current;
}
function paintFilter(){
  const active = [state.trade, state.ptype, state.size, state.week].filter((v) => v !== "").length;
  const btn = $("filter-btn");
  btn.classList.toggle("on", active > 0);
  btn.querySelector("span").textContent = active ? "Filter (" + active + ")" : "Filter";
}
function pageHref(city){
  if (!city) return PAGE;
  return PAGE + "?city=" + encodeURIComponent(city);
}
function paintSections(){
  document.querySelectorAll("#sections a").forEach((a) => {
    a.href = pageHref(state.city).replace(PAGE, a.dataset.path);
    const on = a.dataset.section === SECTION;
    a.classList.toggle("on", on);
    if (on) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
}
function paintCities(){
  paintSections();
  const nav = $("cities");
  nav.replaceChildren();
  if (subscribed){
    const all = document.createElement("a");
    all.href = PAGE;
    all.dataset.city = "";
    all.textContent = "All";
    if (!state.city){
      all.className = "on";
      all.setAttribute("aria-current", "page");
    }
    nav.appendChild(all);
  }
  DATA.cities.forEach((c) => {
    const a = document.createElement("a");
    a.href = pageHref(c.id);
    a.dataset.city = c.id;
    a.textContent = c.label;
    if (c.id === state.city){
      a.className = "on";
      a.setAttribute("aria-current", "page");
    }
    nav.appendChild(a);
  });
}
function fitHeader(){
  const bar = document.querySelector(".top-inner");
  if (bar) document.body.style.paddingTop = bar.offsetHeight + "px";
}
function syncUrl(){
  const url = new URL(location.href);
  [["city", state.city], ["ptype", state.ptype], ["trade", state.trade], ["size", state.size]].forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  });
  if (state.city && state.city === pathCity()) url.searchParams.delete("city");
  history.replaceState(null, "", url);
}
function setCity(id){
  state.city = id || "";
  state.week = "";
  state.ptype = "";
  open.clear();
  resetPages();
  syncUrl();
  render();
}
function fillSelects(){
  paintCities();
  fitHeader();
  const cityHtml = '<option value="">' + (subscribed ? "All cities" : "Select a city") + "</option>" + DATA.cities.map((c) => '<option value="' + c.id + '">' + c.label + "</option>").join("");
  $("city").innerHTML = cityHtml;
  $("city").value = state.city;
  fillTypes();
  $("trade").innerHTML = '<option value="">All trades</option>' + DATA.trades.map((t) => '<option value="' + t + '">' + t + "</option>").join("");
  $("trade").value = state.trade;
  $("size").value = state.size;
  fillWeeks();
}
function draw(){
  if (!SORT_LABEL[state.sort]) { state.sort = "issued"; state.dir = "desc"; }
  if (!subscribed && state.sort !== "issued") { state.sort = "issued"; state.dir = "desc"; }
  const list = DATA.rows.filter(matches);
  const body = $("rows");
  body.replaceChildren();
  const empty = $("empty");
  if (!state.city && !subscribed){
    empty.hidden = false;
    empty.textContent = "Select a city.";
    $("count").textContent = "";
    $("openfull").hidden = true;
    paintHeads();
    paintFilter();
    return;
  }
  if (!list.length){
    empty.hidden = false;
    empty.textContent = "No records match.";
    $("count").textContent = "0 records";
    $("openfull").hidden = true;
    paintHeads();
    paintFilter();
    return;
  }
  empty.hidden = true;
  const buckets = new Map();
  list.forEach((row) => {
    const type = DATA.types[row[2]];
    if (!buckets.has(type)) buckets.set(type, []);
    buckets.get(type).push(row);
  });
  const groups = [...buckets.entries()].map(([type, rows]) => {
    rows.sort(cmp);
    return {type, total: rows.length, rows: rows};
  });
  groups.sort((a, b) => b.total - a.total || a.type.localeCompare(b.type));
  const frag = document.createDocumentFragment();
  groups.forEach((g) => {
    const expanded = open.has(g.type);
    const gr = document.createElement("tr");
    gr.className = "group";
    const td = document.createElement("td");
    td.colSpan = 5;
    const fold = document.createElement("button");
    fold.type = "button";
    fold.className = "fold";
    fold.dataset.fold = g.type;
    fold.setAttribute("aria-expanded", expanded ? "true" : "false");
    const chev = document.createElement("span");
    chev.className = "chev";
    chev.textContent = expanded ? "▾" : "▸";
    const name = document.createElement("span");
    name.textContent = g.type;
    const n = document.createElement("span");
    n.className = "n";
    n.textContent = g.total.toLocaleString();
    fold.append(chev, name, n);
    td.appendChild(fold);
    gr.appendChild(td);
    frag.appendChild(gr);
    if (expanded){
      frag.appendChild(columnHead());
      const pages = Math.max(1, Math.ceil(g.rows.length / PAGE_SIZE));
      let page = pageOf[g.type] || 1;
      if (page > pages) page = pages;
      if (page < 1) page = 1;
      pageOf[g.type] = page;
      const start = (page - 1) * PAGE_SIZE;
      const slice = g.rows.slice(start, start + PAGE_SIZE);
      slice.forEach((row, i) => addRow(row, !subscribed && start + i >= FREE_ROWS));
      if (pages > 1) frag.appendChild(pagerRow(g.type, page, pages, !subscribed && g.rows.length > FREE_ROWS));
    }
    function addRow(row, peek){
      const tr = document.createElement("tr");
      tr.className = peek ? "data peek" : "data";
      if (peek){
        tr.dataset.signin = "1";
        tr.setAttribute("aria-hidden", "true");
      }
      const issued = document.createElement("td");
      issued.className = "mono";
      issued.textContent = pretty(row[0]);
      if (state.sort === "issued") issued.classList.add("sorted");
      const addr = document.createElement("td");
      addr.className = "addr";
      addr.textContent = row[8] || "—";
      if (state.sort === "address") addr.classList.add("sorted");
      const scope = document.createElement("td");
      scope.className = "scope";
      scope.textContent = row[9] || "—";
      const trade = document.createElement("td");
      trade.className = "trade";
      trade.textContent = tradeNames(row) || "—";
      if (state.sort === "trade") trade.classList.add("sorted");
      const val = document.createElement("td");
      val.className = "mono";
      val.textContent = money(row[7]);
      if (state.sort === "value") val.classList.add("sorted");
      tr.append(issued, addr, scope, trade, val);
      frag.appendChild(tr);
    }
  });
  body.appendChild(frag);
  const city = DATA.cities.find((c) => c.id === state.city);
  const where = city ? city.label : "All cities";
  const rank = "ranked by " + SORT_LABEL[state.sort];
  const shown = [...open].reduce((sum, type) => {
    const group = groups.find((g) => g.type === type);
    if (!group) return sum;
    const page = pageOf[type] || 1;
    return sum + Math.min(PAGE_SIZE, Math.max(0, group.rows.length - (page - 1) * PAGE_SIZE));
  }, 0);
  $("count").innerHTML = "<b>" + list.length.toLocaleString() + "</b> records · " + where + " · " + rank + (shown ? " · " + shown + " on this page" : "");
  const openBtn = $("openfull");
  openBtn.hidden = subscribed;
  if (!openBtn.hidden) openBtn.textContent = "Sign in to view all " + list.length.toLocaleString();
  paintHeads();
  paintFilter();
}
function paintPay(){
  if (subscribed){
    $("openfull").hidden = true;
    $("headsub").hidden = true;
  }
}
function render(){
  fillSelects();
  draw();
  paintPay();
  paintAccount();
  if (!$("filter-menu").hidden) fillFilterValues();
}
function fromUrl(){
  const params = new URLSearchParams(location.search);
  const wanted = (params.get("city") || pathCity()).toLowerCase();
  const match = DATA.cities.find((c) => c.id === wanted || c.label.toLowerCase() === wanted);
  state.city = match ? match.id : "";
  const trade = params.get("trade") || "";
  state.trade = DATA.trades.includes(trade) ? trade : "";
  const ptype = params.get("ptype") || "";
  state.ptype = DATA.types.includes(ptype) ? ptype : "";
  const size = params.get("size") || "";
  state.size = ["0", "1", "2", "3", "4", "5"].includes(size) ? size : "";
  if (state.ptype) open.add(state.ptype);
}
fromUrl();
fillSelects();
$("cities").addEventListener("click", (e) => {
  const link = e.target.closest("a[data-city]");
  if (!link) return;
  e.preventDefault();
  setCity(link.dataset.city || "");
});
$("city").addEventListener("change", () => setCity($("city").value));
["ptype","trade","week"].forEach((id) => $(id).addEventListener("change", () => {
  state.ptype = $("ptype").value;
  state.trade = $("trade").value;
  state.week = $("week").value;
  if (id === "ptype"){
    open.clear();
    if (state.ptype) open.add(state.ptype);
  }
  resetPages();
  syncUrl();
  render();
}));
$("size").addEventListener("change", () => {
  state.size = $("size").value;
  resetPages();
  syncUrl();
  draw();
});
$("q").addEventListener("input", () => {
  state.q = $("q").value.trim().toLowerCase();
  resetPages();
  draw();
});
$("clear").addEventListener("click", () => {
  state.ptype = "";
  state.trade = "";
  state.week = "";
  state.size = "";
  state.q = "";
  open.clear();
  resetPages();
  state.sort = "value";
  state.dir = "desc";
  $("q").value = "";
  $("size").value = "";
  render();
});
function closeFilter(){
  $("filter-menu").hidden = true;
  $("filter-btn").setAttribute("aria-expanded", "false");
}
function closeDownload(){
  $("download-menu").hidden = true;
  $("download-btn").setAttribute("aria-expanded", "false");
}
function csvCell(value){
  const s = value == null ? "" : String(value);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function downloadList(){
  if (!subscribed){
    $("download-pick").hidden = true;
    $("download-offer").hidden = false;
    $("download-sub").href = memberUrl("signup.html");
    return;
  }
  const excel = $("download-format").value === "excel";
  const header = ["Issued","City","Permit type","Address","Scope of work","Trade","Job value"];
  const lines = [header.join(",")];
  DATA.rows.filter(matches).forEach((row) => {
    const city = DATA.cities[row[1]];
    lines.push([
      row[0],
      city.label,
      DATA.types[row[2]],
      row[8] || "",
      row[9] || "",
      tradeNames(row),
      row[7] == null ? "" : String(row[7])
    ].map(csvCell).join(","));
  });
  const blob = new Blob([(excel ? "\uFEFF" : "") + lines.join("\r\n")], {type: "text/csv;charset=utf-8"});
  const a = document.createElement("a");
  const city = DATA.cities.find((c) => c.id === state.city);
  a.href = URL.createObjectURL(blob);
  a.download = (city ? city.id : "all-cities") + "-" + FILESLUG + (excel ? "-excel.csv" : ".csv");
  a.click();
  URL.revokeObjectURL(a.href);
  closeDownload();
}
$("filter-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  if ($("filter-menu").hidden){
    closeDownload();
    fillFilterValues();
    $("filter-menu").hidden = false;
    $("filter-btn").setAttribute("aria-expanded", "true");
  } else closeFilter();
});
$("filter-menu").addEventListener("click", (e) => e.stopPropagation());
$("filter-field").addEventListener("change", fillFilterValues);
$("filter-value").addEventListener("change", () => {
  const field = $("filter-field").value;
  const value = $("filter-value").value;
  if (field === "trade") state.trade = value;
  else if (field === "ptype"){
    state.ptype = value;
    open.clear();
    if (value) open.add(value);
  } else if (field === "size") state.size = value;
  else state.week = value;
  resetPages();
  render();
});
$("download-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  if ($("download-menu").hidden){
    closeFilter();
    $("download-pick").hidden = false;
    $("download-offer").hidden = true;
    $("download-menu").hidden = false;
    $("download-btn").setAttribute("aria-expanded", "true");
  } else closeDownload();
});
$("download-menu").addEventListener("click", (e) => e.stopPropagation());
$("download-go").addEventListener("click", downloadList);
$("download-signin").addEventListener("click", () => { closeDownload(); openGate(); });
function closeAlert(){
  $("alert-menu").hidden = true;
  $("alert-btn").setAttribute("aria-expanded", "false");
}
function paintAlert(){
  $("alert-offer").hidden = subscribed;
  $("alert-form").hidden = !subscribed;
  $("alert-btn").classList.toggle("on", !!(savedAlert && savedAlert.enabled));
  $("alert-off").hidden = !(savedAlert && savedAlert.enabled);
  $("alert-sub").href = memberUrl("signup.html");
}
function fillAlertChoices(){
  const city = savedAlert && savedAlert.city ? savedAlert.city : state.city;
  const ptype = savedAlert && savedAlert.permit_type ? savedAlert.permit_type : state.ptype;
  const trade = savedAlert && savedAlert.trade ? savedAlert.trade : state.trade;
  const size = savedAlert && savedAlert.size !== undefined && savedAlert.size !== null ? String(savedAlert.size) : state.size;
  $("alert-city").innerHTML = '<option value="">Any city</option>' + DATA.cities.map((c) => '<option value="' + c.id + '">' + c.label + "</option>").join("");
  $("alert-city").value = [...$("alert-city").options].some((opt) => opt.value === city) ? city : "";
  $("alert-type").innerHTML = '<option value="">Any permit type</option>' + DATA.types.map((t) => '<option value="' + t.replace(/"/g, "&quot;") + '">' + t.replace(/</g, "") + "</option>").join("");
  $("alert-type").value = [...$("alert-type").options].some((opt) => opt.value === ptype) ? ptype : "";
  $("alert-trade").innerHTML = '<option value="">Any trade</option>' + DATA.trades.map((t) => '<option value="' + t + '">' + t + "</option>").join("");
  $("alert-trade").value = trade || "";
  $("alert-size").value = ["0", "1", "2", "3", "4", "5"].includes(size) ? size : "";
  $("alert-frequency").value = savedAlert && savedAlert.frequency ? savedAlert.frequency : "daily";
  $("alert-note").textContent = savedAlert && savedAlert.enabled ? "Saved. A short sample goes out when a new record matches." : "";
}
function loadAlert(){
  fetch("/api/index.php?r=alerts", {credentials: "same-origin"}).then((res) => res.json()).then((data) => {
    savedAlert = data && data.alert ? data.alert : null;
    paintAlert();
    if (subscribed && !$("alert-menu").hidden) fillAlertChoices();
  }).catch(() => {});
}
function saveAlert(enabled){
  const note = $("alert-note");
  note.textContent = "";
  const body = {
    city: $("alert-city").value,
    permit_type: $("alert-type").value,
    trade: $("alert-trade").value,
    size: $("alert-size").value,
    frequency: $("alert-frequency").value,
    section: SECTION,
    enabled: enabled
  };
  fetch("/api/index.php?r=alerts", {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok){
      note.textContent = data.error || "The alert was not saved.";
      return;
    }
    savedAlert = data.alert || null;
    paintAlert();
    if (savedAlert && savedAlert.enabled) note.textContent = "Saved. A short sample goes out when a new record matches.";
  }).catch(() => {
    note.textContent = "The alert was not saved.";
  });
}
$("alert-btn").addEventListener("click", (e) => {
  e.stopPropagation();
  if ($("alert-menu").hidden){
    closeFilter();
    closeDownload();
    paintAlert();
    if (subscribed) fillAlertChoices();
    $("alert-menu").hidden = false;
    $("alert-btn").setAttribute("aria-expanded", "true");
  } else closeAlert();
});
$("alert-menu").addEventListener("click", (e) => e.stopPropagation());
$("alert-signin").addEventListener("click", () => { closeAlert(); openGate(); });
$("alert-form").addEventListener("submit", (e) => { e.preventDefault(); saveAlert(true); });
$("alert-off").addEventListener("click", () => saveAlert(false));
document.addEventListener("click", (e) => {
  closeFilter();
  closeDownload();
  closeAlert();
  if (!e.target.closest("th[data-sort]") && !e.target.closest(".sort-tip")) hideSortTip();
});
window.addEventListener("scroll", hideSortTip, true);
window.addEventListener("resize", fitHeader);
$("rows").addEventListener("click", (e) => {
  const pageBtn = e.target.closest("[data-page]");
  if (pageBtn){
    pageOf[pageBtn.dataset.ptype] = Number(pageBtn.dataset.page);
    draw();
    const status = document.querySelector(".status");
    if (status){
      const top = status.getBoundingClientRect().top + window.scrollY - document.querySelector(".top").offsetHeight;
      window.scrollTo({top: Math.max(0, top), behavior:"auto"});
    }
    return;
  }
  const th = e.target.closest("th[data-sort]");
  if (th){
    const key = th.dataset.sort;
    if (!subscribed && key !== "issued"){
      showSortTip(th);
      return;
    }
    hideSortTip();
    if (state.sort === key) state.dir = state.dir === "desc" ? "asc" : "desc";
    else {
      state.sort = key;
      state.dir = (key === "value" || key === "issued") ? "desc" : "asc";
    }
    resetPages();
    draw();
    return;
  }
  const fold = e.target.closest("[data-fold]");
  if (fold){
    const type = fold.dataset.fold;
    if (open.has(type)) open.delete(type);
    else {
      open.clear();
      open.add(type);
    }
    draw();
    return;
  }
  if (e.target.closest("[data-signin]")) openGate();
});
$("openfull").addEventListener("click", openGate);
$("to-checkout").addEventListener("click", () => { location.href = checkoutUrl(); });
$("signin").addEventListener("click", () => {
  if (account){
    fetch("/api/index.php?r=logout", {method:"POST", credentials:"same-origin"}).finally(() => {
      account = null;
      subscribed = false;
      savedAlert = null;
      closeGate();
      render();
      paintAlert();
    });
    return;
  }
  openGate();
});
$("login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const err = $("login-err");
  err.hidden = true;
  fetch("/api/index.php?r=login", {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email: $("login-email").value.trim(), password: $("login-password").value})
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok){
      err.textContent = data.error || "Sign in failed.";
      err.hidden = false;
      return;
    }
    account = {label: data.email};
    subscribed = !!data.subscribed;
    closeGate();
    render();
    if (subscribed) loadAlert();
    else { savedAlert = null; paintAlert(); }
  }).catch(() => {
    err.textContent = "Sign in is unavailable.";
    err.hidden = false;
  });
});
$("gate-close").addEventListener("click", closeGate);
$("gate").addEventListener("click", (e) => { if (e.target.id === "gate") closeGate(); });
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (!$("download-menu").hidden){ closeDownload(); return; }
  if (!$("alert-menu").hidden){ closeAlert(); return; }
  if (!$("filter-menu").hidden){ closeFilter(); return; }
  closeGate();
});
render();
fetch("/api/index.php?r=me", {credentials:"same-origin"}).then((res) => res.json()).then((data) => {
  if (data.email) account = {label: data.email};
  subscribed = !!data.subscribed;
  render();
  if (subscribed) { loadAlert(); }
  else paintAlert();
}).catch(() => {});
if (location.hash === "#signin") openGate();
</script>
<script>
if (location.search.indexOf("src=email") !== -1 || location.search.indexOf("src=alert") !== -1) {
  fetch("/hit.php", {
    method: "POST",
    keepalive: true,
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: "path=" + encodeURIComponent(location.pathname + location.search)
  });
}
</script>
</body>
</html>
"""


SIGN = re.compile(r"SIGNAGE|\bSIGNS?\b|AWNING|STOREFRONT|FACADE")
OCC = re.compile(r"OCCUPAN|CERTIFICATE OF")
VIEWS = (
    {
        "file": "index.html",
        "section": "permits",
        "page": "./",
        "fileslug": "permits",
        "title": "Ranked Permit Records",
        "start": "Choose a permit type to open this city's issued records. Filter the list free, or sign in below to view and download every row.",
        "desc": "Issued building permits ranked by city, permit type, and job value.",
        "canon": "https://businesslocalrecords.com/prototype2/",
        "keep": None,
    },
    {
        "file": "occupancy.html",
        "section": "occupancy",
        "page": "occupancy.html",
        "fileslug": "occupancy",
        "title": "Occupancy Records",
        "start": "Choose a permit type to open this city's occupancy records. Filter the list free, or sign in below to view and download every row.",
        "desc": "Occupancy permits and certificates of occupancy for businesses opening a location.",
        "canon": "https://businesslocalrecords.com/prototype2/occupancy.html",
        "keep": "occupancy",
    },
    {
        "file": "signs.html",
        "section": "signs",
        "page": "signs.html",
        "fileslug": "signs",
        "title": "Sign Permit Records",
        "start": "Choose a permit type to open this city's sign and storefront permits. Filter the list free, or sign in below to view and download every row.",
        "desc": "Sign, awning, storefront, and facade permits for businesses spending on their street front.",
        "canon": "https://businesslocalrecords.com/prototype2/signs.html",
        "keep": "signs",
    },
)


def subset(payload, keep):
    if keep is None:
        return payload
    types, streets = [], []
    type_ix, street_ix = {}, {}
    rows = []
    for row in payload["rows"]:
        text = f"{payload['types'][row[2]]} {row[9]}".upper()
        if keep == "occupancy" and not OCC.search(text):
            continue
        if keep == "signs" and not SIGN.search(text):
            continue
        typ = payload["types"][row[2]]
        street = payload["streets"][row[3]]
        if typ not in type_ix:
            type_ix[typ] = len(types)
            types.append(typ)
        if street not in street_ix:
            street_ix[street] = len(streets)
            streets.append(street)
        rows.append([row[0], row[1], type_ix[typ], street_ix[street], *row[4:]])
    return {**payload, "types": types, "streets": streets, "rows": rows}


def main():
    data = load()
    out_dir = OUT.parent
    for view in VIEWS:
        piece = subset(data, view["keep"])
        blob = json.dumps(piece, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
        html = (
            PAGE.replace("__CANON__", view["canon"])
            .replace("__TITLE__", view["title"])
            .replace("__DESC__", view["desc"])
            .replace("__START__", view["start"])
            .replace("__SECTION__", view["section"])
            .replace("__PAGE__", view["page"])
            .replace("__FILESLUG__", view["fileslug"])
            .replace("__DATA__", blob)
        )
        dest = out_dir / view["file"]
        dest.write_text(html, encoding="utf-8")
        if sys.stdout is not None:
            print(f"Wrote {dest.name} with {len(piece['rows']):,} prints, {dest.stat().st_size:,} bytes")
    copied = b.publish_all_city_boards()
    if sys.stdout is not None:
        print(f"Copied the board onto {len(copied) // 3} dated city paths")


if __name__ == "__main__":
    main()
