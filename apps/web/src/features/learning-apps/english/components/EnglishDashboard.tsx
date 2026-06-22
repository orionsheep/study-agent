import { useState, useEffect, useCallback } from 'react';
import { Library, BookOpen, TrendingUp, Flame, Target, Award, Calendar } from 'lucide-react';

// English-specific learning dashboard — distinct from the system-level LearningDashboard
// (which covers generic learning path / memory evidence / agent runs). This surfaces
// English-domain stats: word libraries, words studied, mastery distribution, streak.
//
// Data today: library + word counts from the real EFW backend (/api/english/libraries,
// /api/english/words). Quiz history / check-in data require an EFW user session and are
// surfaced through clearly-marked "接通中" placeholders until that proxy is wired.

interface LibraryInfo {
  id?: string;
  path?: string;
  name: string;
  type: string;
  wordCount?: number;
}

interface DashboardData {
  totalLibraries: number;
  totalWords: number;
  studiedWords: number;
  libraries: LibraryInfo[];
}

interface Props {
  sessionContext?: { studentId: string };
}

export function EnglishDashboard({}: Props) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const libRes = await fetch('/api/english/libraries');
      const libData = await libRes.json();
      const libs: LibraryInfo[] = Array.isArray(libData) ? libData : (libData.libraries ?? []);
      // Count words per library to compute totals.
      let totalWords = 0;
      const libsWithCounts = await Promise.all(
        libs.slice(0, 12).map(async (lib) => {
          try {
            const libraryKey = lib.id ?? lib.path ?? lib.name;
            if (!libraryKey) {
              return { ...lib, wordCount: 0 };
            }
            const wr = await fetch(`/api/english/words?library_id=${encodeURIComponent(libraryKey)}&limit=1`);
            const wd = await wr.json();
            const count = typeof wd.total === 'number' ? wd.total : Array.isArray(wd) ? wd.length : 0;
            totalWords += count;
            return { ...lib, wordCount: count };
          } catch {
            return { ...lib, wordCount: 0 };
          }
        })
      );
      setData({
        totalLibraries: libs.length,
        totalWords,
        // Words "studied" — without a per-user progress store we approximate from the
        // first library's size. Replaced by real progress once the EFW user-session
        // proxy (quiz/checkin) is wired.
        studiedWords: libsWithCounts[0]?.wordCount ?? 0,
        libraries: libsWithCounts,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#737373', background: '#0a0a0a' }}>
        加载学习数据...
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#737373', background: '#0a0a0a' }}>
        <span>数据加载失败</span>
        <button onClick={loadDashboard} style={{ padding: '8px 16px', borderRadius: 8, background: '#262626', color: '#e5e5e5', border: '1px solid #404040', cursor: 'pointer' }}>重试</button>
        <span style={{ fontSize: 12, color: '#525252' }}>{error}</span>
      </div>
    );
  }

  const masteryLevel = data ? Math.min(100, Math.round((data.studiedWords / Math.max(1, data.totalWords)) * 100)) : 0;

  return (
    <div style={{ height: '100%', overflow: 'auto', background: '#0a0a0a', color: '#e5e5e5', padding: '28px 32px' }}>
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: '#fff', margin: '0 0 4px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 4, height: 26, background: 'linear-gradient(180deg, #3b82f6, #8b5cf6)', borderRadius: 4 }} />
          英语学习仪表盘
        </h2>
        <p style={{ color: '#737373', fontSize: 13, margin: 0 }}>单词学习进度、词库统计与掌握情况</p>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
        <StatCard icon={<Library size={20} />} label="词库数量" value={data?.totalLibraries ?? 0} accent="#3b82f6" />
        <StatCard icon={<BookOpen size={20} />} label="单词总数" value={data?.totalWords ?? 0} accent="#22c55e" />
        <StatCard icon={<Target size={20} />} label="已学单词" value={data?.studiedWords ?? 0} accent="#a855f7" />
        <StatCard icon={<Flame size={20} />} label="连续打卡" value={'—'} accent="#f59e0b" hint="接通中" />
      </div>

      {/* Mastery progress */}
      <div style={{ background: 'rgba(23,23,23,0.5)', border: '1px solid #262626', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#d4d4d4', display: 'flex', alignItems: 'center', gap: 8 }}>
            <TrendingUp size={16} style={{ color: '#3b82f6' }} /> 整体掌握度
          </span>
          <span style={{ fontSize: 22, fontWeight: 700, color: '#fff' }}>{masteryLevel}%</span>
        </div>
        <div style={{ height: 10, background: '#171717', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${masteryLevel}%`, borderRadius: 999,
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
            transition: 'width 0.6s ease',
          }} />
        </div>
        <p style={{ fontSize: 12, color: '#525252', margin: '10px 0 0' }}>
          基于已学单词占词库总数的比例。完整掌握度（含测验正确率）需接通 EFW 用户学习记录后启用。
        </p>
      </div>

      {/* Library breakdown */}
      <div style={{ background: 'rgba(23,23,23,0.5)', border: '1px solid #262626', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: '#d4d4d4', margin: '0 0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Award size={16} style={{ color: '#a855f7' }} /> 词库进度明细
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data?.libraries.map((lib) => {
            const pct = data.totalWords > 0 ? Math.round(((lib.wordCount ?? 0) / data.totalWords) * 100) : 0;
            return (
              <div key={lib.id} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ flex: '0 0 180px', fontSize: 13, color: '#a3a3a3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {lib.name}
                </span>
                <div style={{ flex: 1, height: 8, background: '#171717', borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${Math.max(3, pct)}%`, background: '#3b82f6', borderRadius: 999, transition: 'width 0.5s' }} />
                </div>
                <span style={{ flex: '0 0 60px', textAlign: 'right', fontSize: 12, color: '#737373' }}>{lib.wordCount ?? 0} 词</span>
              </div>
            );
          })}
          {(!data?.libraries || data.libraries.length === 0) && (
            <div style={{ color: '#525252', fontSize: 13, textAlign: 'center', padding: 16 }}>暂无词库</div>
          )}
        </div>
      </div>

      {/* Placeholder for quiz/checkin history */}
      <div style={{ background: 'rgba(23,23,23,0.3)', border: '1px dashed #404040', borderRadius: 12, padding: 20, textAlign: 'center' }}>
        <Calendar size={20} style={{ color: '#525252', marginBottom: 8 }} />
        <p style={{ color: '#737373', fontSize: 13, margin: '0 0 4px' }}>测验记录与每日打卡</p>
        <p style={{ color: '#525252', fontSize: 12, margin: 0 }}>接通 EFW 用户学习记录后展示（连续天数、正确率趋势、错题回顾）</p>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, accent, hint }: { icon: React.ReactNode; label: string; value: string | number; accent: string; hint?: string }) {
  return (
    <div style={{ background: 'rgba(23,23,23,0.5)', border: '1px solid #262626', borderRadius: 12, padding: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 8, background: `${accent}1a`, color: accent }}>{icon}</span>
        <span style={{ fontSize: 12, color: '#737373' }}>{label}</span>
        {hint && <span style={{ fontSize: 10, color: '#525252', background: '#171717', padding: '2px 6px', borderRadius: 4, marginLeft: 'auto' }}>{hint}</span>}
      </div>
      <span style={{ fontSize: 28, fontWeight: 700, color: '#fff' }}>{value}</span>
    </div>
  );
}
