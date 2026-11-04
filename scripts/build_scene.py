"""Generate the animated ASCII scenes used by the profile README.

Run with: python build_scene.py

Everything sits on a character grid: `row(k)` gives the baseline of row k and
`CHAR_W` the width of a column, so the art lines up whatever font the viewer has.

Fox art markup: text between « » is cream, text between ‹ › is dark.
"""
from html import escape
from pathlib import Path

CHAR_W = 9.6
ROW_H = 18
WIDTH = 540
FRAME_COLS = 53
FRAME_X = (WIDTH - FRAME_COLS * CHAR_W) / 2
CONTENT_X = FRAME_X + 2 * CHAR_W  # Inner area: 49 columns.
INNER_COLS = FRAME_COLS - 4

# The background matches GitHub's dark mode, so the scenes blend into the page.
COLORS = {
    "bg": "#0D1117", "fg": "#E6EDF3", "dim": "#8B949E", "ok": "#3FB950", "fox": "#F0883E",
    "cream": "#FFF1DF", "dark": "#C9793F", "tree": "#3FB950", "accent": "#58A6FF",
    "fire": "#FF7B72", "gold": "#E3B341",
}
TEXT_ROLES = ("fg", "dim", "ok", "accent")  # Must be readable text: at least 4.5:1.
ART_ROLES = ("fox", "cream", "dark", "tree", "fire", "gold")  # Larger shapes: at least 3:1.


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def contrast_failures():
    """Return every colour that would be hard to read on the background."""
    failures = []
    for roles_group, minimum in ((TEXT_ROLES, 4.5), (ART_ROLES, 3.0)):
        for role in roles_group:
            ratio = contrast(COLORS[role], COLORS["bg"])
            if ratio < minimum:
                failures.append(f"{role} {COLORS[role]} is {ratio:.2f}:1, needs {minimum}:1")
    return failures


EARS = [r" /\     /\ ", r"/  \___/  \ "]
EYES = {
    "front": r"\  «o»   «o»  /",
    "right": r"\   «o»   «o» /",
    "left": r"\ «o»   «o»   /",
    "blink": r"\  «-»   «-»  /",
}
SNOUT = r" `. «(_)» .'"
TAIL_UP_TOP = [r"                 «_»", r"                «/ \»", r"               «/»  /"]
BODY = {
    "rest_up": TAIL_UP_TOP + [r"   )   (______/  /", r"  (‹_|_|_›)_______'"],
    "rest_down": [r"", r"", r"", r"   )   (_______.-«~~~~-.»", r"  (‹_|_|_›)______`-«~~~~-'»"],
    "walk_a": TAIL_UP_TOP + [r"   )   (______/  /", r"  (‹/_|_\›)_______'"],
    "walk_b": [r"", r"", r"", r"   )   (_______.-«~~~~-.»", r"  (‹_\_/_›)______`-«~~~~-'»"],
}

TREE = ["    /\\", "   /  \\", "  /    \\", " /______\\", "    ||"]


def row(k):
    return 22 + ROW_H * k


def col_x(col):
    return CONTENT_X + col * CHAR_W


def walk(eyes, start, end, step=2, pace=0.3):
    """Timeline steps that move the fox from column start to column end."""
    direction = step if end > start else -step
    steps, col, stride = [], start, 0
    while col != end:
        col += direction
        steps.append((pace, eyes, "walk_a" if stride % 2 == 0 else "walk_b", col))
        stride += 1
    return steps


def wag(eyes, col, times=2):
    """Timeline steps that swing the tail."""
    steps = []
    for _ in range(times):
        steps += [(0.4, eyes, "rest_down", col), (0.4, eyes, "rest_up", col)]
    return steps


def text(line, y, x0=CONTENT_X, css="fg"):
    """Render one run with a fixed width, keeping columns aligned on any font."""
    stripped = line.lstrip(" ").rstrip()
    if not stripped:
        return ""
    x = x0 + (len(line) - len(line.lstrip(" "))) * CHAR_W
    length = len(stripped) * CHAR_W
    return (f'<text x="{x:.1f}" y="{y}" class="{css}" textLength="{length:.1f}" '
            f'lengthAdjust="spacing">{escape(stripped, quote=False)}</text>')


