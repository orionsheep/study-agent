"use client";

import type { DragEvent } from "react";
import { useState } from "react";
import type { LearningResource } from "@learnforge/app-protocol";
import { ExternalLink, Film, PlayCircle, PlusCircle } from "lucide-react";
import { bilibiliEmbedUrl, extractBvidFromResource } from "../../lib/video/bilibili";

/* ── Helpers ── */

function resourceUrl(resource: LearningResource) {
  const content = resource.content ?? {};
  const url = content.url ?? content.href;
  return typeof url === "string" && /^https?:\/\//.test(url) ? url : "";
}

function playLabel(value: unknown) {
  const count = Number(value ?? 0);
  if (!Number.isFinite(count) || count <= 0) return "";
  if (count >= 10000) return `${(count / 10000).toFixed(count >= 100000 ? 0 : 1)}万播放`;
  return `${Math.round(count)}播放`;
}

function startResourceDrag(event: DragEvent<HTMLElement>, resource: LearningResource) {
  event.dataTransfer.effectAllowed = "copy";
  event.dataTransfer.setData("application/x-learnforge-resource", JSON.stringify(resource));
  event.dataTransfer.setData("text/plain", resource.title);
}

/* ── VideoResourceCard ── */

export function VideoResourceCard({
  resource,
  onAddResourceToCanvas,
}: {
  resource: LearningResource;
  onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void>;
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const content = resource.content ?? {};
  const url = resourceUrl(resource);
  const bvid = extractBvidFromResource(resource);
  const embedUrl = bilibiliEmbedUrl(bvid);
  const author = String(content.author ?? "B站视频");
  const cover = String(content.cover ?? content.pic ?? content.thumbnail ?? "");
  const duration = String(content.duration ?? "");
  const play = playLabel(content.play);
  const togglePreview = () => { if (embedUrl) setPreviewOpen((open) => !open); };

  return (
    <section
      className="resource-card video-resource-card"
      draggable
      onDragStart={(event) => startResourceDrag(event, resource)}
      data-testid={`video-resource-card-${resource.resource_id}`}
      title="拖到左侧画布生成视频播放器"
    >
      <button type="button" className="video-card-cover" onClick={togglePreview} aria-label="预览视频">
        {cover ? (
          <img src={cover} alt={resource.title} loading="lazy" referrerPolicy="no-referrer" />
        ) : (
          <span className="video-card-cover-fallback"><Film size={26} /></span>
        )}
        {embedUrl ? <span className="video-card-play"><PlayCircle size={34} /></span> : null}
        {duration ? <span className="video-card-duration">{duration}</span> : null}
      </button>
      <div className="video-card-body">
        <strong>{resource.title}</strong>
        <small>{[author, play].filter(Boolean).join(" · ")}</small>
        <div className="video-card-actions">
          {embedUrl ? (
            <button type="button" onClick={togglePreview} title={previewOpen ? "收起" : "预览"}>
              <PlayCircle size={13} />
              <span className="video-action-label">{previewOpen ? "收起" : "预览"}</span>
            </button>
          ) : null}
          {url ? (
            <a href={url} target="_blank" rel="noreferrer" title="打开B站">
              <ExternalLink size={13} />
              <span className="video-action-label">打开B站</span>
            </a>
          ) : null}
          <button type="button" onClick={() => onAddResourceToCanvas(resource)} title="加入画布">
            <PlusCircle size={13} />
            <span className="video-action-label">加入画布</span>
          </button>
        </div>
      </div>
      {previewOpen && embedUrl ? (
        <div className="video-card-embed" data-testid={`video-resource-embed-${resource.resource_id}`}>
          <iframe
            title={`${resource.title} B站预览`}
            src={embedUrl}
            loading="lazy"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation"
            allow="fullscreen; picture-in-picture; autoplay"
            allowFullScreen
          />
        </div>
      ) : null}
    </section>
  );
}

/* ── ResourceCard (router) ── */

export function ResourceCard({
  resource,
  onAddResourceToCanvas,
}: {
  resource: LearningResource;
  onAddResourceToCanvas: (resource: LearningResource) => void | Promise<void>;
}) {
  if (resource.type === "video") {
    return <VideoResourceCard resource={resource} onAddResourceToCanvas={onAddResourceToCanvas} />;
  }
  return (
    <section
      className="resource-card"
      draggable
      onDragStart={(event) => startResourceDrag(event, resource)}
      title="拖到左侧画布生成资源中心"
    >
      <strong>{resource.title}</strong>
      <small>学习资料</small>
      <p>{resource.personalized_reason}</p>
    </section>
  );
}
