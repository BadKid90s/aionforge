from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich import print

from aionforge.core.images import FitMode, parse_ratio
from aionforge.core.prompt_check import validate_prompt_text
from aionforge.core.verify import verify_image
from aionforge.run.workspace import BUCKETS, STORE_DIRS, Product, Workspace, safe_name

app = typer.Typer(
    no_args_is_help=True,
    help="货坊 AionForge — 女装电商出图。Skill 写 prompt，forge generate 出一张图。",
)
workspace_app = typer.Typer(
    no_args_is_help=True,
    help="logo 工作区：创建 bg_white / main / sku / detail 四个交付目录。",
)
product_app = typer.Typer(
    no_args_is_help=True,
    help="商品工作区：facts / refs / prompts / manifest 收在 .forge 下。",
)
prompt_app = typer.Typer(
    no_args_is_help=True,
    help="Prompt 静态检查。",
)
app.add_typer(workspace_app, name="workspace")
app.add_typer(product_app, name="product")
app.add_typer(prompt_app, name="prompt")


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
    """货坊 AionForge — 女装电商出图。"""

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


@workspace_app.command("init")
def workspace_init(
    logo: str = typer.Option(
        ..., "--logo", "-l", help="图案 / logo 设计名，从图案主标题推断；作为 output 下第一层目录。"
    ),
    root: Path = typer.Option(Path("output"), "--root", help="成品根目录，默认 output。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """创建或复用 logo 工作区，并补齐四个交付目录。"""
    try:
        workspace = Workspace.create(root, logo)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")
    _print_ok(
        workspace.root,
        [],
        json_output,
        extra={
            "logo": workspace.logo,
            "workspace": str(workspace.root),
            "buckets": [str(workspace.bucket_dir(bucket)) for bucket in BUCKETS],
        },
    )
    if not json_output:
        print(f"  [green]logo[/green] {workspace.logo}")
        for bucket in BUCKETS:
            print(f"  [green]{bucket}[/green] {workspace.bucket_dir(bucket)}")


@product_app.command("init")
def product_init(
    logo: str = typer.Option(..., "--logo", "-l", help="图案 / logo 设计名。"),
    product: str = typer.Option(
        ..., "--product", "-p", help="衣服款式短名（short / long / tee / hoodie），进入文件名。"
    ),
    root: Path = typer.Option(Path("output"), "--root", help="成品根目录，默认 output。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """创建或复用商品工作区，生成 facts.json / manifest.json 模板。"""
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
    prompt: str | None = typer.Option(
        None, "--prompt", "-p", help="出图提示词。与 --prompt-file 二选一。"
    ),
    prompt_file: Path | None = typer.Option(
        None, "--prompt-file", exists=True, readable=True, help="从文件读取提示词。"
    ),
    refs: list[str] | None = typer.Option(None, "--ref", "-r", help=_REF_HELP),
    name: str = typer.Option("image", "--name", "-n", help=_NAME_HELP),
    bucket: str | None = typer.Option(
        None, "--bucket", "-b", help="成品落点：bg_white / main / sku / detail。"
    ),
    store: str | None = typer.Option(
        None, "--store", help="中间产物落点：refs（印花/白底素材）或 tmp。"
    ),
    ratio: str | None = typer.Option(None, "--ratio", help=_RATIO_HELP),
    fit: FitMode = typer.Option(FitMode.expand, "--fit", help=_FIT_HELP),
    background: str = typer.Option(
        "white",
        "--background",
        help="模型返回透明底时铺的底色，默认 white；详情图可用 #F7F5F2。",
    ),
    cutout: bool = typer.Option(
        False, "--cutout/--no-cutout", help="白底转透明并按图案裁切（印花提取用）。"
    ),
    padding: int = typer.Option(8, "--padding", help="--cutout 时的透明边距像素。"),
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
        help="--cutout 时把封闭白区（字母孔洞、镂空）也清成透明；白色字标不要开。",
    ),
    denoise: int = typer.Option(
        0, "--denoise", help="--cutout 时删除面积小于该像素数的 alpha 孤岛，0 关闭。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """通用出图：成品写 bucket，中间产物写 store；prompt/refs/manifest 写进商品工作区。"""
    from aionforge.adapters.factory import build_image_adapter
    from aionforge.core.config import load_settings
    from aionforge.core.log import configure_logging
    from aionforge.tools.generate import parse_ref, run_generate

    if bool(bucket) == bool(store):
        _fail(
            ValueError("--bucket 与 --store 必须二选一：成品用 bucket，中间产物用 store"),
            json_output,
            stage="params",
        )
    if bucket and bucket not in BUCKETS:
        _fail(
            ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}"),
            json_output,
            stage="params",
        )
    if store and store not in STORE_DIRS:
        _fail(
            ValueError(f"store 必须是 {', '.join(STORE_DIRS)}，收到：{store}"),
            json_output,
            stage="params",
        )
    if cutout and ratio:
        _fail(
            ValueError("--cutout 与 --ratio 不能同时使用：抠图按图案尺寸输出，不套画幅比例"),
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
        _fail(ValueError("必须提供 --prompt 或 --prompt-file"), json_output, stage="params")
    try:
        item = Product.open(product_dir)
        parsed_refs = [parse_ref(item) for item in (refs or [])]
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
                store=store,
                ratio=ratio,
                fit=fit,
                cutout=cutout,
                padding=padding,
                threshold=threshold,
                tolerance=tolerance,
                remove_enclosed_white=remove_enclosed_white,
                denoise=denoise,
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
            bucket=bucket or "",
            store=store or "",
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
            "bucket": bucket or "",
            "store": store or "",
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
    clean_white: bool = typer.Option(
        True,
        "--clean-white/--no-clean-white",
        help="原稿自带 alpha 时，仍清理与边界连通的白底 / 白边。",
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
        help="先用图片模型把图案清洗到纯白底，再本地抠图（适合 alpha 内残留白底的原稿）。",
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
                clean_white=clean_white,
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
                "clean_white": clean_white,
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


@app.command("extract-element")
def extract_element_command(
    source: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        readable=True,
        help="透明底印花（PNG / WebP）。",
    ),
    product_dir: Path = typer.Option(
        ...,
        "--product-dir",
        exists=True,
        file_okay=False,
        help="商品工作区目录，由 forge product init 生成。",
    ),
    name: str = typer.Option(
        "print", "--name", "-n", help="输出前缀：refs/<name>-element-01.png。"
    ),
    min_pixels: int = typer.Option(
        16, "--min-pixels", help="忽略面积小于该像素数的连通域。"
    ),
    padding: int = typer.Option(4, "--padding", help="每个元素的透明边距像素。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """把透明底印花拆成独立元素，并标记元素是否触到画布边缘。"""
    from PIL import Image

    from aionforge.core.elements import element_catalog, extract_alpha_elements

    try:
        item = Product.open(product_dir)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")
    try:
        with Image.open(source) as img:
            if "A" not in img.getbands():
                raise ValueError("元素提取需要透明底印花，先运行 forge cutout")
            image = img.convert("RGBA")
        elements = extract_alpha_elements(
            image, min_pixels=min_pixels, padding=padding
        )
        if not elements:
            raise ValueError("没有可提取的元素；检查 alpha 或调小 --min-pixels")
        paths: list[Path] = []
        for element in elements:
            dest = item.store_path("refs", f"{name}-element-{element.index:02d}")
            element.image.save(dest, format="PNG")
            paths.append(dest)
        catalog = item.refs / f"{safe_name(name)}-elements.json"
        catalog.write_text(
            json.dumps(
                element_catalog(source, elements, paths=paths),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        item.record_task(
            f"{name}-elements", "failed", store="refs", error=str(exc), refs=[source]
        )
        _fail(exc, json_output)
    incomplete = sum(element.touches_edge for element in elements)
    item.record_task(
        f"{name}-elements",
        "ok",
        store="refs",
        refs=[source],
        extra={
            "mode": "element-extract",
            "prefix": name,
            "elements": len(elements),
            "incomplete": incomplete,
            "catalog": str(catalog),
            "min_pixels": min_pixels,
            "padding": padding,
        },
    )
    _print_ok(
        item.root,
        paths,
        json_output,
        extra={
            "logo": item.workspace.logo,
            "product": item.name,
            "product_dir": str(item.root),
            "store": "refs",
            "elements": len(elements),
            "incomplete": incomplete,
            "catalog": str(catalog),
        },
    )


@app.command("composite")
def composite_command(
    garment: Path = typer.Option(
        ...,
        "--garment",
        "-g",
        exists=True,
        readable=True,
        help="成衣图（通常用 bg_white 成品）。",
    ),
    print_file: Path = typer.Option(
        ...,
        "--print",
        "--print-file",
        exists=True,
        readable=True,
        help="透明底印花 PNG / WebP。",
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
    bucket: str | None = typer.Option(
        None, "--bucket", "-b", help="成品落点：bg_white / main / sku / detail。"
    ),
    store: str | None = typer.Option(
        None, "--store", help="中间产物落点：refs 或 tmp。"
    ),
    x: float = typer.Option(0.5, "--x", help="印花中心横坐标，占画布宽度比例。"),
    y: float = typer.Option(0.38, "--y", help="印花中心纵坐标，占画布高度比例。"),
    width: float = typer.Option(0.35, "--width", help="印花宽度，占画布宽度比例。"),
    ink: str = typer.Option(
        "auto", "--ink", help="墨色策略：auto / multiply / normal / white。"
    ),
    shading: float = typer.Option(
        0.25, "--shading", help="布料明暗强度 0-1；multiply 模式不再叠加。"
    ),
    opacity: float = typer.Option(1.0, "--opacity", help="印花不透明度 0-1。"),
    underbase_expand: int = typer.Option(
        0,
        "--underbase-expand",
        help="white 模式下白墨底向外扩张像素；默认 0，调大会出现白边。",
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """本地合成：把印花贴到成衣图上，支持正片叠底与深色衣白墨适配。"""
    from aionforge.core.composite import composite_print

    if bool(bucket) == bool(store):
        _fail(
            ValueError("--bucket 与 --store 必须二选一：成品用 bucket，中间产物用 store"),
            json_output,
            stage="params",
        )
    if bucket and bucket not in BUCKETS:
        _fail(
            ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}"),
            json_output,
            stage="params",
        )
    if store and store not in STORE_DIRS:
        _fail(
            ValueError(f"store 必须是 {', '.join(STORE_DIRS)}，收到：{store}"),
            json_output,
            stage="params",
        )
    try:
        item = Product.open(product_dir)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")
    try:
        result = composite_print(
            garment,
            print_file,
            x=x,
            y=y,
            width=width,
            ink=ink,
            shading=shading,
            opacity=opacity,
            underbase_expand=underbase_expand,
        )
        dest = (
            item.target_path(bucket, name)
            if bucket
            else item.store_path(store or "", name)
        )
        result.image.save(dest, format="PNG")
    except Exception as exc:  # noqa: BLE001
        item.record_task(
            name,
            "failed",
            bucket=bucket or "",
            store=store or "",
            error=str(exc),
            refs=[garment, print_file],
        )
        _fail(exc, json_output)
    item.record_task(
        name,
        "ok",
        bucket=bucket or "",
        store=store or "",
        image=dest,
        refs=[garment, print_file],
        extra={
            "mode": "composite",
            "garment": str(garment),
            "print": str(print_file),
            "placement": {"x": x, "y": y, "width": width},
            "ink": result.ink,
            "shading": shading,
            "opacity": opacity,
            "underbase_expand": underbase_expand,
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
            "bucket": bucket or "",
            "store": store or "",
            "ink": result.ink,
        },
    )


@app.command("verify")
def verify_command(
    image: Path = typer.Option(
        ..., "--image", "-i", exists=True, readable=True, help="要校验的成品图。"
    ),
    ratio: str | None = typer.Option(None, "--ratio", help="期望比例，例如 1:1 / 3:4。"),
    white_bg: bool = typer.Option(False, "--white-bg", help="检查四边是否为纯白背景。"),
    alpha: bool = typer.Option(False, "--alpha", help="检查印花提取是否带透明通道。"),
    print_quality: bool = typer.Option(
        False,
        "--print",
        help="印花质量：透明通道、alpha 边界白边、孤立碎点。",
    ),
    min_side: int = typer.Option(480, "--min-side", help="宽高最小像素。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """成品图客观校验：文件、尺寸、比例、白底、透明通道、印花质量。"""
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
        alpha=alpha,
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
        None, "--facts", exists=True, readable=True, help="商品 facts.json，用于核对印花原文。"
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
            _fail(ValueError(f"facts.json 不是合法 JSON：{exc}"), json_output, stage="params")
    issues = validate_prompt_text(text, has_visible_text=visible_text, facts=facts_data)
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


@app.command("list")
def list_command(
    logo: str = typer.Option(..., "--logo", "-l", help="图案 / logo 设计名。"),
    root: Path = typer.Option(Path("output"), "--root", help="成品根目录，默认 output。"),
    bucket: str | None = typer.Option(
        None, "--bucket", "-b", help="只看某一个 bucket；不填则列出四个。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """列出某个 logo 下已经生成的成品。"""
    from aionforge.cli.envelope import envelope, print_json

    if bucket and bucket not in BUCKETS:
        _fail(
            ValueError(f"bucket 必须是 {', '.join(BUCKETS)}，收到：{bucket}"),
            json_output,
            stage="params",
        )
    try:
        workspace = Workspace.open(root, logo)
    except ValueError as exc:
        _fail(exc, json_output, stage="params")
    assets = workspace.list_assets()
    if bucket:
        assets = {bucket: assets.get(bucket, [])}
    if json_output:
        print_json(
            envelope(
                ok=True,
                run_dir=workspace.root,
                extra={"logo": workspace.logo, "buckets": assets},
            )
        )
        return
    print(f"  [green]logo[/green] {workspace.logo}  {workspace.root}")
    for name, files in assets.items():
        print(f"  [green]{name}[/green] {len(files)}")
        for item in files:
            print(f"    {item['name']}")


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
