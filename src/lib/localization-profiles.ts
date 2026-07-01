import path from "path";

export interface LocalizationProfileOption {
  id: string;
  label: string;
  locale: string;
  platform: string;
  targetLanguage: string;
  path: string;
}

const PROFILE_DEFINITIONS = [
  {
    id: "us_tiktok",
    label: "US TikTok",
    locale: "en-US",
    platform: "TikTok",
    targetLanguage: "en",
    filename: "us_tiktok.json",
  },
  {
    id: "jp_reels",
    label: "Japan Reels",
    locale: "ja-JP",
    platform: "Instagram Reels",
    targetLanguage: "ja",
    filename: "jp_reels.json",
  },
  {
    id: "sea_tiktok",
    label: "SEA TikTok",
    locale: "en-SG",
    platform: "TikTok SEA",
    targetLanguage: "en",
    filename: "sea_tiktok.json",
  },
] as const;

export function localizationProfiles(): LocalizationProfileOption[] {
  return PROFILE_DEFINITIONS.map((profile) => ({
    ...profile,
    path: path.join(
      /*turbopackIgnore: true*/
      process.cwd(),
      "examples",
      "localization_profiles",
      profile.filename
    ),
  }));
}

export function resolveLocalizationProfile(
  profileId: string | null
): LocalizationProfileOption {
  const safeProfileId = profileId || "us_tiktok";
  const profile = localizationProfiles().find((item) => item.id === safeProfileId);
  if (!profile) throw new Error(`unsupported localization profile: ${safeProfileId}`);
  return profile;
}
