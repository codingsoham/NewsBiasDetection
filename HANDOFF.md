# Handoff: News Bias Detection

## Project goal

Build an Android-only, Ground-News-style app for Indian political-news coverage.
It shows story and article-level LEFT/CENTER/RIGHT estimated percentages, makes
uncertainty explicit, and links users to original publisher articles.

Required stack: Python/FastAPI/SQLite backend; Kotlin, Jetpack Compose,
Material 3, Retrofit, Hilt, Room, and Custom Tabs for Android. Do not add
Docker, Postgres, workers, or article-body delivery to the app/API.

## Important quality boundary

This is a functioning experimental research baseline, not a dependable source
of political-bias claims. The selected model's publisher-held-out human-gold
test macro-F1 is **0.445**. UI copy must retain both the `AI-estimated, may be
wrong` warning and the `Unclear` state for low-confidence predictions.

Never reveal article body text through the API or Android app. It is local
research/training data only.

## Completed work through Phase 6 & Real-time Live News Engine

- Phase 1: 3,000 articles collected from 8 Indian publishers in `data/articles.db`.
- Phase 2: 6,000 local-Qwen annotations (two passes); 2,790 agreed silver labels; 250/250 human review queue items completed. Silver-v-gold accuracy is 0.872 and Cohen's kappa is 0.828 on the overlap.
- Phase 3: Leakage-safe split: 2,649 silver train, 125 human-gold validation, 125 human-gold test. NDTV and India Today are entirely held out from train.
- Phase 4: Direct weighted DistilRoBERTa is selected; it scores accuracy 0.416 / macro-F1 0.445 on gold test. Calibration, reliability, baselines, Stage-1/Stage-2 comparison, prior blending, sanity checks, and a genuine head-tail ablation are saved in `results/`.
- Phase 5: `backend/ingest.py` and `backend/app.py` materialize calibrated predictions and story clusters. FastAPI backend with `/stories`, `/stories/{id}`, `/articles/{id}`, `/predict`, `/health/model`, and `/refresh` endpoints.
- Phase 6 (Completed & Verified):
  - Full Android application in `android/` using Jetpack Compose, Material 3, Hilt, Room, Retrofit, Coil, and Custom Tabs.
  - Successfully built APK (`app-debug.apk`) and running on Android emulator (`Pixel_8` on `emulator-5556`).
  - Stacked Left/Center/Right bias bars with spoken content descriptions and percentage text labels.
  - Explicit uncertainty indicators (`Unclear — low confidence` and `AI-estimated, may be wrong`).
  - Story detail screen grouping articles into Left, Center, Right, and Unclear leanings.
  - Outbound link via Chrome Custom Tabs to the original publisher article.
  - Room offline caching with version 2 schema preserving chronological order.
  - About sheet detailing methodology and model limitations.
- Real-time Multi-source News Engine (Option B):
  - Expanded feeds: 16 feeds including direct Indian outlets (The Hindu, Indian Express, NDTV, Times of India, Hindustan Times, ThePrint, India Today, LiveMint) plus Google News India National, Politics, and 24h search feeds.
  - Parallel RSS fetching: `ThreadPoolExecutor(max_workers=12)` fetches over 900+ live articles across Indian news sources in ~3 seconds.
  - Fast batch inference & SentenceTransformer clustering (`all-MiniLM-L6-v2`) caching into multi-source stories (70+ live story clusters formed).
  - Dynamic on-launch and pull-to-refresh sync triggered directly from `GET /stories` (with 90s throttle to avoid publisher rate-limiting).
  - Chronological story ordering: `ORDER BY max(a.fetched_at) DESC` to ensure fresh breaking news is always at the top of the feed.

Evidence and limitations: `docs/results.md`, `docs/data-card.md`, `results/`.

## Phase 6 implementation status

An Android project was created under `android/`.

### Included functionality

- Compose + Material 3; system light/dark theme (`ui/Theme.kt`).
- MVVM and Hilt (`ui/NewsViewModels.kt`, `di/AppModule.kt`).
- Retrofit client for `GET /stories` and `GET /stories/{id}`.
- Room cache (`data/NewsDatabase.kt`) for the feed and viewed story details.
- Pull-to-refresh, loading, empty, error, and offline-cache fallback states.
- Story feed cards: headline, source count, text-labelled stacked percentage
  bar, and explicit experimental/unclear warning.
- Story-detail article grouping by LEFT/CENTER/RIGHT/UNCLEAR; original link
  opens in an Android Custom Tab.
- Accessibility: bars include a spoken percentage content description; colour
  is not the sole leaning signal.
- About bottom sheet explains the experimental estimate and uncertainty.

### Backend compatibility change made for Phase 6

`GET /stories/{id}` now includes the existing persisted prediction object for
each article. The returned article fields are only id/source/url/title/snippet/
published_at/prediction; it does **not** return `text`. The backend smoke test
asserts this contract and passes.

## Android build configuration (important)

Files:

- `android/build.gradle.kts`
- `android/app/build.gradle.kts`
- `android/settings.gradle.kts`
- `android/gradlew.bat`

The project uses **Android Gradle Plugin 9.0.1**, which has built-in Kotlin.
Do **not** add `org.jetbrains.kotlin.android` or `org.jetbrains.kotlin.kapt`.
Room and Hilt annotation processing use KSP.

Current plugins:

```kotlin
id("com.android.application") version "9.0.1" apply false
id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false
id("com.google.devtools.ksp") version "2.2.10-2.0.2" apply false
id("com.google.dagger.hilt.android") version "2.60.1" apply false
```

The original failure was an invalid Kotlin plugin version (`2.60.1`). It was
removed. Android Studio's Gradle daemon subsequently completed **BUILD
SUCCESSFUL** for the corrected sync at 2026-10-29 18:11 IST.

The Codex terminal's Gradle process was unable to create its loopback socket,
which is an execution-harness restriction, not a source build error. Prefer
building from Android Studio/Antigravity or its normal integrated Gradle
environment.

## Next actions for the receiving agent

1. Open `android/` as the Android project and sync Gradle.
2. Run `:app:assembleDebug`; fix all compiler/dependency errors that surface.
   Do not claim the APK is built until this succeeds.
3. Start the local backend from repository root:

   ```powershell
   .\.venv\Scripts\uvicorn.exe backend.app:app --host 0.0.0.0 --port 8000
   ```

4. Run the emulator. The Android default endpoint is `http://10.0.2.2:8000/`.
   For a physical device, build with
   `-PapiBaseUrl=http://YOUR_PC_LAN_IP:8000/`.
5. Verify feed loading, pull-refresh, a story detail page, uncertainty display,
   offline cached content (after one successful fetch), and Custom Tabs link.
6. If changing backend response models, rerun:

   ```powershell
   .\.venv\Scripts\python.exe backend\test_api.py
   ```

## Known code review items to check during APK compilation

- Compose pull-refresh comes from `androidx.compose.material:material`; it is
  explicitly opted in with `ExperimentalMaterialApi`.
- The project requires Java 17 compile options. Android Studio currently has a
  bundled newer JBR; Gradle/AGP should select an appropriate toolchain, but if
  compilation reports a JDK issue, set Gradle JDK to JDK 17.
- `android/gradlew.bat` is a local convenience launcher. If its cached Gradle
  path does not match the machine, use the IDE wrapper or regenerate a standard
  Gradle wrapper; do not treat that as an app-source defect.
- There are two historical head-tail model directories/logs; the chosen model
  remains `models/best/best`, not either head-tail model.

## Secrets and safety

- `.env`, `data/`, `models/`, and `results/` are ignored by git.
- The user previously pasted API tokens into chat. They were removed from
  `.env`; do not reproduce them in any document, code, command output, or
  message. Recommend they revoke leaked tokens.
- There is no current requirement for any paid external model API: labeling
  used local Ollama/Qwen.

## Helpful commands

```powershell
# Backend contract smoke test
.\.venv\Scripts\python.exe backend\test_api.py

# Phase 4 evidence refresh (does not retrain by default)
.\.venv\Scripts\python.exe run_all.py

# Refresh RSS, model predictions, and stories
.\.venv\Scripts\python.exe backend\ingest.py --refresh-rss --refresh-predictions
```

## Definition of Phase 6 complete

An Android debug APK builds successfully; it installs/runs on an emulator;
and the app visibly demonstrates all required feed/detail/cache/refresh/error/
uncertainty/warning/Custom-Tab flows against the local FastAPI backend without
exposing article body text.
