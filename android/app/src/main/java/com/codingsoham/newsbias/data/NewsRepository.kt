package com.codingsoham.newsbias.data

import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton class NewsRepository @Inject constructor(private val api: NewsApi, private val dao: NewsDao) {
    fun stories(): Flow<List<CachedStory>> = dao.stories()
    fun articles(id: Long): Flow<List<CachedArticle>> = dao.articles(id)

    suspend fun getStoryCount(): Int = dao.storyCount()
    suspend fun getArticleCount(storyId: Long): Int = dao.articleCount(storyId)

    suspend fun refreshStories(force: Boolean = false) {
        val now = System.currentTimeMillis()
        try {
            // First attempt multi-story bundle sync for instant atomic offline Room caching
            val bundle = api.bundle(force = force)
            val cachedStories = bundle.items.mapIndexed { idx, it ->
                CachedStory(
                    it.id, it.title, it.sources, it.left, it.center, it.right,
                    it.notPolitical, it.isNotPolitical, idx, now
                )
            }
            val cachedArticles = bundle.items.flatMap { s ->
                s.articles.map { a ->
                    val p = a.prediction
                    CachedArticle(
                        a.id, s.id, a.source, a.url, a.title, a.snippet, a.publishedAt,
                        p?.left, p?.center, p?.right,
                        p?.notPolitical ?: 0f,
                        p?.isNotPolitical ?: false,
                        p?.lowConfidence ?: true,
                        a.sourceDescription,
                        a.sourceFactuality,
                        a.sourceEditorial
                    )
                }
            }
            dao.replaceBundle(cachedStories, cachedArticles)
        } catch (e: Exception) {
            // Fallback to stories endpoint if bundle fails
            val response = api.stories(force = force)
            val items = response.items.mapIndexed { idx, it ->
                CachedStory(
                    it.id, it.title, it.sources, it.left, it.center, it.right,
                    it.notPolitical, it.isNotPolitical, idx, now
                )
            }
            dao.replaceStories(items)
        }
    }

    suspend fun refreshStory(id: Long) {
        val detail = api.story(id)
        dao.replaceArticles(id, detail.articles.map { a ->
            val p = a.prediction
            CachedArticle(
                a.id, id, a.source, a.url, a.title, a.snippet, a.publishedAt,
                p?.left, p?.center, p?.right,
                p?.notPolitical ?: 0f,
                p?.isNotPolitical ?: false,
                p?.lowConfidence ?: true,
                a.sourceDescription,
                a.sourceFactuality,
                a.sourceEditorial
            )
        })
    }
}
