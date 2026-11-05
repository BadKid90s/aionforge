from pathlib import Path

from aionforge.run.job import Job


def test_create_writes_project_plan_manifest(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="pdp", slug="dress")
    assert job.project_path.is_file()
    assert job.plan_path.is_file()
    assert job.manifest_path.is_file()
    assert job.images.is_dir()
    assert job.prompts.is_dir()
    assert "dress" in job.root.name


def test_record_task_replaces_same_name(tmp_path: Path) -> None:
    job = Job.create(tmp_path, workflow="pdp", slug="x")
    prompt = job.write_prompt("main-01", "hello")
    image = job.image_path("main-01")
    image.write_bytes(b"png")
    job.record_task("main-01", "ok", image=image, prompt=prompt)
    job.record_task("main-01", "failed", error="boom")
    import json

    tasks = json.loads(job.manifest_path.read_text())["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["status"] == "failed"
    assert tasks[0]["error"] == "boom"


def test_open_existing_dir(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    job = Job.open(root)
    assert job.project_path.is_file()
    assert json_workflow(job) == "ad-hoc"


def json_workflow(job: Job) -> str:
    import json

    return json.loads(job.project_path.read_text())["workflow"]
