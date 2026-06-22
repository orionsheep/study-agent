import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Remove the broken onClickCapture logic
bad_click_capture = """      onClickCapture={(event) => {
        // react-force-graph can treat a tiny mouse movement as a drag and skip
        // onNodeClick even though hover hit-testing correctly found a node.
        // If the click landed on the graph canvas, use the current hovered node
        // as a fallback so label clicks reliably navigate to the word detail.
        if (event.target instanceof HTMLCanvasElement) selectGraphNode(hoveredNodeRef.current);
      }}"""

content = content.replace(bad_click_capture, "")

# We need to add our own precise click detection state to the top of the component
click_state = """  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  
  // Custom click detection to solve the fragile drag vs click issue
  const pointerRef = useRef<{ x: number, y: number, time: number, isDragging: boolean }>({ x: 0, y: 0, time: 0, isDragging: false });
"""
content = content.replace("  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });", click_state)

# Replace the onNodeClick logic in ForceGraph2D
old_node_events = """          onNodeHover={(node: any) => {
            if (!showLevel2 && node?.level === 2) {
              hoveredNodeRef.current = null;
              setHoveredNode(null);
              if (containerRef.current) containerRef.current.style.cursor = 'default';
              return;
            }
            hoveredNodeRef.current = node || null;
            setHoveredNode(node || null);
            if (containerRef.current) containerRef.current.style.cursor = node ? 'pointer' : 'default';
          }}
          onNodeClick={(node: any) => {
            selectGraphNode(node);
          }}
          onNodeDrag={(node: any) => {
            if (!showLevel2 && node?.level === 2) return false;
          }}
          onNodeDragEnd={(node: any) => {
            if (settings.lockNodeOnDrag && node) {
              node.fx = node.x;
              node.fy = node.y;
            }
          }}"""

new_node_events = """          // Record pointer down to differentiate click from drag
          onBackgroundClick={() => {}} 
          onNodeHover={(node: any) => {
            if (!showLevel2 && node?.level === 2) {
              hoveredNodeRef.current = null;
              setHoveredNode(null);
              if (containerRef.current) containerRef.current.style.cursor = 'default';
              return;
            }
            hoveredNodeRef.current = node || null;
            setHoveredNode(node || null);
            if (containerRef.current) containerRef.current.style.cursor = node ? 'pointer' : 'default';
          }}
          onNodeClick={(node: any, event) => {
            // react-force-graph usually handles basic clicks, but it's very strict.
            // If it manages to fire, it's definitely a click.
            if (!pointerRef.current.isDragging) {
              selectGraphNode(node);
            }
          }}
          onNodeDrag={(node: any) => {
            pointerRef.current.isDragging = true;
            if (!showLevel2 && node?.level === 2) return false;
          }}
          onNodeDragEnd={(node: any) => {
            // Give it a tiny delay to prevent the 'click' event from firing immediately after dropping
            setTimeout(() => { pointerRef.current.isDragging = false; }, 50);
            if (settings.lockNodeOnDrag && node) {
              node.fx = node.x;
              node.fy = node.y;
            }
          }}"""
content = content.replace(old_node_events, new_node_events)

# Add pointer event listeners to the canvas container to catch the "micro-drag" clicks
container_div = """    <div
      ref={containerRef}
      className="fission-graph-container"
      style={{ position: 'absolute', inset: 0, background: '#000', overflow: 'hidden' }}
    >"""

container_div_new = """    <div
      ref={containerRef}
      className="fission-graph-container"
      style={{ position: 'absolute', inset: 0, background: '#000', overflow: 'hidden' }}
      onPointerDown={(e) => {
        pointerRef.current = { x: e.clientX, y: e.clientY, time: Date.now(), isDragging: false };
      }}
      onPointerUp={(e) => {
        const dx = Math.abs(e.clientX - pointerRef.current.x);
        const dy = Math.abs(e.clientY - pointerRef.current.y);
        const dt = Date.now() - pointerRef.current.time;
        // If movement is very small (< 5px) and fast (< 300ms), it's a true click even if force-graph thought it was a micro-drag
        if (dx < 5 && dy < 5 && dt < 300 && !pointerRef.current.isDragging) {
           if (e.target instanceof HTMLCanvasElement && hoveredNodeRef.current) {
               selectGraphNode(hoveredNodeRef.current);
           }
        }
      }}
    >"""
content = content.replace(container_div, container_div_new)

with open(file_path, "w") as f:
    f.write(content)
