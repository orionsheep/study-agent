import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CanvasApp } from "@learnforge/app-protocol";
import {
  BookOpen,
  Braces,
  ChevronDown,
  CheckCircle2,
  ClipboardPaste,
  ExternalLink,
  FileText,
  FileUp,
  FolderOpen,
  Layers3,
  Library,
  Link,
  Loader2,
  NotebookTabs,
  Podcast,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  TextCursorInput,
  TriangleAlert,
} from "lucide-react";
import {
  addNotebookLMLinkSource,
  addNotebookLMTextSource,
  bootstrapNotebookLM,
  createNotebookLMNotebook,
  fetchNotebookLMNotebookSources,
  fetchNotebookLMNotebooks,
  fetchNotebookLMStatus,
  syncNotebookLMNotebook,
  uploadNotebookLMFileSource,
  type NotebookLMBootstrap,
  type NotebookLMNotebook,
  type NotebookLMSource,
  type NotebookLMStatus,
  type SessionContext,
} from "../../../lib/api/client";

type Props = {
  app: CanvasApp;
  onEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void | Promise<void>;
  sessionContext: SessionContext;
};

type SourceCard = NotebookLMSource & {
  refs: Array<Record<string, unknown>>;
};

const ACTIONS = [
  { kind: "study_guide", label: "学习指南", icon: Library, prompt: "请基于当前 NotebookLM 来源生成一份结构化学习指南，必须标注引用依据。" },
  { kind: "quiz", label: "测验", icon: CheckCircle2, prompt: "请基于当前 NotebookLM 来源生成一组诊断测验，题目和解释都要绑定来源。" },
  { kind: "flashcards", label: "闪卡", icon: Braces, prompt: "请基于当前 NotebookLM 来源生成适合复习的闪卡，并按概念分组。" },
  { kind: "audio_overview", label: "音频概览", icon: Podcast, prompt: "请基于当前 NotebookLM 来源生成音频概览脚本，保持对话式但必须忠于来源。" },
];

const GROUPS = [
  { key: "course", label: "课程知识库", match: (item: NotebookLMNotebook) => item.purpose === "course_official" },
  { key: "system", label: "系统推荐", match: (item: NotebookLMNotebook) => item.purpose === "system_review" },
  { key: "personal", label: "我的 Notebook", match: (item: NotebookLMNotebook) => item.purpose === "personal_review" },
  { key: "temporary", label: "临时资料", match: (item: NotebookLMNotebook) => item.purpose === "temporary" },
];

function statusLabel(status?: string) {
  if (!status) return "检测中";
  if (status === "ready") return "来源服务可用";
  if (status === "partial") return "部分来源已同步";
  if (status === "not_synced") return "未同步";
  if (status.startsWith("blocked")) return "来源服务不可用";
  return status;
}

function sourceLabel(source: SourceCard | null) {
  if (!source) return "等待来源";
  if (source.ingest_type === "link") return "链接来源";
  if (source.ingest_type === "file_upload") return "文件来源";
  if (source.ingest_type === "text") return "文本来源";
  if (source.source_scope === "course_official") return "课程正式资料";
  return "Notebook 来源";
}

function sourceFromApi(source: NotebookLMSource): SourceCard {
  const refs = Array.isArray(source.source_refs) ? source.source_refs.filter(isUsableSourceRef) : [];
  const summary = isReadableSourceText(source.summary) ? source.summary : "";
  return { ...source, summary, refs };
}

function isReadableSourceText(value: unknown): boolean {
  const text = String(value ?? "").trim();
  if (!text) return false;
  const sample = text.slice(0, 600);
  if (/%PDF-\d|endobj\b|\/Type\/Page\b|\/Font\b|\/XObject\b|xref\b|trailer\b/i.test(sample)) return false;
  const controlChars = Array.from(sample).filter((ch) => {
    const code = ch.charCodeAt(0);
    return (code < 32 && !"\n\r\t".includes(ch)) || ch === "\uFFFD";
  }).length;
  return controlChars / Math.max(1, sample.length) < 0.02;
}

function isUsableSourceRef(ref: Record<string, unknown>): boolean {
  return isReadableSourceText(ref.snippet ?? ref.quote ?? ref.content ?? ref.text);
}

export function NotebookLMWorkspaceApp({ app, onEvent, sessionContext }: Props) {
  const [status, setStatus] = useState<NotebookLMStatus | null>(null);
  const [bootstrap, setBootstrap] = useState<NotebookLMBootstrap | null>(null);
  const [notebooks, setNotebooks] = useState<NotebookLMNotebook[]>([]);
  const [sources, setSources] = useState<SourceCard[]>([]);
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkTitle, setLinkTitle] = useState("");
  const [textTitle, setTextTitle] = useState("粘贴资料");
  const [textContent, setTextContent] = useState("");
  const [newNotebookTitle, setNewNotebookTitle] = useState("");
  const [sourceManagerOpen, setSourceManagerOpen] = useState(false);
  const [generateMenuOpen, setGenerateMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pendingUploadNotebookIdRef = useRef<string | null>(null);
  const lastContextKeyRef = useRef("");

  const selectedNotebook = useMemo(
    () => notebooks.find((item) => item.id === selectedNotebookId) ?? notebooks[0] ?? null,
    [notebooks, selectedNotebookId],
  );

  const selectedSource = useMemo(
    () => sources.find((source) => source.id === selectedSourceId || source.source_id === selectedSourceId) ?? sources[0] ?? null,
    [selectedSourceId, sources],
  );

  const writableNotebook = selectedNotebook?.purpose !== "course_official" && selectedNotebook?.owner_scope !== "course";
  const ready = status?.status === "ready" || status?.status === "partial";
  const showStatus = status?.status && status.status !== "ready";

  const notebookEventPayload = useCallback((source: SourceCard | null, extra: Record<string, unknown> = {}) => ({
    ...extra,
    learnforge_notebook_id: selectedNotebook?.id,
    notebook_id: selectedNotebook?.id,
    open_notebook_id: bootstrap?.notebook_id || selectedNotebook?.open_notebook_id,
    notebook_title: selectedNotebook?.title,
    source_id: source?.id,
    source_title: source?.title,
    source_refs: source?.refs?.slice(0, 12) ?? [],
  }), [bootstrap?.notebook_id, selectedNotebook]);

  const loadNotebookSources = useCallback(async (notebookId: string) => {
    const [nextBootstrap, sourcePayload] = await Promise.all([
      bootstrapNotebookLM(sessionContext, notebookId).catch((error) => ({ status: "blocked_bootstrap_error", reason: error instanceof Error ? error.message : "bootstrap failed" })),
      fetchNotebookLMNotebookSources(notebookId, sessionContext),
    ]);
    setBootstrap(nextBootstrap);
    const nextSources = sourcePayload.sources.map(sourceFromApi);
    setSources(nextSources);
    setSelectedSourceId((current) => current && nextSources.some((source) => source.id === current || source.source_id === current) ? current : nextSources[0]?.id ?? null);
  }, [sessionContext]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextStatus, nextNotebooks] = await Promise.all([
        fetchNotebookLMStatus(sessionContext).catch((error) => ({ status: "blocked_status_error", reason: error instanceof Error ? error.message : "status failed" })),
        fetchNotebookLMNotebooks(sessionContext).catch(() => []),
      ]);
      setStatus(nextStatus);
      setNotebooks(nextNotebooks);
      const nextNotebookId = selectedNotebookId && nextNotebooks.some((item) => item.id === selectedNotebookId)
        ? selectedNotebookId
        : nextNotebooks[0]?.id ?? null;
      setSelectedNotebookId(nextNotebookId);
      if (nextNotebookId) await loadNotebookSources(nextNotebookId);
      else {
        setSources([]);
        setBootstrap(null);
      }
    } finally {
      setLoading(false);
    }
  }, [loadNotebookSources, selectedNotebookId, sessionContext]);

  useEffect(() => {
    load().catch(() => undefined);
  }, [load]);

  useEffect(() => {
    if (!selectedNotebook) return;
    const payload = notebookEventPayload(selectedSource, {
      source_refs: selectedSource?.refs?.slice(0, 8) ?? [],
    });
    const contextKey = JSON.stringify({
      learnforge_notebook_id: payload.learnforge_notebook_id,
      open_notebook_id: payload.open_notebook_id,
      source_id: payload.source_id,
      source_refs: payload.source_refs.map((ref) => ref.chunk_id ?? ref.document_id ?? ref.title),
    });
    if (lastContextKeyRef.current === contextKey) return;
    lastContextKeyRef.current = contextKey;
    onEvent(app.app_id, "notebooklm.context_select", payload);
  }, [app.app_id, notebookEventPayload, onEvent, selectedNotebook, selectedSource]);

  const selectNotebook = async (notebookId: string) => {
    setSelectedNotebookId(notebookId);
    setSelectedSourceId(null);
    setMessage("");
    await loadNotebookSources(notebookId);
  };

  const createNotebook = async () => {
    const title = newNotebookTitle.trim() || "新的复习 Notebook";
    setImporting(true);
    try {
      const notebook = await createNotebookLMNotebook({ title, tags: ["我的上传", "复习"] }, sessionContext);
      setNewNotebookTitle("");
      await load();
      await selectNotebook(notebook.id);
    } finally {
      setImporting(false);
    }
  };

  const syncSources = async () => {
    if (!selectedNotebook) return;
    setSyncing(true);
    setMessage("");
    try {
      const result = await syncNotebookLMNotebook(selectedNotebook.id, sessionContext);
      setStatus(result);
      const syncedCount = Array.isArray(result.synced) ? result.synced.length : 0;
      const blockedCount = Array.isArray(result.blocked) ? result.blocked.length : 0;
      setMessage(blockedCount ? `已同步 ${syncedCount} 个来源，${blockedCount} 个来源未被 Open Notebook 接收。` : `已同步 ${syncedCount} 个来源。`);
      await loadNotebookSources(selectedNotebook.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "同步失败");
    } finally {
      setSyncing(false);
    }
  };

  // 解析可写 Notebook：当前只读时自动切换到 writableNotebookId，与文件上传行为一致。
  const resolveWritableTarget = async (): Promise<string | null> => {
    if (writableNotebook) return selectedNotebook?.id ?? null;
    const targetId = writableNotebookId;
    if (!targetId) {
      setMessage("找不到可写的 Notebook，请先点左上角「+」新建一个「我的 Notebook」。");
      return null;
    }
    const writableTitle = notebooks.find((item) => item.id === targetId)?.title ?? "我的复习 Notebook";
    setMessage(`当前「${selectedNotebook?.title ?? "课程知识库"}」只读，已自动切换到「${writableTitle}」。`);
    await selectNotebook(targetId);
    return targetId;
  };

  const addLink = async () => {
    if (!linkUrl.trim()) return;
    const targetId = await resolveWritableTarget();
    if (!targetId) return;
    setImporting(true);
    setMessage("");
    try {
      await addNotebookLMLinkSource(targetId, { url: linkUrl.trim(), title: linkTitle.trim() || undefined, sync: true }, sessionContext);
      setLinkUrl("");
      setLinkTitle("");
      setMessage("链接已保存到当前 Notebook。");
      await loadNotebookSources(targetId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "链接保存失败");
    } finally {
      setImporting(false);
    }
  };

  const addText = async () => {
    if (!textContent.trim()) return;
    const targetId = await resolveWritableTarget();
    if (!targetId) return;
    setImporting(true);
    setMessage("");
    try {
      await addNotebookLMTextSource(targetId, { title: textTitle.trim() || "粘贴资料", content: textContent, sync: true }, sessionContext);
      setTextContent("");
      setMessage("文本已保存到当前 Notebook。");
      await loadNotebookSources(targetId);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文本保存失败");
    } finally {
      setImporting(false);
    }
  };

  const writableNotebookId = useMemo(
    () => notebooks.find((item) => item.purpose !== "course_official" && item.owner_scope !== "course")?.id ?? null,
    [notebooks],
  );

  // 点「上传文件」永远有反应：当前若是只读 notebook（如课程知识库），
  // 同步拿到可写 notebook 的 id 作为上传目标，UI 切换放后台不阻塞文件选择器。
  const openFilePicker = () => {
    if (importing) return;
    let targetId: string | null = selectedNotebook?.id ?? null;
    if (!writableNotebook) {
      targetId = writableNotebookId;
      if (!targetId) {
        setMessage("找不到可写的 Notebook，请先点左上角「+」新建一个「我的 Notebook」。");
        return;
      }
      const writableTitle = notebooks.find((item) => item.id === targetId)?.title ?? "我的复习 Notebook";
      setMessage(`当前「${selectedNotebook?.title ?? "课程知识库"}」只读，已自动切换到「${writableTitle}」。`);
      selectNotebook(targetId).catch(() => undefined);
    }
    pendingUploadNotebookIdRef.current = targetId;
    fileInputRef.current?.click();
  };

  const uploadFiles = async (
    files: FileList | File[] | null | undefined,
    notebookIdOverride?: string,
  ) => {
    const list = files ? Array.from(files) : [];
    if (!list.length) return;
    const targetId = notebookIdOverride ?? selectedNotebook?.id;
    if (!targetId) {
      setMessage("请先选择一个 Notebook。");
      return;
    }
    setImporting(true);
    let ok = 0;
    let fail = 0;
    let lastError = "";
    try {
      for (let i = 0; i < list.length; i++) {
        setMessage(`正在上传 ${i + 1}/${list.length}：${list[i].name}`);
        try {
          await uploadNotebookLMFileSource(targetId, { file: list[i], sync: true }, sessionContext);
          ok++;
        } catch (error) {
          fail++;
          lastError = error instanceof Error ? error.message : String(error);
          // 控制台留底，便于排查真实原因（网络/CORS/后端报错）
          console.error("[NotebookLM upload] 失败:", list[i].name, error);
        }
      }
      setMessage(
        fail === 0
          ? `已上传 ${ok} 个文件到当前 Notebook。`
          : `已上传 ${ok}/${list.length}，${fail} 个失败。原因：${lastError || "未知"}`,
      );
      await loadNotebookSources(targetId);
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const askHermes = async (prompt?: string, kind?: string) => {
    if (!selectedNotebook) return;
    const basePrompt = prompt || "请基于当前 NotebookLM 来源回答我的问题，必须说明引用依据。";
    const payload = notebookEventPayload(selectedSource, {
      kind,
      prompt: basePrompt,
      focus_chat: !kind,
    });
    if (!kind) {
      setMessage("已引用当前来源，请在右侧输入你的问题。");
      await onEvent(app.app_id, "notebooklm.context_select", payload);
      return;
    }
    await onEvent(app.app_id, "notebooklm.generate_with_hermes", payload);
  };

  const grouped = GROUPS.map((group) => ({ ...group, items: notebooks.filter(group.match) })).filter((group) => group.items.length);
  const selectedRefs = selectedSource?.refs ?? [];
  const runHermesAction = (prompt?: string, kind?: string) => {
    setGenerateMenuOpen(false);
    askHermes(prompt, kind).catch(() => undefined);
  };

  return (
    <div className="notebooklm-workspace" data-testid="notebooklm-workspace">
      <aside className="nblm-source-rail">
        <div className="nblm-brand">
          <div className="nblm-mark"><Layers3 size={18} /></div>
          <div>
            <strong>NotebookLM</strong>
            <span>来源中心</span>
          </div>
        </div>
        {showStatus ? (
          <div className={`nblm-status ${ready ? "ready" : "blocked"}`} data-testid="notebooklm-status">
            {ready ? <CheckCircle2 size={14} /> : <TriangleAlert size={14} />}
            <span>{statusLabel(status?.status)}</span>
          </div>
        ) : null}

        <div className="nblm-create-row">
          <input value={newNotebookTitle} onChange={(event) => setNewNotebookTitle(event.target.value)} placeholder="新的复习 Notebook" />
          <button type="button" onClick={createNotebook} disabled={importing} title="新建 Notebook">
            <Plus size={15} />
          </button>
        </div>

        <div className="nblm-notebooks" data-testid="notebooklm-notebooks">
          {grouped.map((group) => (
            <section key={group.key} className="nblm-notebook-group">
              <div className="nblm-group-title">
                <FolderOpen size={13} />
                <span>{group.label}</span>
              </div>
              {group.items.map((notebook) => (
                <button
                  key={notebook.id}
                  className={`nblm-notebook-card ${selectedNotebook?.id === notebook.id ? "active" : ""}`}
                  onClick={() => selectNotebook(notebook.id).catch(() => undefined)}
                  title={notebook.title}
                >
                  <NotebookTabs size={15} />
                  <span>{notebook.title}</span>
                  <small>{notebook.source_count ?? 0}</small>
                </button>
              ))}
            </section>
          ))}
          {!notebooks.length && !loading ? (
            <div className="nblm-empty">
              <BookOpen size={20} />
              <span>还没有 Notebook</span>
            </div>
          ) : null}
        </div>
        <div className="nblm-rail-section-head">
          <span>当前来源</span>
          <small>{sources.length}</small>
        </div>
        <section className="nblm-source-list" data-testid="notebooklm-sources">
          {sources.map((source) => (
            <button
              key={source.id}
              className={`nblm-source-card ${selectedSource?.id === source.id ? "active" : ""}`}
              onClick={() => {
                setSelectedSourceId(source.id);
                Promise.resolve(onEvent(app.app_id, "notebooklm.context_select", notebookEventPayload(source, { focus_chat: true }))).catch(() => undefined);
              }}
              title={source.title}
            >
              <FileText size={15} />
              <span>{source.title}</span>
              <small>{source.refs.length} refs</small>
            </button>
          ))}
          {!sources.length && !loading ? (
            <div className="nblm-empty">
              <BookOpen size={20} />
              <span>当前 Notebook 还没有来源</span>
            </div>
          ) : null}
        </section>
      </aside>

      <main className={`nblm-detail ${sourceManagerOpen ? "is-source-manager" : ""}`} data-testid="notebooklm-detail">
        <div className="nblm-toolbar">
          <div className="nblm-preview-head">
            <div>
              <span>{selectedNotebook?.title || "Notebook"}</span>
              <strong>{selectedSource?.title || "等待来源"}</strong>
            </div>
          </div>
          <div className="nblm-toolbar-actions">
            {bootstrap?.embed_url ? (
              <a className="nblm-icon-btn" href={bootstrap.embed_url} target="_blank" rel="noreferrer" title="打开 Open Notebook 来源工作台" aria-label="打开 Open Notebook 来源工作台">
                <ExternalLink size={15} />
              </a>
            ) : null}
            <button
              type="button"
              className={`nblm-compact-btn ${sourceManagerOpen ? "active" : ""}`}
              data-testid="notebooklm-manage-sources"
              onClick={() => {
                setSourceManagerOpen((current) => !current);
                setGenerateMenuOpen(false);
              }}
              title={sourceManagerOpen ? "返回来源预览" : "管理来源"}
            >
              <FolderOpen size={14} />
              <span>{sourceManagerOpen ? "返回预览" : "管理来源"}</span>
            </button>
            <button className="nblm-icon-btn" onClick={syncSources} disabled={syncing || loading || !selectedNotebook} title="同步到 Open Notebook" aria-label="同步到 Open Notebook">
              {syncing ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}
            </button>
            <button className="nblm-compact-btn nblm-ask-btn" onClick={() => runHermesAction()} disabled={!selectedNotebook}>
              <Send size={14} />
              <span>引用到对话</span>
            </button>
            <div className="nblm-menu-wrap">
              <button
                type="button"
                className={`nblm-compact-btn ${generateMenuOpen ? "active" : ""}`}
                data-testid="notebooklm-generate-button"
                onClick={() => setGenerateMenuOpen((current) => !current)}
                disabled={!selectedNotebook}
              >
                <Sparkles size={14} />
                <span>生成</span>
                <ChevronDown size={13} />
              </button>
              {generateMenuOpen ? (
                <div className="nblm-generate-menu" data-testid="notebooklm-generate-menu">
                  {ACTIONS.map((action) => {
                    const Icon = action.icon;
                    return (
                      <button key={action.kind} onClick={() => runHermesAction(action.prompt, action.kind)} disabled={!selectedNotebook}>
                        <Icon size={15} />
                        <span>{action.label}</span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {sourceManagerOpen ? (
          <section className="nblm-source-manager" data-testid="notebooklm-source-manager">
            <div className="nblm-manager-head">
              <div>
                <strong>来源管理</strong>
                <span>{writableNotebook ? "支持文件、链接和粘贴文本" : "课程知识库为只读正式来源"}</span>
              </div>
              <span>{sources.length} sources</span>
            </div>
            {message ? <p className="nblm-manager-message" data-testid="notebooklm-manager-message">{message}</p> : null}
            {!writableNotebook ? <p className="nblm-manager-note">课程正式知识库由系统或管理员维护；个人复习材料请切换到“我的 Notebook”。</p> : null}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="nblm-file-input"
              onChange={(event) => uploadFiles(event.target.files, pendingUploadNotebookIdRef.current ?? undefined).catch(() => undefined)}
              disabled={importing}
            />
            <button className="nblm-wide-action" type="button" onClick={openFilePicker} disabled={importing}>
              {importing ? <Loader2 className="spin" size={15} /> : <FileUp size={15} />}
              <span>上传文件（可多选）</span>
            </button>
            {!writableNotebook ? (
              <small className="nblm-manager-hint">当前是只读课程知识库，点「上传文件」会自动切到「我的复习 Notebook」再传。</small>
            ) : null}

            <div className="nblm-import-grid">
              <div className="nblm-import-box">
                <label>
                  <Link size={13} />
                  <input value={linkTitle} onChange={(event) => setLinkTitle(event.target.value)} placeholder="链接标题" disabled={importing} />
                </label>
                <label>
                  <ClipboardPaste size={13} />
                  <input value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} placeholder="https://..." disabled={importing} />
                </label>
                <button type="button" onClick={addLink} disabled={importing || !linkUrl.trim()}>
                  <Link size={15} />
                  <span>添加链接</span>
                </button>
              </div>

              <div className="nblm-import-box">
                <label>
                  <TextCursorInput size={13} />
                  <input value={textTitle} onChange={(event) => setTextTitle(event.target.value)} placeholder="文本标题" disabled={importing} />
                </label>
                <textarea value={textContent} onChange={(event) => setTextContent(event.target.value)} placeholder="粘贴阅读材料、讲义摘录或题目素材" disabled={importing} />
                <button type="button" onClick={addText} disabled={importing || !textContent.trim()}>
                  <TextCursorInput size={15} />
                  <span>粘贴文本</span>
                </button>
              </div>
            </div>
          </section>
        ) : (
          <>
            <section className="nblm-source-summary">
              <p>{selectedSource?.summary || "当前来源还没有可引用文本。可以重新同步，或上传可解析的文本/PDF 后再向右侧 Hermes 提问。"}</p>
              <div className="nblm-source-meta">
                <span>{sourceLabel(selectedSource)}</span>
                <span>{selectedSource?.sync_status || selectedSource?.upload_status || "source"}</span>
                {selectedSource?.original_url ? <span>{selectedSource.original_url}</span> : null}
              </div>
              {message ? <small>{message}</small> : null}
              {status?.reason && !ready ? <small>{status.reason}</small> : null}
            </section>

            <section className="nblm-citations" data-testid="notebooklm-citations">
              <div className="nblm-section-title">
                <Sparkles size={14} />
                <span>引用片段</span>
              </div>
              {selectedRefs.slice(0, 8).map((ref, index) => (
                <article key={`${String(ref.chunk_id ?? ref.document_id ?? index)}-${index}`}>
                  <strong>{String(ref.title ?? ref.section ?? `引用 ${index + 1}`)}</strong>
                  <p>{String(ref.snippet ?? ref.quote ?? ref.chunk_id ?? ref.document_id ?? "source ref")}</p>
                </article>
              ))}
              {!selectedRefs.length ? <p className="nblm-muted">当前来源没有通过质量门的可展示引用。</p> : null}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
