file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/LearnForgeShell.tsx"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "const { theme, toggleTheme } = useTheme();",
    "const { theme, glassEnabled, toggleTheme, toggleGlass } = useTheme();"
)

content = content.replace(
    "theme={theme}\n        onToggleTheme={toggleTheme}",
    "theme={theme}\n        onToggleTheme={toggleTheme}\n        glassEnabled={glassEnabled}\n        onToggleGlass={toggleGlass}"
)

with open(file_path, "w") as f:
    f.write(content)