def art(line, y):
    """Render a fox line, splitting it into one text run per colour."""
    closers = {"«": ("cream", "»"), "‹": ("dark", "›")}
    out, column, i = [], 0, 0
    while i < len(line):
        if line[i] in closers:
            css, closer = closers[line[i]]
            end = line.index(closer, i)
            run = line[i + 1:end]
            i = end + 1
        else:
            css, end = "fox", i
            while end < len(line) and line[end] not in closers:
                end += 1
            run = line[i:end]
            i = end
        out.append(text(run, y, x0=CONTENT_X + column * CHAR_W, css=css))
        column += len(run)
    return "".join(out)


def block(lines, top_row, col=0, css="fg"):
    return "".join(text(line, row(top_row + i), x0=col_x(col), css=css) for i, line in enumerate(lines))


def on_off(name, flags, durations):
    """Hard on/off keyframes, so frames swap like a flipbook."""
    total, elapsed, stops = sum(durations), 0.0, []
    for flag, duration in zip(flags, durations):
        value = 1 if flag else 0
        stops.append(f"{elapsed / total * 100:.3f}%{{opacity:{value}}}")
        elapsed += duration
        stops.append(f"{max(elapsed / total * 100 - 0.001, 0):.3f}%{{opacity:{value}}}")
    return f"@keyframes {name}{{{''.join(stops)}}}"


def border(title, rows):
    """Draw the window frame out of characters, like the rest of the scene."""
    head = f".-[ {title} ]"
    lines = [text(head + "-" * (FRAME_COLS - len(head) - 1) + ".", row(0), x0=FRAME_X, css="dim")]
    for k in range(1, rows):
        lines.append(text("|", row(k), x0=FRAME_X, css="dim"))
        lines.append(text("|", row(k), x0=FRAME_X + (FRAME_COLS - 1) * CHAR_W, css="dim"))
    lines.append(text("'" + "-" * (FRAME_COLS - 2) + "'", row(rows), x0=FRAME_X, css="dim"))
    return "".join(lines)


def fox_parts(timeline, top_row, delay):
    """Build the fox plus the keyframes that follow its timeline."""
    durations = [step[0] for step in timeline]
    loop = sum(durations)
    first_eyes, first_body = timeline[0][1], timeline[0][2]
    timing = f"{loop:.2f}s step-end {delay:.2f}s infinite"

    def frame(name, content, still):
        css = "frame still" if still else "frame"
        return f'<g class="{css}" style="animation:{name} {timing}">{content}</g>'

    parts = [art(line, row(top_row + i)) for i, line in enumerate(EARS)]
    keyframes = []
    for name, line in EYES.items():
        if any(step[1] == name for step in timeline):
            parts.append(frame(f"e-{name}", art(line, row(top_row + 2)), name == first_eyes))
            keyframes.append(on_off(f"e-{name}", [s[1] == name for s in timeline], durations))
    parts.append(art(SNOUT, row(top_row + 3)))
    for name, lines in BODY.items():
        if any(step[2] == name for step in timeline):
            content = "".join(art(line, row(top_row + 1 + i)) for i, line in enumerate(lines))
            parts.append(frame(f"b-{name}", content, name == first_body))
            keyframes.append(on_off(f"b-{name}", [s[2] == name for s in timeline], durations))

    elapsed, stops = 0.0, []
    for duration, _, _, col in timeline:
        tx = col * CHAR_W
        stops.append(f"{elapsed / loop * 100:.3f}%{{transform:translateX({tx:.1f}px)}}")
        elapsed += duration
        stops.append(f"{max(elapsed / loop * 100 - 0.001, 0):.3f}%{{transform:translateX({tx:.1f}px)}}")
    keyframes.append(f"@keyframes walk{{{''.join(stops)}}}")
    start_tx = timeline[0][3] * CHAR_W
    walker = (f'<g class="walker" style="transform:translateX({start_tx:.1f}px);animation:walk {timing}">'
              f'{"".join(parts)}</g>')
    return walker, keyframes


def prop_frames(prefix, frames, top_row, col, css, pace):
    """Animate a prop by cycling through equally long frames."""
    durations = [pace] * len(frames)
    parts, keyframes = [], []
    for i, lines in enumerate(frames):
        name = f"{prefix}-{i}"
        state = "frame still" if i == 0 else "frame"
        parts.append(f'<g class="{state}" style="animation:{name} {pace * len(frames):.2f}s step-end infinite">'
                     f'{block(lines, top_row, col, css)}</g>')
        keyframes.append(on_off(name, [j == i for j in range(len(frames))], durations))
    return "".join(parts), keyframes


