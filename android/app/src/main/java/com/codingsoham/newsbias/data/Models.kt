package com.codingsoham.newsbias.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.squareup.moshi.Json

data class StoryDto(
    val id: Long,
    val title: String,
    val sources: Int,
    @Json(name="p_left") val left: Float = 0f,
    @Json(name="p_center") val center: Float = 0f,
    @Json(name="p_right") val right: Float = 0f,
    @Json(name="p_not_political") val notPolitical: Float = 0f,
    @Json(name="is_not_political") val isNotPolitical: Boolean = false
)

data class StoriesResponse(val items: List<StoryDto>)

data class StoryBundleItem(
    val id: Long,
    val title: String,
    val sources: Int,
    @Json(name="p_left") val left: Float = 0f,
    @Json(name="p_center") val center: Float = 0f,
    @Json(name="p_right") val right: Float = 0f,
    @Json(name="p_not_political") val notPolitical: Float = 0f,
    @Json(name="is_not_political") val isNotPolitical: Boolean = false,
    val articles: List<ArticleDto> = emptyList()
)

data class StoryBundleResponse(val items: List<StoryBundleItem>)

data class ArticleDto(
    val id: Long,
    val source: String,
    val url: String,
    val title: String,
    val snippet: String?,
    @Json(name="published_at") val publishedAt: String?,
    @Json(name="source_description") val sourceDescription: String? = null,
    @Json(name="source_factuality") val sourceFactuality: String? = null,
    @Json(name="source_editorial") val sourceEditorial: String? = null,
    val prediction: PredictionDto? = null
)

data class StoryDetailDto(val id: Long, val articles: List<ArticleDto>)

data class PredictionDto(
    @Json(name="p_left") val left: Float = 0f,
    @Json(name="p_center") val center: Float = 0f,
    @Json(name="p_right") val right: Float = 0f,
    @Json(name="p_not_political") val notPolitical: Float = 0f,
    @Json(name="is_not_political") val isNotPolitical: Boolean = false,
    @Json(name="low_confidence") val lowConfidence: Boolean = false
)

@Entity(tableName = "stories")
data class CachedStory(
    @PrimaryKey val id: Long,
    val title: String,
    val sources: Int,
    val left: Float,
    val center: Float,
    val right: Float,
    val notPolitical: Float = 0f,
    val isNotPolitical: Boolean = false,
    val orderIndex: Int = 0,
    val refreshedAt: Long
)

@Entity(tableName = "articles")
data class CachedArticle(
    @PrimaryKey val id: Long,
    val storyId: Long,
    val source: String,
    val url: String,
    val title: String,
    val snippet: String?,
    val publishedAt: String?,
    val left: Float?,
    val center: Float?,
    val right: Float?,
    val notPolitical: Float = 0f,
    val isNotPolitical: Boolean = false,
    val lowConfidence: Boolean,
    val sourceDescription: String? = null,
    val sourceFactuality: String? = null,
    val sourceEditorial: String? = null
)

data class GitHubReleaseDto(
    @Json(name = "tag_name") val tagName: String = "",
    val name: String? = null,
    val body: String? = null,
    @Json(name = "published_at") val publishedAt: String? = null,
    val assets: List<GitHubAssetDto> = emptyList()
)

data class GitHubAssetDto(
    val name: String = "",
    @Json(name = "browser_download_url") val downloadUrl: String = "",
    val size: Long = 0L
)

data class AppUpdateInfo(
    val versionName: String,
    val releaseTitle: String,
    val releaseNotes: String,
    val apkUrl: String,
    val apkSize: Long
)
