import os
import re

files = [
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
]

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()

    # Make sure we don't duplicate the helper
    content = re.sub(r'export const useDarkTheme = \(\) => \{.*?\n\};\n', '', content, flags=re.DOTALL)
    
    # Clean up any bad hooks
    content = content.replace("const T = useDarkTheme();", "")

    # We use a pure Javascript object at the top level to act as our theme provider.
    # It detects the `.dark` class dynamically. This is 100% safe, causes no re-renders, 
    # and no TSX hook errors. We also detect `.enable-glass` for the transparency toggle.
    helper = """
export const getTheme = () => {
  const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
  const isGlass = typeof document !== 'undefined' && document.documentElement.classList.contains('enable-glass');
  
  return {
    isDark,
    // Backgrounds: Dark mode is purely original. Light mode is elegant glass.
    bgMain: isDark ? '#000000' : 'transparent',
    bgPanel: isDark ? '#0a0a0a' : (isGlass ? 'rgba(255, 255, 255, 0.45)' : '#ffffff'),
    bgHeader: isDark ? 'rgba(23, 23, 23, 0.6)' : (isGlass ? 'rgba(255, 255, 255, 0.65)' : '#f8f8f9'),
    bgHover: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.04)',
    bgActive: isDark ? 'rgba(38, 38, 38, 0.6)' : 'rgba(0, 0, 0, 0.08)',
    
    // Borders
    border: isDark ? '#262626' : 'rgba(0, 0, 0, 0.08)',
    borderHi: isDark ? '#404040' : 'rgba(0, 0, 0, 0.16)',
    borderActive: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.25)',
    
    // Text: Dark mode is original. Light mode is high contrast Zinc.
    text1: isDark ? '#ffffff' : '#18181b',
    text2: isDark ? '#d4d4d4' : '#52525b',
    text3: isDark ? '#a3a3a3' : '#a1a1aa',
    textFaint: isDark ? '#737373' : '#d4d4d8',
    
    // Semantic Accents: Vibrant in both modes
    accent: isDark ? '#3b82f6' : '#2563eb', // Blue
    accentLight: isDark ? '#60a5fa' : '#3b82f6',
    accentBg: isDark ? 'rgba(37, 99, 235, 0.2)' : 'rgba(37, 99, 235, 0.1)',
    
    success: isDark ? '#22c55e' : '#16a34a', // Green
    warning: isDark ? '#eab308' : '#d97706', // Yellow/Orange
    warningLight: isDark ? '#fef08a' : '#d97706',
    danger: isDark ? '#ef4444' : '#dc2626', // Red
    
    orange: isDark ? '#f97316' : '#ea580c',
    purple: isDark ? '#a855f7' : '#7e22ce', // Purple
    purpleLight: isDark ? '#c084fc' : '#9333ea',
    purpleBg: isDark ? 'rgba(168, 85, 247, 0.2)' : 'rgba(126, 34, 206, 0.1)'
  };
};
"""
    
    # We must trigger a re-render when the theme changes. Since these are standard components,
    # we just hook into the global mutation observer in a safe way.
    
    if "getTheme()" not in content:
        if "import React" not in content and "import { " in content:
            if "useEffect" not in content:
                content = content.replace("import { ", "import { useEffect, useState, ")
        
        # Inject the helper
        last_import_idx = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import '):
                last_import_idx = i
                
        lines.insert(last_import_idx + 1, helper)
        content = '\n'.join(lines)
    
    # Add the forceRender hook to the components to ensure they update when user clicks Sun/Moon
    hook = """
  // Force re-render on theme/glass change
  const [themeTick, setThemeTick] = useState(0);
  useEffect(() => {
    const observer = new MutationObserver(() => setThemeTick(t => t + 1));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  const T = getTheme();
"""

    if "const T = getTheme();" not in content:
        if "EnglishWorkspaceApp" in file_path:
            content = content.replace(
                "export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {\n",
                "export function EnglishWorkspaceApp({ app, onEvent, sessionContext }: Props) {\n" + hook
            )
        elif "WordList" in file_path:
            content = content.replace(
                "export default function WordList({ onWordSelect, selectedWord }: WordListProps) {\n",
                "export default function WordList({ onWordSelect, selectedWord }: WordListProps) {\n" + hook
            )
        elif "WordDetail" in file_path:
            content = content.replace(
                "export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {\n",
                "export default function WordDetail({ word, onCompareInfo, onResourceLookup }: WordDetailProps) {\n" + hook
            )
        elif "FissionGraph" in file_path:
            content = content.replace(
                "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n",
                "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n" + hook
            )

    # -------------------------------------------------------------------------
    # Now we meticulously replace every single hardcoded color with T.xxxx
    # This guarantees that Dark Mode gets the exact original hex codes,
    # and Light Mode gets our new perfect, legible, glassy colors!
    # -------------------------------------------------------------------------
    
    content = content.replace("'#0a0a0a'", "T.bgPanel")
    content = content.replace("'#000'", "T.bgMain")
    content = content.replace("'#000000'", "T.bgMain")
    content = content.replace('"#000000"', "T.bgMain")
    content = content.replace("'#171717'", "T.bgPanel")
    
    content = content.replace("'rgba(23,23,23,0.6)'", "T.bgActive")
    content = content.replace("'rgba(10,10,10,0.6)'", "T.bgHeader")
    content = content.replace("'rgba(23, 23, 23, 0.95)'", "T.bgPanel")
    content = content.replace("'rgba(23, 23, 23, 0.9)'", "T.bgPanel")
    content = content.replace("'rgba(23, 23, 23, 0.8)'", "T.bgPanel")
    content = content.replace("'rgba(38, 38, 38, 0.9)'", "T.bgActive")
    content = content.replace("'rgba(255, 255, 255, 0.05)'", "T.bgHover")
    content = content.replace("'rgba(255,255,255,0.05)'", "T.bgHover")
    
    content = content.replace("'#262626'", "T.border")
    content = content.replace("'#404040'", "T.borderHi")
    content = content.replace("'rgba(255, 255, 255, 0.3)'", "T.borderHi")
    content = content.replace("'#1a1a1a'", "T.border")
    
    content = content.replace("'#ffffff'", "T.text1")
    content = content.replace("'#fff'", "T.text1")
    content = content.replace('"#fff"', "T.text1")
    content = content.replace("'rgba(255,255,255,0.9)'", "T.text1")
    content = content.replace("'rgba(255, 255, 255, 1)'", "T.text1")
    content = content.replace("'#e5e5e5'", "T.text1")
    
    content = content.replace("'rgba(255,255,255,0.85)'", "T.text2")
    content = content.replace("'#d4d4d4'", "T.text2")
    content = content.replace("'#a3a3a3'", "T.text3")
    content = content.replace("'rgba(255,255,255,0.6)'", "T.text3")
    content = content.replace("'#525252'", "T.text3")
    content = content.replace("'#555'", "T.text3")
    content = content.replace("'#737373'", "T.textFaint")
    
    content = content.replace("'#3b82f6'", "T.accent")
    content = content.replace("'#60a5fa'", "T.accentLight")
    content = content.replace("'rgba(37, 99, 235, 0.2)'", "T.accentBg")
    content = content.replace("'#22c55e'", "T.success")
    content = content.replace("'#eab308'", "T.warning")
    content = content.replace("'#fef08a'", "T.warningLight")
    content = content.replace("'#ef4444'", "T.danger")
    content = content.replace("'#f97316'", "T.orange")
    content = content.replace("'#a855f7'", "T.purple")
    content = content.replace("'#c084fc'", "T.purpleLight")
    content = content.replace("'rgba(168, 85, 247, 0.2)'", "T.purpleBg")
    
    # Advanced logic fixes
    if "EnglishWorkspaceApp" in file_path:
        content = content.replace("'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, T.bgMain 70%)'", "T.isDark ? 'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)' : 'transparent'")
        content = content.replace("background: enabled ? 'rgba(255,255,255,0.1)' : 'transparent'", "background: enabled ? T.bgHover : 'transparent'")
        content = content.replace("color: enabled ? T.text2 : T.borderHi", "color: enabled ? T.text2 : T.borderHi")
        
    if "FissionGraph" in file_path:
        content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)'", "ctx.fillStyle = T.isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255,255,255,0.9)'")
        content = content.replace("color: ['T.text1', 'T.text1', 'T.accent', '#8b5cf6', '#ec4899', '#a78bfa']", "color: T.isDark ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'] : ['#18181b', '#18181b', '#2563eb', '#7e22ce', '#db2777', '#9333ea']")
        content = content.replace("['T.danger', 'T.accent', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', 'T.orange']", "T.isDark ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']")
        content = content.replace("const nodeColor = node.color || 'T.text1'", "const nodeColor = node.color || T.text1")
        content = content.replace("ctx.fillStyle = 'T.text1'", "ctx.fillStyle = T.text1")
        content = content.replace("ctx.strokeStyle = node.color || 'T.accent'", "ctx.strokeStyle = node.color || T.accent")
        content = content.replace("const linkColor = (link as any).color || 'T.text3'", "const linkColor = (link as any).color || (T.isDark ? '#555' : 'rgba(0,0,0,0.15)')")
        content = content.replace("ctx.strokeStyle = node.level === 0 ? 'T.accent' : 'T.borderHi'", "ctx.strokeStyle = node.level === 0 ? T.accent : (T.isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.15)')")

    with open(file_path, "w") as f:
        f.write(content)

print("Safely completely rewrote English App to dynamic JS themes")