def stylesheet(keyframes):
    c = COLORS
    return f"""
text{{font:15.5px ui-monospace,SFMono-Regular,Consolas,Menlo,'DejaVu Sans Mono',monospace;white-space:pre}}
.fg{{fill:{c['fg']}}}.dim{{fill:{c['dim']}}}.ok{{fill:{c['ok']}}}.tree{{fill:{c['tree']}}}.accent{{fill:{c['accent']}}}
.fire{{fill:{c['fire']};font-weight:600}}.gold{{fill:{c['gold']};font-weight:600}}
.fox{{fill:{c['fox']};font-weight:600}}.cream{{fill:{c['cream']};font-weight:600}}.dark{{fill:{c['dark']};font-weight:600}}
.bgfill{{fill:{c['bg']}}}
.line{{opacity:0;animation:show .01s linear forwards}}
.frame{{opacity:0}}
.cursor{{fill:{c['fg']};animation:blink 1.1s step-end infinite}}
@keyframes show{{to{{opacity:1}}}}@keyframes hide{{to{{opacity:0;visibility:hidden}}}}
@keyframes type{{to{{transform:translateX(var(--d))}}}}
@keyframes blink{{50%{{opacity:0}}}}
{''.join(keyframes)}
@media (prefers-reduced-motion:reduce){{
*{{animation:none!important}}
.line{{opacity:1!important}}.bgfill{{display:none}}
.walker{{transform:none!important}}.frame.still{{opacity:1}}
}}
"""


def svg_document(label, rows, css, body):
    height = row(rows) + 12
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" '
            f'height="{height}" role="img" aria-label="{escape(label)}">\n<style>{css}</style>\n'
            f'<rect width="{WIDTH}" height="{height}" fill="{COLORS["bg"]}"/>\n{body}\n</svg>\n')


def login_scene():
    def typed(line, k, prefix_len, begin, duration):
        chars = len(line) - prefix_len
        distance = chars * CHAR_W
        cover_x = CONTENT_X + prefix_len * CHAR_W
        y = row(k)
        return (f'<g class="line" style="animation-delay:{begin - 0.02:.2f}s">{text(line, y)}'
                f'<rect x="{cover_x:.1f}" y="{y - 14}" width="{distance + 4:.1f}" height="18" class="bgfill" '
                f'style="--d:{distance:.1f}px;animation:type {duration}s steps({chars}) {begin}s forwards"/></g>')

    def appear(content, begin):
        return f'<g class="line" style="animation-delay:{begin:.2f}s">{content}</g>'

    login = [
        typed("guest@github:~$ ssh fjjorda", 1, 16, 0.6, 1.1),
        appear(text("Connecting to the forest...", row(2), css="dim"), 2.1),
        typed("login: guest", 4, 7, 2.9, 0.6),
        typed("password: ********", 5, 10, 3.9, 0.8),
        appear(text("Access granted.", row(7), css="ok"), 5.2),
        appear(f'<rect class="cursor" x="{col_x(0):.1f}" y="{row(8) - 13}" width="9" height="16"/>', 5.8),
    ]
    body = border("fjjorda", 9) + f'<g class="login">{"".join(login)}</g>'
    return svg_document("Terminal login animation that ends with access granted", 9, stylesheet([]), body)


def strip(label, title, command, timeline, static="", props=()):
    """A short scene for one README section: prompt, fox, props and ground."""
    fox, keyframes = fox_parts(timeline, 2, 0)
    animated = ""
    for prefix, frames, top_row, col, css, pace in props:
        content, frames_css = prop_frames(prefix, frames, top_row, col, css, pace)
        animated += content
        keyframes += frames_css
    body = (border(title, 9) + text(command, row(1), css="dim") + static + animated + fox
            + text("." * INNER_COLS, row(8), css="dim"))
    return svg_document(label, 9, stylesheet(keyframes), body)


def about_scene():
    timeline = [
        (1.8, "right", "rest_up", 0), (0.15, "blink", "rest_up", 0), *walk("right", 0, 6),
        (1.6, "right", "rest_up", 6), *wag("front", 6, 1), (0.15, "blink", "rest_up", 6),
        (1.2, "left", "rest_up", 6), *walk("left", 6, 0), (1.2, "front", "rest_down", 0),
    ]
    trees = block(TREE, 3, 31, "tree") + block(TREE, 3, 40, "tree")
    return strip("An ASCII fox walking towards two trees", "~/about", "guest@forest:~$ cd about/", timeline, trees)


