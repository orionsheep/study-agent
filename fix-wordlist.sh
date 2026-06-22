#!/bin/bash
sed -i '' -e 's/background: \x27var(--bg-1)\x27/background: \x27transparent\x27/g' \
          -e 's/background: \x27rgba(255,255,255,0.05)\x27/background: \x27var(--glass-2)\x27/g' \
          -e 's/color: \x27var(--bg-0)\x27/color: \x27var(--text-1)\x27/g' \
          -e 's/borderRight: \x271px solid var(--border)\x27/borderRight: \x271px solid var(--glass-border)\x27/g' \
          -e 's/borderBottom: \x271px solid var(--border)\x27/borderBottom: \x271px solid var(--glass-border)\x27/g' \
          -e 's/color: \x27var(--text-faint)\x27/color: \x27var(--text-3)\x27/g' \
          -e "s/'#2563eb'/'var(--accent)'/g" \
          -e "s/background: '#1a1a1a'/background: 'var(--glass-border)'/g" \
          -e "s/background: 'linear-gradient(90deg, var(--text-1), #8b5cf6)'/background: 'var(--text-1)'/g" \
          /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx
