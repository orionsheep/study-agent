#!/bin/bash
FILES=(
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/EnglishWorkspaceApp.tsx"
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx"
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordDetail.tsx"
  "/Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/FissionGraph.tsx"
)

for file in "${FILES[@]}"; do
  sed -i '' -e 's/#0a0a0a/var(--ew-bg-panel)/g' \
            -e 's/#000/var(--ew-bg-main)/g' \
            -e 's/#000000/var(--ew-bg-main)/g' \
            -e 's/rgba(23, *23, *23, *0.6)/var(--ew-bg-active)/g' \
            -e 's/rgba(255, *255, *255, *0.05)/var(--ew-bg-hover)/g' \
            -e 's/#262626/var(--ew-border)/g' \
            -e 's/#404040/var(--ew-border-hi)/g' \
            -e 's/#171717/var(--ew-bg-panel)/g' \
            -e 's/#ffffff/var(--ew-text-1)/g' \
            -e 's/#fff/var(--ew-text-1)/g' \
            -e 's/#d4d4d4/var(--ew-text-2)/g' \
            -e 's/#a3a3a3/var(--ew-text-3)/g' \
            -e 's/#737373/var(--ew-text-faint)/g' \
            -e 's/#3b82f6/var(--ew-accent)/g' \
            -e 's/rgba(37, *99, *235, *0.2)/var(--ew-accent-bg)/g' \
            -e "s/'#1a1a1a'/'var(--ew-border)'/g" \
            -e "s/background: 'linear-gradient(90deg, var(--text-1), #8b5cf6)'/background: 'var(--ew-accent)'/g" \
            -e 's/background: \x27rgba(23, 23, 23, 0.95)\x27/background: \x27var(--ew-bg-panel)\x27/g' \
            "$file"
done
