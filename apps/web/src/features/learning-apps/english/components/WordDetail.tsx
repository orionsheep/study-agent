import { useEffect, useState, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkBreaks from 'remark-breaks';
import { ArrowDown, StickyNote, Sparkles } from 'lucide-react';

interface WordDetailProps {
  word: string | null;
  onWordClick?: (word: string) => void;
  onNextWord?: () => void;
  onPrevWord?: () => void;
}

interface ChineseData {
  word: string;
  pronunciation?: string;
  phonetic?: string;
  concise_definition?: string;
  forms?: Record<string, string>;
  definitions?: Array<{
    pos: string;
    explanation_en: string;
    explanation_cn: string;
    example_en: string;
    example_cn: string;
  }>;
  comparison?: Array<{
    word_to_compare: string;
    analysis: string;
  }>;
  collins?: string;
}

export default function WordDetail({ word, onWordClick, onNextWord, onPrevWord }: WordDetailProps) {
  const [content, setContent] = useState<string | null>(null);
  const [chineseData, setChineseData] = useState<ChineseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAddNote, setShowAddNote] = useState(false);
  const [myNotes, setMyNotes] = useState<{ id: string; content: string; createdAt: string }[]>([]);
  const notesRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const requestSeqRef = useRef(0);
  const onWordClickRef = useRef(onWordClick);

  useEffect(() => {
    onWordClickRef.current = onWordClick;
  }, [onWordClick]);

  // Fetch user's own notes for this word
  const fetchMyNotes = useCallback(async () => {
    if (!word) return;
    try {
      const res = await fetch(`/api/english/notes?word=${encodeURIComponent(word)}`);
      if (res.ok) {
        const data = await res.json();
        setMyNotes(data || []);
      } else {
        setMyNotes([]);
      }
    } catch (error) {
      console.error('Failed to fetch notes:', error);
      setMyNotes([]);
    }
  }, [word]);

  useEffect(() => {
    fetchMyNotes();
  }, [fetchMyNotes]);

  useEffect(() => {
    if (!word) {
      setContent(null);
      setChineseData(null);
      return;
    }

    const controller = new AbortController();
    const requestSeq = ++requestSeqRef.current;
    const fetchDetail = async () => {
      setLoading(true);
      setContent(null);
      setChineseData(null);
      try {
        const res = await fetch(`/api/english/words/${encodeURIComponent(word)}`, { signal: controller.signal });
        if (requestSeq !== requestSeqRef.current) return;
        if (res.ok) {
          const data = await res.json();
          if (requestSeq !== requestSeqRef.current) return;
          // Process Markdown content
          let processed = data.content || '';
          processed = processed.replace(/\[\[(.*?)\]\]/g, (_: string, p1: string) => {
            return `[${p1}](#${p1})`;
          });
          setContent(processed);
          setChineseData(data.chinese || null);
        } else {
          setContent(`# 未找到单词"${word}"`);
          setChineseData(null);
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error('Failed to fetch detail', error);
        setContent('# 加载出错');
      } finally {
        if (requestSeq === requestSeqRef.current) setLoading(false);
      }
    };

    fetchDetail();
    return () => controller.abort();
  }, [word]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const key = e.key.toLowerCase();
      if (key === 'j') {
        e.preventDefault();
        playAudio('US');
      } else if (key === 'k') {
        e.preventDefault();
        playAudio('UK');
      } else if (key === 'arrowup' || key === 'w') {
        e.preventDefault();
        if (onPrevWord) onPrevWord();
      } else if (key === 'arrowdown' || key === 's') {
        e.preventDefault();
        if (onNextWord) onNextWord();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [word, onNextWord, onPrevWord]);

  const selectLinkedWord = (target: EventTarget & HTMLElement) => {
    const href = target.getAttribute('data-href') || target.getAttribute('href') || '';
    const text = target.textContent || '';
    const rawTarget = href.startsWith('#')
      ? href.substring(1)
      : href.startsWith('/')
        ? href.split('/').filter(Boolean).pop() || ''
        : href && !/^https?:\/\//i.test(href)
          ? href
          : text;
    const targetWord = decodeURIComponent(rawTarget).replace(/^#/, '').trim().replace(/[，,.;；:：]+$/g, '');
    if (!targetWord) return false;
    onWordClickRef.current?.(targetWord);
    return true;
  };

  const handleLinkClick = (e: React.MouseEvent<HTMLElement>) => {
    e.preventDefault();
    e.stopPropagation();
    selectLinkedWord(e.currentTarget);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handleNativeLinkClick = (event: MouseEvent | PointerEvent) => {
      const rawTarget = event.target;
      const targetElement = rawTarget instanceof Element ? rawTarget : rawTarget instanceof Node ? rawTarget.parentElement : null;
      const link = targetElement?.closest<HTMLElement>('[data-word-link="true"]');
      if (!link) return;
      event.preventDefault();
      event.stopPropagation();
      selectLinkedWord(link);
    };
    container.addEventListener('click', handleNativeLinkClick, true);
    container.addEventListener('pointerup', handleNativeLinkClick, true);
    return () => {
      container.removeEventListener('click', handleNativeLinkClick, true);
      container.removeEventListener('pointerup', handleNativeLinkClick, true);
    };
  // Rebind when the detail view swaps between the empty/loading/content DOM.
  // On the initial empty state containerRef is null, so a one-time listener misses
  // all later markdown links.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [word, content]);

  const scrollToNotes = () => {
    notesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const playAudio = (type: 'US' | 'UK') => {
    if (!word) return;
    const audioType = type === 'US' ? 2 : 1;
    const primaryUrl = `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=${audioType}`;
    const audio = new Audio();
    audio.addEventListener('canplaythrough', () => {
      audio.play().catch((err) => console.error('Audio playback failed:', err));
    });
    audio.addEventListener('error', () => {
      const fallbackUrl = `https://ssl.gstatic.com/dictionary/static/sounds/oxford/${word.toLowerCase()}--_${type.toLowerCase()}_1.mp3`;
      const fallbackAudio = new Audio(fallbackUrl);
      fallbackAudio.play().catch((err) => {
        console.error('Fallback audio also failed:', err);
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(word);
          utterance.lang = type === 'UK' ? 'en-GB' : 'en-US';
          window.speechSynthesis.speak(utterance);
        }
      });
    });
    audio.src = primaryUrl;
    audio.load();
  };

  const renderCollinsStars = (collins: string | undefined) => {
    if (!collins) return null;
    const stars = parseInt(collins);
    if (isNaN(stars) || stars <= 0) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 2, marginLeft: 8 }} title={`柯林斯星级: ${stars}`}>
        {[...Array(stars)].map((_, i) => (
          <svg key={i} style={{ width: 14, height: 14, color: '#eab308', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ))}
      </div>
    );
  };

  if (!word) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-faint)',
          fontWeight: 300,
          letterSpacing: '0.05em',
          background: 'var(--bg-1)',
        }}
      >
        选择一个单词查看详情
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-1)',
        color: '#e5e5e5',
      }}
    >
      {/* Header with Word Title */}
      <div style={{ padding: '24px 24px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 style={{ fontSize: 36, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.02em', margin: 0 }}>
              {word}
            </h1>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => playAudio('US')}
              style={{
                padding: '8px 12px',
                borderRadius: 9999,
                background: 'var(--glass-border)',
                color: 'var(--text-3)',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 12,
                transition: 'all 0.15s',
              }}
              title="美式发音 (J)"
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--glass-border)'; e.currentTarget.style.color = '#60a5fa'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--glass-border)'; e.currentTarget.style.color = 'var(--text-3)'; }}
            >
              <span style={{ fontWeight: 700 }}>US</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              </svg>
            </button>
            <button
              onClick={() => playAudio('UK')}
              style={{
                padding: '8px 12px',
                borderRadius: 9999,
                background: 'var(--glass-border)',
                color: 'var(--text-3)',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 12,
                transition: 'all 0.15s',
              }}
              title="英式发音 (K)"
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--glass-border)'; e.currentTarget.style.color = '#f87171'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--glass-border)'; e.currentTarget.style.color = 'var(--text-3)'; }}
            >
              <span style={{ fontWeight: 700 }}>UK</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              </svg>
            </button>
          </div>
        </div>

        {/* Pronunciation & Concise Definition */}
        {chineseData && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-3)', fontFamily: 'monospace', fontSize: 14, marginBottom: 8 }}>
              <span>/{chineseData.phonetic || chineseData.pronunciation}/</span>
              {renderCollinsStars(chineseData.collins)}
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ flex: 1, fontSize: 18, color: '#d4d4d4', fontWeight: 500 }}>
                {chineseData.concise_definition}
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <button
                  onClick={() => setShowAddNote(!showAddNote)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 8px',
                    borderRadius: 6,
                    fontSize: 12,
                    border: '1px solid var(--glass-border)',
                    background: showAddNote ? '#2563eb' : 'var(--glass-border)',
                    color: showAddNote ? 'var(--text-1)' : 'var(--text-3)',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s',
                  }}
                >
                  <MessageSquarePlus size={12} />
                  <span>{showAddNote ? '收起' : '笔记'}</span>
                </button>
                <button
                  onClick={scrollToNotes}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 8px',
                    borderRadius: 6,
                    fontSize: 12,
                    border: '1px solid var(--glass-border)',
                    background: 'var(--glass-border)',
                    color: 'var(--text-3)',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-1)'; e.currentTarget.style.borderColor = 'var(--glass-border-hi)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-3)'; e.currentTarget.style.borderColor = 'var(--glass-border)'; }}
                >
                  <ArrowDown size={12} />
                  <span>查看笔记</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Scrollable Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '24px 24px 32px' }}>
        {/* Markdown Content */}
        {loading && (
          <div style={{ marginBottom: 24, color: 'var(--text-faint)', fontSize: 14 }}>
            加载 {word} 中...
          </div>
        )}
        {content && (
          <div
            className="english-markdown"
            onClickCapture={(e) => {
              const target = (e.target as HTMLElement).closest<HTMLElement>('[data-word-link="true"]');
              if (!target) return;
              e.preventDefault();
              e.stopPropagation();
              selectLinkedWord(target);
            }}
            style={{ marginBottom: 32 }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkBreaks]}
              rehypePlugins={[rehypeRaw]}
              components={{
                a: (props) => (
                  <button
                    type="button"
                    data-word-link="true"
                    data-href={props.href}
                    onClick={handleLinkClick}
                    onPointerDown={(e) => {
                      e.stopPropagation();
                    }}
                    style={{
                      color: '#60a5fa',
                      background: 'transparent',
                      border: 0,
                      padding: 0,
                      margin: 0,
                      font: 'inherit',
                      textDecoration: 'none',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none'; }}
                  >
                    {props.children}
                  </button>
                ),
                small: (props) => (
                  <span {...props} style={{ fontSize: 10, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700, margin: '0 4px' }} />
                ),
                p: (props) => (
                  <div {...props} style={{ marginBottom: 8, color: '#d4d4d4', lineHeight: 1.75 }} />
                ),
                strong: (props) => (
                  <strong {...props} style={{ color: '#fef08a', fontWeight: 700 }} />
                ),
                em: (props) => (
                  <em {...props} style={{ color: 'var(--text-3)' }} />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {/* Word Forms */}
        {chineseData?.forms && Object.keys(chineseData.forms).length > 0 && (
          <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: 24, marginBottom: 32 }}>
            <h3 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-1)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 4, height: 24, background: 'var(--text-1)', borderRadius: 4 }} />
              词形变化
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {Object.entries(chineseData.forms).map(([key, value]) => (
                <div
                  key={key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: 'rgba(23, 23, 23, 0.5)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 6,
                    padding: '8px 12px',
                  }}
                >
                  <span style={{ color: 'var(--text-faint)', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginRight: 8 }}>
                    {key}
                  </span>
                  <span style={{ color: '#e5e5e5', fontWeight: 500 }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Detailed Definitions */}
        {chineseData?.definitions && chineseData.definitions.length > 0 && (
          <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: 24, marginBottom: 32 }}>
            <h3 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-1)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 4, height: 24, background: '#3b82f6', borderRadius: 4 }} />
              详细释义
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {chineseData.definitions.map((def, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(23, 23, 23, 0.3)',
                    borderRadius: 8,
                    padding: 16,
                    border: '1px solid var(--glass-border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        background: 'var(--glass-border)',
                        color: 'var(--text-3)',
                        fontSize: 11,
                        borderRadius: 4,
                        textTransform: 'uppercase',
                        fontWeight: 700,
                        letterSpacing: '0.05em',
                      }}
                    >
                      {def.pos}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                      <p style={{ color: '#e5e5e5', margin: '0 0 4px' }}>{def.explanation_en}</p>
                      <p style={{ color: 'var(--text-faint)', fontSize: 14, margin: 0 }}>{def.explanation_cn}</p>
                    </div>
                    <div style={{ paddingLeft: 12, borderLeft: '2px solid var(--glass-border-hi)' }}>
                      <p style={{ color: '#d4d4d4', fontStyle: 'italic', margin: '0 0 4px' }}>"{def.example_en}"</p>
                      <p style={{ color: 'var(--text-faint)', fontSize: 14, margin: 0 }}>{def.example_cn}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Comparisons */}
        {chineseData?.comparison && chineseData.comparison.length > 0 && (
          <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: 24, marginBottom: 32 }}>
            <h3 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-1)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 4, height: 24, background: '#a855f7', borderRadius: 4 }} />
              近义词辨析
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {chineseData.comparison.map((comp, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(23, 23, 23, 0.3)',
                    borderRadius: 8,
                    padding: 16,
                    border: '1px solid var(--glass-border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
                    <span style={{ color: '#c084fc', fontWeight: 700, fontSize: 18 }}>{comp.word_to_compare}</span>
                    <span style={{ color: 'var(--text-faint)', fontSize: 14 }}>vs {word}</span>
                  </div>
                  <p style={{ color: '#d4d4d4', lineHeight: 1.7, fontSize: 14, margin: 0 }}>{comp.analysis}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes Section */}
        <div ref={notesRef} style={{ borderTop: '1px solid var(--glass-border)', paddingTop: 24, paddingBottom: 32 }}>
          <h3 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-1)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 4, height: 24, background: '#f97316', borderRadius: 4 }} />
            笔记
          </h3>
          {myNotes.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {myNotes.map((note) => (
                <div
                  key={note.id}
                  style={{
                    padding: 12,
                    background: 'rgba(30, 58, 138, 0.2)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 8,
                  }}
                >
                  <p style={{ fontSize: 14, color: '#d4d4d4', lineHeight: 1.6, whiteSpace: 'pre-wrap', margin: 0 }}>
                    {note.content}
                  </p>
                  <p style={{ fontSize: 12, color: '#525252', marginTop: 8 }}>
                    {new Date(note.createdAt).toLocaleDateString('zh-CN')}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-faint)' }}>暂无笔记</div>
          )}
        </div>
      </div>
    </div>
  );
}

// MessageSquarePlus icon component (inline to avoid missing import)
function MessageSquarePlus({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <line x1="9" y1="12" x2="15" y2="12" />
      <line x1="12" y1="9" x2="12" y2="15" />
    </svg>
  );
}
