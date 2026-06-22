import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add a simple safe theme detector if not present
if "const isDark =" not in content:
    helper = "\n  const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');\n"
    content = content.replace("export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {", 
                              "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {" + helper)
    # Add re-render trigger on theme change
    if "useEffect(() => { const obs" not in content:
        hook = """
  const [, setTick] = useState(0);
  useEffect(() => {
    const obs = new MutationObserver(() => setTick(t => t + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, []);
"""
        content = content.replace(helper, helper + hook)

# Replace the specific hardcoded canvas colors with light/dark aware versions
content = content.replace("backgroundColor=\"#000000\"", "backgroundColor={isDark ? '#000000' : '#ffffff'}")
content = content.replace("ctx.strokeStyle = node.color || '#3b82f6'", "ctx.strokeStyle = node.color || (isDark ? '#3b82f6' : '#2563eb')")
content = content.replace("const nodeColor = node.color || '#fff'", "const nodeColor = node.color || (isDark ? '#ffffff' : '#18181b')")
content = content.replace("ctx.fillStyle = '#ffffff'", "ctx.fillStyle = isDark ? '#ffffff' : '#18181b'")
content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)'", "ctx.fillStyle = isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.9)'")
content = content.replace("ctx.strokeStyle = node.level === 0 ? '#3b82f6' : 'rgba(255, 255, 255, 0.3)'", "ctx.strokeStyle = node.level === 0 ? (isDark ? '#3b82f6' : '#2563eb') : (isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.15)')")
content = content.replace("const linkColor = (link as any).color || '#555'", "const linkColor = (link as any).color || (isDark ? '#555' : 'rgba(0,0,0,0.15)')")

# Replace arrays
content = content.replace(
    "color: ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)]",
    "color: isDark ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)] : ['#18181b', '#18181b', '#2563eb', '#7e22ce', '#db2777', '#9333ea'][Math.floor(Math.random() * 6)]"
)
content = content.replace(
    "['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'].map",
    "(isDark ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']).map"
)

with open(file_path, "w") as f:
    f.write(content)
print("Patched FissionGraph safely")
