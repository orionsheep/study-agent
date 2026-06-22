import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# 1. Fix the resize observer polling so it always updates accurately
old_poll = """    let stableCount = 0;
    let lastW = 0, lastH = 0;
    const pollInterval = setInterval(() => {
      if (!containerRef.current) return;
      // Same offsetWidth/offsetHeight fix as updateDimensions — see comment there.
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;
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
    }, 200);"""

new_poll = """    let lastW = 0, lastH = 0;
    const pollInterval = setInterval(() => {
      if (!containerRef.current) return;
      const width = containerRef.current.offsetWidth;
      const height = containerRef.current.offsetHeight;
      if (width > 0 && height > 0) {
        if (Math.round(width) !== lastW || Math.round(height) !== lastH) {
          lastW = Math.round(width); lastH = Math.round(height);
          setDimensions({ width, height });
        }
      }
    }, 150);"""
content = content.replace(old_poll, new_poll)


# 2. Fix the auto-fit effect so it actually centers properly on dimensions change
old_effect = """  useEffect(() => {
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
  }, [data, dimensions]);"""

new_effect = """  useEffect(() => {
    if (fgRef.current && data.nodes.length > 0 && dimensions.width > 0) {
      const fitDelay = data.nodes.length > 60 ? 1200 : 400;
      const timer = setTimeout(() => {
        if (!fgRef.current) return;
        try {
          if (data.nodes.length < 5) {
            fgRef.current.centerAt(0, 0, 300);
            fgRef.current.zoom(1.2, 300);
          } else {
            fgRef.current.zoomToFit(400, 60);
            setTimeout(() => {
              try { if (fgRef.current) fgRef.current.centerAt(0, 0, 300); } catch {}
            }, 450);
          }
        } catch {}
      }, fitDelay);
      
      const resizeTimer = setTimeout(() => {
         try { if (fgRef.current) fgRef.current.centerAt(0, 0, 200); } catch {}
      }, 150);
      
      return () => { clearTimeout(timer); clearTimeout(resizeTimer); }
    }
  }, [data, dimensions]);"""
content = content.replace(old_effect, new_effect)

with open(file_path, "w") as f:
    f.write(content)
