package com.codingsoham.newsbias

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.codingsoham.newsbias.ui.*
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint class MainActivity: ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent {
        NewsBiasTheme { Surface { val nav=rememberNavController(); NavHost(nav,"feed") {
            composable("feed") { FeedScreen(onStory={nav.navigate("story/$it")}) }
            composable("story/{id}") { entry ->
                entry.arguments?.getString("id")?.toLongOrNull()?.let { id ->
                    DetailScreen(id, onBack={nav.popBackStack()})
                }
            }
        } } }
    } }
}
