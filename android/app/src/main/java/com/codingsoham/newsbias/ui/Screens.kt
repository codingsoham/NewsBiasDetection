package com.codingsoham.newsbias.ui

import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import androidx.hilt.navigation.compose.hiltViewModel
import com.codingsoham.newsbias.BuildConfig
import com.codingsoham.newsbias.data.AppUpdateInfo
import com.codingsoham.newsbias.data.CachedArticle
import com.codingsoham.newsbias.data.CachedStory
import com.codingsoham.newsbias.data.DownloadState
import java.io.File
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

private const val UNCLEAR_THRESHOLD = 0.45f

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen(onStory: (Long) -> Unit, viewModel: FeedViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val updateInfo by viewModel.updateInfo.collectAsState()
    val downloadState by viewModel.downloadState.collectAsState()
    val checkMessage by viewModel.updateCheckMessage.collectAsState()

    var showInfo by remember { mutableStateOf(false) }
    var selectedCategory by remember { mutableStateOf("All") }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    var lastSeenTopStoryId by remember { mutableStateOf<Long?>(null) }

    val isScrolledDown by remember {
        derivedStateOf {
            listState.firstVisibleItemIndex > 0 || listState.firstVisibleItemScrollOffset > 80
        }
    }

    LaunchedEffect(listState.firstVisibleItemIndex, state.stories) {
        if (listState.firstVisibleItemIndex == 0 && state.stories.isNotEmpty()) {
            lastSeenTopStoryId = state.stories.first().id
        }
    }

    val newStoriesCount by remember(state.stories, lastSeenTopStoryId, isScrolledDown) {
        derivedStateOf {
            if (!isScrolledDown || lastSeenTopStoryId == null || state.stories.isEmpty()) {
                0
            } else {
                val idx = state.stories.indexOfFirst { it.id == lastSeenTopStoryId }
                if (idx > 0) idx else if (idx == -1) state.stories.size else 0
            }
        }
    }

    val hasNewContentAbove by remember {
        derivedStateOf { newStoriesCount > 0 }
    }

    val filteredStories = remember(state.stories, selectedCategory) {
        if (selectedCategory == "All") state.stories
        else state.stories.filter { it.category() == selectedCategory }
    }

    Scaffold(
        containerColor = NewsBiasColors.Background,
        topBar = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(NewsBiasColors.Background)
            ) {
                TopAppBar(
                    title = {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(NewsBiasColors.BrandAccent, shape = CircleShape)
                            )
                            Column {
                                Text(
                                    "NewsBias",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Black,
                                    color = NewsBiasColors.TextPrimary,
                                    letterSpacing = (-0.5).sp
                                )
                                Text(
                                    "India Edition • AI Balanced News",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = NewsBiasColors.TextSecondary
                                )
                            }
                        }
                    },
                    actions = {
                        Surface(
                            onClick = { showInfo = true },
                            shape = RoundedCornerShape(20.dp),
                            color = NewsBiasColors.SurfaceElevated,
                            border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                            modifier = Modifier.padding(end = 12.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(6.dp)
                                        .background(NewsBiasColors.BrandAccent, shape = CircleShape)
                                )
                                Text(
                                    "About",
                                    style = MaterialTheme.typography.labelMedium,
                                    fontWeight = FontWeight.SemiBold,
                                    color = NewsBiasColors.TextPrimary
                                )
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = NewsBiasColors.Background
                    )
                )

                // Category Filter Chips
                if (state.stories.isNotEmpty()) {
                    val availableCategories = listOf("All", "Politics", "Civic & Factual", "Judiciary & Law", "Economy")
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 4.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 6.dp)
                    ) {
                        items(availableCategories) { cat ->
                            val count = if (cat == "All") state.stories.size else state.stories.count { it.category() == cat }
                            if (count > 0 || cat == "All") {
                                val isSelected = selectedCategory == cat
                                Surface(
                                    onClick = {
                                        selectedCategory = cat
                                        coroutineScope.launch { listState.scrollToItem(0) }
                                    },
                                    shape = RoundedCornerShape(20.dp),
                                    color = if (isSelected) NewsBiasColors.BrandAccent.copy(alpha = 0.2f) else NewsBiasColors.SurfaceCard,
                                    border = androidx.compose.foundation.BorderStroke(
                                        1.dp,
                                        if (isSelected) NewsBiasColors.BrandAccent else NewsBiasColors.BorderSubtle
                                    )
                                ) {
                                    Text(
                                        text = if (cat == "All") "All ($count)" else "$cat ($count)",
                                        modifier = Modifier.padding(horizontal = 13.dp, vertical = 6.dp),
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                        color = if (isSelected) NewsBiasColors.TextPrimary else NewsBiasColors.TextSecondary
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    ) { pad ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(pad)
        ) {
            PullContent(state.loading, { viewModel.refresh(force = true) }) {
                when {
                    state.stories.isEmpty() && state.loading -> Loading()
                    state.stories.isEmpty() -> Empty(state.error ?: "No stories available. Pull down to refresh.")
                    filteredStories.isEmpty() -> Empty("No stories found in category '$selectedCategory'.")
                    else -> LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        state.error?.let { item { ErrorCard(it) } }
                        items(filteredStories, key = { it.id }) {
                            StoryCard(it) { onStory(it.id) }
                        }
                    }
                }
            }

            // Top Banner Pill (Appears when new content is available above while scrolled down)
            AnimatedVisibility(
                visible = isScrolledDown && hasNewContentAbove,
                enter = fadeIn(animationSpec = tween(250)) + slideInVertically(animationSpec = tween(300)) { -it },
                exit = fadeOut(animationSpec = tween(200)) + slideOutVertically(animationSpec = tween(250)) { -it },
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .padding(top = 10.dp)
                    .zIndex(10f)
            ) {
                Surface(
                    onClick = {
                        coroutineScope.launch {
                            listState.animateScrollToItem(0)
                            if (state.stories.isNotEmpty()) {
                                lastSeenTopStoryId = state.stories.first().id
                            }
                        }
                    },
                    shape = RoundedCornerShape(24.dp),
                    color = NewsBiasColors.SurfaceElevated,
                    border = androidx.compose.foundation.BorderStroke(1.5.dp, NewsBiasColors.BrandAccent),
                    shadowElevation = 8.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowUpward,
                            contentDescription = "New stories above",
                            tint = NewsBiasColors.BrandAccent,
                            modifier = Modifier.size(16.dp)
                        )
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .background(NewsBiasColors.NotPoliticalColor, shape = CircleShape)
                        )
                        Text(
                            text = if (newStoriesCount > 1) "$newStoriesCount new stories above" else "New stories above",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = NewsBiasColors.TextPrimary
                        )
                    }
                }
            }

            // Floating Up Arrow Action Button (Scroll to top)
            AnimatedVisibility(
                visible = isScrolledDown,
                enter = fadeIn(animationSpec = tween(200)) + scaleIn(animationSpec = tween(200)),
                exit = fadeOut(animationSpec = tween(150)) + scaleOut(animationSpec = tween(150)),
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = 16.dp, bottom = 20.dp)
                    .zIndex(10f)
            ) {
                Surface(
                    onClick = {
                        coroutineScope.launch {
                            listState.animateScrollToItem(0)
                            if (state.stories.isNotEmpty()) {
                                lastSeenTopStoryId = state.stories.first().id
                            }
                        }
                    },
                    shape = CircleShape,
                    color = NewsBiasColors.SurfaceElevated,
                    shadowElevation = 6.dp,
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                    modifier = Modifier.size(50.dp)
                ) {
                    Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                        Icon(
                            imageVector = Icons.Default.KeyboardArrowUp,
                            contentDescription = "Scroll to top",
                            modifier = Modifier.size(30.dp),
                            tint = NewsBiasColors.BrandAccent
                        )
                        if (hasNewContentAbove) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .align(Alignment.TopEnd)
                                    .offset(x = (-8).dp, y = 8.dp)
                                    .background(NewsBiasColors.NotPoliticalColor, shape = CircleShape)
                            )
                        }
                    }
                }
            }
        }
    }
    if (showInfo) {
        InfoSheet(
            onDismiss = { showInfo = false },
            onCheckUpdate = { viewModel.checkForUpdates(isManual = true) },
            checkMessage = checkMessage
        )
    }

    updateInfo?.let { info ->
        UpdateBottomSheet(
            info = info,
            downloadState = downloadState,
            onStartDownload = { viewModel.startDownload(info) },
            onInstall = { viewModel.installDownloaded(it) },
            onDismiss = { viewModel.dismissUpdate() }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScreen(id: Long, onBack: () -> Unit, viewModel: DetailViewModel = hiltViewModel()) {
    BackHandler(onBack = onBack)
    LaunchedEffect(id) { viewModel.load(id) }
    val state by viewModel.state.collectAsState()
    var showInfo by remember { mutableStateOf(false) }
    var selectedFilter by remember { mutableStateOf("ALL") }
    val detailListState = rememberLazyListState()
    val detailScope = rememberCoroutineScope()
    val isDetailScrolledDown by remember {
        derivedStateOf {
            detailListState.firstVisibleItemIndex > 1 || detailListState.firstVisibleItemScrollOffset > 100
        }
    }

    Scaffold(
        containerColor = NewsBiasColors.Background,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Story Coverage",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary,
                        letterSpacing = (-0.3).sp
                    )
                },
                navigationIcon = {
                    IconButton(
                        onClick = onBack,
                        modifier = Modifier.padding(start = 6.dp)
                    ) {
                        Surface(
                            shape = CircleShape,
                            color = NewsBiasColors.SurfaceElevated,
                            border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                            modifier = Modifier.size(36.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.ArrowBack,
                                    contentDescription = "Back",
                                    tint = NewsBiasColors.TextPrimary,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    }
                },
                actions = {
                    Surface(
                        onClick = { showInfo = true },
                        shape = RoundedCornerShape(20.dp),
                        color = NewsBiasColors.SurfaceElevated,
                        border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                        modifier = Modifier.padding(end = 12.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(6.dp)
                                    .background(NewsBiasColors.BrandAccent, shape = CircleShape)
                            )
                            Text(
                                "About",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = NewsBiasColors.TextPrimary
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NewsBiasColors.Background
                )
            )
        }
    ) { pad ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(pad)
        ) {
            PullContent(state.loading, viewModel::refresh) {
                when {
                    state.articles.isEmpty() && state.loading -> Loading()
                    state.articles.isEmpty() -> Empty(state.error ?: "No articles saved for this story.")
                    else -> {
                        val availableLeanings = listOf("ALL", "LEFT", "CENTER", "RIGHT", "NOT_POLITICAL")
                        val filteredArticles = when (selectedFilter) {
                            "ALL" -> state.articles
                            else -> state.articles.filter { it.leaning() == selectedFilter }
                        }

                        LazyColumn(
                            state = detailListState,
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                        state.error?.let { item { ErrorCard(it) } }

                        // 1. Perspective Filter Chips
                        item {
                            LazyRow(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                contentPadding = PaddingValues(vertical = 4.dp)
                            ) {
                                items(availableLeanings) { filter ->
                                    val count = if (filter == "ALL") state.articles.size else state.articles.count { it.leaning() == filter }
                                    if (count > 0 || filter == "ALL") {
                                        val isSelected = selectedFilter == filter
                                        val filterLabel = when (filter) {
                                            "ALL" -> "All ($count)"
                                            "LEFT" -> "Left ($count)"
                                            "CENTER" -> "Center ($count)"
                                            "RIGHT" -> "Right ($count)"
                                            "NOT_POLITICAL" -> "Non-Political ($count)"
                                            else -> filter
                                        }
                                        val chipColor = when {
                                            !isSelected -> NewsBiasColors.SurfaceCard
                                            filter == "LEFT" -> NewsBiasColors.LeftBg
                                            filter == "CENTER" -> NewsBiasColors.CenterBg
                                            filter == "RIGHT" -> NewsBiasColors.RightBg
                                            filter == "NOT_POLITICAL" -> NewsBiasColors.NotPoliticalBg
                                            else -> NewsBiasColors.SurfaceElevated
                                        }
                                        val chipBorder = when {
                                            !isSelected -> NewsBiasColors.BorderSubtle
                                            filter == "LEFT" -> NewsBiasColors.LeftColor
                                            filter == "CENTER" -> NewsBiasColors.CenterColor
                                            filter == "RIGHT" -> NewsBiasColors.RightColor
                                            filter == "NOT_POLITICAL" -> NewsBiasColors.NotPoliticalColor
                                            else -> NewsBiasColors.BrandAccent
                                        }

                                        Surface(
                                            onClick = { selectedFilter = filter },
                                            shape = RoundedCornerShape(20.dp),
                                            color = chipColor,
                                            border = androidx.compose.foundation.BorderStroke(1.dp, chipBorder)
                                        ) {
                                            Text(
                                                filterLabel,
                                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
                                                style = MaterialTheme.typography.labelMedium,
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                                color = if (isSelected) NewsBiasColors.TextPrimary else NewsBiasColors.TextSecondary
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // 2. Filtered or Grouped Article Cards
                        if (selectedFilter != "ALL") {
                            items(filteredArticles, key = { it.id }) { ArticleCard(it) }
                        } else {
                            listOf("LEFT", "CENTER", "RIGHT", "NOT_POLITICAL", "UNCLEAR").forEach { leaning ->
                                val groupArticles = state.articles.filter { it.leaning() == leaning }
                                if (groupArticles.isNotEmpty()) {
                                    item {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                                            modifier = Modifier.padding(top = 6.dp, bottom = 2.dp)
                                        ) {
                                            val indicatorColor = when (leaning) {
                                                "LEFT" -> NewsBiasColors.LeftColor
                                                "CENTER" -> NewsBiasColors.CenterColor
                                                "RIGHT" -> NewsBiasColors.RightColor
                                                "NOT_POLITICAL" -> NewsBiasColors.NotPoliticalColor
                                                else -> NewsBiasColors.UnclearColor
                                            }
                                            Box(
                                                modifier = Modifier
                                                    .size(8.dp)
                                                    .background(indicatorColor, shape = CircleShape)
                                            )
                                            val displayHeading = when (leaning) {
                                                "NOT_POLITICAL" -> "NON-POLITICAL / CIVIC"
                                                else -> leaning
                                            }
                                            Text(
                                                displayHeading,
                                                style = MaterialTheme.typography.labelLarge,
                                                fontWeight = FontWeight.ExtraBold,
                                                letterSpacing = 1.sp,
                                                color = indicatorColor
                                            )
                                            Text(
                                                "(${groupArticles.size})",
                                                style = MaterialTheme.typography.labelMedium,
                                                color = NewsBiasColors.TextTertiary
                                            )
                                        }
                                    }
                                    items(groupArticles, key = { it.id }) { ArticleCard(it) }
                                }
                            }
                        }
                    }
                }
            }
            }

            // Floating Up Arrow Action Button (Scroll to top in DetailScreen)
            AnimatedVisibility(
                visible = isDetailScrolledDown,
                enter = fadeIn(animationSpec = tween(200)) + scaleIn(animationSpec = tween(200)),
                exit = fadeOut(animationSpec = tween(150)) + scaleOut(animationSpec = tween(150)),
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(end = 16.dp, bottom = 20.dp)
                    .zIndex(10f)
            ) {
                Surface(
                    onClick = {
                        detailScope.launch {
                            detailListState.animateScrollToItem(0)
                        }
                    },
                    shape = CircleShape,
                    color = NewsBiasColors.SurfaceElevated,
                    shadowElevation = 6.dp,
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                    modifier = Modifier.size(50.dp)
                ) {
                    Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                        Icon(
                            imageVector = Icons.Default.KeyboardArrowUp,
                            contentDescription = "Scroll to top",
                            modifier = Modifier.size(30.dp),
                            tint = NewsBiasColors.BrandAccent
                        )
                    }
                }
            }
        }
    }
    if (showInfo) InfoSheet(onDismiss = { showInfo = false })
}

@Composable
private fun StoryCard(item: CachedStory, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = NewsBiasColors.SurfaceCard
        ),
        border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Top metadata row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    color = NewsBiasColors.SurfaceElevated,
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle)
                ) {
                    Text(
                        "${item.sources} ${if (item.sources == 1) "source" else "sources"} reporting",
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color(0xFF93C5FD),
                        fontWeight = FontWeight.SemiBold
                    )
                }

                Text(
                    "Compare perspectives →",
                    style = MaterialTheme.typography.labelSmall,
                    color = NewsBiasColors.LeftColor,
                    fontWeight = FontWeight.Medium
                )
            }

            // Headline
            Text(
                item.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = NewsBiasColors.TextPrimary,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 22.sp
            )

            // Leaning representation
            val isNonPol = item.isNotPolitical || (item.notPolitical >= 0.35f && item.notPolitical >= maxOf(item.left, item.center, item.right))
            if (isNonPol) {
                NotPoliticalBadge()
            } else if (maxOf(item.left, item.center, item.right) < UNCLEAR_THRESHOLD) {
                Surface(
                    color = NewsBiasColors.SurfaceElevated,
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        "Balanced Multi-Perspective Consensus",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = NewsBiasColors.UnclearColor,
                        fontWeight = FontWeight.Medium
                    )
                }
            } else {
                LeaningBar(item.left, item.center, item.right)
            }
        }
    }
}

