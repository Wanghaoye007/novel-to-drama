from novel_drama_engine.localization import (
    build_localization_package,
    render_localization_package_markdown,
    rewrite_localization_package_with_llm,
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
    assert package.issues[0].location.startswith("EP01.")


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
