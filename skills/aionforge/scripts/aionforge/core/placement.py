"""落点与亮度计算：composite 与 print adapt 共用的纯几何/色彩工具。

位置预设对照成人团体服 T 恤印花尺寸规范（以平铺成衣含袖画布、躯干占画布宽 ~0.50 / ~52cm 为基准）：
- left_chest: 左胸小标（8-12cm），穿着者左胸（正面图右侧），距左肩缝 5.5-8cm，距中线 4-6cm
- chest_center: 胸前居中大图（28-32cm），距领口下方 7-9cm（top 对齐）
- back_center: 全背印花（28-32cm × 35cm），距后领线下 2-5cm（top 对齐）
- back_neck: 上背小标（5-8cm），距后领缝正下方 3-5cm（top 对齐）
- hem_left / hem_right: 下摆衣角标（5-8cm），距下摆缝上 5cm（bottom 对齐）
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

_ANCHORS = {"center", "top", "bottom"}


@dataclass(frozen=True)
class PlacementPreset:
    region: str
    side: str
    x: float
    y: float
    width: float
    max_height: float
    anchor: str
    cm_spec: str
    reference_line: str


PLACEMENT_PRESETS: dict[str, PlacementPreset] = {
    "left_chest": PlacementPreset(
        region="left_chest",
        side="front",
        x=0.61,
        y=0.29,
        width=0.09,
        max_height=0.11,
        anchor="center",
        cm_spec="8-12cm × 8-12cm",
        reference_line="距左肩缝 5.5-8cm，距中线 4-6cm",
    ),
    "chest_center": PlacementPreset(
        region="chest_center",
        side="front",
        x=0.50,
        y=0.27,
        width=0.28,
        max_height=0.32,
        anchor="top",
        cm_spec="28-32cm × 28-32cm",
        reference_line="距领口下方 7-9cm",
    ),
    "back_center": PlacementPreset(
        region="back_center",
        side="back",
        x=0.50,
        y=0.19,
        width=0.30,
        max_height=0.40,
        anchor="top",
        cm_spec="28-32cm × 35cm",
        reference_line="距后领线下 2-5cm",
    ),
    "back_neck": PlacementPreset(
        region="back_neck",
        side="back",
        x=0.50,
        y=0.17,
        width=0.07,
        max_height=0.09,
        anchor="top",
        cm_spec="5-8cm × 5-8cm",
        reference_line="距后领缝正下方 3-5cm",
    ),
    "hem_left": PlacementPreset(
        region="hem_left",
        side="front",
        x=0.66,
        y=0.84,
        width=0.065,
        max_height=0.08,
        anchor="bottom",
        cm_spec="5-8cm × 5-8cm",
        reference_line="距下摆缝上 5cm（穿着者左侧）",
    ),
    "hem_right": PlacementPreset(
        region="hem_right",
        side="front",
        x=0.34,
        y=0.84,
        width=0.065,
        max_height=0.08,
        anchor="bottom",
        cm_spec="5-8cm × 5-8cm",
        reference_line="距下摆缝上 5cm（穿着者右侧）",
    ),
}


def get_preset(region: str) -> PlacementPreset:
    """获取标准位置预设；未知区域名时抛出 ValueError。"""
    preset = PLACEMENT_PRESETS.get(region)
    if preset is None:
        available = ", ".join(PLACEMENT_PRESETS)
        raise ValueError(f"--region 必须是 {available}，收到：{region}")
    return preset


def resolve_geometry(
    *,
    region: str | None = None,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    max_height: float | None = None,
    anchor: str | None = None,
    default_x: float = 0.5,
    default_y: float = 0.38,
    default_width: float = 0.35,
) -> tuple[float, float, float, float | None, str]:
    """合并标准预设与显式几何参数，返回 (x, y, width, max_height, anchor)。"""
    if region is not None:
        preset = get_preset(region)
        base_x = preset.x
        base_y = preset.y
        base_width = preset.width
        base_max_height: float | None = preset.max_height
        base_anchor = preset.anchor
    else:
        base_x = default_x
        base_y = default_y
        base_width = default_width
        base_max_height = None
        base_anchor = "center"

    resolved_x = base_x if x is None else x
    resolved_y = base_y if y is None else y
    resolved_width = base_width if width is None else width
    resolved_max_height = base_max_height if max_height is None else max_height
    resolved_anchor = base_anchor if anchor is None else anchor

    for name, value in (
        ("x", resolved_x),
        ("y", resolved_y),
        ("width", resolved_width),
    ):
        if not 0 < value <= 1:
            raise ValueError(f"--{name} 必须在 (0, 1] 之间，收到：{value}")
    if resolved_max_height is not None and not 0 < resolved_max_height <= 1:
        raise ValueError(
            f"--max-height 必须在 (0, 1] 之间，收到：{resolved_max_height}"
        )
    if resolved_anchor not in _ANCHORS:
        raise ValueError(
            f"--anchor 必须是 {', '.join(sorted(_ANCHORS))}，收到：{resolved_anchor}"
        )
    return (
        resolved_x,
        resolved_y,
        resolved_width,
        resolved_max_height,
        resolved_anchor,
    )


def placement_box(
    canvas_size: tuple[int, int],
    subject_size: tuple[int, int],
    *,
    x: float = 0.5,
    y: float = 0.38,
    width: float = 0.35,
    max_height: float | None = None,
    anchor: str = "center",
) -> tuple[int, int, int, int]:
    """把 0-1 的画布比例换算成 (left, top, width, height) 像素框。"""
    if anchor not in _ANCHORS:
        raise ValueError(
            f"anchor 必须是 {', '.join(sorted(_ANCHORS))}，收到：{anchor}"
        )
    canvas_width, canvas_height = canvas_size
    subject_width, subject_height = subject_size
    target_width = max(1, round(canvas_width * width))
    target_height = max(
        1, round(target_width * subject_height / max(1, subject_width))
    )
    if max_height is not None:
        max_height_px = max(1, round(canvas_height * max_height))
        if target_height > max_height_px:
            target_height = max_height_px
            target_width = max(
                1, round(target_height * subject_width / max(1, subject_height))
            )
    left = round(canvas_width * x - target_width / 2)
    if anchor == "top":
        top = round(canvas_height * y)
    elif anchor == "bottom":
        top = round(canvas_height * y - target_height)
    else:
        top = round(canvas_height * y - target_height / 2)
    return left, top, target_width, target_height


def validate_box(box: tuple[int, int, int, int], canvas_size: tuple[int, int]) -> None:
    """确认落点完全在画布内；超出时抛 ValueError。"""
    left, top, width, height = box
    canvas_width, canvas_height = canvas_size
    if (
        left < 0
        or top < 0
        or left + width > canvas_width
        or top + height > canvas_height
    ):
        raise ValueError("印花超出画布：调小 --width 或调整 --x / --y")


def mean_luminance(image: Image.Image) -> float:
    """返回 0-255 的平均亮度。"""
    gray = image.convert("L")
    histogram = gray.histogram()
    total = sum(histogram)
    if not total:
        return 0.0
    return sum(value * count for value, count in enumerate(histogram)) / total
