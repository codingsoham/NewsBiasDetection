package com.codingsoham.newsbias.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.codingsoham.newsbias.data.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FeedState(
    val stories: List<CachedStory> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class FeedViewModel @Inject constructor(
    private val repository: NewsRepository,
    private val appUpdater: AppUpdater
) : ViewModel() {
    private val loading = MutableStateFlow(false)
    private val error = MutableStateFlow<String?>(null)

    val updateInfo = MutableStateFlow<AppUpdateInfo?>(null)
    val downloadState = MutableStateFlow<DownloadState>(DownloadState.Idle)
    val updateCheckMessage = MutableStateFlow<String?>(null)

    val state: StateFlow<FeedState> = combine(
        repository.stories(),
        loading,
        error
    ) { stories, l, e ->
        FeedState(stories, l, e)
    }.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        FeedState(loading = false)
    )

    init {
        // Automatically check for GitHub releases on app open
        checkForUpdates(isManual = false)

        // App launch: do NOT trigger pull-to-refresh spinner.
        // Cached stories from Room render instantly (0ms delay).
        // Only trigger an initial background fetch if Room is completely empty (first run).
        viewModelScope.launch {
            if (repository.getStoryCount() == 0) {
                loading.value = true
                runCatching {
                    repository.refreshStories(force = false)
                }.onFailure {
                    error.value = "Offline mode. Connect to internet to download news."
                }
                loading.value = false
            }
        }
    }

    fun checkForUpdates(isManual: Boolean = false) {
        viewModelScope.launch {
            val info = appUpdater.checkForUpdate()
            if (info != null) {
                updateInfo.value = info
            } else if (isManual) {
                updateCheckMessage.value = "You are on the latest version (v${com.codingsoham.newsbias.BuildConfig.VERSION_NAME})."
            }
        }
    }

    fun startDownload(info: AppUpdateInfo) {
        viewModelScope.launch {
            downloadState.value = DownloadState.Downloading(0f, 0L, info.apkSize)
            runCatching {
                val file = appUpdater.downloadApk(info.apkUrl, info.versionName) { progress, downloaded, total ->
                    downloadState.value = DownloadState.Downloading(progress, downloaded, total)
                }
                downloadState.value = DownloadState.ReadyToInstall(file)
                appUpdater.installApk(file)
            }.onFailure {
                downloadState.value = DownloadState.Error(it.message ?: "Failed to download update.")
            }
        }
    }

    fun installDownloaded(file: java.io.File) {
        appUpdater.installApk(file)
    }

    fun dismissUpdate() {
        updateInfo.value = null
        downloadState.value = DownloadState.Idle
    }

    fun dismissCheckMessage() {
        updateCheckMessage.value = null
    }

    // Manual pull-to-refresh: triggered only when user physically pulls down
    fun refresh(force: Boolean = true) = viewModelScope.launch {
        loading.value = true
        error.value = null
        runCatching {
            repository.refreshStories(force = force)
        }.onFailure {
            val hasStories = repository.getStoryCount() > 0
            if (hasStories) {
                error.value = "Offline mode. Showing cached stories."
            } else {
                error.value = "Could not refresh. Please check your internet connection."
            }
        }
        loading.value = false
    }
}

data class DetailState(
    val articles: List<CachedArticle> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null
)

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
@HiltViewModel
class DetailViewModel @Inject constructor(
    private val repository: NewsRepository
) : ViewModel() {
    private val id = MutableStateFlow<Long?>(null)
    private val loading = MutableStateFlow(false)
    private val error = MutableStateFlow<String?>(null)

    val state: StateFlow<DetailState> = id.filterNotNull().flatMapLatest { storyId ->
        combine(repository.articles(storyId), loading, error) { articles, l, e ->
            DetailState(articles, l, e)
        }
    }.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        DetailState(loading = false)
    )

    fun load(storyId: Long) {
        id.value = storyId
        error.value = null

        // Render cached articles from Room immediately (0ms latency).
        // Concurrently fetch authoritative story detail from network to ensure exact content alignment.
        viewModelScope.launch {
            val count = repository.getArticleCount(storyId)
            if (count == 0) {
                loading.value = true
            }
            runCatching {
                repository.refreshStory(storyId)
            }.onFailure {
                if (repository.getArticleCount(storyId) == 0) {
                    error.value = "Offline mode. No cached articles for this story yet."
                }
            }
            loading.value = false
        }
    }

    // Manual pull-to-refresh on detail screen
    fun refresh() = viewModelScope.launch {
        val storyId = id.value ?: return@launch
        loading.value = true
        error.value = null
        runCatching {
            repository.refreshStory(storyId)
        }.onFailure {
            val count = repository.getArticleCount(storyId)
            if (count > 0) {
                error.value = "Offline mode. Showing cached articles."
            } else {
                error.value = "Could not refresh story. Check internet connection."
            }
        }
        loading.value = false
    }
}
