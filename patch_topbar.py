file_path = "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/app-canvas/TopBar.tsx"
with open(file_path, "r") as f:
    content = f.read()

# Add new icons
if "Droplets" not in content:
    content = content.replace(
        "Moon, PanelLeftClose, PanelLeftOpen, Sun, User", 
        "Moon, PanelLeftClose, PanelLeftOpen, Sun, User, Droplets, Droplet"
    )

# Add prop
content = content.replace(
    "onToggleTheme: () => void;",
    "onToggleTheme: () => void;\n  glassEnabled: boolean;\n  onToggleGlass: () => void;"
)

content = content.replace(
    "theme, onToggleTheme,",
    "theme, onToggleTheme, glassEnabled, onToggleGlass,"
)

# Add button next to theme toggle
button_html = """
      <button
        className="theme-toggle"
        title={glassEnabled ? "关闭毛玻璃效果 (使用纯色背景)" : "开启毛玻璃效果 (液态玻璃质感)"}
        aria-label={glassEnabled ? "关闭毛玻璃效果" : "开启毛玻璃效果"}
        onClick={onToggleGlass}
      >
        {glassEnabled ? <Droplets size={16} /> : <Droplet size={16} />}
      </button>
"""

content = content.replace(
    '<button className="btn btn-icon" title="导出">',
    button_html + '\n      <button className="btn btn-icon" title="导出">'
)

with open(file_path, "w") as f:
    f.write(content)
