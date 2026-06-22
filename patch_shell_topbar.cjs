const fs = require('fs');

const shellPath = '/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/LearnForgeShell.tsx';
let shellContent = fs.readFileSync(shellPath, 'utf8');

if (!shellContent.includes('glassEnabled')) {
    shellContent = shellContent.replace(
        'const { theme, toggleTheme } = useTheme();',
        'const { theme, glassEnabled, toggleTheme, toggleGlass } = useTheme();'
    );
    shellContent = shellContent.replace(
        'theme={theme}\n        onToggleTheme={toggleTheme}',
        'theme={theme}\n        onToggleTheme={toggleTheme}\n        glassEnabled={glassEnabled}\n        onToggleGlass={toggleGlass}'
    );
    fs.writeFileSync(shellPath, shellContent);
}

const topbarPath = '/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/app-canvas/TopBar.tsx';
let topbarContent = fs.readFileSync(topbarPath, 'utf8');

if (!topbarContent.includes('Droplets')) {
    topbarContent = topbarContent.replace(
        'Moon, PanelLeftClose, PanelLeftOpen, Sun, User',
        'Moon, PanelLeftClose, PanelLeftOpen, Sun, User, Droplets, Droplet'
    );
    
    topbarContent = topbarContent.replace(
        'onToggleTheme: () => void;',
        'onToggleTheme: () => void;\n  glassEnabled?: boolean;\n  onToggleGlass?: () => void;'
    );
    
    topbarContent = topbarContent.replace(
        'theme, onToggleTheme, onToggleCanvas',
        'theme, onToggleTheme, glassEnabled, onToggleGlass, onToggleCanvas'
    );
    
    const btnHtml = `
      <button
        className="theme-toggle"
        title={glassEnabled ? "关闭毛玻璃效果" : "开启毛玻璃效果"}
        aria-label={glassEnabled ? "关闭毛玻璃效果" : "开启毛玻璃效果"}
        onClick={onToggleGlass}
      >
        {glassEnabled ? <Droplets size={16} /> : <Droplet size={16} />}
      </button>
`;
    topbarContent = topbarContent.replace(
        '<button className="btn btn-icon" title="导出">',
        btnHtml + '\n      <button className="btn btn-icon" title="导出">'
    );
    fs.writeFileSync(topbarPath, topbarContent);
}

const onboardingPath = '/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/app/OnboardingFlow.tsx';
let obContent = fs.readFileSync(onboardingPath, 'utf8');
if (!obContent.includes('glassEnabled')) {
    obContent = obContent.replace(
        'const { theme, toggleTheme } = useTheme();',
        'const { theme, glassEnabled, toggleTheme, toggleGlass } = useTheme();'
    );
    obContent = obContent.replace(
        'theme={theme} onToggleTheme={toggleTheme}',
        'theme={theme} onToggleTheme={toggleTheme} glassEnabled={glassEnabled} onToggleGlass={toggleGlass}'
    );
    fs.writeFileSync(onboardingPath, obContent);
}

console.log('Shell and TopBar patched');
