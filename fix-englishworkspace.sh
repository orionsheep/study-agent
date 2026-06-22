#!/bin/bash
sed -i '' -e 's/background: \x27var(--bg-0)\x27/background: \x27transparent\x27/g' \
          -e 's/background: \x27var(--bg-1)\x27/background: \x27transparent\x27/g' \
          -e 's/borderRight: \x271px solid var(--border)\x27/borderRight: \x271px solid var(--glass-border)\x27/g' \
          -e 's/borderBottom: \x271px solid var(--border)\x27/borderBottom: \x271px solid var(--glass-border)\x27/g' \
          -e 's/borderTop: \x271px solid var(--border)\x27/borderTop: \x271px solid var(--glass-border)\x27/g' \
          /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx
