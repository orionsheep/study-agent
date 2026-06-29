export type AppearanceTheme = "light" | "dark";

export type BrandAssetName = "learnforge-logo" | "ai-tutor-avatar";

export type FolderIconKey =
  | "notes"
  | "quiz"
  | "mindmap"
  | "infographic"
  | "image"
  | "code"
  | "ppt"
  | "video"
  | "demo"
  | "other";

export type WallpaperId =
  | "sonoma"
  | "radial-sky-blue"
  | "imac-blue"
  | "imac-green"
  | "imac-orange"
  | "imac-pink"
  | "imac-purple"
  | "imac-silver"
  | "imac-yellow"
  | "pure-white"
  | "pure-black";

export type WallpaperDefinition = {
  id: WallpaperId;
  label: string;
  file?: string;
  accent: string;
};

export const DEFAULT_WALLPAPER_ID: WallpaperId = "sonoma";

export const WALLPAPERS: WallpaperDefinition[] = [
  { id: "sonoma", label: "Sonoma", file: "/wallpapers/apple/sonoma.webp", accent: "#f0b37a" },
  { id: "radial-sky-blue", label: "Radial Sky", file: "/wallpapers/apple/radial-sky-blue.webp", accent: "#8cc9ff" },
  { id: "imac-blue", label: "iMac Blue", file: "/wallpapers/apple/imac-blue.webp", accent: "#55a9dc" },
  { id: "imac-green", label: "iMac Green", file: "/wallpapers/apple/imac-green.webp", accent: "#7fbe9b" },
  { id: "imac-orange", label: "iMac Orange", file: "/wallpapers/apple/imac-orange.webp", accent: "#f2a15d" },
  { id: "imac-pink", label: "iMac Pink", file: "/wallpapers/apple/imac-pink.webp", accent: "#ed9db9" },
  { id: "imac-purple", label: "iMac Purple", file: "/wallpapers/apple/imac-purple.webp", accent: "#a99be5" },
  { id: "imac-silver", label: "iMac Silver", file: "/wallpapers/apple/imac-silver.webp", accent: "#c9ced6" },
  { id: "imac-yellow", label: "iMac Yellow", file: "/wallpapers/apple/imac-yellow.webp", accent: "#f2d46a" },
  { id: "pure-white", label: "Pure White", accent: "#ffffff" },
  { id: "pure-black", label: "Pure Black", accent: "#050505" },
];

export const APP_ICON_FILES: Record<string, string> = {
  "profile.dashboard": "student_profile_app.png",
  "learning.path": "learning_path_app.png",
  "knowledge.graph": "knowledge_graph_app.png",
  "mindmap.concept": "folder_mindmap_app.png",
  "quiz.practice": "quiz_practice_app.png",
  "physics.work_energy_demo": "work_energy_demo_app.png",
  "math.gradient_descent_demo": "folder_demo_app.png",
  "code.lab": "code_lab_app.png",
  "notes.session": "session_notes_app.png",
  "dashboard.learning": "learning_dashboard_app.png",
  "resource.center": "resource_bundle_app.png",
  "ppt.preview": "folder_ppt_app.png",
  "image.explanation": "folder_image_app.png",
  "video.script": "folder_video_app.png",
  "video.player": "folder_video_app.png",
  "custom.html": "folder_infographic_app.png",
  "resource.folder": "folder_other_app.png",
  "tutor.chat": "tutor_chat_app.png",
  "english.workspace": "folder_notes_app.png",
  "notebooklm.workspace": "folder_mindmap_app.png",
  "humanities.notebook": "folder_mindmap_app.png",
  "exam.cram": "learning_path_app.png",
};

export const FOLDER_ICON_FILES: Record<FolderIconKey, string> = {
  notes: "folder_notes_app.png",
  quiz: "folder_quiz_app.png",
  mindmap: "folder_mindmap_app.png",
  infographic: "folder_infographic_app.png",
  image: "folder_image_app.png",
  code: "folder_code_app.png",
  ppt: "folder_ppt_app.png",
  video: "folder_video_app.png",
  demo: "folder_demo_app.png",
  other: "folder_other_app.png",
};

export const BRAND_ASSET_FILES: Record<BrandAssetName, string> = {
  "learnforge-logo": "learnforge-logo.png",
  "ai-tutor-avatar": "ai-tutor-avatar.png",
};

export const ICON_FILES = [
  "code_lab_app.png",
  "folder_code_app.png",
  "folder_demo_app.png",
  "folder_image_app.png",
  "folder_infographic_app.png",
  "folder_mindmap_app.png",
  "folder_notes_app.png",
  "folder_other_app.png",
  "folder_ppt_app.png",
  "folder_quiz_app.png",
  "folder_video_app.png",
  "knowledge_graph_app.png",
  "learning_dashboard_app.png",
  "learning_path_app.png",
  "quiz_practice_app.png",
  "resource_bundle_app.png",
  "session_notes_app.png",
  "student_profile_app.png",
  "tutor_chat_app.png",
  "work_energy_demo_app.png",
] as const;

function normalizeTheme(theme: AppearanceTheme): AppearanceTheme {
  return theme === "dark" ? "dark" : "light";
}

function iconPath(file: string, theme: AppearanceTheme): string {
  return `/icons/${normalizeTheme(theme)}/${file}`;
}

export function normalizeWallpaperId(value: unknown): WallpaperId {
  return WALLPAPERS.some((wallpaper) => wallpaper.id === value)
    ? value as WallpaperId
    : DEFAULT_WALLPAPER_ID;
}

export function wallpaperById(id: WallpaperId): WallpaperDefinition {
  return WALLPAPERS.find((wallpaper) => wallpaper.id === id) ?? WALLPAPERS[0];
}

export function wallpaperCssValue(id: WallpaperId): string {
  const wallpaper = wallpaperById(id);
  return wallpaper.file ? `url("${wallpaper.file}")` : "none";
}

export function wallpaperOverlayCssValue(id: WallpaperId, theme: AppearanceTheme): string {
  if (id === "pure-white") {
    return theme === "dark"
      ? "linear-gradient(rgba(255,255,255,0.98), rgba(255,255,255,0.98))"
      : "linear-gradient(rgba(255,255,255,1), rgba(255,255,255,1))";
  }
  if (id === "pure-black") {
    return "linear-gradient(rgba(5,5,6,1), rgba(5,5,6,1))";
  }
  return theme === "dark"
    ? "linear-gradient(180deg, rgba(5,7,12,0.55), rgba(5,7,12,0.72))"
    : "linear-gradient(180deg, rgba(255,255,255,0.28), rgba(255,255,255,0.56))";
}

export function themedBrandAsset(name: BrandAssetName, theme: AppearanceTheme): string {
  return `/brand/${normalizeTheme(theme)}/${BRAND_ASSET_FILES[name]}`;
}

export function themedAppIcon(appType: string, theme: AppearanceTheme): string | undefined {
  const file = APP_ICON_FILES[appType];
  return file ? iconPath(file, theme) : undefined;
}

export function themedFolderIcon(folderKey: FolderIconKey, theme: AppearanceTheme): string {
  return iconPath(FOLDER_ICON_FILES[folderKey] ?? FOLDER_ICON_FILES.other, theme);
}

export function themedIconAssetFromPath(path: string, theme: AppearanceTheme): string {
  const file = path.split("/").pop();
  if (!file) return path;
  return iconPath(file, theme);
}
