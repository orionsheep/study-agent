file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# We need to make sure the graph recenters itself whenever the dimensions change
# We can find the existing useEffect for auto-fit and improve it.

old_effect = """  // Auto-fit graph to viewport. Re-runs when data loads or the container size settles
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
  }, [data, dimensions]);"""

new_effect = """  // Auto-fit graph to viewport. Re-runs when data loads or the container size settles.
  // We use a debounced approach: every time the dimensions change (like resizing the panel 
  // or opening the app), we wait a tiny bit and recenter to ensure the center word stays exactly in the middle.
  useEffect(() => {
    if (fgRef.current && data.nodes.length > 0 && dimensions.width > 0) {
      const fitDelay = data.nodes.length > 60 ? 1200 : 400;
      const timer = setTimeout(() => {
        if (!fgRef.current) return;
        try {
          if (data.nodes.length < 5) {
            // For small graphs, just center and zoom
            fgRef.current.centerAt(0, 0, 300);
            fgRef.current.zoom(1.2, 300);
          } else {
            // First zoom to fit to ensure all nodes are visible
            fgRef.current.zoomToFit(400, 60);
            
            // Then force the origin (0,0) which is our root word to the exact center of the new dimensions
            setTimeout(() => {
              try { 
                if (fgRef.current) fgRef.current.centerAt(0, 0, 300); 
              } catch { /* instance torn down */ }
            }, 450);
          }
        } catch {
          // ignore
        }
      }, fitDelay);
      
      // Also add a safety net: if this is a resize event, recenter immediately without the long initial delay
      const resizeTimer = setTimeout(() => {
         try { if (fgRef.current) fgRef.current.centerAt(0, 0, 200); } catch {}
      }, 100);
      
      return () => {
        clearTimeout(timer);
        clearTimeout(resizeTimer);
      }
    }
  }, [data, dimensions]);"""

content = content.replace(old_effect, new_effect)

# Let's also fix the d3Force center. Previously it was: fgRef.current.d3Force('center')?.strength(1.0);
# We need to make sure the root node is firmly pinned to 0,0
content = content.replace("node.fx = 0;", "node.fx = 0; node.vx = 0;")
content = content.replace("node.fy = 0;", "node.fy = 0; node.vy = 0;")

with open(file_path, "w") as f:
    f.write(content)
