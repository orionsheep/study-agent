import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add useTheme import
if "useTheme" not in content:
    content = content.replace(
        "import { useState", 
        "import { useState, useMemo } from 'react';\nimport { useTheme } from '../../../../lib/state/useTheme';\n// import { useState"
    )
    content = content.replace("from 'react';\n// import { useState", "from 'react';\nimport { useState")

theme_hook = """
  const { theme } = useTheme();
  const t = useMemo(() => ({
    bgMain: theme === 'dark' ? '#000000' : 'transparent',
    bgPanel: theme === 'dark' ? '#0a0a0a' : 'transparent',
    bgHeader: theme === 'dark' ? 'rgba(10,10,10,0.6)' : 'var(--glass-1)',
    bgActive: theme === 'dark' ? 'rgba(23,23,23,0.6)' : 'var(--glass-2)',
    bgHover: theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'var(--glass-3)',
    border: theme === 'dark' ? '#262626' : 'var(--glass-border)',
    borderHi: theme === 'dark' ? '#404040' : 'var(--glass-border-hi)',
    text1: theme === 'dark' ? '#ffffff' : 'var(--text-1)',
    text2: theme === 'dark' ? '#d4d4d4' : 'var(--text-2)',
    text3: theme === 'dark' ? '#a3a3a3' : 'var(--text-3)',
    textFaint: theme === 'dark' ? '#737373' : 'var(--text-faint)',
    accent: theme === 'dark' ? '#3b82f6' : 'var(--text-1)',
    accentBg: theme === 'dark' ? 'rgba(37, 99, 235, 0.2)' : 'var(--glass-2)',
  }), [theme]);
"""

if "const t = useMemo" not in content:
    content = re.sub(
        r'(export function EnglishWorkspaceApp\(\{.*?\}.*?\{)',
        r'\1' + theme_hook,
        content,
        flags=re.DOTALL
    )

replacements = [
    ("'#0a0a0a'", "t.bgPanel"),
    ("'#000'", "t.bgMain"),
    ("'#000000'", "t.bgMain"),
    ("'#171717'", "t.border"),
    ("'rgba(23,23,23,0.6)'", "t.bgActive"),
    ("'rgba(10,10,10,0.6)'", "t.bgHeader"),
    ("'rgba(255,255,255,0.05)'", "t.bgHover"),
    ("'#262626'", "t.border"),
    ("'#404040'", "t.borderHi"),
    ("'#ffffff'", "t.text1"),
    ("'#fff'", "t.text1"),
    ("'rgba(255,255,255,0.9)'", "t.text1"),
    ("'rgba(255,255,255,0.6)'", "t.text3"),
    ("'rgba(255,255,255,0.85)'", "t.text2"),
    ("'rgba(255,255,255,0.2)'", "t.border"),
    ("'#d4d4d4'", "t.text2"),
    ("'#a3a3a3'", "t.text3"),
    ("'#737373'", "t.textFaint"),
    ("'#3b82f6'", "t.accent"),
]

for old, new in replacements:
    content = content.replace(old, new)

content = content.replace("background: enabled ? 'rgba(255,255,255,0.1)' : 'transparent'", "background: enabled ? t.bgHover : 'transparent'")
content = content.replace("color: enabled ? t.text2 : t.border", "color: enabled ? t.text2 : t.borderHi")

with open(file_path, "w") as f:
    f.write(content)
print("English Workspace patched")
