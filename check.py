#!/usr/bin/env python3
"""Checks the Loam community catalog: run by CI on every pull request, and by hand with `python3 check.py`.

index.json, for every version of every plugin: the tag exists in the repository, points to the pinned commit, and
the plugin.json there has the plugin's id, the version's version and the permissions the catalog lists.

themes.json, for every theme: themes/<id>.json exists, is valid JSON, and uses only the keys, colours and values
docs/THEMES.md describes, with readable contrast (WCAG AA) in each appearance; every file of themes/ is listed.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ID = re.compile(r"^[a-z][a-z0-9.-]*$")
VERSION = re.compile(r"^\d+(\.\d+){0,3}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SDK = re.compile(r"^\d+\.\d+$")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")

COLOR_KEYS = {
    "accent", "text", "secondaryText", "background", "separator", "codeBackground", "link", "marker", "heading",
    "highlight", "tagText", "tagBackground", "checkbox", "checkboxBorder", "quoteBar", "sidebar", "ditherInk",
    "ditherPaper", "highlightText", "quoteBackground",
}
# The keys of a theme and what each value may be: a type, a set of words, or a (low, high) number range.
NUMBER = (int, float)
THEME_KEYS = {
    "fonts": {"body": str, "mono": str, "interface": str, "size": (9, 40), "letterSpacing": (-1, 3)},
    "editor": {"lineHeight": (0.8, 3), "columnWidth": (320, 2400), "paragraphSpacing": (0, 2)},
    "headings": {"font": str, "weight": {"regular", "medium", "semibold", "bold", "heavy"}, "sizes": list,
                 "rules": list, "letterSpacing": (-2, 3)},
    "tasks": {"checkbox": {"circle", "square"}, "strikethrough": bool},
    "tags": {"shape": {"rounded", "capsule"}},
    "sidebar": {"selection": {"filled", "soft"}},
    "shape": {"corners": {"soft", "square", "round"}},
    "icons": {"tint": {"mono", "color"}, "set": {"phosphor", "system"}},
    "cards": {"style": {"flat", "glass"}},
    "labels": {"style": {"mono", "plain"}},
    "decor": {"halftone": bool},
    "home": {"banner": bool},
    "images": {"dither": bool, "dotSize": (1, 8)},
}
APPEARANCES = {"light", "dark", "auto"}


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def check_plugins(path="index.json"):
    with open(path) as file:
        catalog = json.load(file)
    problems = []
    seen = set()
    for plugin in catalog.get("plugins", []):
        pid = plugin.get("id", "")
        where = f"plugin {pid or '?'}"
        if not ID.match(pid):
            problems.append(f"{where}: id must be lowercase letters, digits, '-' and '.'")
        if pid in seen:
            problems.append(f"{where}: listed twice")
        seen.add(pid)
        for key in ("name", "repo"):
            if not plugin.get(key):
                problems.append(f"{where}: no {key}")
        if not plugin.get("repo", "").startswith("https://"):
            problems.append(f"{where}: repo must be an https URL")
        versions = plugin.get("versions") or []
        if not versions:
            problems.append(f"{where}: no versions")
        for version in versions:
            label = f"{where} {version.get('version', '?')}"
            before = len(problems)
            if not VERSION.match(version.get("version", "")):
                problems.append(f"{label}: version must be numbers, like 1.2.0")
            if not COMMIT.match(version.get("commit", "")):
                problems.append(f"{label}: commit must be a full 40-character sha")
            if version.get("minSDK") and not SDK.match(version["minSDK"]):
                problems.append(f"{label}: minSDK must look like 1.12")
            if len(problems) > before or not plugin.get("repo", "").startswith("https://"):
                continue
            with tempfile.TemporaryDirectory() as folder:
                try:
                    git("clone", "-q", "--depth", "1", "--branch", version["tag"], "--", plugin["repo"], folder)
                except subprocess.CalledProcessError as error:
                    problems.append(f"{label}: cannot clone tag {version['tag']}: {error.stderr.strip()}")
                    continue
                commit = git("rev-parse", "HEAD", cwd=folder)
                if commit != version["commit"]:
                    problems.append(f"{label}: tag {version['tag']} is {commit}, not {version['commit']}")
                try:
                    with open(f"{folder}/plugin.json") as file:
                        manifest = json.load(file)
                except (OSError, ValueError) as error:
                    problems.append(f"{label}: no readable plugin.json: {error}")
                    continue
                if manifest.get("id") != pid:
                    problems.append(f"{label}: plugin.json says id {manifest.get('id')!r}")
                if manifest.get("version") != version["version"]:
                    problems.append(f"{label}: plugin.json says version {manifest.get('version')!r}")
                if version.get("permissions") is not None and sorted(manifest.get("permissions", [])) != sorted(version["permissions"]):
                    problems.append(f"{label}: plugin.json asks for {manifest.get('permissions', [])}, the catalog lists {version['permissions']}")
    return len(seen), problems


def check_colors(colors, where, problems):
    if not isinstance(colors, dict):
        problems.append(f"{where}: must be an object")
        return
    for key, value in colors.items():
        if key not in COLOR_KEYS:
            problems.append(f"{where}.{key}: not a theme colour (docs/THEMES.md lists them)")
        elif not isinstance(value, str) or not COLOR.match(value):
            problems.append(f"{where}.{key}: {value!r} is not #RRGGBB or #RRGGBBAA")


def luminance(hex_color):
    def channel(value):
        value = int(value, 16) / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = hex_color[1:3], hex_color[3:5], hex_color[5:7]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


# What must stay readable, as in Loam's own themes (WCAG AA): (colour, surface, minimum ratio).
READABLE = [
    ("text", "background", 4.5), ("heading", "background", 4.5), ("text", "sidebar", 4.5),
    ("secondaryText", "background", 3), ("link", "background", 3), ("accent", "background", 3),
    ("tagText", "tagBackground", 3),
]


def check_contrast(theme, where, problems):
    appearance = theme.get("appearance", "auto")
    light = theme.get("colors", {})
    sides = []
    if appearance != "dark":
        sides.append(("light" if appearance == "auto" else appearance, light))
    if appearance != "light":
        sides.append(("dark", {**light, **theme.get("dark", {}).get("colors", {})} if appearance == "auto" else light))
    for side, colors in sides:
        if appearance == "auto" and side == "dark" and not theme.get("dark"):
            problems.append(f"{where}: appearance auto needs a dark block, or set appearance to light or dark")
            continue
        for key, surface, minimum in READABLE:
            color, ground = colors.get(key), colors.get(surface)
            if not color or not ground or not COLOR.match(color) or not COLOR.match(ground):
                continue
            ratio = contrast(color, ground)
            if ratio < minimum:
                problems.append(f"{where}: {side} {key} on {surface} is {ratio:.2f}:1, needs {minimum}:1")


def check_theme(theme, where, problems):
    if not isinstance(theme, dict):
        problems.append(f"{where}: must be a JSON object")
        return
    for key, value in theme.items():
        if key == "name":
            if not isinstance(value, str) or not value:
                problems.append(f"{where}: name must be a string")
        elif key == "appearance":
            if value not in APPEARANCES:
                problems.append(f"{where}: appearance must be light, dark or auto")
        elif key == "colors":
            check_colors(value, f"{where}: colors", problems)
        elif key == "dark":
            if not isinstance(value, dict) or set(value) - {"colors"}:
                problems.append(f"{where}: dark only holds colors")
            else:
                check_colors(value.get("colors", {}), f"{where}: dark.colors", problems)
        elif key in THEME_KEYS:
            if not isinstance(value, dict):
                problems.append(f"{where}: {key} must be an object")
                continue
            for sub, item in value.items():
                rule = THEME_KEYS[key].get(sub)
                label = f"{where}: {key}.{sub}"
                if rule is None:
                    problems.append(f"{label}: not a theme key (docs/THEMES.md lists them)")
                elif isinstance(rule, set):
                    if item not in rule:
                        problems.append(f"{label}: must be one of {', '.join(sorted(rule))}")
                elif isinstance(rule, tuple):
                    if isinstance(item, bool) or not isinstance(item, NUMBER) or not rule[0] <= item <= rule[1]:
                        problems.append(f"{label}: must be a number from {rule[0]} to {rule[1]}")
                elif rule is list:
                    if not isinstance(item, list) or not all(isinstance(n, NUMBER) and not isinstance(n, bool) for n in item):
                        problems.append(f"{label}: must be a list of numbers")
                elif not isinstance(item, rule) or (rule is not bool and isinstance(item, bool)):
                    problems.append(f"{label}: must be a {rule.__name__}")
        else:
            problems.append(f"{where}: {key} is not a theme key (docs/THEMES.md lists them)")


def check_themes(path="themes.json"):
    with open(path) as file:
        catalog = json.load(file)
    folder = os.path.join(os.path.dirname(path) or ".", "themes")
    problems = []
    seen = set()
    for entry in catalog.get("themes", []):
        tid = entry.get("id", "")
        where = f"theme {tid or '?'}"
        if not ID.match(tid):
            problems.append(f"{where}: id must be lowercase letters, digits, '-' and '.'")
        if tid in seen:
            problems.append(f"{where}: listed twice")
        seen.add(tid)
        for key in ("name", "author", "description"):
            if not entry.get(key):
                problems.append(f"{where}: no {key}")
        if not VERSION.match(entry.get("version", "")):
            problems.append(f"{where}: version must be numbers, like 1.0.0")
        if entry.get("appearance", "auto") not in APPEARANCES:
            problems.append(f"{where}: appearance must be light, dark or auto")
        try:
            with open(os.path.join(folder, f"{tid}.json")) as file:
                theme = json.load(file)
        except (OSError, ValueError) as error:
            problems.append(f"{where}: no readable themes/{tid}.json: {error}")
            continue
        check_theme(theme, f"{where} (themes/{tid}.json)", problems)
        if isinstance(theme, dict):
            check_contrast(theme, f"{where} (themes/{tid}.json)", problems)
        if isinstance(theme, dict) and theme.get("name", entry.get("name")) != entry.get("name"):
            problems.append(f"{where}: themes/{tid}.json is named {theme.get('name')!r}, themes.json says {entry.get('name')!r}")
        if isinstance(theme, dict) and theme.get("appearance", "auto") != entry.get("appearance", "auto"):
            problems.append(f"{where}: themes.json and themes/{tid}.json disagree on appearance")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json") and name[:-5] not in seen:
                problems.append(f"themes/{name}: not listed in themes.json")
    return len(seen), problems


def main(plugins="index.json", themes="themes.json"):
    plugin_count, problems = check_plugins(plugins)
    theme_count, theme_problems = check_themes(themes)
    problems += theme_problems
    for problem in problems:
        print(problem)
    print(f"{plugin_count} plugins, {theme_count} themes, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
