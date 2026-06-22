import os
import re

files = [
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/EnglishDashboard.tsx",
    "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/QuizPanel.tsx"
]

def process_html_styles(content):
    # This safely replaces hardcoded colors in React style objects with CSS variables
    # We do NOT touch FissionGraph.tsx canvas drawing logic here, only style={{...}} blocks
    
    # Backgrounds
    content = content.replace("background: '#0a0a0a'", "background: 'var(--bg-1)'")
    content = content.replace("backgroundColor: '#0a0a0a'", "backgroundColor: 'var(--bg-1)'")
    content = content.replace("background: '#000'", "background: 'var(--bg-0)'")
    content = content.replace("background: '#000000'", "background: 'var(--bg-0)'")
    content = content.replace("background: '#171717'", "background: 'var(--bg-2)'")
    content = content.replace("background: 'rgba(23,23,23,0.6)'", "background: 'var(--glass-2)'")
    content = content.replace("background: 'rgba(10,10,10,0.6)'", "background: 'var(--glass-1)'")
    content = content.replace("background: 'rgba(255,255,255,0.05)'", "background: 'var(--glass-2)'")
    content = content.replace("background: 'rgba(255, 255, 255, 0.05)'", "background: 'var(--glass-2)'")
    
    # Borders
    content = content.replace("border: '1px solid #262626'", "border: '1px solid var(--glass-border)'")
    content = content.replace("borderRight: '1px solid #262626'", "borderRight: '1px solid var(--glass-border)'")
    content = content.replace("borderBottom: '1px solid #262626'", "borderBottom: '1px solid var(--glass-border)'")
    content = content.replace("borderTop: '1px solid #171717'", "borderTop: '1px solid var(--glass-border)'")
    content = content.replace("borderColor: '#404040'", "borderColor: 'var(--glass-border-hi)'")
    content = content.replace("borderColor: '#262626'", "borderColor: 'var(--glass-border)'")
    
    # Text colors
    content = content.replace("color: '#ffffff'", "color: 'var(--text-1)'")
    content = content.replace("color: '#fff'", "color: 'var(--text-1)'")
    content = content.replace("color: '#e5e5e5'", "color: 'var(--text-1)'")
    content = content.replace("color: '#d4d4d4'", "color: 'var(--text-2)'")
    content = content.replace("color: '#a3a3a3'", "color: 'var(--text-3)'")
    content = content.replace("color: '#737373'", "color: 'var(--text-faint)'")
    
    # Accents
    content = content.replace("color: '#3b82f6'", "color: 'var(--accent)'")
    content = content.replace("color: '#60a5fa'", "color: 'var(--accent)'")
    content = content.replace("background: 'rgba(37, 99, 235, 0.2)'", "background: 'var(--accent-bg, rgba(37, 99, 235, 0.1))'")
    content = content.replace("color: '#22c55e'", "color: 'var(--st-done)'")
    content = content.replace("color: '#eab308'", "color: 'var(--st-weak)'")
    content = content.replace("color: '#ef4444'", "color: 'var(--st-risk)'")
    content = content.replace("color: '#f97316'", "color: '#ea580c'")
    content = content.replace("color: '#a855f7'", "color: '#9333ea'")
    content = content.replace("color: '#c084fc'", "color: '#a855f7'")

    return content

for file_path in files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # Apply general HTML style replacements
    if "FissionGraph.tsx" not in file_path:
        content = process_html_styles(content)
        
        # Specific complex replacements
        if "EnglishWorkspaceApp" in file_path:
            content = content.replace("background: 'radial-gradient(ellipse at center, rgba(38,38,38,0.2) 0%, #000 70%)'", "background: 'radial-gradient(ellipse at center, var(--glass-border) 0%, var(--bg-0) 70%)'")
            content = content.replace("background: enabled ? 'rgba(255,255,255,0.1)' : 'transparent'", "background: enabled ? 'var(--glass-2)' : 'transparent'")
            content = content.replace("color: enabled ? '#d4d4d4' : '#404040'", "color: enabled ? 'var(--text-1)' : 'var(--text-3)'")
        elif "WordList" in file_path:
            content = content.replace("background: selectedWordsForQuiz.size === 0 ? '#262626' : '#2563eb'", "background: selectedWordsForQuiz.size === 0 ? 'var(--glass-border)' : 'var(--accent)'")
            content = content.replace("background: isSelectMode ? 'rgba(37, 99, 235, 0.2)' : 'transparent'", "background: isSelectMode ? 'var(--accent-bg, rgba(37, 99, 235, 0.1))' : 'transparent'")
            content = content.replace("color: isSelectMode ? '#fff' : '#737373'", "color: isSelectMode ? 'var(--text-1)' : 'var(--text-3)'")
            content = content.replace("background: 'linear-gradient(90deg, #fff, #8b5cf6)'", "background: 'linear-gradient(90deg, var(--text-1), #8b5cf6)'")

    with open(file_path, "w") as f:
        f.write(content)

print("HTML styles replaced with CSS variables safely")
