from __future__ import annotations

from pathlib import Path

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import LocalizedScriptBatch
from novel_drama_engine.renderer import render_localization_result, render_marketing_assets
from novel_drama_engine.rounds import MarketingAssetGenerator, ScriptLocalizer
from novel_drama_engine.storage import ProjectStore


def artifact_token(value: str) -> str:
    token = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in value
    ).strip("-")
    return token or "default"


def localization_artifact_prefix(locale: str, platform: str) -> str:
    return f"{artifact_token(locale)}_{artifact_token(platform)}"


def read_localization_artifact(
    store: ProjectStore,
    round_number: int,
    locale: str,
    platform: str,
) -> LocalizedScriptBatch | None:
    prefix = localization_artifact_prefix(locale, platform)
    path = store.project_dir / f"round_{round_number:03d}" / f"localization_{prefix}.json"
    if not path.exists():
        return None
    return LocalizedScriptBatch.model_validate_json(path.read_text(encoding="utf-8"))


def localize_project_round(
    *,
    store: ProjectStore,
    round_number: int,
    locale: str,
    platform: str,
    guidance: str,
    llm: JsonLLM,
) -> tuple[LocalizedScriptBatch, Path, Path]:
    round_result = store.read_round_result(round_number)
    localized = ScriptLocalizer(llm).run(
        round_result=round_result,
        locale=locale,
        platform=platform,
        guidance=guidance,
    )
    prefix = localization_artifact_prefix(locale, platform)
    json_path = store.write_round_artifact(
        round_number,
        f"localization_{prefix}",
        localized,
    )
    markdown_path = store.write_text_artifact(
        round_number,
        f"localized_scripts_{prefix}.md",
        render_localization_result(localized),
    )
    return localized, json_path, markdown_path


def generate_project_ad_assets(
    *,
    store: ProjectStore,
    round_number: int,
    locale: str,
    platform: str,
    guidance: str,
    llm: JsonLLM,
) -> tuple[Path, Path]:
    round_result = store.read_round_result(round_number)
    localized = read_localization_artifact(
        store,
        round_number,
        locale,
        platform,
    )
    assets = MarketingAssetGenerator(llm).run(
        round_result=round_result,
        localized_script=localized,
        locale=locale,
        platform=platform,
        guidance=guidance,
    )
    prefix = localization_artifact_prefix(locale, platform)
    json_path = store.write_round_artifact(
        round_number,
        f"marketing_assets_{prefix}",
        assets,
    )
    markdown_path = store.write_text_artifact(
        round_number,
        f"marketing_assets_{prefix}.md",
        render_marketing_assets(assets),
    )
    return json_path, markdown_path
