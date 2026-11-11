from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich import print

from aionforge.core.images import FitMode, parse_ratio
from aionforge.core.prompt_check import validate_prompt_text
from aionforge.core.verify import verify_image
from aionforge.run.workspace import BUCKETS, Product, Workspace, safe_name

app = typer.Typer(
    no_args_is_help=True,
    help="货坊 AionForge — 印花 T 恤电商出图。Skill 负责流程编排，forge 负责确定性执行。",
)
product_app = typer.Typer(
    no_args_is_help=True,
    help="商品工作区：创建交付目录与 .forge 下的 facts / refs / prompts / manifest。",
)
prompt_app = typer.Typer(
    no_args_is_help=True,
    help="Prompt 静态检查。",
)
print_app = typer.Typer(
    no_args_is_help=True,
    help="印花体检与配色适配：metrics 只读指标，adapt 输出适配后的透明印花。",
)
app.add_typer(product_app, name="product")
app.add_typer(prompt_app, name="prompt")
app.add_typer(print_app, name="print")


def _version_callback(value: bool) -> None:
    if not value:
        return
    from importlib.metadata import PackageNotFoundError, version

    try:
        number = version("aionforge")
    except PackageNotFoundError:
        number = "0.0.0"
    print(f"aionforge {number}")
    raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="显示版本号。",
    ),
) -> None:
    """货坊 AionForge — 印花 T 恤电商出图。"""


_RATIO_HELP = "输出图片比例，格式 W:H，输出宽高均大于 480px。"
_FIT_HELP = "比例不符时：expand 扩图铺满（默认，禁止留白），crop 居中裁切。"
_JSON_HELP = "以 JSON 信封输出（ok / run_dir / images / error）。"
_NAME_HELP = "结果图文件名（不含扩展名），写入 <logo>/<bucket>/<name>.png。"
_REF_HELP = "参考图。可重复。角色写法 garment=./a.png、model=./b.jpg、pose=./pose.jpg。"


def _fail(exc: Exception, json_output: bool, stage: str = "execution") -> None:
    from aionforge.cli.envelope import envelope, error_payload, print_json
    from aionforge.core.log import get_logger

    get_logger("cli").exception("%s", exc)
    if json_output:
        print_json(
            envelope(
                ok=False,
                error=error_payload(
                    stage,
                    str(exc),
                    "核对 --product-dir / --bucket / 输入路径，或运行 forge doctor",
                ),
            )
        )
    else:
        print(f"[red]失败[/red] {exc}")
    raise typer.Exit(code=1) from exc


def _print_ok(
    root: Path,
    images: list[Path],
    json_output: bool,
    extra: dict | None = None,
) -> None:
    from aionforge.cli.envelope import envelope, print_json

    if json_output:
        print_json(envelope(ok=True, run_dir=root, images=images, extra=extra))
        return
    print(f"  [green]工作目录[/green] {root}")
    for path in images:
        print(f"  [green]图片[/green] {path}")


def _read_prompt(prompt: str | None, prompt_file: Path | None) -> str:
    if prompt_file is not None:
        return prompt_file.read_text(encoding="utf-8").strip()
    return (prompt or "").strip()


