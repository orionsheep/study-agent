import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add useTheme to FissionGraph to properly style the canvas
if "useTheme" not in content:
    content = content.replace(
        "import { useRef, useEffect, useState, useMemo } from 'react';", 
        "import { useRef, useEffect, useState, useMemo } from 'react';\nimport { useTheme } from '../../../../lib/state/useTheme';"
    )

if "const { theme } = useTheme();" not in content:
    content = content.replace(
        "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {",
        "export default function FissionGraph({ word, onNodeClick, mode = 'dashboard' }: FissionGraphProps) {\n  const { theme } = useTheme();\n  const isDark = theme === 'dark';"
    )

# Fix HTML styles in FissionGraph
content = content.replace("background: '#000'", "background: 'var(--bg-0)'")
content = content.replace("background: 'radial-gradient(ellipse at center, #0a0a0a 0%, #000 100%)'", "background: 'radial-gradient(ellipse at center, var(--bg-1) 0%, var(--bg-0) 100%)'")
content = content.replace("background: 'rgba(23, 23, 23, 0.95)'", "background: 'var(--glass-bg)'")
content = content.replace("background: 'rgba(23, 23, 23, 0.9)'", "background: 'var(--glass-bg)'")
content = content.replace("background: 'rgba(23, 23, 23, 0.8)'", "background: 'var(--glass-1)'")
content = content.replace("background: 'rgba(38, 38, 38, 0.9)'", "background: 'var(--glass-2)'")
content = content.replace("border: '1px solid #262626'", "border: '1px solid var(--glass-border)'")
content = content.replace("color: '#737373'", "color: 'var(--text-3)'")
content = content.replace("color: '#a3a3a3'", "color: 'var(--text-2)'")
content = content.replace("color: '#d4d4d4'", "color: 'var(--text-1)'")
content = content.replace("color: '#fff'", "color: 'var(--text-1)'")

# Fix Canvas drawing colors using isDark
content = content.replace("backgroundColor=\"#000000\"", "backgroundColor={isDark ? '#000000' : '#ffffff'}")
content = content.replace("ctx.strokeStyle = node.color || '#3b82f6';", "ctx.strokeStyle = node.color || (isDark ? '#3b82f6' : '#2563eb');")
content = content.replace("const nodeColor = node.color || '#fff';", "const nodeColor = node.color || (isDark ? '#ffffff' : '#18181b');")
content = content.replace("ctx.fillStyle = '#fff';", "ctx.fillStyle = isDark ? '#ffffff' : '#ffffff';")
content = content.replace("ctx.fillStyle = '#ffffff';", "ctx.fillStyle = isDark ? '#ffffff' : '#18181b';")
content = content.replace("ctx.fillStyle = 'rgba(0, 0, 0, 1)';", "ctx.fillStyle = isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.95)';")
content = content.replace("ctx.strokeStyle = node.level === 0 ? '#3b82f6' : 'rgba(255, 255, 255, 0.3)';", "ctx.strokeStyle = node.level === 0 ? (isDark ? '#3b82f6' : '#2563eb') : (isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.15)');")
content = content.replace("const linkColor = (link as any).color || '#555';", "const linkColor = (link as any).color || (isDark ? '#555' : 'rgba(0,0,0,0.15)');")

content = content.replace("color: ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)],", "color: isDark ? ['#ffffff', '#ffffff', '#3b82f6', '#8b5cf6', '#ec4899', '#a78bfa'][Math.floor(Math.random() * 6)] : ['#18181b', '#18181b', '#2563eb', '#7e22ce', '#db2777', '#9333ea'][Math.floor(Math.random() * 6)],")
content = content.replace("['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'].map(", "(isDark ? ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'] : ['#dc2626', '#2563eb', '#16a34a', '#d97706', '#7e22ce', '#db2777', '#0891b2', '#ea580c']).map(")

with open(file_path, "w") as f:
    f.write(content)

print("FissionGraph Canvas patched safely")