@Composable
private fun ArticleCard(item: CachedArticle) {
    val context = LocalContext.current
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable {
                CustomTabsIntent.Builder().build().launchUrl(context, Uri.parse(item.url))
            },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = NewsBiasColors.SurfaceCard
        ),
        border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // 1. Publisher Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        item.source,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary
                    )
                    if (!item.sourceFactuality.isNullOrBlank()) {
                        Surface(
                            color = NewsBiasColors.SurfaceElevated,
                            shape = RoundedCornerShape(6.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle)
                        ) {
                            Text(
                                item.sourceFactuality,
                                modifier = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = Color(0xFF93C5FD),
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                Text(
                    item.publishedAt?.take(10) ?: "",
                    style = MaterialTheme.typography.labelSmall,
                    color = NewsBiasColors.TextTertiary
                )
            }

            // 2. Dedicated Source Description Box
            if (!item.sourceDescription.isNullOrBlank()) {
                Surface(
                    color = NewsBiasColors.SurfaceElevated.copy(alpha = 0.7f),
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.Top,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .width(3.dp)
                                .height(30.dp)
                                .background(NewsBiasColors.BrandAccent, shape = RoundedCornerShape(2.dp))
                        )
                        Text(
                            item.sourceDescription,
                            style = MaterialTheme.typography.bodySmall,
                            color = NewsBiasColors.TextSecondary,
                            lineHeight = 17.sp
                        )
                    }
                }
            }

            // 3. Article Title
            Text(
                item.title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = NewsBiasColors.TextPrimary,
                lineHeight = 21.sp
            )

            // 4. Snippet
            item.snippet?.takeIf { it.isNotBlank() }?.let {
                Text(
                    it,
                    style = MaterialTheme.typography.bodyMedium,
                    color = NewsBiasColors.TextSecondary,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                    lineHeight = 19.sp
                )
            }

            // 5. Leaning Bar OR Non-Political Badge
            val isNonPol = item.isNotPolitical || item.leaning() == "NOT_POLITICAL"
            if (isNonPol) {
                NotPoliticalBadge()
            } else if (item.lowConfidence || item.leaning() == "UNCLEAR") {
                Surface(
                    color = NewsBiasColors.SurfaceElevated,
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        "Coverage Stance: Objective / Unclear",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = NewsBiasColors.UnclearColor,
                        fontWeight = FontWeight.Medium
                    )
                }
            } else {
                LeaningBar(item.left ?: 0f, item.center ?: 0f, item.right ?: 0f)
            }

            // 6. Action Row
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 2.dp),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Read full article on ${item.source} ↗",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = NewsBiasColors.LeftColor
                )
            }
        }
    }
}

