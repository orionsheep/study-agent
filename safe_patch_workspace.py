import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx"
with open(file_path, "r") as f:
    content = f.read()

if "const isDark =" not in content:
    helper = "\nconst isDark = () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark');\n"
    content = content.replace("export function EnglishWorkspaceApp", helper + "export function EnglishWorkspaceApp")

replacements = [
    ("'#0a0a0a'", "(isDark()?'#0a0a0a':'transparent')"),
    ("'#000'", "(isDark()?'#000':'transparent')"),
    ("'#000000'", "(isDark()?'#000000':'transparent')"),
    ("'#171717'", "(isDark()?'#171717':'var(--glass-border)')"),
    ("'rgba(23,23,23,0.6)'", "(isDark()?'rgba(23,23,23,0.6)':'var(--glass-2)')"),
    ("'rgba(10,10,10,0.6)'", "(isDark()?'rgba(10,10,10,0.6)':'var(--glass-1)')"),
    ("'rgba(255,255,255,0.05)'", "(isDark()?'rgba(255,255,255,0.05)':'var(--glass-2)')"),
    ("'#262626'", "(isDark()?'#262626':'var(--glass-border)')"),
    ("'#404040'", "(isDark()?'#404040':'var(--glass-border-hi)')"),
    ("'#ffffff'", "(isDark()?'#ffffff':'var(--text-1)')"),
    ("'#fff'", "(isDark()?'#fff':'var(--text-1)')"),
    ("'rgba(255,255,255,0.9)'", "(isDark()?'rgba(255,255,255,0.9)':'var(--text-1)')"),
    ("'rgba(255,255,255,0.6)'", "(isDark()?'rgba(255,255,255,0.6)':'var(--text-3)')"),
    ("'rgba(255,255,255,0.85)'", "(isDark()?'rgba(255,255,255,0.85)':'var(--text-2)')"),
    ("'rgba(255,255,255,0.2)'", "(isDark()?'rgba(255,255,255,0.2)':'var(--glass-border)')"),
    ("'#d4d4d4'", "(isDark()?'#d4d4d4':'var(--text-2)')"),
    ("'#a3a3a3'", "(isDark()?'#a3a3a3':'var(--text-3)')"),
    ("'#737373'", "(isDark()?'#737373':'var(--text-faint)')"),
    ("'#3b82f6'", "(isDark()?'#3b82f6':'var(--accent)')"),
    ("'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)'", "(isDark()?'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)':'transparent')"),
    ("background: enabled ? 'rgba(255,255,255,0.1)' : 'transparent'", "background: enabled ? (isDark()?'rgba(255,255,255,0.1)':'var(--glass-2)') : 'transparent'"),
    ("color: enabled ? '#d4d4d4' : '#404040'", "color: enabled ? (isDark()?'#d4d4d4':'var(--text-2)') : (isDark()?'#404040':'var(--glass-border-hi)')"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)
print("Patched EnglishWorkspaceApp")
