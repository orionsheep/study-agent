import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add useTheme import
if "useTheme" not in content:
    content = content.replace(
        "import { useState, useEffect", 
        "import { useState, useEffect, useMemo } from 'react';\nimport { useTheme } from '../../../../lib/state/useTheme';\n//"
    )
    content = content.replace("from 'react';\n// } from 'react';", "from 'react';")

# Insert theme hook inside WordDetail
theme_hook = """
  const { theme } = useTheme();
  const t = useMemo(() => ({
    bgMain: theme === 'dark' ? '#0a0a0a' : '#ffffff',
    bgPanel: theme === 'dark' ? '#171717' : '#f8f8f9',
    bgHover: theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0,0,0,0.04)',
    bgActive: theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0,0,0,0.08)',
    border: theme === 'dark' ? '#262626' : 'rgba(0,0,0,0.08)',
    borderHi: theme === 'dark' ? '#404040' : 'rgba(0,0,0,0.15)',
    text1: theme === 'dark' ? '#ffffff' : '#18181b',
    text2: theme === 'dark' ? '#d4d4d4' : '#52525b',
    text3: theme === 'dark' ? '#a3a3a3' : '#a1a1aa',
    textFaint: theme === 'dark' ? '#737373' : '#d4d4d8',
    accent: theme === 'dark' ? '#3b82f6' : '#18181b',
    accentLight: theme === 'dark' ? '#60a5fa' : '#52525b',
    success: theme === 'dark' ? '#22c55e' : '#18181b',
    warning: theme === 'dark' ? '#eab308' : '#52525b',
    warningLight: theme === 'dark' ? '#fef08a' : '#18181b',
    danger: theme === 'dark' ? '#ef4444' : '#dc2626',
    orange: theme === 'dark' ? '#f97316' : '#52525b',
    purple: theme === 'dark' ? '#a855f7' : '#18181b',
    purpleLight: theme === 'dark' ? '#c084fc' : '#52525b',
  }), [theme]);
"""

if "const t = useMemo" not in content:
    content = re.sub(
        r'(export default function WordDetail\(\{.*?\}.*?\{)',
        r'\1' + theme_hook,
        content,
        flags=re.DOTALL
    )

# Safely replace hardcoded strings with t.xxx
replacements = [
    ("'#0a0a0a'", "t.bgMain"),
    ("'#171717'", "t.bgPanel"),
    ("'rgba(255, 255, 255, 0.05)'", "t.bgHover"),
    ("'rgba(255,255,255,0.05)'", "t.bgHover"),
    ("'#262626'", "t.border"),
    ("'#404040'", "t.borderHi"),
    ("'#ffffff'", "t.text1"),
    ("'#fff'", "t.text1"),
    ("'#e5e5e5'", "t.text1"),
    ("'#d4d4d4'", "t.text2"),
    ("'#a3a3a3'", "t.text3"),
    ("'#525252'", "t.text3"),
    ("'#737373'", "t.textFaint"),
    ("'#3b82f6'", "t.accent"),
    ("'#60a5fa'", "t.accentLight"),
    ("'#22c55e'", "t.success"),
    ("'#eab308'", "t.warning"),
    ("'#fef08a'", "t.warningLight"),
    ("'#f97316'", "t.orange"),
    ("'#a855f7'", "t.purple"),
    ("'#c084fc'", "t.purpleLight"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)
print("WordDetail patched")
