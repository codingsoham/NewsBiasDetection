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
    private val repository: NewsRepository
) : ViewModel() {
    private val loading = MutableStateFlow(false)
    private val error = MutableStateFlow<String?>(null)

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
        if (id.value == storyId) return
        id.value = storyId
        error.value = null

        // Render cached articles from Room immediately with loading = false.
        // Only fetch from network if this story has no cached articles yet.
        viewModelScope.launch {
            val count = repository.getArticleCount(storyId)
            if (count == 0) {
                loading.value = true
                runCatching {
                    repository.refreshStory(storyId)
                }.onFailure {
                    error.value = "Offline mode. No cached articles for this story yet."
                }
                loading.value = false
            }
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
