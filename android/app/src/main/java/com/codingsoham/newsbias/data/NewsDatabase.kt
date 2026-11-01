package com.codingsoham.newsbias.data

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

@Dao interface NewsDao {
    @Query("SELECT * FROM stories ORDER BY orderIndex ASC") fun stories(): Flow<List<CachedStory>>
    @Query("DELETE FROM stories") suspend fun clearStories(): Int
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun saveStories(items: List<CachedStory>)
    @Query("SELECT COUNT(*) FROM stories") suspend fun storyCount(): Int

    @Query("SELECT * FROM articles WHERE storyId=:storyId") fun articles(storyId: Long): Flow<List<CachedArticle>>
    @Query("DELETE FROM articles WHERE storyId=:storyId") suspend fun deleteArticles(storyId: Long): Int
    @Query("DELETE FROM articles") suspend fun clearAllArticles(): Int
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun saveArticles(items: List<CachedArticle>)
    @Query("SELECT COUNT(*) FROM articles WHERE storyId=:storyId") suspend fun articleCount(storyId: Long): Int
    @Query("DELETE FROM articles WHERE storyId NOT IN (SELECT id FROM stories)") suspend fun deleteOrphanedArticles(): Int

    @androidx.room.Transaction
    suspend fun replaceStories(items: List<CachedStory>) {
        clearStories()
        saveStories(items)
        deleteOrphanedArticles()
    }

    @androidx.room.Transaction
    suspend fun replaceArticles(storyId: Long, items: List<CachedArticle>) {
        deleteArticles(storyId)
        saveArticles(items)
    }

    @androidx.room.Transaction
    suspend fun replaceBundle(stories: List<CachedStory>, articles: List<CachedArticle>) {
        clearStories()
        saveStories(stories)
        if (articles.isNotEmpty()) {
            clearAllArticles()
            saveArticles(articles)
        } else {
            deleteOrphanedArticles()
        }
    }
}
@Database(entities=[CachedStory::class,CachedArticle::class], version=4, exportSchema=false)
abstract class NewsDatabase : RoomDatabase() { abstract fun dao(): NewsDao }
