#!/usr/bin/env python3
"""
lottery_engine/cli/registry_report.py

Registry completeness report for Wave 1 states.
Shows which states are fully seeded, which are stubs,
which slugs are verified, and which source coverage exists.

Usage:
    python -m cli.registry_report
    python -m cli.registry_report --state GA
    python -m cli.registry_report --format detail
    python -m cli.registry_report --format sources
    python -m cli.registry_report --wave 1
"""
import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── ANSI ───────────────────────────────────────────────────────────────────────
def _c(s, code): return f"\033[{code}m{s}\033[0m" if sys.stdout.isatty() else s
def _green(s):  return _c(s, "32")
def _red(s):    return _c(s, "31")
def _amber(s):  return _c(s, "33")
def _bold(s):   return _c(s, "1")
def _dim(s):    return _c(s, "2")
def _cyan(s):   return _c(s, "36")


WAVE1_ORDER = ["GA","FL","NY","PA","OH","MI","IL","TN","CA","TX","OR"]

MODULE_MAP = {
    "GA": "registry.definitions.georgia",
    "FL": "registry.definitions.florida",
    "NY": "registry.definitions.new_york",
    "PA": "registry.definitions.pennsylvania",
    "OH": "registry.definitions.ohio",
    "MI": "registry.definitions.michigan",
    "IL": "registry.definitions.illinois",
    "TN": "registry.definitions.tennessee",
    "CA": "registry.definitions.california",
    "TX": "registry.definitions.texas",
    "OR": "registry.definitions.oregon",
}


def load_state_data(state_code: str) -> dict | None:
    """Load REGISTRY_META and definition lists for one state."""
    mod_name = MODULE_MAP.get(state_code)
    if not mod_name:
        return None
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        return None

    meta        = getattr(mod, "REGISTRY_META", {})
    job_defs    = getattr(mod, "JOB_DEFINITIONS", [])
    src_maps    = getattr(mod, "SOURCE_MAPPINGS", [])

    # Derived stats
    # Always use .value so sources_present contains plain strings, not enum objects
    sources_present  = sorted(set(
        m.source_name.value if hasattr(m.source_name, "value") else str(m.source_name)
        for m in src_maps
    ))
    estimated_slugs  = sum(1 for m in src_maps if "ESTIMATED" in (m.notes or ""))
    verified_slugs   = sum(1 for m in src_maps if getattr(m, "slug_verified", False))
    games            = sorted(set(j.game_type for j in job_defs))
    draw_times       = {}
    for j in job_defs:
        draw_times.setdefault(j.game_type, set()).add(j.draw_time)

    # Status badge
    status = meta.get("status", "unknown")
    has_ln = any("lottery.net" in str(s) for s in sources_present)

    return {
        "code":            state_code,
        "name":            meta.get("state_name", state_code),
        "wave":            meta.get("wave", "?"),
        "tier":            meta.get("tier", "?"),
        "complexity":      meta.get("complexity", "?"),
        "status":          status,
        "games":           games,
        "draws_per_day":   meta.get("draws_per_day", "?"),
        "draw_times":      {g: sorted(t) for g, t in draw_times.items()},
        "n_jobs":          len(job_defs),
        "n_mappings":      len(src_maps),
        "sources":         sources_present,
        "has_lottery_net": has_ln,
        "estimated_slugs": estimated_slugs,
        "verified_slugs":  verified_slugs,
        "slugs_verified":  meta.get("slugs_verified", False),
        "game_names":      meta.get("game_names", {}),
        "notes":           meta.get("notes", ""),
    }


def status_badge(d: dict) -> str:
    s = d["status"]
    if s == "seeded"   : return _green("SEEDED")
    if s == "stub"     : return _amber("STUB  ")
    return _dim(s.upper()[:6].ljust(6))


def slug_badge(d: dict) -> str:
    if d["slugs_verified"]:
        return _green("verified")
    if d["estimated_slugs"] > 0:
        return _amber(f"est:{d['estimated_slugs']}")
    return _dim("untagged")


def complexity_badge(c: str) -> str:
    if c == "standard": return _green("standard")
    if c == "moderate": return _amber("moderate")
    if c == "high":     return _red("high    ")
    return c


def _sources_str(d: dict) -> str:
    parts = []
    for src in ["lottery.net", "lotterycorner.com", "lotteryusa.com"]:
        has = any(src in str(s) for s in d["sources"])
        if has:
            parts.append(_green(src[:6]))
        else:
            parts.append(_dim(src[:6]))
    return " ".join(parts)


# ── Report formats ─────────────────────────────────────────────────────────────

def print_summary(states: list[dict]) -> None:
    """One-line-per-state table."""
    print()
    print(_bold("Wave 1 Registry Summary"))
    print(_bold("─" * 90))
    hdr = (f"  {'ST':<4} {'NAME':<14} {'TIER':<5} {'COMPLEXITY':<10} "
           f"{'STATUS':<8} {'JOBS':<5} {'MAPS':<5} {'SLUGS':<12} "
           f"{'LN':<3} {'LC':<3} {'LU':<3} {'GAMES'}")
    print(_bold(hdr))
    print("─" * 90)

    for d in states:
        ln = _green("✓") if any("lottery.net"      in s for s in d["sources"]) else _dim("–")
        lc = _green("✓") if any("lotterycorner.com" in s for s in d["sources"]) else _dim("–")
        lu = _green("✓") if any("lotteryusa.com"    in s for s in d["sources"]) else _dim("–")
        games = "+".join(d["games"])
        dpd   = f"({d['draws_per_day']}/day)"
        print(
            f"  {d['code']:<4} {d['name']:<14} {d['tier']:<5} "
            f"{complexity_badge(d['complexity']):<18} "
            f"{status_badge(d):<16} "
            f"{d['n_jobs']:<5} {d['n_mappings']:<5} "
            f"{slug_badge(d):<20} "
            f"{ln}  {lc}  {lu}  {games} {dpd}"
        )
    print()


def print_detail(states: list[dict]) -> None:
    """Per-state detailed breakdown."""
    print()
    print(_bold("Wave 1 Registry Detail Report"))
    print()
    for d in states:
        icon = "✓" if d["status"]=="seeded" else "◎"
        print(_bold(f"  {icon} {d['code']} — {d['name']}"))
        print(f"    Wave: {d['wave']}  Tier: {d['tier']}  "
              f"Complexity: {complexity_badge(d['complexity'])}  "
              f"Status: {status_badge(d)}")
        print(f"    Jobs: {d['n_jobs']}  Mappings: {d['n_mappings']}  "
              f"Draws/day: {d['draws_per_day']}")

        for game, times in d["draw_times"].items():
            gname = d["game_names"].get(game, game)
            print(f"    {game} ({gname}): {', '.join(times)}")

        print(f"    Sources: {', '.join(d['sources']) or 'none'}")

        slug_info = (
            _green("verified on live site")
            if d["slugs_verified"]
            else _amber(f"{d['estimated_slugs']} ESTIMATED — run dry-run validation first")
        )
        print(f"    Slugs:   {slug_info}")

        if d["notes"]:
            # Wrap notes at 70 chars
            words = d["notes"].split()
            line, lines = "", []
            for w in words:
                if len(line)+len(w)+1 > 70:
                    lines.append(line)
                    line = w
                else:
                    line = (line+" "+w).strip()
            if line:
                lines.append(line)
            for i, l in enumerate(lines):
                prefix = "    Notes: " if i == 0 else "           "
                print(f"{prefix}{_dim(l)}")
        print()


