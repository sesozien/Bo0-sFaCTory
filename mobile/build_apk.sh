#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v npx >/dev/null 2>&1; then
  echo "Node.js مطلوب قبل البناء."
  exit 1
fi

echo "سيتم إنشاء APK تجريبي لأندرويد عبر Expo EAS."
echo "إذا لم تكن مسجل الدخول، نفّذ: npx eas-cli login"
npx eas-cli@latest build --platform android --profile preview
