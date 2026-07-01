from novel_drama_engine.localization import (
    build_localization_package,
    render_localization_package_markdown,
    rewrite_localization_package_with_llm,
)
from novel_drama_engine.localization_profiles import (
    get_localization_profile,
    list_localization_profiles,
    localization_profiles_payload,
    resolve_localization_profile,
)
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    LocalizationProfile,
    LocalizationRewrite,
    LocalizedEpisodePackage,
    LocalizedScene,
    RoundResult,
)


def build_round_result(round_number, outputs):
    return RoundResult(
        project_id="demo",
        round_number=round_number,
        source_analysis=outputs[0],
        episode_context=outputs[1],
        story_bible=outputs[2],
        script_batch=outputs[3],
        quality_report=outputs[4],
        next_round_context=outputs[5],
    )


def test_build_localization_package_applies_profile(happy_round_outputs):
    result = build_round_result(1, happy_round_outputs)
    profile = LocalizationProfile(
        profile_id="us_tiktok",
        locale="en-US",
        platform="TikTok",
        target_language="en",
        title_prefix="Viral Short",
        replacements={
            "林晚": "Lena Lin",
            "林雪": "Selena Lin",
            "顾承": "Grant Gu",
            "大小姐": "heiress",
            "生日宴": "birthday gala",
        },
        forbidden_terms=["heiress"],
    )

    package = build_localization_package(result, profile)

    assert package.profile.profile_id == "us_tiktok"
    assert package.episodes[0].title == "Viral Short 被赶出 birthday gala"
    assert "Lena Lin" in package.episodes[0].scenes[0].adapted_lines[0]
    assert "Grant Gu（冷）：滚出去。" in package.episodes[0].scenes[0].adapted_lines
    assert package.issues[0].term == "heiress"
    assert package.issues[0].location == "EP01.cliffhanger"


def test_render_localization_package_markdown(happy_round_outputs):
    result = build_round_result(1, happy_round_outputs)
    profile = LocalizationProfile(
        profile_id="us_tiktok",
        locale="en-US",
        platform="TikTok",
        target_language="en",
        compliance_notes=["Keep conflict verbal-first."],
        production_notes=["Prioritize close-up reactions."],
    )

    package = build_localization_package(result, profile)
    text = render_localization_package_markdown(package)

    assert "# Localization Package Round 1" in text
    assert "Profile: us_tiktok" in text
    assert "- Keep conflict verbal-first." in text
    assert "### EP01 被赶出生日宴" in text
    assert "No forbidden terms found." in text


def test_rewrite_localization_package_with_llm_preserves_metadata_and_rescans_issues(
    happy_round_outputs,
):
    result = build_round_result(1, happy_round_outputs)
    profile = LocalizationProfile(
        profile_id="us_tiktok",
        locale="en-US",
        platform="TikTok",
        target_language="en",
        forbidden_terms=["heiress"],
    )
    package = build_localization_package(result, profile)
    rewrite = LocalizationRewrite(
        episodes=[
            LocalizedEpisodePackage(
                episode=1,
                title="Kicked Out of the Gala",
                hook_3s="Throw her out!",
                main_emotion="public humiliation",
                watch_reason="Viewers want the comeback.",
                cliffhanger="The butler calls her the heiress.",
                scenes=[
                    LocalizedScene(
                        heading="1-1 Night / Interior / Lin family gala",
                        characters=["Lena", "Selena", "Grant"],
                        adapted_lines=[
                            "Grant: Get out.",
                            "The butler calls her the heiress.",
                        ],
                    )
                ],
            )
        ]
    )

    rewritten = rewrite_localization_package_with_llm(
        package,
        StaticJsonLLM([rewrite]),
    )

    assert rewritten.project_id == "demo"
    assert rewritten.profile.profile_id == "us_tiktok"
    assert rewritten.episodes[0].title == "Kicked Out of the Gala"
    assert rewritten.issues[0].term == "heiress"
    assert rewritten.issues[0].location == "EP01.cliffhanger"


def test_localization_profile_registry_lists_default_profiles():
    profiles = list_localization_profiles("examples/localization_profiles")
    profile_ids = [profile.profile_id for profile in profiles]

    assert profile_ids == sorted(profile_ids)
    assert {"us_tiktok", "us_reela", "jp_reela", "sea_tiktok"}.issubset(profile_ids)


def test_localization_profile_registry_reads_profile_by_id():
    profile = get_localization_profile("examples/localization_profiles", "jp_reela")

    assert profile.locale == "ja-JP"
    assert profile.platform == "Reela"
    assert profile.target_language == "ja"


def test_localization_profiles_payload_returns_summaries():
    payload = localization_profiles_payload("examples/localization_profiles")

    assert payload["profile_count"] >= 4
    assert any(profile["profile_id"] == "sea_tiktok" for profile in payload["profiles"])


def test_resolve_localization_profile_requires_one_selector(tmp_path):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        '{"profile_id":"custom","locale":"en-US","platform":"TikTok","target_language":"en"}',
        encoding="utf-8",
    )

    file_profile = resolve_localization_profile(
        profile_path=profile_path,
        profile_id=None,
        profiles_dir="examples/localization_profiles",
    )
    id_profile = resolve_localization_profile(
        profile_path=None,
        profile_id="us_tiktok",
        profiles_dir="examples/localization_profiles",
    )

    assert file_profile.profile_id == "custom"
    assert id_profile.profile_id == "us_tiktok"