@product_app.command("init")
def product_init(
    logo: str = typer.Option(..., "--logo", "-l", help="图案 / logo 设计名。"),
    product: str = typer.Option(
        ...,
        "--product",
        "-p",
        help="衣服款式短名（short / long / tee / hoodie），进入文件名。",
    ),
    root: Path = typer.Option(Path("output"), "--root", help="成品根目录，默认 output。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """创建或复用 logo 与商品工作区，生成 facts.json / manifest.json 模板。"""
    try:
        workspace = Workspace.create(root, logo)
        item = Product.create(workspace, product)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")
    _print_ok(
        item.root,
        [],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "workspace": str(item.workspace.root),
            "product_dir": str(item.root),
            "facts": str(item.facts_path),
            "manifest": str(item.manifest_path),
            "buckets": [str(item.bucket_dir(bucket)) for bucket in BUCKETS],
        },
    )
    if not json_output:
        print(f"  [green]商品[/green] {item.name}")
        print(f"  [green]facts[/green] {item.facts_path}")
        print(f"  [green]manifest[/green] {item.manifest_path}")


@app.command("generate")
def generate_command(
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录，由 forge product init 生成。",
    ),
    bucket: str = typer.Option(
        ..., "--bucket", "-b", help="成品落点：bg_white / main / detail。"
    ),
    prompt: str | None = typer.Option(
        None, "--prompt", "-p", help="出图提示词。与 --prompt-file 二选一。"
    ),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", exists=True, readable=True, help="从文件读取提示词。"
    ),
    refs: list[str] | None = typer.Option(None, "--ref", "-r", help=_REF_HELP),
    name: str = typer.Option("image", "--name", "-n", help=_NAME_HELP),
    ratio: str | None = typer.Option(None, "--ratio", help=_RATIO_HELP),
    fit: FitMode = typer.Option(FitMode.expand, "--fit", help=_FIT_HELP),
    background: str = typer.Option(
        "white",
        "--background",
        help="模型返回透明底时铺的底色，默认 white；详情图可用 #F7F5F2。",
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """调用图片模型生成单张成品图，写入指定 bucket；prompt 与参考图收进商品工作区。"""
    from aionforge.adapters.factory import build_image_adapter
    from aionforge.core.config import load_settings
    from aionforge.core.log import configure_logging
    from aionforge.tools.generate import parse_ref, run_generate

    if bucket not in BUCKETS:
        _fail(
            ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}"),
            json_output,
            stage="params",
        )
    if ratio:
        try:
            parse_ratio(ratio)
        except ValueError as exc:
            _fail(exc, json_output, stage="params")
    text = _read_prompt(prompt, prompt_file)
    if not text:
        _fail(
            ValueError("必须提供 --prompt 或 --prompt-file"),
            json_output,
            stage="params",
        )
    try:
        item = Product.open(product_dir)
        parsed_refs = [parse_ref(ref) for ref in (refs or [])]
    except ValueError as exc:
        _fail(exc, json_output, stage="params")

    settings = load_settings()
    configure_logging(settings, console=False)

    async def run():
        image = build_image_adapter(settings.image)
        try:
            return await run_generate(
                text,
                parsed_refs,
                item,
                image,
                name=name,
                bucket=bucket,
                ratio=ratio,
                fit=fit,
                background=background,
            )
        finally:
            await image.aclose()

    try:
        saved = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        item.record_task(
            name,
            "failed",
            bucket=bucket,
            error=str(exc),
            refs=[ref.path for ref in parsed_refs],
        )
        _fail(exc, json_output)
    _print_ok(
        item.root,
        [saved],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "bucket": bucket,
        },
    )


@app.command("cutout")
def cutout_command(
    source: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="平面 logo 图案稿（JPG / PNG / WebP）。",
    ),
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录，由 forge product init 生成。",
    ),
    name: str = typer.Option(
        "print", "--name", "-n", help="输出文件名，写入 refs/<name>.png。"
    ),
    padding: int = typer.Option(8, "--padding", help="透明边距像素。"),
    threshold: int = typer.Option(
        238,
        "--threshold",
        help="亮度阈值：背景估计失败时，亮度 >= 该值的像素视为背景（0-255）。",
    ),
    tolerance: int = typer.Option(
        18,
        "--tolerance",
        help="背景色容差：与边缘采样背景色的最大通道差（0-255）。",
    ),
    remove_enclosed_white: bool = typer.Option(
        False,
        "--remove-enclosed-white/--keep-enclosed-white",
        help="把封闭白区（字母孔洞、镂空）也清成透明；白色字标不要开。",
    ),
    denoise: int = typer.Option(
        0, "--denoise", help="删除面积小于该像素数的 alpha 孤岛，0 关闭。"
    ),
    ai: bool = typer.Option(
        False,
        "--ai",
        help="先用图片模型把图案清洗到纯白底，再本地抠图（适合残留复杂白边的原稿）。",
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """提取平面图案：默认本地抠图；--ai 时先让图片模型清洗白底。"""
    from aionforge.core.images import prepare_logo

    try:
        item = Product.open(product_dir)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")

    if ai:
        from aionforge.adapters.factory import build_image_adapter
        from aionforge.core.config import load_settings
        from aionforge.core.log import configure_logging
        from aionforge.tools.extract import run_logo_extract

        settings = load_settings()
        configure_logging(settings, console=False)

        async def run():
            image = build_image_adapter(settings.image)
            try:
                return await run_logo_extract(
                    source,
                    item,
                    image,
                    name=name,
                    padding=padding,
                    threshold=threshold,
                    tolerance=tolerance,
                    remove_enclosed_white=remove_enclosed_white,
                    denoise=denoise,
                )
            finally:
                await image.aclose()

        try:
            dest = asyncio.run(run())
        except Exception as exc:  # noqa: BLE001
            item.record_task(
                name, "failed", store="refs", error=str(exc), refs=[source]
            )
            _fail(exc, json_output)
    else:
        try:
            staged = item.tmp / f"{safe_name(name)}-cutout.png"
            prepare_logo(
                source,
                staged,
                padding=padding,
                threshold=threshold,
                tolerance=tolerance,
                remove_enclosed_white=remove_enclosed_white,
                denoise=denoise,
            )
            dest = item.store_path("refs", name)
            dest.write_bytes(staged.read_bytes())
        except Exception as exc:  # noqa: BLE001
            item.record_task(
                name, "failed", store="refs", error=str(exc), refs=[source]
            )
            _fail(exc, json_output)
        item.record_task(
            name,
            "ok",
            store="refs",
            image=dest,
            refs=[source],
            extra={
                "mode": "local-cutout",
                "source": str(source),
                "threshold": threshold,
                "tolerance": tolerance,
                "remove_enclosed_white": remove_enclosed_white,
                "denoise": denoise,
            },
        )
    _print_ok(
        item.root,
        [dest],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "store": "refs",
            "mode": "ai-cutout" if ai else "local-cutout",
        },
    )


@app.command("extract-core-element")
def extract_core_element_command(
    source: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="原始印花稿：白底 PNG / JPG 或透明 PNG / WebP 均可。",
    ),
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录，由 forge product init 生成。",
    ),
    name: str = typer.Option(
        "core-element",
        "--name",
        "-n",
        help="输出名：refs/<name>.png，同时写 prompt 与 manifest。",
    ),
    element_hint: str = typer.Option(
        "",
        "--element-hint",
        help="要提取的核心元素描述，例如「黄色笑脸骷髅头」；留空由模型自行挑选。",
    ),
    padding: int = typer.Option(12, "--padding", help="透明边距像素。"),
    denoise: int = typer.Option(
        4, "--denoise", help="删除面积小于该像素数的 alpha 孤岛，0 关闭。"
    ),
    threshold: int = typer.Option(
        238, "--threshold", help="本地抠白底的亮度阈值。"
    ),
    tolerance: int = typer.Option(
        18, "--tolerance", help="本地抠白底的通道容差。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """用图片模型提取一枚完整、独立、可缩小的核心元素（如左胸心口小标）。"""
    from aionforge.adapters.factory import build_image_adapter
    from aionforge.core.config import load_settings
    from aionforge.core.log import configure_logging
    from aionforge.tools.element_ai import run_element_extract

    try:
        item = Product.open(product_dir)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")

    settings = load_settings()
    configure_logging(settings, console=False)

    async def run():
        adapter = build_image_adapter(settings.image)
        try:
            return await run_element_extract(
                source,
                item,
                adapter,
                name=name,
                element_hint=element_hint,
                padding=padding,
                denoise=denoise,
                threshold=threshold,
                tolerance=tolerance,
            )
        finally:
            await adapter.aclose()

    try:
        dest, meta = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        item.record_task(
            name, "failed", store="refs", error=str(exc), refs=[source]
        )
        _fail(exc, json_output)
    _print_ok(
        item.root,
        [dest],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "store": "refs",
            "command": "extract-core-element",
            **meta,
        },
    )


@print_app.command("metrics")
def print_metrics_command(
    inputs: list[Path] = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="原稿或透明印花；可重复传入多张。",
    ),
    max_colors: int = typer.Option(
        8, "--max-colors", help="调色板最多取几种主色。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """给印花做客观体检：比例、色数、细节密度、笔画宽度；不写文件。"""
    from aionforge.core.print import measure_print

    try:
        results = [
            measure_print(path, max_colors=max_colors).to_dict() for path in inputs
        ]
    except Exception as exc:  # noqa: BLE001
        _fail(exc, json_output)
    if json_output:
        from aionforge.cli.envelope import envelope, print_json

        print_json(envelope(ok=True, images=[], extra={"prints": results}))
        return
    for item in results:
        palette = ", ".join(
            f"{entry['hex']}({entry['share']:.0%})" for entry in item["palette"][:4]
        )
        print(
            f"  [green]{item['source']}[/green] "
            f"{item['size'][0]}x{item['size'][1]} "
            f"aspect={item['aspect']:.2f} "
            f"colors={len(item['palette'])} "
            f"edge={item['edge_density']:.3f} "
            f"stroke={item['mean_stroke_ratio']:.3f} "
            f"holes={item['transparent_holes']} "
            f"edge_touch={item['touches_edge']} "
            f"palette=[{palette}]"
        )


@print_app.command("adapt")
def print_adapt_command(
    print_file: Path = typer.Option(
        ...,
        "--print",
        "--print-file",
        exists=True,
        readable=True,
        help="透明印花 PNG。",
    ),
    garment: Path = typer.Option(
        ...,
        "--garment",
        "-g",
        exists=True,
        readable=True,
        help="该颜色的成衣图。",
    ),
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录。",
    ),
    name: str = typer.Option(
        "print-fit", "--name", "-n", help="输出 refs/<name>.png。"
    ),
    strategy: str = typer.Option(
        "auto",
        "--strategy",
        help="auto / multiply / normal / white / lighten / darken / palette / outline。",
    ),
    palette: str | None = typer.Option(
        None, "--palette", help="palette 策略的目标色，逗号分隔 Hex。"
    ),
    x: float = typer.Option(0.5, "--x", help="采样区域中心 x，0-1。"),
    y: float = typer.Option(0.38, "--y", help="采样区域中心 y，0-1。"),
    width: float = typer.Option(0.35, "--width", help="采样区域宽度占画布比例。"),
    outline_px: int = typer.Option(4, "--outline-px", help="outline 策略的描边像素。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """按成衣底色重映射印花颜色；保持 alpha、几何和文字形状不变。"""
    from aionforge.core.print import adapt_print, parse_palette

    item = None
    try:
        item = Product.open(product_dir)
        report = adapt_print(
            print_file,
            garment,
            strategy=strategy,
            palette=parse_palette(palette),
            x=x,
            y=y,
            width=width,
            outline_px=outline_px,
        )
        dest = item.store_path("refs", name)
        report.image.save(dest, format="PNG")
        item.record_task(
            name,
            "ok",
            store="refs",
            image=dest,
            refs=[print_file, garment],
            extra={
                "mode": "print-adapt",
                "strategy": report.strategy,
                "contrast_before": report.contrast_before,
                "contrast_after": report.contrast_after,
                "map": report.color_map,
                "warnings": report.warnings,
            },
        )
    except Exception as exc:  # noqa: BLE001
        if item is not None:
            item.record_task(
                name,
                "failed",
                store="refs",
                error=str(exc),
                refs=[print_file, garment],
            )
        _fail(exc, json_output)
    _print_ok(
        item.root,
        [dest],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "store": "refs",
            **report.to_dict(),
        },
    )
    if not json_output:
        print(
            f"  [green]strategy[/green] {report.strategy}  "
            f"[green]contrast[/green] {report.contrast_before:.2f} -> "
            f"{report.contrast_after:.2f}"
        )
        for warning in report.warnings:
            print(f"  [yellow]warning[/yellow] {warning}")


@app.command("composite")
def composite_command(
    garment: Path = typer.Option(
        ...,
        "--garment",
        "-g",
        exists=True,
        readable=True,
        help="成衣实拍图。",
    ),
    print_file: Path | None = typer.Option(
        None,
        "--print",
        "--print-file",
        exists=True,
        readable=True,
        help="透明底印花 PNG / WebP。与 --placement 至少给一个。",
    ),
    placement: str | None = typer.Option(
        None,
        "--placement",
        help="从 facts.print.placements 读取 source / x / y / width / ink。",
    ),
    color: str | None = typer.Option(
        None,
        "--color",
        "-c",
        help="成衣颜色名；配合 --placement 自动读取该色专属的撞色适配印花与墨色。",
    ),
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录，由 forge product init 生成。",
    ),
    name: str = typer.Option(
        "print-composite", "--name", "-n", help="结果图文件名（不含扩展名）。"
    ),
    bucket: str = typer.Option(
        "bg_white", "--bucket", "-b", help="成品落点，默认 bg_white。"
    ),
    x: float | None = typer.Option(
        None, "--x", help="印花中心横坐标，占画布宽度比例；默认 0.5。"
    ),
    y: float | None = typer.Option(
        None, "--y", help="印花中心纵坐标，占画布高度比例；默认 0.38。"
    ),
    width: float | None = typer.Option(
        None, "--width", help="印花宽度，占画布宽度比例；默认 0.35。"
    ),
    ink: str | None = typer.Option(
        None, "--ink", help="墨色策略：auto / multiply / normal / white；默认 auto。"
    ),
    shading: float = typer.Option(
        0.25, "--shading", help="布料明暗强度 0-1；multiply 模式不再叠加。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """本地合成：把印花贴到成衣实拍图上，支持正片叠底与深色衣白墨适配。"""
    from aionforge.core.composite import composite_print

    if bucket not in BUCKETS:
        _fail(
            ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}"),
            json_output,
            stage="params",
        )
    if print_file is None and not placement:
        _fail(
            ValueError("必须提供 --print 或 --placement"),
            json_output,
            stage="params",
        )
    try:
        item = Product.open(product_dir)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")

    resolved_print: Path | None = print_file
    resolved_x = 0.5
    resolved_y = 0.38
    resolved_width = 0.35
    resolved_ink = "auto"
    placement_id = ""

    if placement:
        facts_data = item.facts()
        placements = facts_data.get("print", {}).get("placements") or []
        if not isinstance(placements, list) or not placements:
            _fail(
                ValueError(
                    "facts 里没有 print.placements；先走 aionforge-print 写入印花计划"
                ),
                json_output,
                stage="params",
            )
        selected = next(
            (entry for entry in placements if entry.get("id") == placement), None
        )
        if selected is None:
            available = ", ".join(str(entry.get("id")) for entry in placements)
            _fail(
                ValueError(f"找不到 placement：{placement}；可用：{available}"),
                json_output,
                stage="params",
            )
        source = selected.get("source")
        selected_ink = str(selected.get("ink", "auto"))
        if color:
            adaptations = selected.get("adaptations") or {}
            if isinstance(adaptations, dict) and color in adaptations:
                color_adapt = adaptations[color] or {}
                source = color_adapt.get("source") or source
                selected_ink = str(color_adapt.get("ink") or selected_ink)
            else:
                colors_list = facts_data.get("colors") or []
                color_entry = next(
                    (c for c in colors_list if c.get("name") == color), None
                )
                if color_entry:
                    ca = color_entry.get("color_adaptation") or {}
                    side = selected.get("side", "front")
                    adapted_src = (
                        ca.get("adapted_source_back")
                        if side == "back" and ca.get("adapted_source_back")
                        else ca.get("adapted_source")
                    )
                    if adapted_src and selected.get("region") != "left_chest":
                        source = adapted_src
                    elif (
                        ca.get("badge_source")
                        and selected.get("region") == "left_chest"
                    ):
                        source = ca.get("badge_source")
                    if ca.get("ink"):
                        selected_ink = str(ca.get("ink"))
        if not source:
            _fail(
                ValueError(f"placement {placement} 缺少 source"),
                json_output,
                stage="params",
            )
        candidate = item.resolve(str(source))
        if not candidate.is_file():
            _fail(
                ValueError(f"placement 印花不存在：{candidate}"),
                json_output,
                stage="params",
            )
        resolved_print = candidate
        resolved_x = float(selected.get("x", 0.5))
        resolved_y = float(selected.get("y", 0.38))
        resolved_width = float(selected.get("width", 0.35))
        resolved_ink = selected_ink
        placement_id = placement

    if print_file is not None:
        resolved_print = print_file
    if x is not None:
        resolved_x = x
    if y is not None:
        resolved_y = y
    if width is not None:
        resolved_width = width
    if ink is not None:
        resolved_ink = ink
    if resolved_print is None:
        _fail(
            ValueError("必须提供 --print 或 --placement"),
            json_output,
            stage="params",
        )

    try:
        result = composite_print(
            garment,
            resolved_print,
            x=resolved_x,
            y=resolved_y,
            width=resolved_width,
            ink=resolved_ink,
            shading=shading,
        )
        dest = item.target_path(bucket, name)
        result.image.save(dest, format="PNG")
    except Exception as exc:  # noqa: BLE001
        item.record_task(
            name,
            "failed",
            bucket=bucket,
            error=str(exc),
            refs=[garment, resolved_print] if resolved_print else [garment],
        )
        _fail(exc, json_output)
    item.record_task(
        name,
        "ok",
        bucket=bucket,
        image=dest,
        refs=[garment, resolved_print],
        extra={
            "mode": "composite",
            "garment": str(garment),
            "print": str(resolved_print),
            "placement": {
                "x": resolved_x,
                "y": resolved_y,
                "width": resolved_width,
            },
            "placement_id": placement_id,
            "ink": result.ink,
            "shading": shading,
        },
    )
    _print_ok(
        item.root,
        [dest],
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "bucket": bucket,
            "ink": result.ink,
            "placement": placement_id,
        },
    )


@app.command("verify")
def verify_command(
    image: Path = typer.Option(
        ..., "--image", "-i", exists=True, readable=True, help="要校验的图片。"
    ),
    ratio: str | None = typer.Option(
        None, "--ratio", help="期望比例，例如 1:1 / 3:4。"
    ),
    white_bg: bool = typer.Option(
        False, "--white-bg", help="检查四边是否为纯白背景。"
    ),
    print_quality: bool = typer.Option(
        False,
        "--print",
        help="印花检查模式：校验透明通道、alpha 边界白边比例与孤立碎点。",
    ),
    min_side: int = typer.Option(480, "--min-side", help="宽高最小像素。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """图片客观校验：文件、尺寸、比例、白底、透明印花质量。"""
    from aionforge.cli.envelope import envelope, print_json

    if ratio:
        try:
            parse_ratio(ratio)
        except ValueError as exc:
            _fail(exc, json_output, stage="params")
    checks = verify_image(
        image,
        ratio=ratio,
        white_bg=white_bg,
        print_quality=print_quality,
        min_side=min_side,
    )
    ok = all(item["pass"] for item in checks)
    if json_output:
        print_json(envelope(ok=ok, images=[image], extra={"checks": checks}))
    else:
        for item in checks:
            mark = "[green][PASS][/green]" if item["pass"] else "[red][FAIL][/red]"
            detail = f"  {item['detail']}" if item["detail"] else ""
            print(f"{mark} {item['name']}{detail}")
            if not item["pass"] and item.get("suggestion"):
                print(f"       {item['suggestion']}")
    if not ok:
        raise typer.Exit(code=1)


@prompt_app.command("check")
def prompt_check(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True, help="要检查的 Prompt 文件。"
    ),
    facts: Path | None = typer.Option(
        None,
        "--facts",
        exists=True,
        readable=True,
        help="商品 facts.json，用于核对印花原文。",
    ),
    visible_text: bool = typer.Option(
        False, "--visible-text", help="本张图需要渲染画面内文字。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """检查参考图指代、Hex 色号、VISIBLE_TEXT_BLOCK 和印花原文。"""
    from aionforge.cli.envelope import envelope, print_json

    text = file.read_text(encoding="utf-8")
    facts_data = None
    if facts is not None:
        try:
            facts_data = json.loads(facts.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail(
                ValueError(f"facts.json 不是合法 JSON：{exc}"),
                json_output,
                stage="params",
            )
    issues = validate_prompt_text(
        text, has_visible_text=visible_text, facts=facts_data
    )
    ok = not issues
    if json_output:
        print_json(
            envelope(
                ok=ok,
                extra={"file": str(file), "issues": issues},
            )
        )
    else:
        if ok:
            print("[green][PASS][/green] prompt")
        for issue in issues:
            print(f"[red][FAIL][/red] {issue}")
    if not ok:
        raise typer.Exit(code=1)


@app.command("doctor")
def doctor(
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
    deep: bool = typer.Option(
        False,
        "--deep",
        help="真实 POST 一次 /images/edits，验证出图通道（会产生一次模型调用）。",
    ),
) -> None:
    """配置与连通性自检。任一检查失败时退出码为 1。"""
    from aionforge.cli.doctor import collect_checks
    from aionforge.cli.envelope import envelope, print_json
    from aionforge.core.config import ConfigError, load_settings

    try:
        settings = load_settings()
    except ConfigError as exc:
        if json_output:
            print_json(
                envelope(
                    ok=False,
                    extra={
                        "checks": [
                            {
                                "name": "config",
                                "pass": False,
                                "detail": str(exc),
                                "suggestion": str(exc),
                            }
                        ]
                    },
                )
            )
        else:
            print(f"[red][FAIL][/red] config  {exc}")
        raise typer.Exit(code=1) from exc

    checks = collect_checks(settings, deep=deep)
    ok = all(item["pass"] for item in checks)
    if json_output:
        print_json(envelope(ok=ok, extra={"checks": checks}))
    else:
        for item in checks:
            mark = "[green][PASS][/green]" if item["pass"] else "[red][FAIL][/red]"
            detail = f"  {item['detail']}" if item["detail"] else ""
            print(f"{mark} {item['name']}{detail}")
            if not item["pass"] and item.get("suggestion"):
                print(f"       {item['suggestion']}")
    if not ok:
        raise typer.Exit(code=1)
