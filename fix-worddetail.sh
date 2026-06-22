#!/bin/bash
sed -i '' -e 's/background: \x27rgba(255,255,255,0.05)\x27/background: \x27var(--glass-2)\x27/g' \
          -e 's/background: \x27rgba(255, 255, 255, 0.05)\x27/background: \x27var(--glass-2)\x27/g' \
          -e 's/borderBottom: \x271px solid var(--border)\x27/borderBottom: \x271px solid var(--glass-border)\x27/g' \
          -e 's/borderTop: \x271px solid var(--border)\x27/borderTop: \x271px solid var(--glass-border)\x27/g' \
          -e "s/background: 'var(--text-1)'/background: 'var(--text-3)'/g" \
          /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx
