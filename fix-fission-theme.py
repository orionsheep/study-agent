import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Make sure we don't double inject
if "import { useTheme }" not in content:
    content = content.replace(
        "import { useRef, useEffect, useState, useMemo } from 'react';", 
        "import { useRef, useEffect, useState, useMemo } from 'react';\nimport { useTheme } from '../../../../lib/state/useTheme';"
    )

if "const { theme } = useTheme();" not in content:
    content = content.replace(
        "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {",
        "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n  const { theme } = useTheme();\n  const isDark = theme === 'dark';"
    )

# Fix background objects (use regular regex for strings)
content = re.sub(r"'#000'", "'var(--ew-bg-main, #000)'", content)
content = re.sub(r"'#000000'", "'var(--ew-bg-main, #000000)'", content)
content = re.sub(r"backgroundColor=\"#000000\"", "backgroundColor={isDark ? '#000000' : '#ffffff'}", content)

content = re.sub(r"'rgba\(23, 23, 23, 0\.95\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.95))'", content)
content = re.sub(r"'rgba\(23, 23, 23, 0\.9\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.9))'", content)
content = re.sub(r"'rgba\(23, 23, 23, 0\.8\)'", "'var(--ew-bg-panel, rgba(23, 23, 23, 0.8))'", content)

content = re.sub(r"'#262626'", "'var(--ew-border, #262626)'", content)

content = re.sub(r"'#737373'", "'var(--ew-text-faint, #737373)'", content)
content = re.sub(r"'#a3a3a3'", "'var(--ew-text-3, #a3a3a3)'", content)
content = re.sub(r"'#d4d4d4'", "'var(--ew-text-2, #d4d4d4)'", content)
content = re.sub(r"'#fff'", "'var(--ew-text-1, #fff)'", content)
content = re.sub(r"'#ffffff'", "'var(--ew-text-1, #ffffff)'", content)

# Canvas Drawing Logic
content = content.replace("ctx.strokeStyle = node.color || 'var(--ew-accent, #3b82f6)';", "ctx.strokeStyle = node.color || (isDark ? '#3b82f6' : '#2563eb');")
content = content.replace("const nodeColor = node.color || 'var(--ew-text-1, #fff)';", "const nodeColor = node.color || (isDark ? '#ffffff' : '#18181b');")
content = content.replace("ctx.fillStyle = 'var(--ew-text-1, #fff)';", "ctx.fillStyle = isDark ? '#ffffff' : '#18181b';")
content = content.replace("ctx.fillStyle = 'var(--ew-text-1, #ffffff)';", "ctx.fillStyle = '#ffffff';")
content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)';", "ctx.fillStyle = isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.9)';")
content = content.replace("ctx.strokeStyle = node.level === 0 ? 'var(--ew-accent, #3b82f6)' : 'rgba(255, 255, 255, 0.3)';", "ctx.strokeStyle = node.level === 0 ? (isDark ? '#3b82f6' : '#2563eb') : (isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(15, 23, 42, 0.15)');")
content = content.replace("const linkColor = (link as any).color || 'var(--ew-text-3, #555)';", "const linkColor = (link as any).color || (isDark ? '#555' : 'rgba(99, 102, 241, 0.25)');")

content = content.replace(
    "color: ['var(--ew-text-1, #ffffff)', 'var(--ew-text-1, #ffffff)', 'var(--ew-accent, #3b82f6)', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)],",
    "color: isDark ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)] : ['#94a3b8', '#cbd5e1', '#3b82f6', '#8b5cf6', '#f472b6', '#c084fc'][Math.floor(Math.random() * 6)],"
)
content = content.replace(
    "['var(--ew-danger, #ef4444)', 'var(--ew-accent, #3b82f6)', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', 'var(--ew-orange, #f97316)'].map",
    "(isDark ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']).map"
)

content = content.replace("'radial-gradient(ellipse at center, var(--ew-bg-panel, #0a0a0a) 0%, var(--ew-bg-main, #000) 100%)'", "isDark ? 'radial-gradient(ellipse at center, #0a0a0a 0%, #000 100%)' : 'radial-gradient(ellipse at center, #ffffff 0%, #f8fafc 100%)'")

with open(file_path, "w") as f:
    f.write(content)
