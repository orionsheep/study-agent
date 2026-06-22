import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Make the light mode nodes elegant instead of dead black
content = content.replace(
    "['#18181b', '#18181b', '#2563eb', '#7e22ce', '#db2777', '#9333ea']",
    "['#94a3b8', '#cbd5e1', '#3b82f6', '#8b5cf6', '#f472b6', '#c084fc']" # Beautiful light elegant particles
)

content = content.replace(
    "backgroundColor={isDark ? '#000000' : '#ffffff'}",
    "backgroundColor={isDark ? '#000000' : '#f8fafc'}" # Slate 50 for a very soft white canvas
)

content = content.replace(
    "ctx.fillStyle = isDark ? '#ffffff' : '#18181b';",
    "ctx.fillStyle = isDark ? '#ffffff' : '#334155';" # Slate 700 for root node text
)

content = content.replace(
    "const nodeColor = node.color || (isDark ? '#ffffff' : '#18181b');",
    "const nodeColor = node.color || (isDark ? '#ffffff' : '#475569');" # Slate 600 for child nodes
)

# Text inside the nodes
content = content.replace(
    "ctx.fillStyle = isDark ? '#ffffff' : '#ffffff';",
    "ctx.fillStyle = '#ffffff';" # Inner node text always white
)

# Links
content = content.replace(
    "const linkColor = (link as any).color || (isDark ? '#555' : 'rgba(0,0,0,0.15)');",
    "const linkColor = (link as any).color || (isDark ? '#555' : 'rgba(99, 102, 241, 0.25)');" # Elegant indigo links
)

# Tooltip/Label backgrounds
content = content.replace(
    "ctx.fillStyle = isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.95)';",
    "ctx.fillStyle = isDark ? 'rgba(0, 0, 0, 1)' : 'rgba(255, 255, 255, 0.98)';"
)

content = content.replace(
    "ctx.strokeStyle = node.level === 0 ? (isDark ? '#3b82f6' : '#2563eb') : (isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.15)');",
    "ctx.strokeStyle = node.level === 0 ? (isDark ? '#3b82f6' : '#2563eb') : (isDark ? 'rgba(255, 255, 255, 0.3)' : 'rgba(15, 23, 42, 0.12)');"
)

with open(file_path, "w") as f:
    f.write(content)
