file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/styles.css"
with open(file_path, "r") as f:
    content = f.read()

# Remove opacity and filter from dimmed windows so they don't fade out
old_dimmed = ".appwin.dimmed { opacity: 0.85; filter: none; border-color: var(--glass-border); box-shadow: var(--shadow-md); }"
new_dimmed = ".appwin.dimmed { opacity: 1; filter: none; border-color: var(--glass-border); box-shadow: var(--shadow-md); z-index: 10; }"

content = content.replace(old_dimmed, new_dimmed)

with open(file_path, "w") as f:
    f.write(content)
