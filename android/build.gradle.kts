plugins {
    id("com.android.application") version "9.3.3" apply false
    // AGP 9 includes Kotlin support. Do not apply kotlin-android/kapt here.
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false
    // AGP 9.0.1 embeds Kotlin 2.2.10, so KSP must use its matching line.
    id("com.google.devtools.ksp") version "2.3.6" apply false
    id("com.google.dagger.hilt.android") version "2.60.1" apply false
}
