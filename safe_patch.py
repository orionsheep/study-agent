import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Make sure we don't double patch
if "const isDark =" not in content:
    # Add a safe, non-hook-based theme checker inside the render cycle (or just a helper)
    helper = "\nconst isDark = () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark');\n"
    content = content.replace("export default function WordList", helper + "export default function WordList")

# Now we replace the strings EXACTLY
replacements = [
    ("'#0a0a0a'", "(isDark()?'#0a0a0a':'transparent')"),
    ("'#171717'", "(isDark()?'#171717':'var(--glass-1)')"),
    ("'rgba(255,255,255,0.05)'", "(isDark()?'rgba(255,255,255,0.05)':'var(--glass-2)')"),
    ("'#262626'", "(isDark()?'#262626':'var(--glass-border)')"),
    ("'#404040'", "(isDark()?'#404040':'var(--glass-border-hi)')"),
    ("'#ffffff'", "(isDark()?'#ffffff':'var(--text-1)')"),
    ("'#fff'", "(isDark()?'#fff':'var(--text-1)')"),
    ("'#d4d4d4'", "(isDark()?'#d4d4d4':'var(--text-2)')"),
    ("'#a3a3a3'", "(isDark()?'#a3a3a3':'var(--text-3)')"),
    ("'#737373'", "(isDark()?'#737373':'var(--text-faint)')"),
    ("'#3b82f6'", "(isDark()?'#3b82f6':'var(--accent)')"),
    ("'rgba(37, 99, 235, 0.2)'", "(isDark()?'rgba(37, 99, 235, 0.2)':'var(--glass-2)')"),
    ("'#22c55e'", "(isDark()?'#22c55e':'var(--text-1)')"),
    ("'#eab308'", "(isDark()?'#eab308':'var(--text-2)')"),
    ("'#ef4444'", "(isDark()?'#ef4444':'var(--st-risk)')"),
    ("'#a855f7'", "(isDark()?'#a855f7':'var(--text-1)')"),
    ("'#c084fc'", "(isDark()?'#c084fc':'var(--text-2)')"),
    ("'rgba(168, 85, 247, 0.2)'", "(isDark()?'rgba(168, 85, 247, 0.2)':'var(--glass-2)')"),
    ("'#e5e5e5'", "(isDark()?'#e5e5e5':'var(--text-1)')"),
    ("'#525252'", "(isDark()?'#525252':'var(--text-3)')"),
    ("'#1a1a1a'", "(isDark()?'#1a1a1a':'var(--glass-border)')"),
    ("'linear-gradient(90deg, #fff, #8b5cf6)'", "(isDark()?'linear-gradient(90deg, #fff, #8b5cf6)':'var(--text-1)')")
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)
print("Patched WordList")
