file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/OnboardingFlow.tsx"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    "const { theme, toggleTheme } = useTheme();",
    "const { theme, glassEnabled, toggleTheme, toggleGlass } = useTheme();"
)

content = content.replace(
    "theme={theme} onToggleTheme={toggleTheme}",
    "theme={theme} onToggleTheme={toggleTheme} glassEnabled={glassEnabled} onToggleGlass={toggleGlass}"
)

with open(file_path, "w") as f:
    f.write(content)
