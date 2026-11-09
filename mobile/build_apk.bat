@echo off
cd /d "%~dp0"
echo سيتم إنشاء APK تجريبي لأندرويد عبر Expo EAS.
echo إذا لم تكن مسجل الدخول، نفّذ: npx eas-cli login
npx eas-cli@latest build --platform android --profile preview
pause
