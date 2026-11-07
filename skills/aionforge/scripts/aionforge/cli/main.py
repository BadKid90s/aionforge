from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print

from aionforge.core.images import FitMode, parse_ratio

app = typer.Typer(
    no_args_is_help=True,
    help="货坊 AionForge — 女装电商出图。Skill 写 prompt，forge generate 出一张图。",
)
job_app = typer.Typer(
    no_args_is_help=True,
    help="任务目录：创建 project.json / plan.json / manifest.json。",
)
app.add_typer(job_app, name="job")

_RATIO_HELP = "输出图片比例，格式 W:H，输出宽高均大于 480px。"
_FIT_HELP = "比例不符时：expand 扩图铺满（默认，禁止留白），crop 居中裁切。"
_JSON_HELP = "以 JSON 信封输出（ok / run_dir / images / error）。"
_JOB_DIR_HELP = "已有任务目录；不给则在 --output-dir 下新建。"
_NAME_HELP = "结果图文件名（不含扩展名），写入 images/<name>.png。"
_REF_HELP = "参考图。可重复。角色写法 garment=./a.png、model=./b.jpg。"


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
                    "运行 forge doctor 检查配置，或核对输入路径与 prompt",
                ),
            )
        )
    else:
        print(f"[red]失败[/red] {exc}")
    raise typer.Exit(code=1) from exc


def _resolve_job(job_dir: Path | None, output_dir: Path | None, command: str, slug: str):
    from aionforge.run.job import Job

    if job_dir is not None:
        return Job.open(job_dir)
    base = output_dir or Path.cwd() / "output" / command
    return Job.create(base, workflow=command, slug=slug)


def _print_ok(
    run_dir: Path,
    images: list[Path],
    json_output: bool,
    extra: dict | None = None,
) -> None:
    from aionforge.cli.envelope import envelope, print_json

    if json_output:
        print_json(envelope(ok=True, run_dir=run_dir, images=images, extra=extra))
        return
    print(f"  [green]运行目录[/green] {run_dir}")
    for path in images:
        print(f"  [green]图片[/green] {path}")


def _read_prompt(prompt: str | None, prompt_file: Path | None) -> str:
    if prompt_file is not None:
        return prompt_file.read_text(encoding="utf-8").strip()
    return (prompt or "").strip()


@job_app.command("init")
def job_init(
    workflow: str = typer.Option(
        "pdp",
        "--workflow",
        "-w",
        help="工作流 id：extract / compose / tryon / vary / sku / pdp / deconstruct。",
    ),
    slug: str = typer.Option("job", "--slug", "-s", help="任务短名，进入目录名。"),
    output_dir: Path | None = typer.Option(
        None, "--output-dir", help="任务根目录，默认 output/<workflow>。"
    ),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """创建空任务目录，供 Skill 写入 facts.json / plan.json 后再逐张出图。"""
    from aionforge.run.job import Job

    base = output_dir or Path.cwd() / "output" / workflow
    job = Job.create(base, workflow=workflow, slug=slug)
    extra = {"workflow": workflow, "project": str(job.project_path)}
    _print_ok(job.root, [], json_output, extra=extra)
    if not json_output:
        print(f"  [green]project[/green] {job.project_path}")
        print(f"  [green]plan[/green] {job.plan_path}")
        print(f"  [green]manifest[/green] {job.manifest_path}")


@app.command("generate")
def generate_command(
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
    cutout: bool = typer.Option(
        False, "--cutout/--no-cutout", help="白底转透明并按图案裁切（印花提取用）。"
    ),
    padding: int = typer.Option(8, "--padding", help="--cutout 时的透明边距像素。"),
    job_dir: Path | None = typer.Option(None, "--job-dir", help=_JOB_DIR_HELP),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="新建任务时的根目录。"),
    json_output: bool = typer.Option(False, "--json", help=_JSON_HELP),
) -> None:
    """通用出图：--prompt 或 --prompt-file，加可选参考图。换装/提取/合成都走这一条。"""
    from aionforge.adapters.factory import build_image_adapter
    from aionforge.core.config import load_settings
    from aionforge.core.log import configure_logging
    from aionforge.tools.generate import parse_ref, run_generate

    if ratio:
        parse_ratio(ratio)
    text = _read_prompt(prompt, prompt_file)
    if not text:
        raise typer.BadParameter("必须提供 --prompt 或 --prompt-file")

    settings = load_settings()
    configure_logging(settings, console=False)
    job = _resolve_job(job_dir, output_dir, "generate", name)
    try:
        parsed_refs = [parse_ref(item) for item in (refs or [])]
    except ValueError as exc:
        _fail(exc, json_output, stage="params")

    async def run():
        image = build_image_adapter(settings.image)
        try:
            return await run_generate(
                text,
                parsed_refs,
                job,
                image,
                name=name,
                ratio=ratio,
                fit=fit,
                cutout=cutout,
                padding=padding,
            )
        finally:
            await image.aclose()

    try:
        saved = asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        job.record_task(name, "failed", error=str(exc), refs=[item.path for item in parsed_refs])
        _fail(exc, json_output)
    _print_ok(job.root, [saved], json_output)


@app.command("doctor")
def doctor(json_output: bool = typer.Option(False, "--json", help=_JSON_HELP)) -> None:
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

    checks = collect_checks(settings)
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
