import re

file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Fix the duplicate background on canvas container
content = content.replace("style={{ position: 'absolute', inset: 0, background: 'var(--ew-bg-main, #000)', overflow: 'hidden' }}", "style={{ position: 'absolute', inset: 0, background: 'transparent', overflow: 'hidden' }}")

with open(file_path, "w") as f:
    f.write(content)
