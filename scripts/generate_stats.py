#!/usr/bin/env python3
"""
Generates a custom GitHub Stats SVG card with real-time data:
  - Total contributions (all time)
  - Contributions this year
  - Max contributions in a single day (all time)
  - Repos contributed to (all time)

Requires env var: GH_TOKEN or GITHUB_TOKEN
"""

import os
import sys
import requests
from datetime import datetime, timezone

USERNAME = "divyansh-1009"
OUTPUT_PATH = "assets/github_stats.svg"
GH_GRAPHQL = "https://api.github.com/graphql"


def gql(query, variables=None):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: No GH_TOKEN or GITHUB_TOKEN set.", file=sys.stderr)
        sys.exit(1)
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(GH_GRAPHQL, json=payload, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
        sys.exit(1)
    return data["data"]


META_QUERY = """
{
  user(login: "%s") {
    createdAt
    repositoriesContributedTo(
      first: 1
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
      includeUserRepositories: true
    ) {
      totalCount
    }
  }
}
""" % USERNAME

YEAR_QUERY = """
query($from: DateTime!, $to: DateTime!) {
  user(login: "%s") {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
          }
        }
      }
    }
  }
}
""" % USERNAME


def get_year_stats(year):
    now_utc = datetime.now(timezone.utc)
    from_dt = f"{year}-01-01T00:00:00Z"
    to_dt = f"{year}-12-31T23:59:59Z"
    if year == now_utc.year:
        to_dt = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = gql(YEAR_QUERY, {"from": from_dt, "to": to_dt})
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    total = cal["totalContributions"]
    max_day = max(
        (d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]),
        default=0,
    )
    return total, max_day


def generate_svg(total_all, total_year, max_day, repos):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    W, H = 540, 270

    stats = [
        ("Total Contributions", f"{total_all:,}", "#00e5ff"),
        ("Contributions This Year", f"{total_year:,}", "#f72585"),
        ("Max Contributions in a Day", f"{max_day:,}", "#a855f7"),
        ("Repos Contributed To", f"{repos:,}", "#00ff9f"),
    ]

    cell_w = W // 2
    cell_h = (H - 55) // 2
    sep_y = 50 + cell_h

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    svg.append("""  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2.2" result="cb"/>
      <feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="gpink">
      <feGaussianBlur stdDeviation="3" result="cb"/>
      <feMerge><feMergeNode in="cb"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .bg  { fill: url(#bg); }
      .b1  { fill: none; stroke: #00e5ff; stroke-width: 1.3; opacity: .45; }
      .b2  { fill: none; stroke: #f72585; stroke-width: .5; opacity: .18; }
      .ttl { font-family: "Courier New",monospace; font-size: 11.5px; fill: #f72585; letter-spacing: 2.5px; filter: url(#gpink); }
      .lbl { font-family: "Courier New",monospace; font-size: 10.5px; fill: #8b949e; }
      .val { font-family: "Courier New",monospace; font-size: 24px; font-weight: bold; filter: url(#glow); }
      .sep { stroke: #21262d; stroke-width: 1; }
      .ts  { font-family: "Courier New",monospace; font-size: 8.5px; fill: #3d444d; }
      .dot { fill: none; stroke-width: 1; opacity: .6; }
    </style>
  </defs>""")

    svg.append(f'  <rect class="bg" width="{W}" height="{H}" rx="10"/>')
    svg.append(f'  <rect class="b1" x="3" y="3" width="{W-6}" height="{H-6}" rx="8"/>')
    svg.append(f'  <rect class="b2" x="7" y="7" width="{W-14}" height="{H-14}" rx="6"/>')

    # Corner dots
    for cx, cy in [(18, 18), (W-18, 18), (18, H-18), (W-18, H-18)]:
        svg.append(f'  <circle cx="{cx}" cy="{cy}" r="3" class="dot" stroke="#00e5ff"/>')

    svg.append(f'  <text class="ttl" x="{W//2}" y="30" text-anchor="middle">[ GITHUB ANALYTICS ]</text>')

    # Dividers
    svg.append(f'  <line class="sep" x1="{cell_w}" y1="44" x2="{cell_w}" y2="{H-22}"/>')
    svg.append(f'  <line class="sep" x1="18" y1="{sep_y}" x2="{W-18}" y2="{sep_y}"/>')

    positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for idx, (col, row) in enumerate(positions):
        label, value, color = stats[idx]
        cx = col * cell_w + cell_w // 2
        base_y = 50 + row * cell_h + cell_h // 2
        svg.append(f'  <text class="val" x="{cx}" y="{base_y - 6}" text-anchor="middle" fill="{color}">{value}</text>')
        svg.append(f'  <text class="lbl" x="{cx}" y="{base_y + 16}" text-anchor="middle">{label}</text>')

    svg.append(f'  <text class="ts" x="{W//2}" y="{H-9}" text-anchor="middle">Real-time · Updated: {now_str}</text>')
    svg.append('</svg>')
    return '\n'.join(svg)


if __name__ == "__main__":
    print(f"Fetching data for: {USERNAME}")

    meta = gql(META_QUERY)
    created_at = meta["user"]["createdAt"]
    repos_count = meta["user"]["repositoriesContributedTo"]["totalCount"]
    start_year = int(created_at[:4])
    current_year = datetime.now(timezone.utc).year

    print(f"Account created: {created_at}  |  Repos contributed to: {repos_count}")

    total_all = 0
    global_max_day = 0
    total_year = 0

    for year in range(start_year, current_year + 1):
        yt, ym = get_year_stats(year)
        total_all += yt
        if ym > global_max_day:
            global_max_day = ym
        if year == current_year:
            total_year = yt
        print(f"  {year}: {yt:>6,} contributions  |  max/day: {ym}")

    print(f"\nAll-time total : {total_all:,}")
    print(f"This year      : {total_year:,}")
    print(f"Max in one day : {global_max_day:,}")
    print(f"Repos          : {repos_count:,}")

    os.makedirs("assets", exist_ok=True)
    svg_content = generate_svg(total_all, total_year, global_max_day, repos_count)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"\nSVG saved → {OUTPUT_PATH}")
