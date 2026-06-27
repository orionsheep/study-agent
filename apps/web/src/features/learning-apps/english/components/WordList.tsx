import { useEffect, useRef, useState, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Search, Folder, ChevronLeft, CheckSquare, Square, Play, Circle, Settings } from 'lucide-react';

interface WordListProps {
  onWordSelect: (word: string) => void;
  selectedWord: string | null;
}

interface LibraryItem {
  name: string;
  type: 'file' | 'directory';
  path: string;
  source?: 'system' | 'user';
  libraryId?: string;
  wordCount?: number;
}

interface WordWithData {
  word: string;
  chineseData: {
    concise_definition?: string;
    phonetic?: string;
    collins?: string;
  } | null;
}

export default function WordList({ onWordSelect, selectedWord }: WordListProps) {
  const [words, setWords] = useState<(string | WordWithData)[]>([]);
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([]);
  const [viewMode, setViewMode] = useState<'libraries' | 'words'>('libraries');
  const [currentPath, setCurrentPath] = useState('');
  const [currentLibraryName, setCurrentLibraryName] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const parentRef = useRef<HTMLDivElement>(null);
  const [showChinese] = useState(true);
  const [showScore] = useState(true);
  const [groupSize] = useState(50);

  const [groups, setGroups] = useState<{ index: number; label: string }[]>([]);
  const [selectedGroupIndex, setSelectedGroupIndex] = useState<number>(-1);
  const [sortBy, setSortBy] = useState<'default' | 'familiarity_asc' | 'familiarity_desc'>('default');
  const [progress, setProgress] = useState<Record<string, number>>({});
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedWordsForQuiz, setSelectedWordsForQuiz] = useState<Set<string>>(new Set());

  // Fetch progress on mount
  useEffect(() => {
    fetch('/api/english/user/progress', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setProgress(data))
      .catch(() => setProgress({}));
  }, []);

  // Fetch library items when currentPath changes
  useEffect(() => {
    const fetchLibraryItems = async () => {
      if (viewMode !== 'libraries') return;
      try {
        const res = await fetch(`/api/english/libraries?path=${encodeURIComponent(currentPath)}`);
        if (res.ok) {
          const data = await res.json();
          setLibraryItems(data);
        }
      } catch (error) {
        console.error('Failed to fetch library items', error);
      }
    };
    fetchLibraryItems();
  }, [currentPath, viewMode]);

  // Fetch groups when a library is selected
  useEffect(() => {
    const fetchGroups = async () => {
      if (viewMode === 'words' && currentPath && !searchQuery) {
        try {
          let url;
          if (currentPath.startsWith('user:')) {
            const libraryId = currentPath.replace('user:', '');
            url = `/api/english/user/libraries/${libraryId}/groups?groupSize=${groupSize}`;
          } else {
            url = `/api/english/library-groups?path=${encodeURIComponent(currentPath)}&groupSize=${groupSize}`;
          }
          const res = await fetch(url);
          if (res.ok) {
            const data = await res.json();
            if (data.groups) {
              const formattedGroups = data.groups.map((g: any) => ({ index: g.index, label: g.name }));
              setGroups(formattedGroups);
            } else {
              setGroups(data);
            }
          }
        } catch (error) {
          console.error('Failed to fetch groups', error);
        }
      } else {
        setGroups([]);
      }
    };
    fetchGroups();
  }, [currentPath, viewMode, searchQuery, groupSize]);

  // Fetch words based on search or selected library
  useEffect(() => {
    const fetchWords = async () => {
      setLoading(true);
      try {
        let url = '/api/english/words';
        if (searchQuery) {
          url = `/api/english/words?query=${encodeURIComponent(searchQuery)}&includeDefinitions=${showChinese}`;
        } else if (viewMode === 'libraries') {
          setLoading(false);
          return;
        } else if (currentPath) {
          if (currentPath.startsWith('user:')) {
            const libraryId = currentPath.replace('user:', '');
            url = `/api/english/user/libraries/${libraryId}/words?groupIndex=${selectedGroupIndex}&groupSize=${groupSize}&includeDefinitions=${showChinese}`;
          } else {
            url = `/api/english/library-words?path=${encodeURIComponent(currentPath)}&groupIndex=${selectedGroupIndex}&groupSize=${groupSize}&includeDefinitions=${showChinese}`;
          }
        }
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data.words) {
            if (showChinese && data.words.length > 0 && data.words[0].chineseData) {
              setWords(data.words.map((w: any) => ({ word: w.word, chineseData: w.chineseData })));
            } else {
              setWords(data.words.map((w: any) => w.word || w));
            }
          } else {
            setWords(data);
          }
        }
      } catch (error) {
        console.error('Failed to fetch words', error);
      } finally {
        setLoading(false);
      }
    };
    const timeoutId = setTimeout(() => fetchWords(), 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, currentPath, viewMode, selectedGroupIndex, groupSize, showChinese]);

  // Auto-switch viewMode based on state
  useEffect(() => {
    if (searchQuery) {
      setViewMode('words');
    } else if (!currentLibraryName && !currentPath && viewMode === 'words') {
      setViewMode('libraries');
    }
  }, [searchQuery, currentLibraryName, currentPath, viewMode]);

  // Sort words
  const sortedWords = useMemo(() => {
    return [...words].sort((a, b) => {
      if (sortBy === 'default') return 0;
      const wordA = typeof a === 'string' ? a : a.word;
      const wordB = typeof b === 'string' ? b : b.word;
      const scoreA = progress[wordA] || 0;
      const scoreB = progress[wordB] || 0;
      if (sortBy === 'familiarity_asc') return scoreA - scoreB;
      return scoreB - scoreA;
    });
  }, [words, sortBy, progress]);

  const rowVirtualizer = useVirtualizer({
    count: sortedWords.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => (showChinese ? 60 : 40),
    overscan: 5,
  });

  const handleItemClick = (item: LibraryItem) => {
    setCurrentPath(item.path);
    setCurrentLibraryName(item.name.replace('.csv', ''));
    if (item.type === 'directory') {
      // 目录：进入下一层，展示目录内容（点「考试考纲」→ 列出 14 个考纲 csv：
      // 初中/高中/CET4/CET6/考研/托福/SAT，各顺序+乱序）。
      setViewMode('libraries');
    } else {
      // 文件（csv）：进入该词库的单词视图。
      setViewMode('words');
    }
    setSelectedGroupIndex(-1);
  };

  const handleBackToLibraries = () => {
    setSearchQuery('');
    const parts = currentPath.split('/');
    parts.pop();
    setCurrentPath(parts.join('/'));
    setCurrentLibraryName(null);
    setViewMode('libraries');
    setIsSelectMode(false);
    setSelectedWordsForQuiz(new Set());
  };

  const toggleSelectMode = () => {
    setIsSelectMode(!isSelectMode);
    setSelectedWordsForQuiz(new Set());
  };

  const toggleSelectAll = () => {
    if (selectedWordsForQuiz.size === sortedWords.length) {
      setSelectedWordsForQuiz(new Set());
    } else {
      setSelectedWordsForQuiz(new Set(sortedWords.map(getWordString)));
    }
  };

  const toggleWordSelection = (word: string) => {
    const newSet = new Set(selectedWordsForQuiz);
    if (newSet.has(word)) {
      newSet.delete(word);
    } else {
      newSet.add(word);
    }
    setSelectedWordsForQuiz(newSet);
  };

  const getProgressColor = (score: number | undefined) => {
    if (score === undefined) return 'var(--ew-text-3, #a3a3a3)';
    if (score >= 2) return 'var(--ew-success, #22c55e)';
    if (score === 1) return 'var(--ew-warning, #eab308)';
    return 'var(--ew-danger, #ef4444)';
  };

  const renderCollinsStars = (collins: string | undefined) => {
    if (!collins) return null;
    const stars = parseInt(collins);
    if (isNaN(stars) || stars <= 0) return null;
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 2, marginLeft: 8 }} title={`柯林斯星级: ${stars}`}>
        {[...Array(stars)].map((_, i) => (
          <svg key={i} style={{ width: 12, height: 12, color: 'var(--ew-warning, #eab308)', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ))}
      </div>
    );
  };

  const getWordString = (item: string | WordWithData) => {
    return typeof item === 'string' ? item : item.word;
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--ew-bg-panel, #0a0a0a)', borderRight: '1px solid var(--ew-border)' }}>
      {/* Search Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--ew-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {viewMode === 'words' && (
            <button
              onClick={handleBackToLibraries}
              style={{ padding: 8, color: 'var(--ew-text-3, #a3a3a3)', background: 'none', border: 'none', cursor: 'pointer', borderRadius: 8, transition: 'all 0.15s' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--ew-text-1, #fff)'; e.currentTarget.style.background = 'var(--ew-bg-hover, rgba(255,255,255,0.05))'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--ew-text-3, #a3a3a3)'; e.currentTarget.style.background = 'none'; }}
              title="返回"
            >
              <ChevronLeft size={20} />
            </button>
          )}
          <div style={{ position: 'relative', flex: 1 }}>
            <Search style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--ew-text-faint, #737373)', width: 16, height: 16, pointerEvents: 'none' }} />
            <input
              type="text"
              placeholder="搜索单词..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--ew-bg-card, #171717)',
                color: 'var(--ew-text-1, #e5e5e5)',
                paddingLeft: 36,
                paddingRight: 16,
                paddingTop: 8,
                paddingBottom: 8,
                borderRadius: 8,
                border: '1px solid var(--ew-border)',
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--ew-border-hi, #404040)'; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--ew-border, #262626)'; }}
            />
          </div>
        </div>
      </div>

      {/* Navigation Header for Words View */}
      {viewMode === 'words' && !searchQuery && currentLibraryName && (
        <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--ew-border)', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, color: 'var(--ew-text-3, #a3a3a3)', fontWeight: 500 }}>{currentLibraryName}</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{ background: 'var(--ew-bg-card, #171717)', color: 'var(--ew-text-3, #a3a3a3)', fontSize: 11, border: '1px solid var(--ew-border)', borderRadius: 4, padding: '2px 6px', outline: 'none' }}
              >
                <option value="default">默认</option>
                <option value="familiarity_asc">熟悉度升序</option>
                <option value="familiarity_desc">熟悉度降序</option>
              </select>
            </div>
            <button
              onClick={toggleSelectMode}
              style={{
                padding: 4,
                borderRadius: 4,
                border: 'none',
                cursor: 'pointer',
                background: isSelectMode ? 'var(--ew-accent-bg, rgba(37, 99, 235, 0.2))' : 'transparent',
                color: isSelectMode ? 'var(--ew-accent, #3b82f6)' : 'var(--ew-text-faint, #737373)',
                transition: 'all 0.15s',
              }}
              title="选择单词"
            >
              <CheckSquare size={16} />
            </button>
          </div>

          {groups.length > 0 && (
            <select
              value={selectedGroupIndex}
              onChange={(e) => setSelectedGroupIndex(Number(e.target.value))}
              style={{ width: '100%', background: 'var(--ew-bg-card, #171717)', color: 'var(--ew-text-2, #d4d4d4)', fontSize: 11, border: '1px solid var(--ew-border)', borderRadius: 4, padding: '4px 8px', outline: 'none' }}
            >
              {groups.map((group) => (
                <option key={group.index} value={group.index}>{group.label}</option>
              ))}
            </select>
          )}

          {isSelectMode && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--ew-bg-card, #171717)', padding: 8, borderRadius: 6, border: '1px solid var(--ew-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: 'var(--ew-text-3, #a3a3a3)' }}>已选 {selectedWordsForQuiz.size} 个</span>
                <button
                  onClick={toggleSelectAll}
                  style={{ fontSize: 11, color: 'var(--ew-accent, #3b82f6)', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                >
                  {selectedWordsForQuiz.size === sortedWords.length ? '取消全选' : '全选'}
                </button>
              </div>
              <button
                onClick={() => {
                  if (selectedWordsForQuiz.size === 0) return;
                  // Emit event for quiz
                  window.dispatchEvent(new CustomEvent('english:startQuiz', {
                    detail: { words: Array.from(selectedWordsForQuiz) }
                  }));
                }}
                disabled={selectedWordsForQuiz.size === 0}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 11,
                  background: selectedWordsForQuiz.size === 0 ? 'var(--ew-border, #262626)' : '#2563eb',
                  color: 'var(--ew-text-1, #fff)',
                  border: 'none',
                  borderRadius: 4,
                  padding: '4px 8px',
                  cursor: selectedWordsForQuiz.size === 0 ? 'not-allowed' : 'pointer',
                  opacity: selectedWordsForQuiz.size === 0 ? 0.5 : 1,
                }}
              >
                <Play size={10} /> 测验
              </button>
            </div>
          )}
        </div>
      )}

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto' }} ref={parentRef}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 14, color: 'var(--ew-text-faint, #737373)' }}>
            {/* Indeterminate progress bar — gives immediate visual feedback while the
                word list loads from the backend (7508 words can take a moment). */}
            <div style={{ width: '70%', height: 4, borderRadius: 999, background: 'var(--ew-border, #1a1a1a)', overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: '40%', borderRadius: 999,
                background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                animation: 'lf-wordload 1.1s ease-in-out infinite',
              }} />
            </div>
            <span style={{ fontSize: 13 }}>加载单词中…</span>
          </div>
        ) : viewMode === 'libraries' && !searchQuery ? (
          // Libraries List
          <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {libraryItems.map((item) => (
              <button
                key={item.name}
                onClick={() => handleItemClick(item)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: 12,
                  borderRadius: 8,
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--ew-bg-hover)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: 12,
                  flexShrink: 0,
                  background: item.type === 'directory' ? 'rgba(59, 130, 246, 0.1)' : item.source === 'user' ? 'rgba(168, 85, 247, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                }}>
                  {item.type === 'directory' ? (
                    <Folder size={16} style={{ color: 'var(--ew-accent, #3b82f6)' }} />
                  ) : (
                    <svg width={16} height={16} style={{ color: item.source === 'user' ? 'var(--ew-purple, #a855f7)' : 'var(--ew-success, #22c55e)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--ew-text-1, #e5e5e5)' }}>{item.name.replace('.csv', '')}</span>
                    {item.source === 'user' && (
                      <span style={{ fontSize: 10, padding: '2px 6px', background: 'var(--ew-purple-bg, rgba(168, 85, 247, 0.2))', color: 'var(--ew-purple-light, #c084fc)', borderRadius: 4 }}>我的库</span>
                    )}
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--ew-text-faint, #737373)' }}>
                    {item.type === 'directory' ? '文件夹' : item.source === 'user' ? `${item.wordCount || 0} 个单词` : '文件'}
                  </span>
                </div>
              </button>
            ))}
            {libraryItems.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--ew-text-faint, #737373)', fontSize: 14, padding: '32px 0' }}>
                空目录
              </div>
            )}
          </div>
        ) : (
          // Words List (Virtualized)
          <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const item = sortedWords[virtualRow.index];
              const wordString = getWordString(item);
              const score = progress[wordString];
              const isSelected = selectedWordsForQuiz.has(wordString);

              let definition = '';
              let phonetic = '';
              let collins = '';

              if (typeof item !== 'string' && item.chineseData) {
                definition = item.chineseData.concise_definition || '';
                phonetic = item.chineseData.phonetic || '';
                collins = item.chineseData.collins || '';
              }

              const isActive = selectedWord === wordString;

              return (
                <div
                  key={virtualRow.index}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0 16px',
                      background: isActive ? 'var(--ew-accent-bg)' : 'transparent',
                      borderBottom: '1px solid var(--ew-border)',
                      cursor: isSelectMode ? 'pointer' : 'default',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--ew-bg-hover)'; }}
                    onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                    onClick={() => isSelectMode && toggleWordSelection(wordString)}
                  >
                    {isSelectMode ? (
                      <div style={{ marginRight: 12, color: 'var(--ew-text-faint, #737373)' }}>
                        {isSelected ? <CheckSquare size={16} style={{ color: 'var(--ew-accent, #3b82f6)' }} /> : <Square size={16} />}
                      </div>
                    ) : showScore ? (
                      <Circle size={8} style={{ marginRight: 12, color: getProgressColor(score), fill: 'currentColor', flexShrink: 0 }} />
                    ) : null}

                    <button
                      onClick={(e) => {
                        if (isSelectMode) {
                          toggleWordSelection(wordString);
                          return;
                        }
                        onWordSelect(wordString);
                      }}
                      style={{
                        flex: 1,
                        textAlign: 'left',
                        border: 'none',
                        background: 'none',
                        cursor: 'pointer',
                        padding: 0,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        minWidth: 0,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                        <span style={{
                          fontSize: 14,
                          color: isActive ? 'var(--ew-text-1, #fff)' : 'var(--ew-text-3, #a3a3a3)',
                          fontWeight: isActive ? 500 : 'normal',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {wordString}
                        </span>
                        {phonetic && (
                          <span style={{ fontSize: 11, color: 'var(--ew-text-faint, #737373)', fontFamily: 'monospace', marginLeft: 8, flexShrink: 0 }}>
                            /{phonetic}/
                          </span>
                        )}
                        {renderCollinsStars(collins)}
                      </div>
                      {showChinese && definition && (
                        <span style={{ fontSize: 12, color: 'var(--ew-text-3, #525252)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 2 }}>
                          {definition}
                        </span>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