@Composable
fun NotPoliticalBadge(modifier: Modifier = Modifier) {
    Surface(
        color = NewsBiasColors.NotPoliticalBg,
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.NotPoliticalColor.copy(alpha = 0.35f)),
        modifier = modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(NewsBiasColors.NotPoliticalColor, shape = CircleShape)
            )
            Text(
                "Non-Political • Civic & Factual News",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = NewsBiasColors.NotPoliticalColor
            )
        }
    }
}

@Composable
fun LeaningBar(
    left: Float,
    center: Float,
    right: Float,
    modifier: Modifier = Modifier
) {
    val sum = (left + center + right).takeIf { it > 0f } ?: 1f
    val pL = (left / sum * 100).roundToInt()
    val pC = (center / sum * 100).roundToInt()
    val pR = (right / sum * 100).roundToInt()

    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(26.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(NewsBiasColors.SurfaceElevated)
            .semantics {
                contentDescription = "Left $pL percent, Center $pC percent, Right $pR percent"
            }
    ) {
        if (pL > 0) {
            Surface(
                color = NewsBiasColors.LeftColor,
                modifier = Modifier
                    .weight((left / sum).coerceAtLeast(0.04f))
                    .fillMaxHeight()
            ) {
                Box(contentAlignment = Alignment.Center) {
                    if (pL >= 10) {
                        Text(
                            "L $pL%",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        }
        if (pC > 0) {
            Surface(
                color = NewsBiasColors.CenterColor,
                modifier = Modifier
                    .weight((center / sum).coerceAtLeast(0.04f))
                    .fillMaxHeight()
            ) {
                Box(contentAlignment = Alignment.Center) {
                    if (pC >= 10) {
                        Text(
                            "C $pC%",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF0F172A)
                        )
                    }
                }
            }
        }
        if (pR > 0) {
            Surface(
                color = NewsBiasColors.RightColor,
                modifier = Modifier
                    .weight((right / sum).coerceAtLeast(0.04f))
                    .fillMaxHeight()
            ) {
                Box(contentAlignment = Alignment.Center) {
                    if (pR >= 10) {
                        Text(
                            "R $pR%",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        }
    }
}

private fun CachedArticle.leaning(): String {
    if (isNotPolitical) return "NOT_POLITICAL"
    if (lowConfidence) return "UNCLEAR"
    val l = left ?: return "UNCLEAR"
    val c = center ?: return "UNCLEAR"
    val r = right ?: return "UNCLEAR"
    val np = notPolitical
    if (np >= 0.35f && np >= l && np >= c && np >= r) return "NOT_POLITICAL"
    return if (maxOf(l, c, r) < UNCLEAR_THRESHOLD) "UNCLEAR" else if (l >= c && l >= r) "LEFT" else if (c >= r) "CENTER" else "RIGHT"
}

fun CachedStory.category(): String {
    if (isNotPolitical || (notPolitical >= 0.35f && notPolitical >= maxOf(left, center, right))) {
        return "Civic & Factual"
    }
    val t = title.lowercase()
    if (t.contains("court") || t.contains("sc") || t.contains("hc") || t.contains("cji") ||
        t.contains("verdict") || t.contains("bench") || t.contains("bail") || t.contains("plea") ||
        t.contains("judge") || t.contains("hearing") || t.contains("legal")
    ) {
        return "Judiciary & Law"
    }
    if (t.contains("election") || t.contains("poll") || t.contains("vote") || t.contains("bjp") ||
        t.contains("congress") || t.contains("modi") || t.contains("rahul") || t.contains("rally") ||
        t.contains("party") || t.contains("bloc") || t.contains("campaign") || t.contains("minister")
    ) {
        return "Politics"
    }
    if (t.contains("bank") || t.contains("poverty") || t.contains("budget") || t.contains("price") ||
        t.contains("gdp") || t.contains("rupee") || t.contains("tax") || t.contains("inflation") ||
        t.contains("trade") || t.contains("economy")
    ) {
        return "Economy"
    }
    return "Politics"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PullContent(
    refreshing: Boolean,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    val state = rememberPullToRefreshState()
    PullToRefreshBox(
        isRefreshing = refreshing,
        onRefresh = onRefresh,
        modifier = modifier.fillMaxSize(),
        state = state,
        indicator = {
            PullToRefreshDefaults.Indicator(
                state = state,
                isRefreshing = refreshing,
                modifier = Modifier.align(Alignment.TopCenter),
                containerColor = NewsBiasColors.SurfaceElevated,
                color = NewsBiasColors.BrandAccent
            )
        }
    ) {
        val density = androidx.compose.ui.platform.LocalDensity.current
        val offsetPx = with(density) {
            val progress = state.distanceFraction.coerceIn(0f, 1.5f)
            if (refreshing) 52.dp.toPx() else (progress * 48.dp.toPx())
        }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .graphicsLayer {
                    translationY = offsetPx
                }
        ) {
            content()
        }
    }
}

@Composable
private fun Loading() {
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = NewsBiasColors.BrandAccent)
    }
}

@Composable
private fun Empty(message: String) {
    Box(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(message, color = NewsBiasColors.TextSecondary, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ErrorCard(message: String) {
    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF2A1519)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE11D48).copy(alpha = 0.4f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            message,
            Modifier.padding(14.dp),
            color = Color(0xFFFDA4AF),
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InfoSheet(
    onDismiss: () -> Unit,
    onCheckUpdate: (() -> Unit)? = null,
    checkMessage: String? = null
) {
    val sheetState = rememberModalBottomSheetState(
        skipPartiallyExpanded = true
    )
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = NewsBiasColors.SurfaceCard,
        dragHandle = { BottomSheetDefaults.DragHandle(color = NewsBiasColors.BorderStrong) }
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 24.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .background(NewsBiasColors.BrandAccent, shape = CircleShape)
                )
                Text(
                    "About NewsBias India",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = NewsBiasColors.TextPrimary
                )
            }

            Text(
                "NewsBias analyzes multi-source news coverage across India using natural language processing to detect political framing, grammatical actor-target attributions, and source diversity.",
                style = MaterialTheme.typography.bodyMedium,
                color = NewsBiasColors.TextSecondary,
                lineHeight = 20.sp
            )

            // 1. Perspective Ratings Guide
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = NewsBiasColors.SurfaceElevated,
                border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Understanding Perspective Ratings",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary
                    )
                    Text("• Left: Progressive, opposition critique, constitutional and welfare emphasis.", style = MaterialTheme.typography.bodySmall, color = NewsBiasColors.LeftColor)
                    Text("• Center: Factual broadsheet reporting, judicial proceedings, balanced multi-viewpoint analysis.", style = MaterialTheme.typography.bodySmall, color = NewsBiasColors.CenterColor)
                    Text("• Right: Cultural nationalism, ruling administration policy, civilizational narratives.", style = MaterialTheme.typography.bodySmall, color = NewsBiasColors.RightColor)
                    Text("• Non-Political: Civic, weather, science, sports, and technical reporting without ideological spin.", style = MaterialTheme.typography.bodySmall, color = NewsBiasColors.NotPoliticalColor)
                }
            }

            // 2. Outlet Factuality & Sourcing Standards Guide
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = NewsBiasColors.SurfaceElevated,
                border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Outlet Factuality & Sourcing Tiers",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary
                    )
                    Text(
                        "• High: Outlets with rigorous primary sourcing, established fact-checking protocols, verified independent reporting standards, and minimal retractions (e.g. The Hindu, Indian Express, Hindustan Times, Times of India, NDTV).",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF93C5FD),
                        lineHeight = 18.sp
                    )
                    Text(
                        "• Standard: Regional news publications, digital portals, and syndication desks providing mainstream coverage with standard wire and agency reporting.",
                        style = MaterialTheme.typography.bodySmall,
                        color = NewsBiasColors.TextSecondary,
                        lineHeight = 18.sp
                    )
                    Text(
                        "• Mixed: Outlets with pronounced ideological stances, commentary-heavy formats, or history of selective reporting where opinion-driven framing strongly influences coverage (e.g. OpIndia, Swarajya, Organiser, National Herald).",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFFDA4AF),
                        lineHeight = 18.sp
                    )
                }
            }

            // 3. App Version & GitHub Releases Updater
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = NewsBiasColors.SurfaceElevated,
                border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                "App Version",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = NewsBiasColors.TextPrimary
                            )
                            Text(
                                "v${BuildConfig.VERSION_NAME} (Production)",
                                style = MaterialTheme.typography.bodySmall,
                                color = NewsBiasColors.TextSecondary
                            )
                        }
                        if (onCheckUpdate != null) {
                            OutlinedButton(
                                onClick = onCheckUpdate,
                                shape = RoundedCornerShape(8.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderStrong),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Text(
                                    "Check Update 🔄",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.SemiBold,
                                    color = NewsBiasColors.BrandAccent
                                )
                            }
                        }
                    }
                    if (!checkMessage.isNullOrBlank()) {
                        Text(
                            checkMessage,
                            style = MaterialTheme.typography.bodySmall,
                            color = NewsBiasColors.CenterColor,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            Button(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = NewsBiasColors.BrandAccent)
            ) {
                Text("Understood", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UpdateBottomSheet(
    info: AppUpdateInfo,
    downloadState: DownloadState,
    onStartDownload: () -> Unit,
    onInstall: (File) -> Unit,
    onDismiss: () -> Unit
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    ModalBottomSheet(
        onDismissRequest = {
            if (downloadState !is DownloadState.Downloading) {
                onDismiss()
            }
        },
        sheetState = sheetState,
        containerColor = NewsBiasColors.SurfaceCard,
        contentColor = NewsBiasColors.TextPrimary,
        tonalElevation = 8.dp
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 28.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .background(NewsBiasColors.BrandAccent.copy(alpha = 0.2f), shape = CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text("🚀", fontSize = 22.sp)
                }
                Column {
                    Text(
                        "New Update Available",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary
                    )
                    Text(
                        "${info.versionName} • ${(info.apkSize / (1024 * 1024.0)).let { "%.1f MB".format(it) }}",
                        style = MaterialTheme.typography.bodySmall,
                        color = NewsBiasColors.CenterColor,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            // Release Notes Box
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = NewsBiasColors.SurfaceElevated,
                border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderSubtle),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        "What's New in ${info.versionName}:",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = NewsBiasColors.TextPrimary
                    )
                    Text(
                        info.releaseNotes.trim(),
                        style = MaterialTheme.typography.bodySmall,
                        color = NewsBiasColors.TextSecondary,
                        lineHeight = 18.sp,
                        maxLines = 10,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

            // Download State / Action
            when (downloadState) {
                is DownloadState.Idle -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        OutlinedButton(
                            onClick = onDismiss,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, NewsBiasColors.BorderStrong)
                        ) {
                            Text("Later", color = NewsBiasColors.TextSecondary)
                        }
                        Button(
                            onClick = onStartDownload,
                            modifier = Modifier.weight(2f),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = NewsBiasColors.BrandAccent)
                        ) {
                            Text("Update Now 📥", fontWeight = FontWeight.Bold)
                        }
                    }
                }
                is DownloadState.Downloading -> {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                "Downloading APK update...",
                                style = MaterialTheme.typography.bodySmall,
                                color = NewsBiasColors.TextSecondary
                            )
                            Text(
                                "${(downloadState.progress * 100).toInt()}%",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.Bold,
                                color = NewsBiasColors.BrandAccent
                            )
                        }
                        LinearProgressIndicator(
                            progress = { downloadState.progress },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = NewsBiasColors.BrandAccent,
                            trackColor = NewsBiasColors.SurfaceElevated
                        )
                        Text(
                            "${(downloadState.downloadedBytes / (1024 * 1024.0)).let { "%.1f MB".format(it) }} / ${(downloadState.totalBytes / (1024 * 1024.0)).let { "%.1f MB".format(it) }}",
                            style = MaterialTheme.typography.labelSmall,
                            color = NewsBiasColors.TextTertiary,
                            modifier = Modifier.align(Alignment.End)
                        )
                    }
                }
                is DownloadState.ReadyToInstall -> {
                    Button(
                        onClick = { onInstall(downloadState.file) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = NewsBiasColors.CenterColor)
                    ) {
                        Text("Install Update 📲", fontWeight = FontWeight.Bold, color = Color(0xFF0F172A))
                    }
                }
                is DownloadState.Error -> {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            "Download error: ${downloadState.message}",
                            style = MaterialTheme.typography.bodySmall,
                            color = NewsBiasColors.RightColor
                        )
                        Button(
                            onClick = onStartDownload,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = NewsBiasColors.BrandAccent)
                        ) {
                            Text("Retry Download 🔄", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}