def print_sources(states: list[dict]) -> None:
    """Per-state per-game per-draw_time source coverage matrix."""
    print()
    print(_bold("Wave 1 Source Coverage Matrix"))
    print(_bold("─" * 80))
    print(f"  {'ST':<4} {'GAME':<8} {'TIME':<10} {'lottery.net':<20} "
          f"{'lotterycorner':<20} {'lotteryusa':<15}")
    print("─" * 80)

    from registry.definitions import ALL_SOURCE_MAPPINGS

    for d in states:
        state = d["code"]
        for game in d["games"]:
            for dt in d["draw_times"].get(game, []):
                maps = [m for m in ALL_SOURCE_MAPPINGS
                        if m.job_def.state == state
                        and m.job_def.game_type == game
                        and m.job_def.draw_time == dt]

                def cell(src_key):
                    m = next((x for x in maps if src_key in str(x.source_name)), None)
                    if not m:
                        return _dim("—")
                    slug = m.source_game_slug or "?"
                    est  = "ESTIMATED" in (m.notes or "")
                    verified = getattr(m, "slug_verified", False)
                    if verified:
                        return _green(slug[:18])
                    elif est:
                        return _amber(f"~{slug[:17]}")
                    else:
                        return slug[:18]

                print(f"  {state:<4} {game:<8} {dt:<10} "
                      f"{cell('lottery.net'):<28} "
                      f"{cell('lotterycorner'):<28} "
                      f"{cell('lotteryusa'):<22}")
    print()
    print(_dim("  Legend: green=slug verified  amber=slug estimated(~)  —=not mapped"))
    print()


def print_onboarding_order(states: list[dict]) -> None:
    """Print recommended onboarding order with rationale."""
    print()
    print(_bold("Recommended Wave 1 Onboarding Order"))
    print(_bold("─" * 60))

    ORDER_NOTES = {
        "GA": ("DONE",   "Reference state. All architecture validated."),
        "FL": ("NEXT-1", "High-value standard state. Safe validation of FL slugs."),
        "NY": ("NEXT-2", "Unique game names (Numbers/Win4). Tests name flexibility."),
        "PA": ("NEXT-3", "Standard slugs. Confirms PA draw timing and LZ handling."),
        "OH": ("4",      "Standard. Validates OH engine behavior."),
        "MI": ("5",      "Daily 3/4 game names. Cross-checks slug pattern."),
        "IL": ("6",      "Standard. Large state, good coverage test."),
        "TN": ("7",      "Cash 3/4 names like GA. Quick win after GA reference."),
        "CA": ("8",      "3-draw/day. First moderate-complexity state in wave."),
        "TX": ("9",      "4-draw/day + Daily 4 name. Primary complexity test."),
        "OR": ("10",     "Game availability unclear. Validate before ingesting."),
    }

    for d in states:
        step, rationale = ORDER_NOTES.get(d["code"], ("?", ""))
        status_str = status_badge(d)
        complexity_str = complexity_badge(d["complexity"])
        step_str = _green(f"[{step}]") if step == "DONE" else f"[{step}]"
        print(f"  {step_str:<8} {d['code']:<4} {d['name']:<15} "
              f"{complexity_str:<18}  {_dim(rationale)}")
    print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        prog="python -m cli.registry_report",
        description="Registry completeness report for Wave 1 states.",
    )
    p.add_argument("--state",  help="Show only this state, e.g. GA")
    p.add_argument("--format", default="all",
                   choices=["all","summary","detail","sources","order"],
                   help="Report format (default: all)")
    p.add_argument("--wave",   type=int, default=1, help="Wave number (default: 1)")
    args = p.parse_args()

    states_to_show = [s for s in WAVE1_ORDER
                      if args.state is None or s == args.state.upper()]
    data = [d for code in states_to_show
            if (d := load_state_data(code)) is not None]

    missing = [s for s in states_to_show
               if not any(d["code"] == s for d in data)]
    if missing:
        print(_red(f"\nMISSING from registry: {missing}"))
        print(_dim("  Create registry/definitions/{state}.py for each missing state.\n"))

    if args.format in ("all", "summary"):
        print_summary(data)

    if args.format in ("all", "order"):
        print_onboarding_order(data)

    if args.format in ("all", "detail"):
        print_detail(data)

    if args.format in ("all", "sources"):
        print_sources(data)


if __name__ == "__main__":
    main()