def urbanpulse_scene():
    timeline = [
        (2.2, "right", "rest_up", 0), (0.15, "blink", "rest_up", 0), (1.8, "right", "rest_up", 0),
        *walk("right", 0, 4), *wag("right", 4, 1), (1.6, "right", "rest_up", 4),
        *walk("left", 4, 0), (1.4, "front", "rest_down", 0),
    ]
    city = block([
        "       ____",
        "  __  |    | __",
        " |  | |    ||  |",
        " |  |_|    ||  |",
        "_|__|_|____||__|_",
    ], 3, 31, "fg")
    windows = [
        ["", "", "        o", "  o      o  o", "     "],
        ["", "", "          o", "  o      o", "             o"],
        ["", "", "        o o", "           o", "  o"],
    ]
    alert = [["", " "], ["", "  (!)"], ["", "  (!)"], ["", " "]]
    props = [("win", windows, 3, 31, "gold", 0.9), ("alert", alert, 1, 36, "fire", 0.7)]
    return strip("An ASCII fox watching a city at night while an incident alert blinks", "~/projects/urbanpulse",
                 "guest@forest:~/projects$ cd urbanpulse/", timeline, city, props)


def firesentinel_scene():
    timeline = [
        (2.6, "right", "rest_up", 0), (0.15, "blink", "rest_up", 0), (1.6, "right", "rest_up", 0),
        *wag("right", 0, 1), (2.0, "front", "rest_down", 0), (0.15, "blink", "rest_down", 0),
        (1.6, "right", "rest_up", 0),
    ]
    base = block(["  _\\/_\\/_"], 7, 35, "dark")
    flames = [
        ["     (", "    ) )", "   ( ( (", "    ) ) )"],
        ["      )", "    ( (", "   ) ) )", "   ( ( ("],
        ["    (", "     ) )", "    ( ( (", "   ) ) )"],
    ]
    # The satellite crosses the top row, scanning the fire below.
    satellite = [[f"{' ' * col}=[o]="] for col in range(14, 44, 6)]
    props = [("fire", flames, 3, 35, "fire", 0.28), ("sat", satellite, 2, 0, "accent", 1.2)]
    return strip("An ASCII fox watching a flickering fire while a satellite passes overhead",
                 "~/projects/firesentinel", "guest@forest:~/projects$ cd firesentinel/", timeline, base, props)


def casa_scene():
    timeline = [
        (2.0, "right", "rest_up", 0), *walk("right", 0, 8), (1.8, "right", "rest_up", 8),
        (0.15, "blink", "rest_up", 8), *wag("right", 8, 2), (1.2, "front", "rest_up", 8),
        *walk("left", 8, 0), (1.2, "front", "rest_down", 0),
    ]
    house = block([
        "      ___",
        "    /     \\",
        "  /_________\\",
        "   |  _  _ |",
        "   | | ||_||",
        "   |_|_|___|",
    ], 2, 33, "fg")
    window = [["#"], [" "], ["#"], ["#"]]
    hearts = [[""], ["<3"], [" <3"], [""]]
    props = [("win", window, 6, 42, "gold", 0.8), ("heart", hearts, 2, 24, "fire", 1.0)]
    return strip("An ASCII fox walking up to a small house with a lit window and a heart floating above",
                 "~/projects/casa-esperanza", "guest@forest:~/projects$ cd casa-esperanza/", timeline, house, props)


def dream_sync_scene():
    timeline = [
        (4.0, "blink", "rest_down", 0), (0.4, "front", "rest_down", 0), (0.3, "blink", "rest_down", 0),
        (3.0, "blink", "rest_down", 0), (1.0, "right", "rest_up", 0), (0.2, "blink", "rest_up", 0),
        (0.8, "right", "rest_up", 0),
    ]
    console = block([
        " .---------.",
        " | [_____] |",
        " |---------|",
        " | [_____] |",
        " '---------'",
    ], 3, 34, "fg")
    sparks = [["", "z"], ["", "z", ""], [" Z", "z"], ["  z", " Z", "z"], ["", "", ""]]
    sync = [["<-"], [" <"], ["  "], ["->"], [" >"], ["  "]]
    screen = [["o  "], [" o "], ["  o"]]
    props = [("zzz", sparks, 2, 13, "cream", 0.9), ("sync", sync, 5, 29, "accent", 0.5),
             ("screen", screen, 4, 39, "gold", 0.5)]
    return strip("An ASCII fox asleep next to a handheld console that syncs while it dreams",
                 "~/projects/dream-sync", "guest@forest:~/projects$ cd dream-sync/", timeline, console, props)


