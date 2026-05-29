"""SVG rasterization helpers. Full implementation added in a later task."""


def is_svg(path: str) -> bool:
    return path.lower().endswith(".svg")


def rasterize_svg_to_png(svg_path: str, out_dir: str, target_px: int = 512) -> str:
    raise NotImplementedError  # implemented in a later task
