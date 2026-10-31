# Android app

The app is a Kotlin/Jetpack Compose client for the local FastAPI service. It
never receives article body text: it reads only titles, snippets, sources,
links, timestamps, and model probabilities.

## What is included

- Material 3 Compose UI with light/dark system theming.
- Story feed and detail view; detail articles are grouped by estimated leaning.
- Text-labelled stacked LEFT/CENTER/RIGHT percentage bars, so colour is never
  the only way the leaning is communicated.
- `Unclear` for low-confidence results, a visible AI-estimate warning, and an
  explanation sheet.
- Pull-to-refresh plus a Room cache for offline viewing of the latest stories
  and loaded story details.
- Original articles open through Android Custom Tabs.

## Run against the local API

1. From the repository root, activate `.venv` and launch the API:

   ```powershell
   .\.venv\Scripts\uvicorn.exe backend.app:app --host 0.0.0.0 --port 8000
   ```

2. Open `android/` in Android Studio and wait for Gradle sync.
   This project uses Android Gradle Plugin 9's built-in Kotlin support; do not
   add the legacy `org.jetbrains.kotlin.android` or `kotlin-kapt` plugins.
3. Start an Android emulator and run the `app` configuration. The default API
   URL is `http://10.0.2.2:8000/`, which is the emulator alias for this PC.
4. For a physical device, give Gradle the PC's LAN URL while building:

   ```powershell
   .\gradlew.bat :app:installDebug -PapiBaseUrl=http://YOUR_PC_LAN_IP:8000/
   ```

The app permits cleartext HTTP only for this local-development workflow. Use
HTTPS before distributing it outside the local network.
