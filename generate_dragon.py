#!/usr/bin/env python3
"""
Generate a single self-adapting animated SVG dragon for GitHub profiles.

Usage:
    python generate_dragon.py --user manteshswami --out dist/dragon.svg
"""
import argparse
import json
import os
import sys
import urllib.request

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }
    }
  }
}
"""

CELL = 11
GAP = 3
STEP = CELL + GAP
MARGIN = 20


def fetch_contributions(login, token):
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "dragon-snake-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    if "errors" in data:
        raise RuntimeError(f"GitHub API error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = {}
    for w, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[(w, day["weekday"])] = day["contributionCount"]
    return grid, len(weeks)


def level_for_count(count, all_counts):
    if count == 0:
        return 0
    nonzero = sorted(c for c in all_counts if c > 0)
    if not nonzero:
        return 1
    q1 = nonzero[len(nonzero) // 4] if len(nonzero) >= 4 else nonzero[0]
    q2 = nonzero[len(nonzero) // 2]
    q3 = nonzero[(len(nonzero) * 3) // 4] if len(nonzero) >= 4 else nonzero[-1]
    if count <= q1:
        return 1
    if count <= q2:
        return 2
    if count <= q3:
        return 3
    return 4


def build_path(num_weeks):
    path = []
    for w in range(num_weeks):
        rows = range(7) if w % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((w, r))
    return path


def cell_pixel(w, r):
    return MARGIN + w * STEP + CELL / 2, MARGIN + r * STEP + CELL / 2


def render_svg(grid, num_weeks):
    path = build_path(num_weeks)
    n = len(path)

    all_counts = list(grid.values())
    levels = {cell: level_for_count(grid.get(cell, 0), all_counts) for cell in path}

    width = MARGIN * 2 + num_weeks * STEP
    height = MARGIN * 2 + 7 * STEP

    step_time = 0.12
    total = n * step_time
    reset_frac = 0.985

    svg = []
    svg.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">'
    )
    
    # --- Embedded CSS for automatic Light / Dark mode switching ---
    svg.append("""
    <style>
      @media (prefers-color-scheme: dark) {
        .bg { fill: #0d1117; }
        .empty { fill: #161b22; }
        .lvl-1 { fill: #0e4429; }
        .lvl-2 { fill: #006d32; }
        .lvl-3 { fill: #26a641; }
        .lvl-4 { fill: #39d353; }
        .dragon-body { fill: #ff6b35; }
        .dragon-belly { fill: #ffb703; }
        .dragon-spike { fill: #7a1f0d; }
        .dragon-eye { fill: #39d353; }
      }
      @media (prefers-color-scheme: light), (prefers-color-scheme: no-preference) {
        .bg { fill: #ffffff; }
        .empty { fill: #ebedf0; }
        .lvl-1 { fill: #c6e48b; }
        .lvl-2 { fill: #7bc96f; }
        .lvl-3 { fill: #239a3b; }
        .lvl-4 { fill: #196127; }
        .dragon-body { fill: #2ea043; }
        .dragon-belly { fill: #7ee787; }
        .dragon-spike { fill: #0e4429; }
        .dragon-eye { fill: #ffd33d; }
      }
    </style>
    """)

    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" class="bg"/>')

    # --- grid cells ---
    for i, (w, r) in enumerate(path):
        x = MARGIN + w * STEP
        y = MARGIN + r * STEP
        lvl = levels[(w, r)]
        t1 = round(i / n, 4)
        svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" class="empty"/>')
        if lvl > 0:
            svg.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" class="lvl-{lvl}" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;1;1;0" '
                f'keyTimes="0;{t1};{t1};{reset_frac};1" '
                f'dur="{total:.2f}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>'
                f'</rect>'
            )

    # --- motion path ---
    pts = [cell_pixel(w, r) for w, r in path]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    # --- dragon segments ---
    seg_count = 7
    for seg in range(seg_count):
        delay = seg * step_time * 1.1
        is_head = seg == 0
        is_tail = seg == seg_count - 1
        scale = 1.15 if is_head else (0.55 if is_tail else 1.0 - seg * 0.06)

        parts = []
        if is_head:
            parts.append(f'<circle r="{6*scale:.1f}" class="dragon-body"/>')
            parts.append(f'<path d="M -3,-5 L -5,-11 L -1,-6 Z" class="dragon-spike"/>')
            parts.append(f'<path d="M 3,-5 L 5,-11 L 1,-6 Z" class="dragon-spike"/>')
            parts.append(f'<circle cx="3" cy="-1" r="1.6" class="dragon-eye"/>')
            parts.append(f'<circle cx="3.4" cy="-1" r="0.6" fill="#000"/>')
            parts.append(f'<path d="M 5,2 L 9,1 L 9,3.5 Z" class="dragon-body"/>')
            parts.append(f'<circle cx="8.3" cy="1.8" r="0.5" class="dragon-spike"/>')
        elif is_tail:
            parts.append(f'<path d="M -3,-3 L 4,0 L -3,3 Z" class="dragon-body"/>')
        else:
            parts.append(f'<circle r="{5*scale:.1f}" class="dragon-body"/>')
            parts.append(f'<circle r="{2.5*scale:.1f}" cy="{1.5*scale:.1f}" class="dragon-belly"/>')
            parts.append(
                f'<path d="M -2,{-5*scale:.1f} L 0,{-9*scale:.1f} L 2,{-5*scale:.1f} Z" '
                f'class="dragon-spike"/>'
            )

        seg_svg = "".join(parts)
        svg.append(
            f'<g>{seg_svg}'
            f'<animateMotion dur="{total:.2f}s" begin="{delay:.2f}s" '
            f'repeatCount="indefinite" rotate="auto" path="{d}"/>'
            f'</g>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    grid, num_weeks = fetch_contributions(args.user, token)
    svg = render_svg(grid, num_weeks)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(svg)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
