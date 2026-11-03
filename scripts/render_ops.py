"""Replay recorded drawing ops into PNG and PDF.

Both poster scripts record their layout as a list of ops and then call this, so
the print PDF, the on-screen PNG and the SVG all come from one description and
cannot drift.

Why matplotlib rather than an SVG rasteriser: the sandbox has no libcairo, no
rsvg and no headless browser, so `cairosvg`, `rsvg-convert` and `convert` all
fail. matplotlib is pure Python with bundled fonts and emits both raster and
true vector PDF from the same figures. The PDF is the good one; the PNG is for
looking at on screen.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                        # noqa: E402
from matplotlib.lines import Line2D                    # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch   # noqa: E402

# points per op-unit. The op coordinate system is ~381 units per 100 mm, and a
# PDF point is 1/72 inch, so 1 unit = 0.2646 pt would be exact. We scale the
# figure instead and let matplotlib handle the mapping.
UNITS_PER_INCH = 381.0 / 3.937                         # 96.8


def _fig(W: int, H: int):
    fig = plt.figure(figsize=(W / UNITS_PER_INCH, H / UNITS_PER_INCH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    ax.set_facecolor("white")
    return fig, ax


def _draw(ax, ops, W, H):
    ax.add_patch(plt.Rectangle((0, 0), W, H, facecolor="white", edgecolor="none"))
    # three passes: rects, then lines, then polylines and dots, then text -- so
    # text is never painted underneath a later box and a data curve is never
    # hidden by its own gridlines
    for o in ops:
        if o["op"] == "poly":
            xs = [p[0] for p in o["pts"]]
            ys = [p[1] for p in o["pts"]]
            ax.plot(xs, ys, color=o["color"], linewidth=o["sw"] * 0.62,
                    solid_capstyle="round", solid_joinstyle="round", zorder=4)
        elif o["op"] == "dot":
            ax.add_patch(plt.Circle((o["x"], o["y"]), o["r"],
                                    facecolor=o["color"], edgecolor="none", zorder=6))
        if o["op"] == "rect":
            kw = {"linestyle": (0, (5, 3))} if o["dash"] else {}
            ax.add_patch(FancyBboxPatch(
                (o["x"], o["y"]), o["w"], o["h"],
                boxstyle="round,pad=0,rounding_size=6",
                facecolor=o["fill"], edgecolor=o["stroke"],
                linewidth=o["sw"] * 0.62, **kw))
        elif o["op"] == "line":
            if o.get("head"):
                ax.add_patch(FancyArrowPatch(
                    (o["x1"], o["y1"]), (o["x2"], o["y2"]),
                    arrowstyle="-|>", mutation_scale=11,
                    color=o["color"], linewidth=o["sw"] * 0.62,
                    shrinkA=0, shrinkB=0,
                    linestyle=(0, (5, 3)) if o["dash"] else "solid"))
            else:
                ln = Line2D([o["x1"], o["x2"]], [o["y1"], o["y2"]],
                            color=o["color"], linewidth=o["sw"] * 0.62,
                            solid_capstyle="butt")
                if o["dash"]:
                    ln.set_linestyle((0, (5, 3)))
                ax.add_line(ln)
    for o in ops:
        if o["op"] != "text":
            continue
        ax.text(o["x"], o["y"], o["s"], fontsize=o["size"] * 0.70,
                color=o["fill"],
                ha={"start": "left", "middle": "center", "end": "right"}[o["anchor"]],
                va="baseline",
                fontweight="bold" if o["weight"] in ("700", "600") else "normal",
                fontstyle="italic" if o.get("italic") else "normal",
                family="DejaVu Sans", zorder=5)


def render(ops, W: int, H: int, png: str, pdf: str | None = None,
           dpi: int = 200) -> None:
    fig, ax = _fig(W, H)
    _draw(ax, ops, W, H)
    fig.savefig(png, dpi=dpi, facecolor="white", pil_kwargs={"optimize": True})
    plt.close(fig)
    size_kb = __import__("os").path.getsize(png) / 1024
    print(f"wrote {png}  ({dpi} dpi, {size_kb:.0f} kB)")
    if pdf:
        fig, ax = _fig(W, H)
        _draw(ax, ops, W, H)
        fig.savefig(pdf, facecolor="white")
        plt.close(fig)
        print(f"wrote {pdf}  (vector)")
