import type { LearningResource } from "@learnforge/app-protocol";

export type BilibiliEmbedOptions = {
  autoplay?: boolean;
  danmaku?: boolean;
  poster?: boolean;
  page?: number;
};

export const DEFAULT_BILIBILI_EMBED_OPTIONS: Required<BilibiliEmbedOptions> = {
  autoplay: false,
  danmaku: false,
  poster: true,
  page: 1
};

const BVID_PATTERN = /\b(BV[0-9A-Za-z]{4,})\b/;

export function extractBvidFromResource(resource: LearningResource | Record<string, unknown>) {
  const content = typeof resource.content === "object" && resource.content ? resource.content as Record<string, unknown> : {};
  const sourceRefs = Array.isArray(resource.source_refs) ? resource.source_refs : [];
  const candidates = [
    content.bvid,
    content.url,
    content.href,
    content.embed_url,
    resource.title,
    ...sourceRefs.flatMap((ref) => {
      const record = typeof ref === "object" && ref ? ref as Record<string, unknown> : {};
      return [record.bvid, record.url, record.href, record.resource_id, record.chunk_id];
    })
  ];
  for (const item of candidates) {
    if (typeof item !== "string") continue;
    const match = item.match(BVID_PATTERN);
    if (match) return match[1];
  }
  return "";
}

export function bilibiliEmbedUrl(bvid: string, options: BilibiliEmbedOptions = {}) {
  const cleanBvid = bvid.trim();
  if (!cleanBvid) return "";
  const merged = { ...DEFAULT_BILIBILI_EMBED_OPTIONS, ...options };
  const params = new URLSearchParams({
    bvid: cleanBvid,
    poster: merged.poster ? "1" : "0",
    autoplay: merged.autoplay ? "1" : "0",
    danmaku: merged.danmaku ? "1" : "0",
    p: String(merged.page || 1)
  });
  return `https://player.bilibili.com/player.html?${params.toString()}`;
}
