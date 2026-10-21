"""Validate per-platform metadata against each platform's limits and write CLIPS.md.

Usage: python build_report.py <clips_dir>
Reads <clips_dir>/metadata.json and render_log.json (written by render.py).
Hashtags are appended to each platform's main text, and limits are checked on
that final, ready-to-paste text. Lengths are counted in UTF-16 units, the
strictest way the platforms count (an emoji counts as 2).

Exit code 1 when any hard limit or hashtag rule is broken; under-target
lengths are only warnings. Limits and their sources: references/platforms.md.
"""
import json
import re
import sys
from pathlib import Path

# key, label, title (max, target), main text (field, max, target), hashtags (min, max)
PLATFORMS = [
    ("youtube", "YouTube Shorts", (100, 85), ("description", 5000, 1500), (3, 8)),
    ("tiktok", "TikTok", None, ("caption", 2200, 1000), (3, 6)),
    ("instagram", "Instagram Reels", None, ("caption", 2200, 1800), (3, 5)),
    ("facebook", "Facebook Reels", (255, 150), ("description", 63206, 1000), (1, 3)),
]
HASHTAG_RE = re.compile(r"^\w+$")

LABELS = {
    "en": {"clips": "clips", "source": "Source", "language": "Language", "summary": "Summary",
           "clip": "Clip", "duration": "Duration", "range": "Source range", "hook": "Hook", "why": "Why",
           "file": "File", "title": "Title", "description": "Description", "caption": "Caption",
           "notes": "Check by hand", "chars": "characters"},
    "es": {"clips": "clips", "source": "Fuente", "language": "Idioma", "summary": "Resumen",
           "clip": "Clip", "duration": "Duración", "range": "Tramo del original", "hook": "Hook", "why": "Por qué",
           "file": "Archivo", "title": "Título", "description": "Descripción", "caption": "Texto",
           "notes": "Revisar a mano", "chars": "caracteres"},
}


def u16(text):
    return len(text.encode("utf-16-le")) // 2


def as_text(value):
    return "\n\n".join(value) if isinstance(value, list) else (value or "")


def mmss(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m:02d}:{s:02d}"


def main():
    out_dir = Path(sys.argv[1])
    meta = json.loads((out_dir / "metadata.json").read_text())
    renders = {r["id"]: r for r in json.loads((out_dir / "render_log.json").read_text())}
    L = LABELS.get(meta.get("language", "en"), LABELS["en"])
    errors, warnings = [], []

    src = meta["source"]
    md = [f"# {src['title']} — {L['clips']}", "",
          f"{L['source']}: {src['url']} ({src.get('channel', '')}, {src.get('duration', '')}) · "
          f"{L['language']}: {meta.get('language', '')}", "",
          f"## {L['summary']}", "",
          f"| {L['clip']} | {L['duration']} | {L['range']} | {L['hook']} | {L['why']} |",
          "|---|---|---|---|---|"]
    for cid, clip in meta["clips"].items():
        r = renders.get(cid, {})
        ranges = ", ".join(f"{mmss(a)}–{mmss(b)}" for a, b in r.get("source_ranges", []))
        md.append(f"| {cid} | {r.get('duration', '?')} s | {ranges} | {r.get('hook', '')} | {clip.get('why', '')} |")

    for cid, clip in meta["clips"].items():
        r = renders.get(cid, {})
        md += ["", f"## {L['clip']} {cid}: {r.get('hook', '')}", "",
               f"{L['file']}: `{r.get('file', f'clip_{cid}.mp4')}` · {r.get('duration', '?')} s", ""]
        for key, label, title_rule, (field, body_max, body_target), (tag_min, tag_max) in PLATFORMS:
            p = clip.get(key)
            if not p:
                errors.append(f"{cid}/{key}: missing")
                continue
            md += [f"### {label}", ""]
            if title_rule:
                title = p.get("title", "")
                n = u16(title)
                if n > title_rule[0]:
                    errors.append(f"{cid}/{key} title: {n} > {title_rule[0]}")
                elif n < title_rule[1]:
                    warnings.append(f"{cid}/{key} title: {n} < target {title_rule[1]}")
                if key == "youtube" and re.search("[<>]", title):
                    errors.append(f"{cid}/youtube title: YouTube rejects < and >")
                md += [f"**{L['title']}** ({n}/{title_rule[0]})", "", "```text", title, "```", ""]

            tags = [t.lstrip("#") for t in p.get("hashtags", [])]
            bad = [t for t in tags if not HASHTAG_RE.match(t)]
            if bad:
                errors.append(f"{cid}/{key} hashtags not single words: {bad}")
            if not tag_min <= len(tags) <= tag_max:
                errors.append(f"{cid}/{key} hashtags: {len(tags)} (allowed {tag_min}-{tag_max})")
            if len({t.lower() for t in tags}) != len(tags):
                errors.append(f"{cid}/{key} hashtags repeated")

            body = as_text(p.get(field)).strip()
            final = body + ("\n\n" + " ".join(f"#{t}" for t in tags) if tags else "")
            n = u16(final)
            if n > body_max:
                errors.append(f"{cid}/{key} {field}: {n} > {body_max}")
            elif n < body_target:
                warnings.append(f"{cid}/{key} {field}: {n} < target {body_target}")
            if key == "youtube" and re.search("[<>]", final):
                errors.append(f"{cid}/youtube description: YouTube rejects < and >")
            md += [f"**{L[field]}** ({n:,}/{body_max:,} {L['chars']})", "", "```text", final, "```", ""]

    if meta.get("notes"):
        md += [f"## {L['notes']}", ""] + [f"- {n}" for n in meta["notes"]]
    (out_dir / "CLIPS.md").write_text("\n".join(md).rstrip() + "\n")

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"CLIPS.md written: {len(meta['clips'])} clips, {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
