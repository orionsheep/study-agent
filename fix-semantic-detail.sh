#!/bin/bash
sed -i '' -e 's/#eab308/var(--st-weak)/g' \
          -e 's/#e5e5e5/var(--ew-text-1)/g' \
          -e 's/#60a5fa/var(--ew-accent)/g' \
          -e 's/#fef08a/var(--st-weak)/g' \
          -e 's/#a855f7/var(--ew-accent)/g' \
          -e 's/#c084fc/var(--ew-accent)/g' \
          -e 's/#f97316/var(--st-weak)/g' \
          -e 's/#525252/var(--ew-text-3)/g' \
          /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx
