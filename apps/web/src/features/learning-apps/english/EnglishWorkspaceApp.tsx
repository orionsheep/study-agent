import { useState, useEffect, useCallback, useRef } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { ChevronLeft, ChevronRight, PanelLeftOpen, MessageSquareText, Monitor, LayoutDashboard, X, Minimize2, BarChart3, BrainCircuit, Clock } from 'lucide-react';
import type { CanvasApp } from '@learnforge/app-protocol';
import type { SessionContext } from '../../../lib/api/client';
import WordList from './components/WordList';
import WordDetail from './components/WordDetail';
import FissionGraph from './components/FissionGraph';
import QuizPanel from './components/QuizPanel';
import { EnglishDashboard } from './components/EnglishDashboard';

// 1:1 restoration of the english-word-fission ThreeColumnLayout + Immersive mode.
//
// Dashboard mode (default): three resizable columns share the window simultaneously —
//   Left   : WordList (library browser + virtualized words), collapsible
//   Middle : WordDetail (phonetic, Collins stars, definitions, examples) + history nav
//   Right  : FissionGraph (force-directed synonym network)
//
// Immersive mode: the FissionGraph becomes a full-bleed background and the WordList +
// WordDetail become floating draggable windows over it, exactly like the original
// /immersive route.
//
// All AI dialogue stays in the right-side Hermes (TutorChat). Selecting a word reports
// up via the `english.word_select` app event, which the shell turns into the Hermes
// english context. No embedded chat panel here.

interface Props {
  app: CanvasApp;
  onEvent: (appId: string, eventType: string, payload: Record<string, unknown>) => void | Promise<void>;
  sessionContext?: SessionContext;
}

type Mode = 'dashboard' | 'immersive' | 'stats' | 'quiz';

export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {
  const [selectedWord, setSelectedWord] = useState<string | null>(
    String(app.payload?.incoming_word ?? app.payload?.selected_word ?? '') || null
  );
  const [mode, setMode] = useState<Mode>('dashboard');
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);

  // Browsing history (back/forward) — mirrors the original dashboard.
  const [history, setHistory] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);

  // Listen for incoming_word updates (e.g. from the global selection toolbar).
  useEffect(() => {
    const incoming = app.payload?.incoming_word as string | undefined;
    if (incoming && incoming !== selectedWord) {
      handleSelectWord(incoming);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.payload?.incoming_word]);

  // Centralized word selection: updates UI state + history + bubbles up to the shell
  // so the right-side Hermes picks up the word as its english context.
  const handleSelectWord = useCallback((word: string) => {
    const normalized = String(word || '').trim().toLowerCase();
    if (!normalized) return;
    setSelectedWord((prev) => {
      if (prev === normalized) return prev;
      setHistory((h) => {
        const baseIndex = currentIndex >= 0 ? currentIndex : h.length - 1;
        const next = [...h.slice(0, baseIndex + 1), normalized];
        setCurrentIndex(next.length - 1);
        return next;
      });
      return normalized;
    });
    void Promise.resolve(onEvent(app.app_id, 'english.word_select', { word: normalized })).catch(() => undefined);
  }, [app.app_id, onEvent, currentIndex]);

  const handleBack = useCallback(() => {
    if (currentIndex > 0) {
      const idx = currentIndex - 1;
      setCurrentIndex(idx);
      const w = history[idx];
      setSelectedWord(w);
      onEvent(app.app_id, 'english.word_select', { word: w });
    }
  }, [currentIndex, history, app.app_id, onEvent]);

  const handleForward = useCallback(() => {
    if (currentIndex < history.length - 1) {
      const idx = currentIndex + 1;
      setCurrentIndex(idx);
      const w = history[idx];
      setSelectedWord(w);
      onEvent(app.app_id, 'english.word_select', { word: w });
    }
  }, [currentIndex, history, app.app_id, onEvent]);

  const toggleMode = useCallback(() => {
    setMode((m) => (m === 'immersive' ? 'dashboard' : 'immersive'));
  }, []);

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%', background: 'var(--ew-bg-main, #000)', overflow: 'hidden' }}>
      {mode === 'dashboard' ? (
        <DashboardMode
          selectedWord={selectedWord}
          isLeftSidebarOpen={isLeftSidebarOpen}
          onToggleSidebar={() => setIsLeftSidebarOpen((v) => !v)}
          onOpenSidebar={() => setIsLeftSidebarOpen(true)}
          onSelectWord={handleSelectWord}
          onBack={handleBack}
          onForward={handleForward}
          canBack={currentIndex > 0}
          canForward={currentIndex < history.length - 1}
          onToggleMode={toggleMode}
          onOpenStats={() => setMode('stats')}
          onOpenQuiz={() => setMode('quiz')}
        />
      ) : mode === 'stats' ? (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid #262626', background: 'var(--ew-bg-panel, #0a0a0a)' }}>
            <button
              onClick={() => setMode('dashboard')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, background: 'transparent', color: 'var(--ew-text-3, #a3a3a3)' }}
              title="返回单词工作区"
            >
              <ChevronLeft size={14} /> 返回工作区
            </button>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <EnglishDashboard sessionContext={sessionContext} />
          </div>
        </div>
      ) : mode === 'quiz' ? (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid #262626', background: 'var(--ew-bg-panel, #0a0a0a)' }}>
            <button
              onClick={() => setMode('dashboard')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, background: 'transparent', color: 'var(--ew-text-3, #a3a3a3)' }}
              title="返回单词工作区"
            >
              <ChevronLeft size={14} /> 返回工作区
            </button>
            <span style={{ fontSize: 13, color: 'var(--ew-text-2, #d4d4d4)', fontWeight: 500 }}>
              {selectedWord ? `测验 · ${selectedWord}` : '单词测验'}
            </span>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto', background: 'var(--ew-bg-panel, #0a0a0a)' }}>
            <QuizPanel word={selectedWord} />
          </div>
        </div>
      ) : (
        <ImmersiveMode
          selectedWord={selectedWord}
          onSelectWord={handleSelectWord}
          onToggleMode={toggleMode}
          onBack={handleBack}
          onForward={handleForward}
          canBack={currentIndex > 0}
          canForward={currentIndex < history.length - 1}
        />
      )}
    </div>
  );
}

// ── Dashboard mode: three resizable columns ───────────────────────────────

interface DashboardProps {
  selectedWord: string | null;
  isLeftSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenSidebar: () => void;
  onSelectWord: (word: string) => void;
  onBack: () => void;
  onForward: () => void;
  canBack: boolean;
  canForward: boolean;
  onToggleMode: () => void;
  onOpenStats: () => void;
  onOpenQuiz: () => void;
}

function DashboardMode({
  selectedWord, isLeftSidebarOpen, onToggleSidebar, onOpenSidebar, onSelectWord, onBack, onForward, canBack, canForward, onToggleMode, onOpenStats, onOpenQuiz,
}: DashboardProps) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    <PanelGroup direction="horizontal" style={{ flex: 1, minHeight: 0 }}>
      {/* Left column: Word List */}
      {isLeftSidebarOpen ? (
        <>
          <Panel defaultSize={20} minSize={15} maxSize={32} style={{ background: 'var(--ew-bg-panel, #0a0a0a)' }}>
            <div style={{ height: '100%', borderRight: '1px solid #171717' }}>
              <WordList onWordSelect={onSelectWord} selectedWord={selectedWord} />
            </div>
          </Panel>
          <PanelResizeHandle style={resizeHandleStyle} />
        </>
      ) : null}

      {/* Middle column: Word Detail + history nav */}
      <Panel defaultSize={40} minSize={28} style={{ background: 'var(--ew-bg-panel, #0a0a0a)' }}>
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', borderRight: '1px solid #171717' }}>
          {/* Nav header */}
          <div style={{
            height: 44, flexShrink: 0, borderBottom: '1px solid #171717',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0 10px', background: 'var(--ew-bg-header, rgba(10,10,10,0.6))', backdropFilter: 'blur(8px)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {isLeftSidebarOpen ? (
                <button onClick={onToggleSidebar} style={navBtnStyle} title="收起词库">
                  <PanelLeftOpen size={16} style={{ transform: 'scaleX(-1)' }} />
                </button>
              ) : (
                <button onClick={onOpenSidebar} style={navBtnStyle} title="展开词库">
                  <PanelLeftOpen size={16} />
                </button>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 2, background: 'var(--ew-bg-active, rgba(23,23,23,0.6))', borderRadius: 8, padding: 2, border: '1px solid #262626' }}>
                <button onClick={onBack} disabled={!canBack} style={navArrowStyle(canBack)} title="上一个">
                  <ChevronLeft size={16} />
                </button>
                <button onClick={onForward} disabled={!canForward} style={navArrowStyle(canForward)} title="下一个">
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
            {/* Right side: english-context hint + stats entry */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {selectedWord ? (
                <span style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  fontSize: 11, color: '#c4b5fd', maxWidth: 180,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }} title={`在右侧导师对话中讨论 ${selectedWord}`}>
                  <MessageSquareText size={11} style={{ flexShrink: 0 }} />
                  右侧讨论：<strong style={{ color: 'var(--ew-text-1, #fff)', fontWeight: 600 }}>{selectedWord}</strong>
                </span>
              ) : null}
            </div>
          </div>
          {/* Word detail body — scrollable. WordDetail uses min-height so its content
              can grow taller than the viewport and actually scroll here. */}
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <WordDetail word={selectedWord} onWordClick={onSelectWord} />
          </div>
        </div>
      </Panel>

      <PanelResizeHandle style={resizeHandleStyle} />

      {/* Right column: Fission Graph */}
      <Panel defaultSize={40} minSize={28} style={{ background: 'var(--ew-bg-main, #000)', position: 'relative' }}>
        {/* Radial vignette, matching the original dashboard right column */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0,
          background: 'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)',
        }} />
        <div style={{ position: 'absolute', inset: 0 }}>
          <FissionGraph word={selectedWord} onNodeClick={onSelectWord} mode="dashboard" />
        </div>
        {/* Immersive toggle (inline, top-right) */}
        <button onClick={onToggleMode} style={immersiveToggleInlineStyle} title="进入浸润模式">
          <Monitor size={14} />
          <span>Immersive</span>
        </button>
      </Panel>
    </PanelGroup>

    {/* Bottom toolbar — restores the original ThreeColumnLayout global footer actions:
        stats, quiz, immersive. Keeps the english module self-contained (only the
        tutor chat / agent is handled by the shell-level Hermes on the right). */}
    <div style={{
      flexShrink: 0, height: 40, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 14px', borderTop: '1px solid #171717', background: 'var(--ew-bg-panel, #0a0a0a)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button onClick={onOpenStats} style={footerBtnStyle} title="英语学习统计">
          <BarChart3 size={14} />
          <span>统计</span>
        </button>
        <button onClick={onOpenQuiz} style={footerBtnStyle} title="单词测验">
          <BrainCircuit size={14} />
          <span>测验</span>
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button onClick={onToggleMode} style={footerBtnStyle} title="进入浸润模式">
          <Monitor size={14} />
          <span>Immersive</span>
        </button>
      </div>
    </div>
    </div>
  );
}

// ── Immersive mode: full-bleed graph + floating draggable windows ──────────
// 1:1 restoration of the original /immersive route: the FissionGraph becomes a
// full-screen background and WordList + WordDetail become floating, draggable,
// resizable, minimizable glassmorphism windows over it.

interface ImmersiveProps {
  selectedWord: string | null;
  onSelectWord: (word: string) => void;
  onToggleMode: () => void;
  onBack: () => void;
  onForward: () => void;
  canBack: boolean;
  canForward: boolean;
}

function ImmersiveMode({ selectedWord, onSelectWord, onToggleMode, onBack, onForward, canBack, canForward }: ImmersiveProps) {
  const [showList, setShowList] = useState(true);
  const [showDetail, setShowDetail] = useState(true);

  return (
    <div style={{ position: 'absolute', inset: 0, background: 'var(--ew-bg-main, #000)', overflow: 'hidden' }}>
      {/* Background fission graph */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
        <FissionGraph word={selectedWord} onNodeClick={onSelectWord} mode="immersive" />
      </div>

      {/* Floating: Word List */}
      {showList ? (
        <DraggableWindow
          title="Word Library"
          initialPosition={{ x: 32, y: 32 }}
          initialSize={{ width: 320, height: 600 }}
          onClose={() => setShowList(false)}
        >
          <WordList onWordSelect={onSelectWord} selectedWord={selectedWord} />
        </DraggableWindow>
      ) : null}

      {/* Floating: Word Detail — with history back/forward in the header */}
      {showDetail ? (
        <DraggableWindow
          title={selectedWord ?? 'Word Details'}
          initialPosition={{ x: 376, y: 32 }}
          initialSize={{ width: 500, height: 600 }}
          onClose={() => setShowDetail(false)}
          headerActions={
            <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <button
                onClick={onBack}
                disabled={!canBack}
                style={immersiveNavArrowStyle(canBack)}
                title="Back"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={onForward}
                disabled={!canForward}
                style={immersiveNavArrowStyle(canForward)}
                title="Forward"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          }
        >
          <div style={{ height: '100%', overflow: 'auto' }}>
            <WordDetail word={selectedWord} onWordClick={onSelectWord} />
          </div>
        </DraggableWindow>
      ) : null}

      {/* Re-open buttons (mirrors the original "Show Library" / "Show Details") */}
      <div style={{ position: 'absolute', bottom: 24, left: 24, display: 'flex', gap: 8, zIndex: 40 }}>
        {!showList ? (
          <button onClick={() => setShowList(true)} style={reopenBtnStyle}>显示词库</button>
        ) : null}
        {!showDetail ? (
          <button onClick={() => setShowDetail(true)} style={reopenBtnStyle}>显示详情</button>
        ) : null}
      </div>

      {/* Exit immersive (floating, bottom-right) */}
      <button onClick={onToggleMode} style={immersiveExitStyle} title="退出浸润模式">
        <LayoutDashboard size={22} />
      </button>
    </div>
  );
}

// ── DraggableWindow — 1:1 port of the original DraggableContainer ──────────
// Supports: drag (via header), 8-direction resize (edges + corners), minimize
// (collapses to a pill), and Apple-style glassmorphism. Uses Pointer Events so
// it works on touch + mouse without separate code paths.

interface DraggableWindowProps {
  title: string;
  initialPosition?: { x: number; y: number };
  initialSize?: { width: number; height: number };
  onClose?: () => void;
  minWidth?: number;
  minHeight?: number;
  headerActions?: React.ReactNode;
  children: React.ReactNode;
}

function DraggableWindow({
  title,
  initialPosition = { x: 20, y: 20 },
  initialSize = { width: 400, height: 600 },
  onClose,
  minWidth = 280,
  minHeight = 200,
  headerActions,
  children,
}: DraggableWindowProps) {
  const [pos, setPos] = useState(initialPosition);
  const [size, setSize] = useState(initialSize);
  const [isMinimized, setIsMinimized] = useState(false);
  // A single interaction ref holds whichever drag/resize is in progress, so we
  // only bind one set of window listeners at a time.
  const interaction = useRef<null | {
    kind: 'drag' | 'resize';
    dir?: string;
    startX: number; startY: number;
    baseX: number; baseY: number; baseW: number; baseH: number;
    pointerId: number;
  }>(null);

  const onInteractionMove = useCallback((e: PointerEvent) => {
    const it = interaction.current;
    if (!it || e.pointerId !== it.pointerId) return;
    const dx = e.clientX - it.startX;
    const dy = e.clientY - it.startY;
    if (it.kind === 'drag') {
      setPos({ x: it.baseX + dx, y: it.baseY + dy });
      return;
    }
    // resize — mirror the original DraggableContainer direction math
    let newW = it.baseW, newH = it.baseH, newX = it.baseX, newY = it.baseY;
    const dir = it.dir ?? '';
    if (dir.includes('e')) newW = Math.max(minWidth, it.baseW + dx);
    if (dir.includes('s')) newH = Math.max(minHeight, it.baseH + dy);
    if (dir.includes('w')) {
      const possible = it.baseW - dx;
      if (possible >= minWidth) { newW = possible; newX = it.baseX + dx; }
    }
    if (dir.includes('n')) {
      const possible = it.baseH - dy;
      if (possible >= minHeight) { newH = possible; newY = it.baseY + dy; }
    }
    setSize({ width: newW, height: newH });
    setPos({ x: newX, y: newY });
  }, [minWidth, minHeight]);

  const onInteractionUp = useCallback((e: PointerEvent) => {
    const it = interaction.current;
    if (!it || e.pointerId !== it.pointerId) return;
    interaction.current = null;
    window.removeEventListener('pointermove', onInteractionMove);
    window.removeEventListener('pointerup', onInteractionUp);
    window.removeEventListener('pointercancel', onInteractionUp);
  }, [onInteractionMove]);

  const startDrag = (e: React.PointerEvent) => {
    // Don't start a drag when clicking header buttons / actions.
    const target = e.target as HTMLElement;
    if (target.closest('button')) return;
    e.preventDefault();
    interaction.current = {
      kind: 'drag', startX: e.clientX, startY: e.clientY,
      baseX: pos.x, baseY: pos.y, baseW: size.width, baseH: size.height, pointerId: e.pointerId,
    };
    window.addEventListener('pointermove', onInteractionMove);
    window.addEventListener('pointerup', onInteractionUp);
    window.addEventListener('pointercancel', onInteractionUp);
  };

  const startResize = (e: React.PointerEvent, dir: string) => {
    e.stopPropagation();
    e.preventDefault();
    interaction.current = {
      kind: 'resize', dir, startX: e.clientX, startY: e.clientY,
      baseX: pos.x, baseY: pos.y, baseW: size.width, baseH: size.height, pointerId: e.pointerId,
    };
    window.addEventListener('pointermove', onInteractionMove);
    window.addEventListener('pointerup', onInteractionUp);
    window.addEventListener('pointercancel', onInteractionUp);
  };

  useEffect(() => {
    return () => {
      // Clean up any stray listeners if the window unmounts mid-drag.
      window.removeEventListener('pointermove', onInteractionMove);
      window.removeEventListener('pointerup', onInteractionUp);
      window.removeEventListener('pointercancel', onInteractionUp);
    };
  }, [onInteractionMove, onInteractionUp]);

  // Minimized state: collapse to a draggable pill (matches the original look).
  if (isMinimized) {
    return (
      <div
        onPointerDown={startDrag}
        onClick={() => setIsMinimized(false)}
        style={{
          position: 'absolute', left: pos.x, top: pos.y, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
          borderRadius: 14, cursor: 'pointer',
          background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255,255,255,0.2)',
          boxShadow: '0 20px 40px -10px rgba(0,0,0,0.5)',
        }}
      >
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: 'rgba(234,179,8,0.85)' }} />
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ew-text-1, rgba(255,255,255,0.9))' }}>{title}</span>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'absolute', left: pos.x, top: pos.y, width: size.width, height: size.height,
        zIndex: 40, display: 'flex', flexDirection: 'column', borderRadius: 16, overflow: 'hidden',
        // Apple-style glassmorphism — more transparent than the dashboard so the
        // background fission graph shows through, with stronger blur + saturation.
        background: 'rgba(20,20,20,0.25)', backdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(255,255,255,0.08)',
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
      }}
    >
      {/* Header bar */}
      <div
        onPointerDown={startDrag}
        style={{
          height: 44, flexShrink: 0, cursor: 'grab', userSelect: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 12px', borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: 'linear-gradient(180deg, rgba(255,255,255,0.05), transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          {headerActions ? (
            <div onPointerDown={(e) => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center' }}>
              {headerActions}
            </div>
          ) : null}
          <span style={{
            fontSize: 13, fontWeight: 600, color: 'var(--ew-text-1, rgba(255,255,255,0.9))', letterSpacing: '0.02em',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {title}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button
            onClick={() => setIsMinimized(true)}
            onPointerDown={(e) => e.stopPropagation()}
            style={headerBtnStyle}
            title="最小化"
          >
            <Minimize2 size={14} />
          </button>
          {onClose ? (
            <button
              onClick={onClose}
              onPointerDown={(e) => e.stopPropagation()}
              style={{ ...headerBtnStyle, color: 'var(--ew-text-3, rgba(255,255,255,0.6))' }}
              title="关闭"
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.2)'; e.currentTarget.style.color = '#f87171'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--ew-text-3, rgba(255,255,255,0.6))'; }}
            >
              <X size={14} />
            </button>
          ) : null}
        </div>
      </div>
      {/* Content */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {children}
      </div>
      {/* Resize handles — 4 edges + 4 corners, matching the original */}
      <div onPointerDown={(e) => startResize(e, 'n')} style={{ ...resizeEdgeStyle, top: 0, left: 0, width: '100%', height: 4, cursor: 'n-resize' }} />
      <div onPointerDown={(e) => startResize(e, 's')} style={{ ...resizeEdgeStyle, bottom: 0, left: 0, width: '100%', height: 4, cursor: 's-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'w')} style={{ ...resizeEdgeStyle, top: 0, left: 0, width: 4, height: '100%', cursor: 'w-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'e')} style={{ ...resizeEdgeStyle, top: 0, right: 0, width: 4, height: '100%', cursor: 'e-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'nw')} style={{ ...resizeCornerStyle, top: 0, left: 0, cursor: 'nw-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'ne')} style={{ ...resizeCornerStyle, top: 0, right: 0, cursor: 'ne-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'sw')} style={{ ...resizeCornerStyle, bottom: 0, left: 0, cursor: 'sw-resize' }} />
      <div onPointerDown={(e) => startResize(e, 'se')} style={{ ...resizeCornerStyle, bottom: 0, right: 0, cursor: 'se-resize' }} />
    </div>
  );
}

// ── Shared styles ──────────────────────────────────────────────────────────

const resizeHandleStyle: React.CSSProperties = {
  width: 4,
  background: 'var(--ew-bg-card, #171717)',
  cursor: 'col-resize',
  transition: 'background 0.15s',
};

const navBtnStyle: React.CSSProperties = {
  padding: 6, borderRadius: 8, border: 'none', cursor: 'pointer',
  background: 'transparent', color: 'var(--ew-text-faint, #737373)', display: 'flex', alignItems: 'center',
  transition: 'color 0.15s, background 0.15s',
};

const navArrowStyle = (enabled: boolean): React.CSSProperties => ({
  padding: 4, borderRadius: 6, border: 'none', cursor: enabled ? 'pointer' : 'not-allowed',
  background: 'transparent', color: enabled ? 'var(--ew-text-3, #a3a3a3)' : 'var(--ew-border-hi, #404040)',
  display: 'flex', alignItems: 'center', transition: 'color 0.15s, background 0.15s',
});

// Bottom toolbar button style — restores the original ThreeColumnLayout footer
// action look: compact, muted, hover-brightens.
const footerBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px',
  borderRadius: 8, border: '1px solid #262626', background: 'var(--ew-bg-active, rgba(23,23,23,0.6))',
  color: 'var(--ew-text-3, #a3a3a3)', fontSize: 12, cursor: 'pointer', transition: 'color 0.15s, background 0.15s',
};

// Immersive floating-window header button (minimize / close).
const headerBtnStyle: React.CSSProperties = {
  width: 28, height: 28, padding: 0, border: 'none', borderRadius: 999,
  background: 'transparent', color: 'var(--ew-text-3, rgba(255,255,255,0.6))', cursor: 'pointer',
  display: 'grid', placeItems: 'center', transition: 'background 0.15s, color 0.15s',
};

// Immersive history nav arrows (back/forward in the WordDetail floating window).
const immersiveNavArrowStyle = (enabled: boolean): React.CSSProperties => ({
  width: 26, height: 26, padding: 0, border: 'none', borderRadius: 999,
  background: 'transparent', color: enabled ? 'var(--ew-text-2, rgba(255,255,255,0.85))' : 'rgba(255,255,255,0.2)',
  cursor: enabled ? 'pointer' : 'not-allowed', display: 'grid', placeItems: 'center',
  transition: 'background 0.15s',
});

// Resize handle styles for the floating windows — edges are thin strips, corners
// are slightly larger hit areas, matching the original DraggableContainer.
const resizeEdgeStyle: React.CSSProperties = {
  position: 'absolute', zIndex: 50, pointerEvents: 'auto',
};
const resizeCornerStyle: React.CSSProperties = {
  position: 'absolute', width: 16, height: 16, zIndex: 50, pointerEvents: 'auto',
};

const immersiveToggleInlineStyle: React.CSSProperties = {
  position: 'absolute', top: 12, right: 12, zIndex: 20,
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '6px 12px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.12)',
  background: 'rgba(10,10,10,0.7)', backdropFilter: 'blur(10px)',
  color: 'var(--ew-text-3, #a3a3a3)', fontSize: 12, cursor: 'pointer', transition: 'color 0.15s',
};

const reopenBtnStyle: React.CSSProperties = {
  padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
  background: 'rgba(10,10,10,0.7)', backdropFilter: 'blur(10px)',
  color: 'var(--ew-text-1, #fff)', fontSize: 13, cursor: 'pointer',
};

const immersiveExitStyle: React.CSSProperties = {
  position: 'absolute', bottom: 24, right: 24, zIndex: 50,
  width: 52, height: 52, borderRadius: '50%', border: 'none', cursor: 'pointer',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'var(--ew-text-1, #fff)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  boxShadow: '0 10px 30px -5px rgba(99,102,241,0.5)',
};
