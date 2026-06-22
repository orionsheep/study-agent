import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add useTheme import
if "useTheme" not in content:
    content = content.replace(
        "import { useState, useMemo", 
        "import { useState, useMemo } from 'react';\nimport { useTheme } from '../../../../lib/state/useTheme';\n//"
    )
    # Fix potential double import if we messed up
    content = content.replace("from 'react';\n// } from 'react';", "from 'react';")

# Find the WordList function
content = content.replace(
    "export default function WordList({",
    "export default function WordList({"
)

# Insert theme hook inside WordList
theme_hook = """
  const { theme } = useTheme();
  const t = useMemo(() => ({
    bgMain: theme === 'dark' ? '#0a0a0a' : '#f8f8f9',
    bgPanel: theme === 'dark' ? '#0a0a0a' : '#ffffff',
    bgHover: theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)',
    bgActive: theme === 'dark' ? '#171717' : '#f4f4f5',
    border: theme === 'dark' ? '#262626' : 'rgba(0,0,0,0.08)',
    borderHi: theme === 'dark' ? '#404040' : 'rgba(0,0,0,0.15)',
    text1: theme === 'dark' ? '#ffffff' : '#18181b',
    text2: theme === 'dark' ? '#d4d4d4' : '#52525b',
    text3: theme === 'dark' ? '#a3a3a3' : '#a1a1aa',
    textFaint: theme === 'dark' ? '#737373' : '#d4d4d8',
    accent: theme === 'dark' ? '#3b82f6' : '#18181b',
    accentBg: theme === 'dark' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(24, 24, 27, 0.08)',
    success: theme === 'dark' ? '#22c55e' : '#18181b',
    warning: theme === 'dark' ? '#eab308' : '#52525b',
    danger: theme === 'dark' ? '#ef4444' : '#dc2626',
    userLib: theme === 'dark' ? '#a855f7' : '#18181b',
    userLibText: theme === 'dark' ? '#c084fc' : '#52525b',
    userLibBg: theme === 'dark' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(24, 24, 27, 0.08)',
  }), [theme]);
"""

if "const t = useMemo" not in content:
    content = re.sub(
        r'(export default function WordList\(\{.*?\}.*?\{)',
        r'\1' + theme_hook,
        content,
        flags=re.DOTALL
    )

# Safely replace hardcoded strings with t.xxx
replacements = [
    ("'#0a0a0a'", "t.bgMain"),
    ("'#171717'", "t.bgActive"),
    ("'rgba(255,255,255,0.05)'", "t.bgHover"),
    ("'#262626'", "t.border"),
    ("'#404040'", "t.borderHi"),
    ("'#ffffff'", "t.text1"),
    ("'#fff'", "t.text1"),
    ("'#d4d4d4'", "t.text2"),
    ("'#a3a3a3'", "t.text3"),
    ("'#737373'", "t.textFaint"),
    ("'#3b82f6'", "t.accent"),
    ("'rgba(37, 99, 235, 0.2)'", "t.accentBg"),
    ("'#22c55e'", "t.success"),
    ("'#eab308'", "t.warning"),
    ("'#ef4444'", "t.danger"),
    ("'#a855f7'", "t.userLib"),
    ("'#c084fc'", "t.userLibText"),
    ("'rgba(168, 85, 247, 0.2)'", "t.userLibBg"),
    ("'#e5e5e5'", "t.text1"),
    ("'#525252'", "t.text3"),
    ("'#1a1a1a'", "t.border"),
    ("'linear-gradient(90deg, #fff, #8b5cf6)'", "theme === 'dark' ? 'linear-gradient(90deg, #fff, #8b5cf6)' : t.text1")
]

for old, new in replacements:
    content = content.replace(old, new)

# Fix ternary operators that were broken by simple string replacement
content = content.replace("background: selectedWordsForQuiz.size === 0 ? t.border : t.accent", "background: selectedWordsForQuiz.size === 0 ? t.border : t.accent")
content = content.replace("background: isSelectMode ? t.accentBg : 'transparent'", "background: isSelectMode ? t.accentBg : 'transparent'")
content = content.replace("color: isSelectMode ? t.text1 : t.textFaint", "color: isSelectMode ? t.text1 : t.textFaint")

with open(file_path, "w") as f:
    f.write(content)
print("WordList patched")
