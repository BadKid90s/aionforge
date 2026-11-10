import json
from pathlib import Path

from aionforge.run.workspace import BUCKETS, Product, Workspace, safe_name, safe_slug


def test_safe_slug_keeps_chinese_and_rejects_paths() -> None:
    assert safe_slug("Logo 10/黑色") == "Logo-10-黑色"
    assert safe_name("dress-black.png") == "dress-black"
    assert safe_name("../dress black") == "dress-black"
    assert safe_slug("", "logo") == "logo"


def test_create_workspace_and_product(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, "品牌 A")
    assert workspace.root == (tmp_path / "品牌-A").resolve()
    assert workspace.workspace_path.is_file()
    for bucket in BUCKETS:
        assert workspace.bucket_dir(bucket).is_dir()

    product = Product.create(workspace, "dress")
    assert product.root.is_dir()
    assert product.project_path.is_file()
    assert product.facts_path.is_file()
    assert product.manifest_path.is_file()
    assert product.refs.is_dir()
    assert product.prompts.is_dir()
    facts = json.loads(product.facts_path.read_text(encoding="utf-8"))
    assert facts["logo"] == "品牌-A"
    assert facts["product"] == "dress"
    assert facts["print"]["has_print"] is False


def test_product_create_is_idempotent_and_keeps_facts(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, "brand")
    product = Product.create(workspace, "dress")
    product.facts_path.write_text('{"custom": true}', encoding="utf-8")
    again = Product.create(workspace, "dress")
    assert again.facts_path.read_text(encoding="utf-8") == '{"custom": true}'


def test_open_product_reads_project(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, "brand")
    product = Product.create(workspace, "dress")
    opened = Product.open(product.root)
    assert opened.name == "dress"
    assert opened.workspace.root == workspace.root
    assert opened.facts_path == product.facts_path


def test_target_path_archives_existing_image(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, "brand")
    product = Product.create(workspace, "dress")
    target = product.target_path("bg_white", "dress-black")
    target.write_bytes(b"old")
    again = product.target_path("bg_white", "dress-black")
    assert again == target
    archives = list(product.history.iterdir())
    assert len(archives) == 1
    assert archives[0].read_bytes() == b"old"


def test_store_path_only_allows_refs_and_tmp(tmp_path: Path) -> None:
    product = Product.create(Workspace.create(tmp_path, "brand"), "dress")
    assert product.store_path("refs", "print").parent == product.refs
    assert product.store_path("tmp", "white").parent == product.tmp


def test_list_assets(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, "brand")
    product = Product.create(workspace, "dress")
    product.target_path("main", "dress-black-hero").write_bytes(b"png")
    assets = workspace.list_assets()
    assert [item["name"] for item in assets["main"]] == ["dress-black-hero.png"]
    assert assets["bg_white"] == []


def test_manifest_keeps_same_name_in_different_buckets(tmp_path: Path) -> None:
    product = Product.create(Workspace.create(tmp_path, "brand"), "dress")
    product.record_task("dress-black", "ok", bucket="bg_white")
    product.record_task("dress-black", "ok", bucket="sku")
    tasks = json.loads(product.manifest_path.read_text(encoding="utf-8"))["tasks"]
    assert {(task["bucket"], task["name"]) for task in tasks} == {
        ("bg_white", "dress-black"),
        ("sku", "dress-black"),
    }
