import { useRef, useEffect, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { forceCollide } from 'd3-force';
import { RefreshCw, Maximize2, ZoomIn, ZoomOut, Eye, EyeOff, Settings, X } from 'lucide-react';

interface FissionGraphProps {
  word: string | null;
  onNodeClick?: (nodeId: string) => void;
  mode?: 'dashboard' | 'immersive';
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: string;
}

interface GraphSettings {
  level1Size: number;
  level2Size: number;
  level1FontSize: number;
  level2FontSize: number;
  chargeStrength: number;
  level1LinkDistance: number;
  level2LinkDistance: number;
  collisionRadius: number;
  lockNodeOnDrag: boolean;
  showHoverTooltip: boolean;
}

const defaultGraphSettings: GraphSettings = {
  level1Size: 1.0,
  level2Size: 0.6,
  level1FontSize: 12,
  level2FontSize: 9,
  chargeStrength: -400,
  level1LinkDistance: 180,
  level2LinkDistance: 100,
  collisionRadius: 40,
  lockNodeOnDrag: false,
  showHoverTooltip: true,
};

export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {
  const [data, setData] = useState<{ nodes: any[]; links: any[]; definitions?: Record<string, string> }>({ nodes: [], links: [] });
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showLevel2, setShowLevel2] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [uiSettings, setUiSettings] = useState<GraphSettings>({ ...defaultGraphSettings });
  const [settings, setSettings] = useState<GraphSettings>({ ...defaultGraphSettings });

  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const resetToDefaults = () => {
    setUiSettings({ ...defaultGraphSettings });
    setSettings({ ...defaultGraphSettings });
  };

  useEffect(() => {
    if (!word) {
      setData({ nodes: [], links: [] });
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/english/fission?word=${encodeURIComponent(word)}`);
        const graphData = await res.json();
        // 中心词（level 0）钉在 graph 原点 (0,0)，辐射图围绕画布中心展开。
        // 在数据进入 force-graph 前就设 fx/fy，确保 simulation 不会把它推开。
        graphData.nodes?.forEach((n: any) => { if (n.level === 0) { n.fx = 0; n.fy = 0; n.x = 0; n.y = 0; } });
        setData(graphData);
      } catch (error) {
        console.error('Failed to fetch graph data', error);
      } finally {
        setTimeout(() => setIsLoading(false), 100);
      }
    };

    fetchData();
  }, [word, refreshKey]);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        if (width > 0 && height > 0) {
          setDimensions((prev) => (Math.round(prev.width) === Math.round(width) && Math.round(prev.height) === Math.round(height) ? prev : { width, height }));
        }
      }
    };

    // Measure on every rAF for the first few frames — the container's size is not
    // stable until the resizable Panel layout settles, and a single setTimeout easily
    // samples a stale intermediate size (e.g. 400×1050 before the Panel clamps to 508×808).
    updateDimensions();
    let raf2 = requestAnimationFrame(updateDimensions);
    const timer1 = setTimeout(updateDimensions, 50);
    const timer2 = setTimeout(updateDimensions, 150);
    const timer3 = setTimeout(updateDimensions, 350);

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions((prev) => (Math.round(prev.width) === Math.round(width) && Math.round(prev.height) === Math.round(height) ? prev : { width, height }));
        }
      }
    });

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    window.addEventListener('resize', updateDimensions);

    // Polling fallback: ResizeObserver occasionally fails to fire when the container
    // lives inside a react-resizable-panels Panel whose layout settles asynchronously.
    // A short polling interval catches the final size and then idles once stable.
    let stableCount = 0;
    let lastW = 0, lastH = 0;
    const pollInterval = setInterval(() => {
      if (!containerRef.current) return;
      const { width, height } = containerRef.current.getBoundingClientRect();
      if (width > 0 && height > 0) {
        if (Math.round(width) !== lastW || Math.round(height) !== lastH) {
          lastW = Math.round(width); lastH = Math.round(height);
          setDimensions({ width, height });
          stableCount = 0;
        } else {
          stableCount++;
          if (stableCount > 8) clearInterval(pollInterval); // stable for ~1.6s, stop
        }
      }
    }, 200);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'h' && !e.repeat && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        setShowLevel2((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      cancelAnimationFrame(raf2);
      clearInterval(pollInterval);
      observer.disconnect();
      window.removeEventListener('resize', updateDimensions);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Configure d3 forces for the loaded graph size. Large graphs (world: 100+ nodes)
  // with the default charge/link settings clump or drift indefinitely, which both
  // looks "half-loaded" and misaligns hover hit-areas. We loosen charge and stretch
  // link distance for big graphs so they spread out and converge.
  useEffect(() => {
    if (!fgRef.current || data.nodes.length === 0) return;
    try {
      // 中心词（level 0）固定在 graph 原点 (0,0)，辐射图围绕画布中心展开。
      // 旧实现只在 nodeCanvasObject 渲染时设 fx/fy（时机晚、易被 simulation 抖动），
      // 这里在数据到位、reheat 前就钉住，确保中心词稳定位于 (0,0)。
      data.nodes.forEach((n: any) => {
        if (n.level === 0) { n.fx = 0; n.fy = 0; }
      });
      const big = data.nodes.length > 60;
      const charge = fgRef.current.d3Force("charge");
      if (charge) charge.strength(big ? -120 : -200);
      const link = fgRef.current.d3Force("link");
      if (link) link.distance((l: any) => (l.source?.level === 2 ? 60 : 30));
      fgRef.current.d3ReheatSimulation();
    } catch {
      // instance not ready yet; the [data] dependency will re-run
    }
  }, [data]);

  // Auto-fit graph to viewport. Re-runs when data loads or the container size settles
  // (dimensions updates from 0 → real size). The delay scales with node count: large
  // graphs (world, 100+ nodes) need longer for the force simulation to converge before
  // zoomToFit captures stable node bounds; calling it too early fits to a clump of
  // nodes that are still drifting toward their final positions.
  useEffect(() => {
    if (fgRef.current && data.nodes.length > 0 && dimensions.width > 0) {
      const fitDelay = data.nodes.length > 60 ? 1200 : 400;
      const timer = setTimeout(() => {
        if (!fgRef.current) return;
        try {
          if (data.nodes.length < 5) {
            fgRef.current.centerAt(0, 0, 500);
            fgRef.current.zoom(1.2, 500);
          } else {
            fgRef.current.zoomToFit(600, 60);
            // zoomToFit 把整群节点 fit 进视口（视口中心 = 节点质心），但质心通常
            // 不在 graph 原点，导致固定在 (0,0) 的中心词偏离画布中心。fit 完成后
            // 强制把视口中心对齐 graph 原点，让中心词回到正中。
            setTimeout(() => {
              try { fgRef.current?.centerAt(0, 0, 300); } catch { /* instance torn down */ }
            }, 700);
          }
        } catch {
          // fgRef may briefly point at a tearing-down instance; ignore.
        }
      }, fitDelay);
      return () => clearTimeout(timer);
    }
  }, [data, dimensions]);

  // Update forces when settings change
  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(settings.chargeStrength);
      // center force 保持默认强度（1.0），把节点拉回 (0,0)=画布中心；
      // 旧值 0.05 太弱，节点被电荷推到左下角、整体偏移。
      fgRef.current.d3Force('center')?.strength(1.0);
      fgRef.current.d3Force('link')?.distance((link: any) => {
        if (link.target.level === 1) return settings.level1LinkDistance;
        return settings.level2LinkDistance;
      });
      fgRef.current.d3Force('collide', forceCollide((node: any) => {
        const scale = node.level === 0 ? 1.5 : (node.level === 1 ? settings.level1Size : settings.level2Size);
        const baseRadius = node.val * scale;
        const textWidth = (node.name?.length || 0) * 8;
        return Math.max(baseRadius + settings.collisionRadius, textWidth / 2 + settings.collisionRadius * 0.7);
      }).strength(1.0).iterations(8));

      fgRef.current.d3ReheatSimulation();
      // 不在这里 zoomToFit：它和 [data,dimensions] effect 的 fit+centerAt(0,0) 序列
      // 打架（两个 zoomToFit 时序重叠），会让固定在原点的中心词偏离画布中心。
      // 视口 fit/居中统一交给上面的 [data, dimensions] effect。
    }
  }, [settings.chargeStrength, settings.level1LinkDistance, settings.level2LinkDistance, settings.collisionRadius]);

  // Initialize particle system
  useEffect(() => {
    if (dimensions.width === 0) return;
    const particleCount = 200;
    const newParticles: Particle[] = Array.from({ length: particleCount }, () => ({
      x: (Math.random() - 0.5) * dimensions.width * 3,
      y: (Math.random() - 0.5) * dimensions.height * 3,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 2 + 0.3,
      opacity: Math.random() * 0.4 + 0.1,
      color: ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)],
    }));
    setParticles(newParticles);
  }, [dimensions]);

  const handleRefresh = () => setRefreshKey((prev) => prev + 1);
  const handleZoomIn = () => { if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() * 1.5, 400); };
  const handleZoomOut = () => { if (fgRef.current) fgRef.current.zoom(fgRef.current.zoom() / 1.5, 400); };

  if (!word) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#737373', background: '#000', fontWeight: 300, letterSpacing: '0.05em' }}>
        选择一个单词查看裂变图
      </div>
    );
  }

  return (
    <div ref={containerRef} className="fission-graph-container" style={{ position: 'absolute', inset: 0, background: '#000', overflow: 'hidden' }}>
      {/* Gradient Background */}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, #0a0a0a 0%, #000 100%)', opacity: 0.6, pointerEvents: 'none' }} />

      {/* Controls */}
      <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <ControlButton onClick={handleRefresh} title="刷新">
          <RefreshCw size={18} />
        </ControlButton>
        <ControlButton onClick={handleZoomIn} title="放大">
          <ZoomIn size={18} />
        </ControlButton>
        <ControlButton onClick={handleZoomOut} title="缩小">
          <ZoomOut size={18} />
        </ControlButton>
        <ControlButton
          onClick={() => setShowLevel2(!showLevel2)}
          title={`切换二级节点 (H)`}
          active={!showLevel2}
        >
          {showLevel2 ? <Eye size={18} /> : <EyeOff size={18} />}
        </ControlButton>
        <ControlButton
          onClick={() => setShowSettings(!showSettings)}
          title="设置"
          active={showSettings}
        >
          <Settings size={18} />
        </ControlButton>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div style={{ position: 'absolute', top: 16, right: 64, zIndex: 20, width: 260, background: 'rgba(23, 23, 23, 0.95)', backdropFilter: 'blur(12px)', border: '1px solid #262626', borderRadius: 12, padding: 16, boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid #262626', paddingBottom: 8 }}>
            <h3 style={{ color: '#fff', fontWeight: 500, fontSize: 14, margin: 0 }}>图设置</h3>
            <button onClick={() => setShowSettings(false)} style={{ color: '#a3a3a3', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
              <X size={16} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <SliderControl label="一级节点大小" value={uiSettings.level1Size} min={0.5} max={3.0} step={0.1} unit="x" onChange={(v) => setUiSettings({ ...uiSettings, level1Size: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="二级节点大小" value={uiSettings.level2Size} min={0.3} max={2.0} step={0.1} unit="x" onChange={(v) => setUiSettings({ ...uiSettings, level2Size: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="一级字体" value={uiSettings.level1FontSize} min={8} max={24} step={1} unit="px" onChange={(v) => setUiSettings({ ...uiSettings, level1FontSize: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="二级字体" value={uiSettings.level2FontSize} min={6} max={18} step={1} unit="px" onChange={(v) => setUiSettings({ ...uiSettings, level2FontSize: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="排斥力" value={uiSettings.chargeStrength} min={-15000} max={0} step={50} unit="" onChange={(v) => setUiSettings({ ...uiSettings, chargeStrength: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="一级距离" value={uiSettings.level1LinkDistance} min={50} max={600} step={1} unit="px" onChange={(v) => setUiSettings({ ...uiSettings, level1LinkDistance: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="二级距离" value={uiSettings.level2LinkDistance} min={20} max={400} step={5} unit="px" onChange={(v) => setUiSettings({ ...uiSettings, level2LinkDistance: v })} onCommit={() => setSettings(uiSettings)} />
            <SliderControl label="碰撞间距" value={uiSettings.collisionRadius} min={10} max={100} step={5} unit="px" onChange={(v) => setUiSettings({ ...uiSettings, collisionRadius: v })} onCommit={() => setSettings(uiSettings)} />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid #262626' }}>
              <span style={{ fontSize: 12, color: '#a3a3a3' }}>拖拽后锁定</span>
              <button
                onClick={() => { const newSettings = { ...uiSettings, lockNodeOnDrag: !uiSettings.lockNodeOnDrag }; setUiSettings(newSettings); setSettings(newSettings); }}
                style={{ position: 'relative', width: 40, height: 20, borderRadius: 10, border: 'none', cursor: 'pointer', background: uiSettings.lockNodeOnDrag ? '#2563eb' : '#404040', transition: 'background 0.2s' }}
              >
                <span style={{ position: 'absolute', top: 2, left: 2, width: 16, height: 16, borderRadius: '50%', background: '#fff', transition: 'transform 0.2s', transform: uiSettings.lockNodeOnDrag ? 'translateX(20px)' : 'translateX(0)' }} />
              </button>
            </div>

            <button onClick={resetToDefaults} style={{ width: '100%', marginTop: 8, padding: '8px 12px', background: '#262626', color: '#d4d4d4', border: '1px solid #404040', borderRadius: 8, fontSize: 12, cursor: 'pointer', transition: 'all 0.15s' }}>
              恢复默认
            </button>
          </div>
        </div>
      )}

      {/* Floating Legend */}
      <div style={{ position: 'absolute', bottom: 16, left: 16, zIndex: 20, background: 'rgba(23, 23, 23, 0.9)', backdropFilter: 'blur(12px)', borderRadius: 8, padding: 12, border: '1px solid #262626', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)', maxWidth: 280 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#a3a3a3', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>连接含义</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316',
          ].map((color, index) => {
            const meaningNum = (index + 1).toString();
            const definition = data.definitions?.[meaningNum];
            if (!definition && index > 2) return null;
            return (
              <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <div style={{ width: 12, height: 12, borderRadius: '50%', marginTop: 2, flexShrink: 0, background: color }} />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: '#d4d4d4' }}>类型 {meaningNum}</span>
                  {definition && (
                    <span style={{ fontSize: 10, color: '#737373', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} title={definition}>
                      {definition.replace(/^SKM:.*?\|/, '')}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Loading */}
      {dimensions.width === 0 && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ color: '#737373', animation: 'pulse 2s infinite' }}>初始化中...</div>
        </div>
      )}

      {/* Graph */}
      {dimensions.width > 0 && (
        <ForceGraph2D
          key={`${mode}-${word}-${refreshKey}`}
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={data}
          nodeLabel={() => ''}
          nodeColor="color"
          nodeVal={(node: any) => (node.level === 0 ? 12 : 4)}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            if (!showLevel2 && node.level === 2) return;
            // The hit area must be comfortably grabbable even after zoomToFit shrinks a
            // large (100+ node) graph. A 4px radius becomes sub-pixel when zoomed out,
            // making peripheral nodes effectively unclickable — hence the generous size.
            const size = node.level === 0 ? 14 : (node.level === 1 ? 10 : 8);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
          linkColor="color"
          linkWidth={1.5}
          backgroundColor="#000000"
          d3VelocityDecay={0.15}
          // Scale the simulation cooldown to the graph size: a 29-node graph (hello)
          // settles quickly, but a 100+ node graph (world) needs many more ticks to
          // converge before zoomToFit, otherwise nodes are still drifting and the
          // hover hit-areas misalign with where nodes are drawn.
          d3AlphaDecay={data.nodes.length > 60 ? 0.008 : 0.015}
          cooldownTicks={Math.max(150, data.nodes.length * 3)}
          warmupTicks={Math.max(100, data.nodes.length * 2)}
          linkDirectionalParticleSpeed={0.003}
          onNodeHover={(node: any) => {
            if (!showLevel2 && node?.level === 2) {
              setHoveredNode(null);
              if (containerRef.current) containerRef.current.style.cursor = 'default';
              return;
            }
            setHoveredNode(node || null);
            if (containerRef.current) containerRef.current.style.cursor = node ? 'pointer' : 'default';
          }}
          onNodeClick={(node: any) => {
            if (!showLevel2 && node?.level === 2) return;
            if (onNodeClick) onNodeClick(node.id);
          }}
          onNodeDrag={(node: any) => {
            if (!showLevel2 && node?.level === 2) return false;
          }}
          onNodeDragEnd={(node: any) => {
            if (settings.lockNodeOnDrag && node) {
              node.fx = node.x;
              node.fy = node.y;
            }
          }}
          nodeCanvasObject={(node, ctx, globalScale) => {
            if (!showLevel2 && node.level === 2) return;
            const label = node.name;
            const x = (node.x as number) ?? 0;
            const y = (node.y as number) ?? 0;
            const time = Date.now() / 1000;

            if (node.level === 0) {
              node.fx = 0;
              node.fy = 0;
            }

            const isHovered = hoveredNode && hoveredNode.id === node.id;
            const isNeighbor = hoveredNode && data.links.some((link: any) =>
              (link.source === hoveredNode.id && link.target === node.id) ||
              (link.target === hoveredNode.id && link.source === node.id)
            );

            const scale = isHovered ? 1.3 : isNeighbor ? 1.15 : 1;
            const pulse = node.level === 0 ? Math.sin(time + (node.val || 0)) * 0.15 + 1 : 1;

            if (node.level === 0) {
              const gradient = ctx.createRadialGradient(x, y, 0, x, y, node.val * 3 * pulse);
              gradient.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
              gradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.2)');
              gradient.addColorStop(1, 'rgba(0,0,0,0)');
              ctx.fillStyle = gradient;
              ctx.beginPath();
              ctx.arc(x, y, node.val * 3 * pulse, 0, 2 * Math.PI);
              ctx.fill();

              ctx.fillStyle = '#ffffff';
              ctx.shadowColor = '#ffffff';
              ctx.shadowBlur = 15 * pulse;
              ctx.beginPath();
              ctx.arc(x, y, node.val * 0.8 * scale, 0, 2 * Math.PI);
              ctx.fill();
              ctx.shadowBlur = 0;

              ctx.strokeStyle = node.color || '#3b82f6';
              ctx.lineWidth = 3 / globalScale;
              ctx.beginPath();
              ctx.arc(x, y, node.val * 1.1 * scale, 0, 2 * Math.PI);
              ctx.stroke();
            } else {
              const isLevel1 = node.level === 1;
              const sizeMultiplier = isLevel1 ? settings.level1Size : settings.level2Size;
              const brightness = isLevel1 ? 0.8 : 0.4;
              const glowSize = isLevel1 ? 4.0 : 2.5;

              const gradient = ctx.createRadialGradient(x, y, 0, x, y, node.val * glowSize * scale * sizeMultiplier);
              const nodeColor = node.color || '#fff';
              gradient.addColorStop(0, nodeColor);
              gradient.addColorStop(1, 'rgba(0,0,0,0)');
              ctx.globalAlpha = brightness * (isHovered || isNeighbor ? 1.2 : 1);
              ctx.fillStyle = gradient;
              ctx.beginPath();
              ctx.arc(x, y, node.val * glowSize * scale * sizeMultiplier, 0, 2 * Math.PI);
              ctx.fill();

              ctx.fillStyle = nodeColor;
              ctx.beginPath();
              ctx.arc(x, y, node.val * 0.9 * scale * sizeMultiplier, 0, 2 * Math.PI);
              ctx.fill();

              ctx.fillStyle = '#fff';
              ctx.beginPath();
              ctx.arc(x, y, node.val * 0.35 * scale * sizeMultiplier, 0, 2 * Math.PI);
              ctx.fill();
              ctx.globalAlpha = 1;
            }
          }}
          linkCanvasObject={(link, ctx, globalScale) => {
            const start = link.source as any;
            const end = link.target as any;
            if (typeof start !== 'object' || typeof end !== 'object') return;
            if (!showLevel2 && (start.level === 2 || end.level === 2)) return;

            const isHighlighted = hoveredNode && (start.id === hoveredNode.id || end.id === hoveredNode.id);
            const linkColor = (link as any).color || '#555';
            ctx.strokeStyle = linkColor;
            ctx.lineWidth = (isHighlighted ? 2.5 : 1.5) / globalScale;
            ctx.globalAlpha = isHighlighted ? 0.9 : 0.6;
            ctx.beginPath();
            ctx.moveTo(start.x, start.y);
            ctx.lineTo(end.x, end.y);
            ctx.stroke();
            ctx.globalAlpha = 1;
          }}
          onRenderFramePost={(ctx: any, globalScale: number) => {
            // Draw labels
            data.nodes.forEach((node: any) => {
              if (!showLevel2 && node.level === 2) return;
              const nx = node.x ?? 0;
              const ny = node.y ?? 0;
              const isHovered = hoveredNode && hoveredNode.id === node.id;

              if (node.level < 2 || globalScale > 1.2 || isHovered) {
                let labelOffsetMultiplier = 1.2;
                if (node.level === 0) labelOffsetMultiplier = 1.5;
                else if (node.level === 1) labelOffsetMultiplier = 1.4;
                else labelOffsetMultiplier = 1.2;

                let fontSize = 12 / globalScale;
                if (node.level === 0) fontSize = 16 / globalScale;
                else if (node.level === 1) fontSize = settings.level1FontSize / globalScale;
                else fontSize = settings.level2FontSize / globalScale;
                const labelPadding = 4 / globalScale;

                let labelX = nx;
                let labelY = ny;
                if (node.level === 0) {
                  labelY = ny + node.val * labelOffsetMultiplier + fontSize;
                } else {
                  const angle = Math.atan2(ny, nx);
                  const distance = node.val * labelOffsetMultiplier + fontSize;
                  labelX = nx + Math.cos(angle) * distance;
                  labelY = ny + Math.sin(angle) * distance;
                }

                ctx.font = `${node.level === 0 ? 'bold ' : ''}${fontSize}px "Inter", -apple-system, sans-serif`;
                const nodeName = node.name || '';
                const textMetrics = ctx.measureText(nodeName);
                const textWidth = textMetrics.width;
                const textHeight = fontSize * 1.2;

                ctx.fillStyle = 'rgba(0, 0, 0, 1)';
                ctx.fillRect(
                  labelX - textWidth / 2 - labelPadding,
                  labelY - textHeight / 2 - labelPadding,
                  textWidth + labelPadding * 2,
                  textHeight + labelPadding * 2,
                );
                ctx.strokeStyle = node.level === 0 ? '#3b82f6' : 'rgba(255, 255, 255, 0.3)';
                ctx.lineWidth = 1 / globalScale;
                ctx.strokeRect(
                  labelX - textWidth / 2 - labelPadding,
                  labelY - textHeight / 2 - labelPadding,
                  textWidth + labelPadding * 2,
                  textHeight + labelPadding * 2,
                );
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#ffffff';
                ctx.fillText(nodeName, labelX, labelY);
              }
            });

            // Draw particles
            particles.forEach((p) => {
              ctx.fillStyle = p.color;
              ctx.globalAlpha = p.opacity;
              ctx.beginPath();
              ctx.arc(p.x, p.y, p.size / globalScale, 0, 2 * Math.PI);
              ctx.fill();
              p.x += p.vx;
              p.y += p.vy;
              const boundX = dimensions.width * 1.5;
              const boundY = dimensions.height * 1.5;
              if (p.x > boundX) p.x = -boundX;
              if (p.x < -boundX) p.x = boundX;
              if (p.y > boundY) p.y = -boundY;
              if (p.y < -boundY) p.y = boundY;
            });
            ctx.globalAlpha = 1;
          }}
        />
      )}

      {/* HTML Tooltip Overlay */}
      {hoveredNode && (
        <div ref={tooltipRef} style={{ position: 'absolute', pointerEvents: 'none', zIndex: 50, left: 0, top: 0 }}>
          <div style={{ background: 'rgba(23, 23, 23, 0.95)', backdropFilter: 'blur(12px)', border: '1px solid #262626', borderRadius: 8, padding: '8px 12px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)', maxWidth: 240 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 4 }}>{hoveredNode.name}</div>
            {hoveredNode.phonetic && (
              <div style={{ fontSize: 12, color: '#a3a3a3', fontFamily: 'monospace', marginBottom: 4 }}>/{hoveredNode.phonetic}/</div>
            )}
            {hoveredNode.translation && (
              <div style={{ fontSize: 12, color: '#d4d4d4', lineHeight: 1.5 }}>{hoveredNode.translation}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Control Button component
function ControlButton({ onClick, title, active, children }: { onClick: () => void; title: string; active?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        padding: 8,
        background: active ? '#2563eb' : 'rgba(23, 23, 23, 0.8)',
        color: '#fff',
        borderRadius: 8,
        border: '1px solid #262626',
        cursor: 'pointer',
        backdropFilter: 'blur(8px)',
        transition: 'all 0.15s',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = 'rgba(38, 38, 38, 0.9)'; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = 'rgba(23, 23, 23, 0.8)'; }}
    >
      {children}
    </button>
  );
}

// Slider Control component
function SliderControl({ label, value, min, max, step, unit, onChange, onCommit }: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (val: number) => void;
  onCommit: () => void;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#a3a3a3' }}>
        <span>{label}</span>
        <span>{value.toFixed(step < 1 ? 1 : 0)}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        onMouseUp={onCommit}
        onTouchEnd={onCommit}
        style={{
          width: '100%',
          height: 4,
          borderRadius: 4,
          appearance: 'none',
          background: '#404040',
          cursor: 'pointer',
          outline: 'none',
        }}
      />
    </div>
  );
}