def stack_scene():
    timeline = [
        (2.4, "front", "rest_up", 0), (0.15, "blink", "rest_up", 0), (1.2, "right", "rest_up", 0),
        *wag("right", 0, 2), (1.4, "front", "rest_down", 0), *walk("right", 0, 6),
        (1.4, "right", "rest_up", 6), *walk("left", 6, 0),
    ]
    den = block([
        "      .-----.",
        "    .'  ___  '.",
        "   /   /   \\   \\",
        "  /___/_____\\___\\",
    ], 4, 32, "dark")
    glow = [["$_"], ["$"]]
    props = [("glow", glow, 6, 39, "ok", 0.6)]
    return strip("An ASCII fox next to its den, with a prompt blinking inside", "~/stack", "guest@forest:~$ cd stack/",
                 timeline, den, props)


def contact_scene():
    timeline = [
        (2.8, "front", "rest_up", 0), *wag("front", 0, 2), (0.15, "blink", "rest_up", 0),
        (2.0, "right", "rest_down", 0), (2.4, "blink", "rest_down", 0), (2.4, "blink", "rest_down", 0),
    ]
    scenery = block(["    _.._", "  .' .-'`", " /  /", " |  |", " \\  '.___.;", "  '._  _.'"], 2, 34, "gold")
    stars = [[" *", "", "      ."], ["", "   .", "      *"], [" .", "", "      ."]]
    props = [("stars", stars, 2, 23, "fg", 0.9)]
    return strip("An ASCII fox settling down to sleep under the moon", "~/contact", "guest@forest:~$ cat contact.txt",
                 timeline, scenery, props)


def link_button(label, css, marker, marker_css):
    """A small framed button, drawn with characters and a blinking marker."""
    inner = f" {marker} {label}  "
    cols = len(inner) + 2
    x0 = 3.0
    width = cols * CHAR_W + 2 * x0
    height = 62
    marker_x = x0 + 2 * CHAR_W + CHAR_W  # Border, then one space, then the marker.
    keyframes = ["@keyframes pulse{50%{opacity:.25}}",
                 f".marker{{animation:pulse 1.6s step-end infinite}}"]
    body = (
        text("." + "-" * (cols - 2) + ".", 16, x0=x0, css=css)
        + text("|", 34, x0=x0, css=css)
        + f'<g class="marker">{text(marker, 34, x0=marker_x - CHAR_W, css=marker_css)}</g>'
        + text(label, 34, x0=x0 + 4 * CHAR_W, css="fg")
        + text("|", 34, x0=x0 + (cols - 1) * CHAR_W, css=css)
        + text("'" + "-" * (cols - 2) + "'", 52, x0=x0, css=css)
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height}" width="{width:.1f}" '
            f'height="{height}" role="img" aria-label="{escape(label)}">\n<style>{stylesheet(keyframes)}</style>\n'
            f'<rect width="{width:.1f}" height="{height}" fill="{COLORS["bg"]}"/>\n{body}\n</svg>\n')


BUTTONS = {
    "link-repository": lambda: link_button("view repository", "accent", ">", "accent"),
    "link-demo": lambda: link_button("live demo", "ok", "*", "ok"),
}

SCENES = {
    "scene-01-login": login_scene,
    "scene-02-about": about_scene,
    "scene-03-urbanpulse": urbanpulse_scene,
    "scene-04-firesentinel": firesentinel_scene,
    "scene-05-casa-esperanza": casa_scene,
    "scene-06-dream-sync": dream_sync_scene,
    "scene-07-stack": stack_scene,
    "scene-08-contact": contact_scene,
}


def main():
    failures = contrast_failures()
    if failures:
        raise SystemExit("Contrast check failed:\n" + "\n".join(failures))
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    for name, scene in {**SCENES, **BUTTONS}.items():
        svg = scene()
        (out_dir / f"{name}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg.encode()) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
