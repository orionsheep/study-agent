import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx"
with open(file_path, "r") as f:
    content = f.read()

if "const isDark =" not in content:
    helper = "\nconst isDark = () => typeof document !== 'undefined' && document.documentElement.classList.contains('dark');\n"
    content = content.replace("export default function WordDetail", helper + "export default function WordDetail")

replacements = [
    ("'#0a0a0a'", "(isDark()?'#0a0a0a':'transparent')"),
    ("'#171717'", "(isDark()?'#171717':'transparent')"),
    ("'rgba(255, 255, 255, 0.05)'", "(isDark()?'rgba(255, 255, 255, 0.05)':'var(--glass-2)')"),
    ("'rgba(255,255,255,0.05)'", "(isDark()?'rgba(255,255,255,0.05)':'var(--glass-2)')"),
    ("'#262626'", "(isDark()?'#262626':'var(--glass-border)')"),
    ("'#404040'", "(isDark()?'#404040':'var(--glass-border-hi)')"),
    ("'#ffffff'", "(isDark()?'#ffffff':'var(--text-1)')"),
    ("'#fff'", "(isDark()?'#fff':'var(--text-1)')"),
    ("'#e5e5e5'", "(isDark()?'#e5e5e5':'var(--text-1)')"),
    ("'#d4d4d4'", "(isDark()?'#d4d4d4':'var(--text-2)')"),
    ("'#a3a3a3'", "(isDark()?'#a3a3a3':'var(--text-3)')"),
    ("'#525252'", "(isDark()?'#525252':'var(--text-3)')"),
    ("'#737373'", "(isDark()?'#737373':'var(--text-faint)')"),
    ("'#3b82f6'", "(isDark()?'#3b82f6':'var(--accent)')"),
    ("'#60a5fa'", "(isDark()?'#60a5fa':'var(--text-2)')"),
    ("'#22c55e'", "(isDark()?'#22c55e':'var(--text-1)')"),
    ("'#eab308'", "(isDark()?'#eab308':'var(--text-2)')"),
    ("'#fef08a'", "(isDark()?'#fef08a':'var(--text-2)')"),
    ("'#f97316'", "(isDark()?'#f97316':'var(--text-2)')"),
    ("'#a855f7'", "(isDark()?'#a855f7':'var(--text-1)')"),
    ("'#c084fc'", "(isDark()?'#c084fc':'var(--text-2)')"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(file_path, "w") as f:
    f.write(content)
print("Patched WordDetail")
