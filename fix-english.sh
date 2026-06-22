#!/bin/bash
# Revert to clean state first to be absolutely sure
git checkout /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/

# Inject useTheme hook into the files to handle light/dark cleanly
sed -i '' -e 's/import { useState/import { useState, useMemo /g' /Users/mychanging/Downloads/learnforge-v2-product/apps/web/src/features/learning-apps/english/components/WordList.tsx
