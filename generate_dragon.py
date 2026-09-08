#!/usr/bin/env python3
"""
Generate an animated SVG of a growing dragon "eating" a GitHub contribution graph.
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

    step_time = 0.10
    total = n * step_time

    svg = []
    svg.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">'
    )
    
    # --- Rich Dark Theme CSS ---
    svg.append("""
    <style>
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
    </style>
    """)

    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" class="bg"/>')

    # --- 1. Show all contribution cells immediately (Static background graph) ---
    for w, r in path:
        x = MARGIN + w * STEP
        y = MARGIN + r * STEP
        lvl = levels[(w, r)]
        css_class = f"lvl-{lvl}" if lvl > 0 else "empty"
        svg.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" class="{css_class}"/>')

    # --- Motion path ---
    pts = [cell_pixel(w, r) for w, r in path]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    # --- 2. Growing Dragon Body Segments ---
    seg_count = 10  # More segments for a smoother, longer dragon body
    for seg in range(seg_count):
        delay = seg * step_time * 0.9
        is_head = seg == 0
        is_tail = seg == seg_count - 1
        
        # Make the head large, body smoothly tapers back to the tail tip
        scale = 1.3 if is_head else (0.4 if is_tail else 1.15 - (seg * 0.08))

        parts = []
        if is_head:
            parts.append(f'<circle r="{7*scale:.1f}" class="dragon-body"/>')
            parts.append(f'<path d="M -3,-6 L -6,-13 L -1,-7 Z" class="dragon-spike"/>')
            parts.append(f'<path d="M 3,-6 L 6,-13 L 1,-7 Z" class="dragon-spike"/>')
            parts.append(f'<circle cx="3.5" cy="-1.5" r="1.8" class="dragon-eye"/>')
            parts.append(f'<circle cx="4" cy="-1.5" r="0.7" fill="#000"/>')
            parts.append(f'<path d="M 6,2 L 10,1 L 10,3.8 Z" class="dragon-body"/>')
            parts.append(f'<circle cx="9.3" cy="2" r="0.6" class="dragon-spike"/>')
        elif is_tail:
            parts.append(f'<path d="M -4,-3 L 5,0 L -4,3 Z" class="dragon-body"/>')
        else:
            parts.append(f'<circle r="{6*scale:.1f}" class="dragon-body"/>')
            parts.append(f'<circle r="{3*scale:.1f}" cy="{1.5*scale:.1f}" class="dragon-belly"/>')
            parts.append(
                f'<path d="M -2,{-6*scale:.1f} L 0,{-10*scale:.1f} L 2,{-6*scale:.1f} Z" '
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
