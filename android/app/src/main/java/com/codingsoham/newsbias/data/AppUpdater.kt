package com.codingsoham.newsbias.data

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import com.codingsoham.newsbias.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import retrofit2.http.GET
import java.io.File
import java.io.FileOutputStream
import javax.inject.Inject
import javax.inject.Singleton

interface GitHubReleaseApi {
    @GET("repos/codingsoham/NewsBiasDetection/releases/latest")
    suspend fun getLatestRelease(): GitHubReleaseDto
}

sealed interface DownloadState {
    object Idle : DownloadState
    data class Downloading(val progress: Float, val downloadedBytes: Long, val totalBytes: Long) : DownloadState
    data class ReadyToInstall(val file: File) : DownloadState
    data class Error(val message: String) : DownloadState
}

@Singleton
class AppUpdater @Inject constructor(
    @ApplicationContext private val context: Context,
    private val gitHubApi: GitHubReleaseApi,
    private val okHttpClient: OkHttpClient
) {
    suspend fun checkForUpdate(): AppUpdateInfo? = withContext(Dispatchers.IO) {
        try {
            val release = gitHubApi.getLatestRelease()
            val remoteTag = release.tagName
            val currentVersion = BuildConfig.VERSION_NAME

            if (isNewerVersion(remoteTag, currentVersion)) {
                val apkAsset = release.assets.find { it.name.endsWith(".apk", ignoreCase = true) }
                    ?: release.assets.firstOrNull()

                if (apkAsset != null) {
                    return@withContext AppUpdateInfo(
                        versionName = remoteTag,
                        releaseTitle = release.name ?: "NewsBias $remoteTag",
                        releaseNotes = release.body ?: "New performance improvements and features.",
                        apkUrl = apkAsset.downloadUrl,
                        apkSize = apkAsset.size
                    )
                }
            }
            null
        } catch (e: Exception) {
            null
        }
    }

    suspend fun downloadApk(
        url: String,
        versionName: String,
        onProgress: (Float, Long, Long) -> Unit
    ): File = withContext(Dispatchers.IO) {
        val updatesDir = File(context.cacheDir, "updates").apply { mkdirs() }
        val safeName = versionName.replace("[^a-zA-Z0-9.-]".toRegex(), "_")
        val apkFile = File(updatesDir, "NewsBias-$safeName.apk")

        val request = Request.Builder()
            .url(url)
            .header("Accept", "application/octet-stream")
            .build()

        val response = okHttpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            throw IllegalStateException("Failed to download update: HTTP ${response.code()}")
        }

        val body = response.body() ?: throw IllegalStateException("Empty response body from update server")
        val totalBytes = body.contentLength()
        var downloadedBytes = 0L

        body.byteStream().use { input ->
            FileOutputStream(apkFile).use { output ->
                val buffer = ByteArray(16 * 1024)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    output.write(buffer, 0, bytesRead)
                    downloadedBytes += bytesRead
                    val progress = if (totalBytes > 0) downloadedBytes.toFloat() / totalBytes else 0f
                    onProgress(progress, downloadedBytes, totalBytes)
                }
                output.flush()
            }
        }

        apkFile
    }

    fun installApk(apkFile: File) {
        val fileUri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.provider",
            apkFile
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(fileUri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    companion object {
        fun isNewerVersion(remoteTag: String, currentVersion: String): Boolean {
            val cleanRemote = remoteTag.trim().removePrefix("v").removePrefix("V")
            val cleanCurrent = currentVersion.trim().removePrefix("v").removePrefix("V")
            val remoteParts = cleanRemote.split('.').mapNotNull { it.toIntOrNull() }
            val currentParts = cleanCurrent.split('.').mapNotNull { it.toIntOrNull() }

            val maxLen = maxOf(remoteParts.size, currentParts.size)
            for (i in 0 until maxLen) {
                val r = remoteParts.getOrElse(i) { 0 }
                val c = currentParts.getOrElse(i) { 0 }
                if (r > c) return true
                if (r < c) return false
            }
            return false
        }
    }
}
