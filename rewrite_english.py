import re

files = [
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
]

def add_helper(content):
    if "export const useDarkTheme =" in content:
        return content
        
    helper = """
export const useDarkTheme = () => {
  const [isDark, setIsDark] = useState(() => typeof document !== 'undefined' && document.documentElement.classList.contains('dark'));
  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  
  return {
    bgMain: isDark ? '#000000' : 'transparent',
    bgPanel: isDark ? '#0a0a0a' : 'transparent',
    bgHeader: isDark ? 'rgba(23, 23, 23, 0.6)' : 'transparent',
    bgHover: isDark ? 'rgba(255, 255, 255, 0.05)' : 'var(--glass-2)',
    bgActive: isDark ? 'rgba(23, 23, 23, 0.6)' : 'var(--glass-3)',
    border: isDark ? '#262626' : 'var(--glass-border)',
    borderHi: isDark ? '#404040' : 'var(--glass-border-hi)',
    borderActive: isDark ? 'rgba(255, 255, 255, 0.2)' : 'var(--glass-border-hi)',
    text1: isDark ? '#ffffff' : 'var(--text-1)',
    text2: isDark ? '#d4d4d4' : 'var(--text-2)',
    text3: isDark ? '#a3a3a3' : 'var(--text-3)',
    textFaint: isDark ? '#737373' : 'var(--text-faint)',
    accent: isDark ? '#3b82f6' : 'var(--accent)',
    accentLight: isDark ? '#60a5fa' : 'var(--accent)',
    accentBg: isDark ? 'rgba(37, 99, 235, 0.2)' : 'var(--accent-dim, rgba(0,0,0,0.05))',
    success: isDark ? '#22c55e' : 'var(--st-done)',
    warning: isDark ? '#eab308' : 'var(--st-weak)',
    danger: isDark ? '#ef4444' : 'var(--st-risk)',
    purple: isDark ? '#a855f7' : 'var(--accent)',
    purpleLight: isDark ? '#c084fc' : 'var(--text-2)',
    purpleBg: isDark ? 'rgba(168, 85, 247, 0.2)' : 'var(--glass-2)',
    isDark
  };
};
"""
    # Insert helper after imports
    if "import React" not in content and "import { " in content:
        content = content.replace("import { useState", "import { useState, useEffect")
        # Ensure we don't have duplicates
        content = content.replace("useEffect, useEffect", "useEffect")
        
        last_import_idx = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import '):
                last_import_idx = i
                
        lines.insert(last_import_idx + 1, helper)
        return '\n'.join(lines)
    return content

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()

    # Add helper definition
    content = add_helper(content)
    
    # Insert hook call at the start of the component
    if "EnglishWorkspaceApp" in file_path and "const T = useDarkTheme()" not in content:
        content = content.replace(
            "export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {\n",
            "export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {\n  const T = useDarkTheme();\n"
        )
    elif "WordList" in file_path and "const T = useDarkTheme()" not in content:
        content = content.replace(
            "export default function WordList({ onWordSelect, selectedWord }: WordListProps) {\n",
            "export default function WordList({ onWordSelect, selectedWord }: WordListProps) {\n  const T = useDarkTheme();\n"
        )
    elif "WordDetail" in file_path and "const T = useDarkTheme()" not in content:
        content = content.replace(
            "export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {\n",
            "export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {\n  const T = useDarkTheme();\n"
        )
    elif "FissionGraph" in file_path and "const T = useDarkTheme()" not in content:
        content = content.replace(
            "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n",
            "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n  const T = useDarkTheme();\n"
        )

    # REPLACEMENTS
    
    # General Backgrounds
    content = content.replace("'#0a0a0a'", "T.bgPanel")
    content = content.replace("'#000'", "T.bgMain")
    content = content.replace("'#000000'", "T.bgMain")
    content = content.replace('"#000000"', "T.bgMain")
    content = content.replace("'#171717'", "T.bgPanel")
    content = content.replace("'rgba(23,23,23,0.6)'", "T.bgActive")
    content = content.replace("'rgba(23, 23, 23, 0.95)'", "T.bgPanel")
    content = content.replace("'rgba(23, 23, 23, 0.9)'", "T.bgPanel")
    content = content.replace("'rgba(23, 23, 23, 0.8)'", "T.bgPanel")
    content = content.replace("'rgba(10,10,10,0.6)'", "T.bgHeader")
    content = content.replace("'rgba(255,255,255,0.05)'", "T.bgHover")
    content = content.replace("'rgba(255, 255, 255, 0.05)'", "T.bgHover")
    
    # Borders
    content = content.replace("'#262626'", "T.border")
    content = content.replace("'#404040'", "T.borderHi")
    content = content.replace("'rgba(255,255,255,0.2)'", "T.borderActive")
    content = content.replace("'rgba(255, 255, 255, 0.3)'", "T.borderHi")
    content = content.replace("'#1a1a1a'", "T.border")
    
    # Text
    content = content.replace("'#ffffff'", "T.text1")
    content = content.replace("'#fff'", "T.text1")
    content = content.replace('"#fff"', "T.text1")
    content = content.replace("'rgba(255,255,255,0.9)'", "T.text1")
    content = content.replace("'rgba(255, 255, 255, 1)'", "T.text1")
    content = content.replace("'#e5e5e5'", "T.text1")
    
    content = content.replace("'rgba(255,255,255,0.85)'", "T.text2")
    content = content.replace("'#d4d4d4'", "T.text2")
    content = content.replace("'#c084fc'", "T.purpleLight")
    content = content.replace("'#60a5fa'", "T.accentLight")
    content = content.replace("'#fef08a'", "T.warningLight")
    
    content = content.replace("'#a3a3a3'", "T.text3")
    content = content.replace("'rgba(255,255,255,0.6)'", "T.text3")
    content = content.replace("'#525252'", "T.text3")
    content = content.replace("'#555'", "T.text3")
    
    content = content.replace("'#737373'", "T.textFaint")
    
    # Semantic Colors
    content = content.replace("'#3b82f6'", "T.accent")
    content = content.replace("'rgba(37, 99, 235, 0.2)'", "T.accentBg")
    content = content.replace("'#22c55e'", "T.success")
    content = content.replace("'#eab308'", "T.warning")
    content = content.replace("'#ef4444'", "T.danger")
    content = content.replace("'#f97316'", "T.orange")
    content = content.replace("'#a855f7'", "T.purple")
    content = content.replace("'rgba(168, 85, 247, 0.2)'", "T.purpleBg")

    # Specific complex strings
    if "EnglishWorkspaceApp" in file_path:
        content = content.replace("'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, T.bgMain 70%)'", "T.isDark ? 'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)' : 'transparent'")
        # Fix the hover logic that got broken
        content = content.replace("background: enabled ? 'rgba(255,255,255,0.1)' : 'transparent'", "background: enabled ? T.bgHover : 'transparent'")
        content = content.replace("color: enabled ? T.text2 : T.borderHi", "color: enabled ? T.text2 : T.borderHi")
        
    if "FissionGraph" in file_path:
        content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)'", "ctx.fillStyle = T.isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.9)'")
        content = content.replace("color: ['T.text1', 'T.text1', 'T.accent', '#8b5cf6', '#ec4899', '#a78bfa']", "color: T.isDark ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'] : ['#18181b', '#18181b', '#2563eb', '#7e22ce', '#db2777', '#9333ea']")
        content = content.replace("['T.danger', 'T.accent', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', 'T.orange']", "T.isDark ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']")
        content = content.replace("const nodeColor = node.color || 'T.text1'", "const nodeColor = node.color || T.text1")
        content = content.replace("ctx.fillStyle = 'T.text1'", "ctx.fillStyle = T.text1")
        content = content.replace("ctx.strokeStyle = node.color || 'T.accent'", "ctx.strokeStyle = node.color || T.accent")
        content = content.replace("const linkColor = (link as any).color || 'T.text3'", "const linkColor = (link as any).color || T.borderHi")
        content = content.replace("ctx.strokeStyle = node.level === 0 ? 'T.accent' : 'T.borderHi'", "ctx.strokeStyle = node.level === 0 ? T.accent : T.borderHi")

    with open(file_path, "w") as f:
        f.write(content)

print("Applied perfect T theme to all English components")
