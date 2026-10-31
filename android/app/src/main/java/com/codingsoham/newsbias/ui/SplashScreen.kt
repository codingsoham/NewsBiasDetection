package com.codingsoham.newsbias.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.codingsoham.newsbias.R
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(
    onFinished: () -> Unit
) {
    val scaleAnim = remember { Animatable(0.85f) }
    val contentAlpha = remember { Animatable(0f) }

    // Subtle ambient breathing pulse for the tri-color spectrum
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.7f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "glowAlpha"
    )

    LaunchedEffect(Unit) {
        // Animate entrance smoothly
        contentAlpha.animateTo(1f, animationSpec = tween(400))
        scaleAnim.animateTo(1f, animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow))
        delay(1200)
        // Animate exit fade
        contentAlpha.animateTo(0f, animationSpec = tween(200))
        onFinished()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = NewsBiasColors.Background
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF0F172A),
                            NewsBiasColors.Background,
                            Color(0xFF06090E)
                        )
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 32.dp)
                    .scale(scaleAnim.value)
                    .alpha(contentAlpha.value)
            ) {
                // 1. App Emblem
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(128.dp)
                        .clip(RoundedCornerShape(30.dp))
                        .background(NewsBiasColors.SurfaceElevated)
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.ic_splash_emblem),
                        contentDescription = "NewsBias Emblem",
                        modifier = Modifier.fillMaxSize()
                    )
                }

                Spacer(Modifier.height(24.dp))

                // 2. Title with Accent Dot
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "NewsBias",
                        style = MaterialTheme.typography.headlineLarge.copy(
                            fontSize = 34.sp,
                            fontWeight = FontWeight.ExtraBold,
                            letterSpacing = (-0.5).sp
                        ),
                        color = NewsBiasColors.TextPrimary
                    )
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(NewsBiasColors.BrandAccent, shape = CircleShape)
                    )
                }

                Spacer(Modifier.height(8.dp))

                // 3. Subtitle / Value Proposition
                Text(
                    text = "AI-Powered Multi-Perspective News Analysis",
                    style = MaterialTheme.typography.bodyMedium.copy(fontSize = 14.sp),
                    fontWeight = FontWeight.Normal,
                    color = NewsBiasColors.TextSecondary
                )

                Spacer(Modifier.height(28.dp))

                // 4. Tri-Color Perspective Spectrum Bar (Left, Center, Right)
                Row(
                    modifier = Modifier
                        .width(180.dp)
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .alpha(glowAlpha)
                ) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .background(NewsBiasColors.LeftColor)
                    )
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .background(NewsBiasColors.CenterColor)
                    )
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .background(NewsBiasColors.RightColor)
                    )
                }
            }

            // 5. Bottom Footer Information
            Column(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 36.dp)
                    .alpha(contentAlpha.value),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = "India Edition • 20+ Outlets Aggregated",
                    style = MaterialTheme.typography.labelSmall,
                    color = NewsBiasColors.TextTertiary,
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.5.sp
                )
                Text(
                    text = "Ground News Architecture • Indic-RoBERTa",
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp),
                    color = NewsBiasColors.TextTertiary.copy(alpha = 0.7f)
                )
            }
        }
    }
}
