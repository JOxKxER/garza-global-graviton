package com.garza.globalgraviton.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.util.concurrent.TimeUnit

/**
 * Periodically synchronizes aggregate-only vault batches over a local Wi-Fi or
 * tethered hotspot connection. Only successfully acknowledged batches are
 * marked synced; failures leave them available for the next retry.
 */
class TelemetrySyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val network = findStableLocalNetwork() ?: return@withContext Result.retry()
        val passphrase = GatewayPassphraseStore.read(applicationContext)
            ?: return@withContext Result.failure()
        val vault = ZeroPiiTelemetryVault(
            applicationContext,
            gatewayPassphrase = passphrase
        )
        val batches = vault.readUnsyncedBatches(MAX_BATCHES_PER_RUN)
        if (batches.isEmpty()) return@withContext Result.success()

        for (batch in batches) {
            if (!sendBatch(network, vault, batch)) {
                return@withContext Result.retry()
            }
        }
        Result.success()
    }

    private fun findStableLocalNetwork(): Network? {
        val connectivity = applicationContext.getSystemService(
            ConnectivityManager::class.java
        ) ?: return null
        return connectivity.allNetworks
            .mapNotNull { network ->
                val capabilities = connectivity.getNetworkCapabilities(network)
                    ?: return@mapNotNull null
                if (!isStableLocalTransport(capabilities)) null else network
            }
            .firstOrNull()
    }

    private fun isStableLocalTransport(
        capabilities: NetworkCapabilities
    ): Boolean {
        val wirelessOrEthernet = capabilities.hasTransport(
            NetworkCapabilities.TRANSPORT_WIFI
        ) || capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
        val usable = capabilities.hasCapability(
            NetworkCapabilities.NET_CAPABILITY_NOT_SUSPENDED
        )
        return wirelessOrEthernet && usable
    }

    private suspend fun sendBatch(
        network: Network,
        vault: ZeroPiiTelemetryVault,
        batch: JSONObject
    ): Boolean {
        val connection = network.openConnection(
            GravitonGatewayConfig.telemetryUri.toURL()
        ) as HttpURLConnection
        return try {
            val envelope = vault.encodeGatewayEnvelope(batch)
            val body = android.util.Base64.encodeToString(
                envelope,
                android.util.Base64.NO_WRAP
            ).toByteArray(Charsets.US_ASCII)
            connection.requestMethod = "POST"
            connection.connectTimeout = REQUEST_TIMEOUT_MS
            connection.readTimeout = REQUEST_TIMEOUT_MS
            connection.doOutput = true
            connection.useCaches = false
            connection.setRequestProperty(
                "Content-Type",
                "application/octet-stream"
            )
            connection.setFixedLengthStreamingMode(body.size)
            connection.outputStream.use { it.write(body) }
            val accepted = connection.responseCode in 200..299
            if (accepted) {
                vault.markBatchSynced(batch.getString("batch_digest_sha256"))
            }
            accepted
        } catch (_: Exception) {
            false
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        private const val WORK_NAME = "ggg-telemetry-sync"
        private const val MAX_BATCHES_PER_RUN = 32
        private const val REQUEST_TIMEOUT_MS = 5_000

        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = PeriodicWorkRequestBuilder<TelemetrySyncWorker>(
                15,
                TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request
            )
        }
    }
}

/** Reads the gateway secret from encrypted app storage, never WorkManager data. */
private object GatewayPassphraseStore {
    private const val FILE_NAME = "ggg_gateway_secrets"
    private const val KEY = "gateway_passphrase"

    fun read(context: Context): String? {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        val preferences = EncryptedSharedPreferences.create(
            context,
            FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
        return preferences.getString(KEY, null)?.takeIf { it.isNotEmpty() }
    }
}
