import re

files = [
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx",
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx",
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx",
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
]

theme_definition = """
  // --- PERFECT THEME HOOK ---
  const isDark = () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
  const T = {
    // Glassy Backgrounds
    bgMain: isDark() ? 'rgba(0, 0, 0, 0.2)' : 'rgba(255, 255, 255, 0.4)',
    bgPanel: isDark() ? 'rgba(10, 10, 10, 0.5)' : 'rgba(255, 255, 255, 0.65)',
    bgHeader: isDark() ? 'rgba(23, 23, 23, 0.6)' : 'rgba(255, 255, 255, 0.75)',
    bgHover: isDark() ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.04)',
    bgActive: isDark() ? 'rgba(38, 38, 38, 0.6)' : 'rgba(0, 0, 0, 0.08)',
    
    // Borders
    border: isDark() ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)',
    borderHi: isDark() ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.15)',
    
    // Typography
    text1: isDark() ? '#ffffff' : '#18181b', // Crisp primary
    text2: isDark() ? '#d4d4d4' : '#52525b', // Readable secondary
    text3: isDark() ? '#a3a3a3' : '#71717a', // Muted
    textFaint: isDark() ? '#737373' : '#a1a1aa',
    
    // Semantic Colors (Maintained in both modes, tuned for contrast)
    accent: isDark() ? '#60a5fa' : '#2563eb', // Blue links
    accentBg: isDark() ? 'rgba(59, 130, 246, 0.2)' : 'rgba(37, 99, 235, 0.1)',
    purple: isDark() ? '#c084fc' : '#7e22ce', // My Library tags
    purpleBg: isDark() ? 'rgba(168, 85, 247, 0.2)' : 'rgba(126, 34, 206, 0.1)',
    success: isDark() ? '#4ade80' : '#16a34a', // Correct/Good
    warning: isDark() ? '#fde047' : '#d97706', // Stars/Warning
    danger: isDark() ? '#f87171' : '#dc2626', // Wrong/Danger
    orange: isDark() ? '#fb923c' : '#ea580c', // Orange tags
  };
"""

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()

    # Clean up previous bad patches
    content = re.sub(r'const isDark = \(\) => typeof document.*?;\n', '', content)
    
    # Insert new theme definition at the start of the component
    if "EnglishWorkspaceApp" in file_path:
        content = content.replace("export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {", 
                                  "export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {" + theme_definition)
    elif "WordList" in file_path:
        content = content.replace("export default function WordList({ onWordSelect, selectedWord }: WordListProps) {", 
                                  "export default function WordList({ onWordSelect, selectedWord }: WordListProps) {" + theme_definition)
    elif "WordDetail" in file_path:
        content = content.replace("export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {", 
                                  "export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {" + theme_definition)
    elif "FissionGraph" in file_path:
        content = content.replace("export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {", 
                                  "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {" + theme_definition)

    # -------------------------------------------------------------------------
    # Apply T.* replacements for EnglishWorkspaceApp.tsx
    # -------------------------------------------------------------------------
    if "EnglishWorkspaceApp" in file_path:
        # Backgrounds
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#000['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgMain", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#000000['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgMain", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#0a0a0a['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgPanel", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(10,10,10,0\.6\)['\"]\s*:\s*['\"]var\(--glass-1\)['\"]\s*\)", "T.bgHeader", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(23,23,23,0\.6\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.bgActive", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.05\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.bgHover", content)
        content = re.sub(r"background:\s*enabled\s*\?\s*\(isDark\(\)\?'rgba\(255,255,255,0\.1\)':'var\(--glass-2\)'\)\s*:\s*'transparent'", "background: enabled ? T.bgHover : 'transparent'", content)
        
        # Borders
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#171717['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.border", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#262626['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.border", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.2\)['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.borderHi", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#404040['\"]\s*:\s*['\"]var\(--glass-border-hi\)['\"]\s*\)", "T.borderHi", content)
        
        # Text
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#ffffff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#fff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.9\)['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.85\)['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.text2", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#d4d4d4['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.text2", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.6\)['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#a3a3a3['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#737373['\"]\s*:\s*['\"]var\(--text-faint\)['\"]\s*\)", "T.textFaint", content)
        
        # Colors / Accents
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#3b82f6['\"]\s*:\s*['\"]var\(--accent\)['\"]\s*\)", "T.accent", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]radial-gradient\(ellipse at center, rgba\(38,38,38,0\.2\) 0%, #000 70%\)['\"]\s*:\s*['\"]transparent['\"]\s*\)", "isDark() ? 'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, rgba(0,0,0,0.5) 70%)' : 'radial-gradient(ellipse at center, rgba(255,255,255,0.8) 0%, rgba(240,240,240,0.4) 70%)'", content)
        content = re.sub(r"color:\s*enabled\s*\?\s*\(isDark\(\)\?'#d4d4d4':'var\(--text-2\)'\)\s*:\s*\(isDark\(\)\?'#404040':'var\(--glass-border-hi\)'\)", "color: enabled ? T.text2 : T.borderHi", content)

    # -------------------------------------------------------------------------
    # Apply T.* replacements for WordList.tsx
    # -------------------------------------------------------------------------
    elif "WordList" in file_path:
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#0a0a0a['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgMain", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#171717['\"]\s*:\s*['\"]var\(--glass-1\)['\"]\s*\)", "T.bgPanel", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.05\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.bgHover", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#262626['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.border", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#404040['\"]\s*:\s*['\"]var\(--glass-border-hi\)['\"]\s*\)", "T.borderHi", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#ffffff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#fff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#d4d4d4['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.text2", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#a3a3a3['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#737373['\"]\s*:\s*['\"]var\(--text-faint\)['\"]\s*\)", "T.textFaint", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#3b82f6['\"]\s*:\s*['\"]var\(--accent\)['\"]\s*\)", "T.accent", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(37, 99, 235, 0\.2\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.accentBg", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#22c55e['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.success", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#eab308['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.warning", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#ef4444['\"]\s*:\s*['\"]var\(--st-risk\)['\"]\s*\)", "T.danger", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#a855f7['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.purple", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#c084fc['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.purple", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(168, 85, 247, 0\.2\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.purpleBg", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#e5e5e5['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#525252['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#1a1a1a['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.borderHi", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*'linear-gradient\(90deg, #fff, #8b5cf6\)'\s*:\s*'var\(--text-1\)'\)", "isDark() ? 'linear-gradient(90deg, #fff, #8b5cf6)' : T.accent", content)

    # -------------------------------------------------------------------------
    # Apply T.* replacements for WordDetail.tsx
    # -------------------------------------------------------------------------
    elif "WordDetail" in file_path:
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#0a0a0a['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgMain", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#171717['\"]\s*:\s*['\"]transparent['\"]\s*\)", "T.bgPanel", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255, 255, 255, 0\.05\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.bgHover", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]rgba\(255,255,255,0\.05\)['\"]\s*:\s*['\"]var\(--glass-2\)['\"]\s*\)", "T.bgHover", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#262626['\"]\s*:\s*['\"]var\(--glass-border\)['\"]\s*\)", "T.border", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#404040['\"]\s*:\s*['\"]var\(--glass-border-hi\)['\"]\s*\)", "T.borderHi", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#ffffff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#fff['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#e5e5e5['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.text1", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#d4d4d4['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.text2", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#a3a3a3['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#525252['\"]\s*:\s*['\"]var\(--text-3\)['\"]\s*\)", "T.text3", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#737373['\"]\s*:\s*['\"]var\(--text-faint\)['\"]\s*\)", "T.textFaint", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#3b82f6['\"]\s*:\s*['\"]var\(--accent\)['\"]\s*\)", "T.accent", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#60a5fa['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.accent", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#22c55e['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.success", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#eab308['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.warning", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#fef08a['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.warning", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#f97316['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.orange", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#a855f7['\"]\s*:\s*['\"]var\(--text-1\)['\"]\s*\)", "T.purple", content)
        content = re.sub(r"\(\s*isDark\(\)\s*\?\s*['\"]#c084fc['\"]\s*:\s*['\"]var\(--text-2\)['\"]\s*\)", "T.purple", content)
        
        # Fix dynamic inline styles for hover
        content = content.replace("e.currentTarget.style.color = '#fff'", "e.currentTarget.style.color = T.text1")
        content = content.replace("e.currentTarget.style.borderColor = '#404040'", "e.currentTarget.style.borderColor = T.borderHi")
        content = content.replace("e.currentTarget.style.color = '#a3a3a3'", "e.currentTarget.style.color = T.text3")
        content = content.replace("e.currentTarget.style.borderColor = '#262626'", "e.currentTarget.style.borderColor = T.border")

    # -------------------------------------------------------------------------
    # Fix FissionGraph completely for light mode
    # -------------------------------------------------------------------------
    elif "FissionGraph" in file_path:
        # Backgrounds
        content = re.sub(r"background:\s*['\"]#000['\"]", "background: T.bgMain", content)
        content = re.sub(r"background:\s*['\"]#000000['\"]", "background: T.bgMain", content)
        content = re.sub(r"background:\s*['\"]rgba\(23, 23, 23, 0.95\)['\"]", "background: T.bgHeader", content)
        content = re.sub(r"background:\s*['\"]rgba\(23, 23, 23, 0.9\)['\"]", "background: T.bgHeader", content)
        content = re.sub(r"background:\s*['\"]rgba\(23, 23, 23, 0.8\)['\"]", "background: T.bgHeader", content)
        content = re.sub(r"background:\s*['\"]rgba\(38, 38, 38, 0.9\)['\"]", "background: T.bgActive", content)
        
        # Gradients
        content = re.sub(r"background:\s*'radial-gradient\(ellipse at center, #0a0a0a 0%, #000 100%\)'", "background: isDark() ? 'radial-gradient(ellipse at center, #0a0a0a 0%, #000 100%)' : 'radial-gradient(ellipse at center, rgba(255,255,255,0.4) 0%, rgba(244,244,245,0.8) 100%)'", content)
        
        # Borders
        content = re.sub(r"border:\s*['\"]1px solid #262626['\"]", "border: `1px solid ${T.border}`", content)
        content = re.sub(r"borderBottom:\s*['\"]1px solid #262626['\"]", "borderBottom: `1px solid ${T.border}`", content)
        content = re.sub(r"borderTop:\s*['\"]1px solid #262626['\"]", "borderTop: `1px solid ${T.border}`", content)
        
        # Text colors
        content = re.sub(r"color:\s*['\"]#fff['\"]", "color: T.text1", content)
        content = re.sub(r"color:\s*['\"]#d4d4d4['\"]", "color: T.text2", content)
        content = re.sub(r"color:\s*['\"]#a3a3a3['\"]", "color: T.text3", content)
        content = re.sub(r"color:\s*['\"]#737373['\"]", "color: T.textFaint", content)
        
        # ForceGraph specific drawing colors
        content = content.replace("backgroundColor=\"#000000\"", "backgroundColor={isDark() ? '#000000' : '#ffffff'}")
        
        # Node and link colors
        content = content.replace("ctx.strokeStyle = node.color || '#3b82f6'", "ctx.strokeStyle = node.color || T.accent")
        content = content.replace("const nodeColor = node.color || '#fff'", "const nodeColor = node.color || (isDark() ? '#fff' : '#18181b')")
        content = content.replace("ctx.fillStyle = '#fff'", "ctx.fillStyle = isDark() ? '#fff' : '#ffffff'")
        content = content.replace("ctx.fillStyle = '#ffffff'", "ctx.fillStyle = isDark() ? '#ffffff' : '#18181b'")
        content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)'", "ctx.fillStyle = isDark() ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.9)'")
        content = content.replace("ctx.strokeStyle = node.level === 0 ? '#3b82f6' : 'rgba(255, 255, 255, 0.3)'", "ctx.strokeStyle = node.level === 0 ? T.accent : (isDark() ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.15)')")
        content = content.replace("const linkColor = (link as any).color || '#555'", "const linkColor = (link as any).color || (isDark() ? '#555' : 'rgba(0,0,0,0.15)')")
        
        # Particle colors
        content = content.replace("color: ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)]", "color: isDark() ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)] : ['#18181b', '#52525b', '#2563eb', '#7e22ce', '#db2777', '#9333ea'][Math.floor(Math.random() * 6)]")
        
        # Legend colors
        content = content.replace("['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316']", "isDark() ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']")

    with open(file_path, "w") as f:
        f.write(content)

print("Applied perfect light mode color mapping")
