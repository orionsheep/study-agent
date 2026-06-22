import re

files = [
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx",
]

replacements = [
    (r"'#0a0a0a'", "'var(--ew-bg-panel, #0a0a0a)'"),
    (r"'#000'", "'var(--ew-bg-main, #000)'"),
    (r"'#000000'", "'var(--ew-bg-main, #000000)'"),
    (r'"#000000"', "'var(--ew-bg-main, #000000)'"),
    (r"'#171717'", "'var(--ew-bg-card, #171717)'"),
    (r"'rgba\(23,23,23,0\.6\)'", "'var(--ew-bg-active, rgba(23,23,23,0.6))'"),
    (r"'rgba\(23, 23, 23, 0\.6\)'", "'var(--ew-bg-active, rgba(23, 23, 23, 0.6))'"),
    (r"'rgba\(10,10,10,0\.6\)'", "'var(--ew-bg-header, rgba(10,10,10,0.6))'"),
    (r"'rgba\(23, 23, 23, 0\.95\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.95))'"),
    (r"'rgba\(23, 23, 23, 0\.9\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.9))'"),
    (r"'rgba\(23, 23, 23, 0\.8\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.8))'"),
    (r"'rgba\(255,255,255,0\.05\)'", "'var(--ew-bg-hover, rgba(255,255,255,0.05))'"),
    (r"'rgba\(255, 255, 255, 0\.05\)'", "'var(--ew-bg-hover, rgba(255, 255, 255, 0.05))'"),
    (r"'#262626'", "'var(--ew-border, #262626)'"),
    (r"'#404040'", "'var(--ew-border-hi, #404040)'"),
    (r"'rgba\(255, 255, 255, 0\.3\)'", "'var(--ew-border-hi, rgba(255, 255, 255, 0.3))'"),
    (r"'#1a1a1a'", "'var(--ew-border, #1a1a1a)'"),
    (r"'#ffffff'", "'var(--ew-text-1, #ffffff)'"),
    (r"'#fff'", "'var(--ew-text-1, #fff)'"),
    (r'"#fff"', "'var(--ew-text-1, #fff)'"),
    (r"'rgba\(255,255,255,0\.9\)'", "'var(--ew-text-1, rgba(255,255,255,0.9))'"),
    (r"'rgba\(255, 255, 255, 1\)'", "'var(--ew-text-1, rgba(255, 255, 255, 1))'"),
    (r"'#e5e5e5'", "'var(--ew-text-1, #e5e5e5)'"),
    (r"'rgba\(255,255,255,0\.85\)'", "'var(--ew-text-2, rgba(255,255,255,0.85))'"),
    (r"'#d4d4d4'", "'var(--ew-text-2, #d4d4d4)'"),
    (r"'#a3a3a3'", "'var(--ew-text-3, #a3a3a3)'"),
    (r"'rgba\(255,255,255,0\.6\)'", "'var(--ew-text-3, rgba(255,255,255,0.6))'"),
    (r"'#525252'", "'var(--ew-text-3, #525252)'"),
    (r"'#555'", "'var(--ew-text-3, #555)'"),
    (r"'#737373'", "'var(--ew-text-faint, #737373)'"),
    (r"'#3b82f6'", "'var(--ew-accent, #3b82f6)'"),
    (r"'#60a5fa'", "'var(--ew-accent-light, #60a5fa)'"),
    (r"'rgba\(37, 99, 235, 0\.2\)'", "'var(--ew-accent-bg, rgba(37, 99, 235, 0.2))'"),
    (r"'#22c55e'", "'var(--ew-success, #22c55e)'"),
    (r"'#eab308'", "'var(--ew-warning, #eab308)'"),
    (r"'#fef08a'", "'var(--ew-warning-light, #fef08a)'"),
    (r"'#ef4444'", "'var(--ew-danger, #ef4444)'"),
    (r"'#f97316'", "'var(--ew-orange, #f97316)'"),
    (r"'#a855f7'", "'var(--ew-purple, #a855f7)'"),
    (r"'#c084fc'", "'var(--ew-purple-light, #c084fc)'"),
    (r"'rgba\(168, 85, 247, 0\.2\)'", "'var(--ew-purple-bg, rgba(168, 85, 247, 0.2))'"),
]

for file_path in files:
    with open(file_path, "r") as f:
        content = f.read()

    for old, new in replacements:
        content = re.sub(old, new, content)
        
    if "EnglishWorkspaceApp" in file_path:
        content = content.replace(
            "'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, var(--ew-bg-main, #000) 70%)'", 
            "'radial-gradient(ellipse at center, var(--ew-gradient-start, rgba(38,38,38,0.2)) 0%, var(--ew-bg-main, #000) 70%)'"
        )

    with open(file_path, "w") as f:
        f.write(content)

print("Injected CSS variables successfully!")
