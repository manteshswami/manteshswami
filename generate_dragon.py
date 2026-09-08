#!/usr/bin/env python3
"""
Generate an animated SVG of a dragon "eating" a GitHub contribution graph.

Usage:
    python generate_dragon.py --user manteshswami --out dist/dragon.svg --theme light
    python generate_dragon.py --user manteshswami --out dist/dragon-dark.svg --theme dark
"""
import argparse
import json
import math
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

THEMES = {
    "light": {
        "background": "#ffffff",
        "empty": "#ebedf0",
        "levels": ["#ebedf0", "#c6e48b", "#7bc96f", "#239a3b", "#196127"],
        "dragon_body": "#2ea043",
        "dragon_belly": "#7ee787",
        "dragon_spike": "#0e4429",
        "dragon_eye": "#ffd33d",
    },
    "dark": {
        "background": "#0d1117",
        "empty": "#161b22",
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "dragon_body": "#ff6b35",
        "dragon_belly": "#ffb703",
        "dragon_spike": "#7a1f0d",
        "dragon_eye": "#39d353",
    },
}

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
    """Bucket a count into 0-4 using simple quartile-ish thresholds."""
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
    """Boustrophedon path visiting every cell of the grid, column by column."""
    path = []
    for w in range(num_weeks):
        rows = range(7) if w % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((w, r))
    return path


def cell_pixel(w, r):
    return MARGIN + w * STEP + CELL / 2, MARGIN + r * STEP + CELL / 2


def render_svg(grid, num_weeks, theme_name):
    theme = THEMES[theme_name]
    path = build_path(num_weeks)
    n = len(path)

    all_counts = list(grid.values())
    levels = {cell: level_for_count(grid.get(cell, 0), all_counts) for cell in path}

    width = MARGIN * 2 + num_weeks * STEP
    height = MARGIN * 2 + 7 * STEP

    step_time = 0.12
    total = n * step_time
    reset_frac = 0.985  # fraction of the loop where filled cells snap back to empty

    svg = []
    svg.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="sans-serif">'
    )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{theme["background"]}"/>')

    # --- grid cells (empty base + animated filled overlay) ---
    for i, (w, r) in enumerate(path):
        x = MARGIN + w * STEP
        y = MARGIN + r * STEP
        lvl = levels[(w, r)]
        fill = theme["levels"][lvl]
        t1 = round(i / n, 4)
        svg.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{theme["empty"]}"/>'
        )
        if lvl > 0:
            svg.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}" opacity="0">'
                f'<animate attributeName="opacity" '
                f'values="0;0;1;1;0" '
                f'keyTimes="0;{t1};{t1};{reset_frac};1" '
                f'dur="{total:.2f}s" begin="0s" repeatCount="indefinite" calcMode="discrete"/>'
                f'</rect>'
            )

    # --- motion path for the dragon (invisible guide) ---
    pts = [cell_pixel(w, r) for w, r in path]
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    # --- dragon segments ---
    seg_count = 7  # 0 = head, last = tail tip
    for seg in range(seg_count):
        delay = seg * step_time * 1.1
        is_head = seg == 0
        is_tail = seg == seg_count - 1
        scale = 1.15 if is_head else (0.55 if is_tail else 1.0 - seg * 0.06)
        body_fill = theme["dragon_body"]

        parts = []
        if is_head:
            parts.append(f'<circle r="{6*scale:.1f}" fill="{body_fill}"/>')
            parts.append(f'<path d="M -3,-5 L -5,-11 L -1,-6 Z" fill="{theme["dragon_spike"]}"/>')
            parts.append(f'<path d="M 3,-5 L 5,-11 L 1,-6 Z" fill="{theme["dragon_spike"]}"/>')
            parts.append(f'<circle cx="3" cy="-1" r="1.6" fill="{theme["dragon_eye"]}"/>')
            parts.append(f'<circle cx="3.4" cy="-1" r="0.6" fill="#000"/>')
            parts.append(f'<path d="M 5,2 L 9,1 L 9,3.5 Z" fill="{body_fill}"/>')
            parts.append(f'<circle cx="8.3" cy="1.8" r="0.5" fill="{theme["dragon_spike"]}"/>')
        elif is_tail:
            parts.append(f'<path d="M -3,-3 L 4,0 L -3,3 Z" fill="{body_fill}"/>')
        else:
            parts.append(f'<circle r="{5*scale:.1f}" fill="{body_fill}"/>')
            parts.append(
                f'<circle r="{2.5*scale:.1f}" cy="{1.5*scale:.1f}" fill="{theme["dragon_belly"]}"/>'
            )
            parts.append(
                f'<path d="M -2,{-5*scale:.1f} L 0,{-9*scale:.1f} L 2,{-5*scale:.1f} Z" '
                f'fill="{theme["dragon_spike"]}"/>'
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
    ap.add_argument("--theme", choices=["light", "dark"], default="dark")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    grid, num_weeks = fetch_contributions(args.user, token)
    svg = render_svg(grid, num_weeks, args.theme)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(svg)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
