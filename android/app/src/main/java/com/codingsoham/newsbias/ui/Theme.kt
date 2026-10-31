package com.codingsoham.newsbias.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object NewsBiasColors {
    val Background = Color(0xFF090C12)
    val SurfaceCard = Color(0xFF131823)
    val SurfaceElevated = Color(0xFF1A2130)
    val SurfaceHighlight = Color(0xFF222B3D)
    val BorderSubtle = Color(0xFF232D40)
    val BorderStrong = Color(0xFF334155)

    // Political spectrum
    val LeftColor = Color(0xFF818CF8)        // Amethyst Indigo
    val LeftBg = Color(0xFF1E2038)
    val CenterColor = Color(0xFF2DD4BF)      // Balanced Teal / Sage
    val CenterBg = Color(0xFF122828)
    val RightColor = Color(0xFFFB7185)       // Coral Sunset Rose
    val RightBg = Color(0xFF331C24)
    val NotPoliticalColor = Color(0xFF34D399) // Mint / Emerald
    val NotPoliticalBg = Color(0xFF0F2E23)
    val UnclearColor = Color(0xFFA78BFA)     // Muted Lavender

    val TextPrimary = Color(0xFFF8FAFC)
    val TextSecondary = Color(0xFF94A3B8)
    val TextTertiary = Color(0xFF64748B)
    val BrandAccent = Color(0xFF6366F1)
}

private val DarkColorScheme = darkColorScheme(
    primary = NewsBiasColors.BrandAccent,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF1E2438),
    onPrimaryContainer = Color(0xFFC7D2FE),
    secondary = NewsBiasColors.CenterColor,
    onSecondary = Color(0xFF0F172A),
    tertiary = NewsBiasColors.RightColor,
    onTertiary = Color.White,
    background = NewsBiasColors.Background,
    onBackground = NewsBiasColors.TextPrimary,
    surface = NewsBiasColors.SurfaceCard,
    onSurface = NewsBiasColors.TextPrimary,
    surfaceVariant = NewsBiasColors.SurfaceElevated,
    onSurfaceVariant = NewsBiasColors.TextSecondary,
    outline = NewsBiasColors.BorderSubtle,
    outlineVariant = NewsBiasColors.BorderStrong,
)

@Composable
fun NewsBiasTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content = content
    )
}
