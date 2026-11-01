package com.codingsoham.newsbias.data

import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface NewsApi {
    @GET("stories") suspend fun stories(@Query("force") force: Boolean = false): StoriesResponse
    @GET("stories/bundle") suspend fun bundle(@Query("force") force: Boolean = false): StoryBundleResponse
    @GET("stories/{id}") suspend fun story(@Path("id") id: Long): StoryDetailDto
}
