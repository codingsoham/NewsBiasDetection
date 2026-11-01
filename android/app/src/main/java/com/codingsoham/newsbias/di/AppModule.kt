package com.codingsoham.newsbias.di

import android.content.Context
import androidx.room.Room
import com.codingsoham.newsbias.BuildConfig
import com.codingsoham.newsbias.data.*
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module @InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton fun moshi(): Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
    @Provides @Singleton fun okHttpClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(45, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()
    @Provides @Singleton fun api(moshi: Moshi, client: OkHttpClient): NewsApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(NewsApi::class.java)
    @Provides @Singleton fun gitHubApi(moshi: Moshi, client: OkHttpClient): GitHubReleaseApi = Retrofit.Builder()
        .baseUrl("https://api.github.com/")
        .client(client)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(GitHubReleaseApi::class.java)
    @Provides @Singleton fun db(@ApplicationContext c: Context): NewsDatabase = Room.databaseBuilder(c, NewsDatabase::class.java, "news-bias.db")
        .fallbackToDestructiveMigration()
        .build()
    @Provides fun dao(db: NewsDatabase): NewsDao = db.dao()
}
