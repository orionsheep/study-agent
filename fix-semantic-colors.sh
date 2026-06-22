#!/bin/bash
sed -i '' -e 's/#22c55e/var(--st-done)/g' \
          -e 's/#eab308/var(--st-weak)/g' \
          -e 's/#ef4444/var(--st-risk)/g' \
          -e 's/#e5e5e5/var(--ew-text-1)/g' \
          -e 's/#525252/var(--ew-text-3)/g' \
          -e 's/#a855f7/var(--ew-accent)/g' \
          -e 's/#c084fc/var(--ew-text-2)/g' \
          -e 's/rgba(168, 85, 247, 0.2)/var(--ew-accent-bg)/g' \
          /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx
