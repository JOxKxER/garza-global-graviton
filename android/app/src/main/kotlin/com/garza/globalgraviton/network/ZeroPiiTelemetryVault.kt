package com.garza.globalgraviton.network

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.security.KeyStore
import java.security.MessageDigest
import java.security.SecureRandom
import java.net.HttpURLConnection
import java.net.URL
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.Mac
import javax.crypto.SecretKeyFactory
import javax.crypto.SecretKey
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Converts transient TUN packets into zero-PII aggregate telemetry and stores
 * each encrypted batch locally. Raw packet bytes never enter a persisted record.
 */
class ZeroPiiTelemetryVault(
    context: Context,
    private val batchSize: Int = DEFAULT_BATCH_SIZE,
    private val gatewayPassphrase: String = ""
) {
    private val appContext = context.applicationContext
    private val vaultFile = File(appContext.filesDir, VAULT_FILE_NAME)
    private val syncedFile = File(appContext.filesDir, SYNCED_FILE_NAME)
    private val writeMutex = Mutex()
    private val secureRandom = SecureRandom()
    private val keyAlias = "ggg.zero_pii.telemetry.v1"

    init {
        require(batchSize in 1..MAX_BATCH_SIZE) {
            "batchSize must be between 1 and $MAX_BATCH_SIZE"
        }
        require(getOrCreateKey().algorithm == KeyProperties.KEY_ALGORITHM_AES)
    }

    /**
     * Encrypt and append a batch on the IO dispatcher.
     *
     * Only packet lengths, batch count, and a SHA-256 batch digest are retained.
     * Packet content, IP addresses, ports, headers, timestamps, and device data
     * are intentionally excluded from the vault record.
     */
    suspend fun appendPacketBatch(packetBytes: List<ByteArray>): BatchReceipt =
        withContext(Dispatchers.IO) {
            require(packetBytes.isNotEmpty()) { "packet batch cannot be empty" }
            require(packetBytes.size <= batchSize) {
                "packet batch exceeds configured batch size"
            }

            val lengths = packetBytes.map { packet ->
                require(packet.size <= MAX_PACKET_BYTES) {
                    "packet exceeds the maximum supported size"
                }
                packet.size
            }
            val digest = digestBatch(packetBytes)
            val record = JSONObject()
                .put("schema", SCHEMA)
                .put("packet_count", packetBytes.size)
                .put("total_bytes", lengths.sum())
                .put("packet_lengths", JSONArray(lengths))
                .put("batch_digest_sha256", digest)

            val encrypted = encrypt(record.toString().toByteArray(Charsets.UTF_8))
            writeMutex.withLock {
                appendLine(encrypted)
            }
            BatchReceipt(packetBytes.size, lengths.sum(), digest)
        }

    /** Read and decrypt local records for local diagnostics only. */
    suspend fun readBatches(): List<JSONObject> = withContext(Dispatchers.IO) {
        if (!vaultFile.exists()) return@withContext emptyList()
        vaultFile.readLines(Charsets.UTF_8).filter { it.isNotBlank() }.map { line ->
            val fields = line.split('.', limit = 2)
            require(fields.size == 2) { "corrupt telemetry vault record" }
            val iv = android.util.Base64.decode(fields[0], android.util.Base64.NO_WRAP)
            val ciphertext = android.util.Base64.decode(
                fields[1],
                android.util.Base64.NO_WRAP
            )
            JSONObject(decrypt(iv, ciphertext).toString(Charsets.UTF_8))
        }
    }

    suspend fun vaultSizeBytes(): Long = withContext(Dispatchers.IO) {
        vaultFile.length()
    }

    /** Return aggregate batches whose digest has not received a 2xx response. */
    suspend fun readUnsyncedBatches(limit: Int): List<JSONObject> =
        withContext(Dispatchers.IO) {
            require(limit > 0) { "limit must be positive" }
            val synced = if (syncedFile.exists()) {
                syncedFile.readLines(Charsets.UTF_8).toHashSet()
            } else {
                emptySet()
            }
            readBatches().asSequence()
                .filter { batch ->
                    batch.has("batch_digest_sha256") &&
                        !synced.contains(batch.getString("batch_digest_sha256"))
                }
                .take(limit)
                .map { batch ->
                    JSONObject()
                        .put("schema", SCHEMA)
                        .put("packet_count", batch.getInt("packet_count"))
                        .put("total_bytes", batch.getInt("total_bytes"))
                        .put(
                            "batch_digest_sha256",
                            batch.getString("batch_digest_sha256")
                        )
                }
                .toList()
        }

    /** Encode one aggregate batch with the shared gateway AES-CBC/HMAC protocol. */
    fun encodeGatewayEnvelope(batch: JSONObject): ByteArray {
        require(gatewayPassphrase.isNotEmpty()) {
            "gateway passphrase must be provided at runtime"
        }
        return encryptForGateway(
            JSONObject()
                .put("schema", SCHEMA)
                .put("packet_count", batch.getInt("packet_count"))
                .put("total_bytes", batch.getInt("total_bytes"))
                .put(
                    "batch_digest_sha256",
                    batch.getString("batch_digest_sha256")
                )
                .toString()
                .toByteArray(Charsets.UTF_8),
            gatewayPassphrase
        )
    }

    suspend fun markBatchSynced(batchDigest: String) = withContext(Dispatchers.IO) {
        require(batchDigest.matches(Regex("[0-9a-f]{64}"))) {
            "invalid batch digest"
        }
        writeMutex.withLock {
            syncedFile.parentFile?.mkdirs()
            FileOutputStream(syncedFile, true).bufferedWriter(Charsets.UTF_8).use {
                it.append(batchDigest).append('\n')
            }
        }
    }

    /**
     * POST one encrypted vault record to the configured local gateway.
     * The gateway receives ciphertext only; the Android Keystore key remains
     * local, so this method never sends raw packets or identifiers.
     */
    suspend fun streamEncryptedBatch(receipt: BatchReceipt): Int =
        withContext(Dispatchers.IO) {
            require(gatewayPassphrase.isNotEmpty()) {
                "gateway passphrase must be provided at runtime"
            }
            val envelope = encodeGatewayEnvelope(
                JSONObject()
                    .put("packet_count", receipt.packetCount)
                    .put("total_bytes", receipt.totalBytes)
                    .put("batch_digest_sha256", receipt.batchDigestSha256)
            )
            val body = android.util.Base64.encodeToString(
                envelope,
                android.util.Base64.NO_WRAP
            )
            val connection = (URL(GravitonGatewayConfig.telemetryUri.toString())
                .openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = NETWORK_TIMEOUT_MS
                readTimeout = NETWORK_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/octet-stream")
                setRequestProperty("Content-Length", body.length.toString())
            }
            try {
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                connection.responseCode
            } finally {
                connection.disconnect()
            }
        }

    private fun encryptForGateway(
        plaintext: ByteArray,
        passphrase: String
    ): ByteArray {
        val salt = ByteArray(GATEWAY_SALT_BYTES)
        val iv = ByteArray(GATEWAY_IV_BYTES)
        secureRandom.nextBytes(salt)
        secureRandom.nextBytes(iv)
        val keyMaterial = SecretKeyFactory.getInstance(
            GATEWAY_KDF
        ).generateSecret(
            PBEKeySpec(
                passphrase.toCharArray(),
                salt,
                GATEWAY_KDF_ITERATIONS,
                GATEWAY_KEY_BITS
            )
        ).encoded
        val cipher = Cipher.getInstance(GATEWAY_CIPHER)
        cipher.init(
            Cipher.ENCRYPT_MODE,
            SecretKeySpec(keyMaterial.copyOf(GATEWAY_AES_KEY_BYTES), "AES"),
            IvParameterSpec(iv)
        )
        val ciphertext = cipher.doFinal(plaintext)
        val authenticated = GATEWAY_MAGIC + salt + iv + ciphertext
        val mac = Mac.getInstance(GATEWAY_MAC)
        mac.init(
            SecretKeySpec(
                keyMaterial.copyOfRange(
                    GATEWAY_AES_KEY_BYTES,
                    GATEWAY_KEY_BYTES
                ),
                GATEWAY_MAC
            )
        )
        return authenticated + mac.doFinal(authenticated)
    }

    private fun digestBatch(packetBytes: List<ByteArray>): String {
        val digest = MessageDigest.getInstance("SHA-256")
        packetBytes.forEach { packet ->
            digest.update(ByteBuffer.allocate(Int.SIZE_BYTES).putInt(packet.size).array())
            digest.update(packet)
        }
        return digest.digest().joinToString("") { byte -> "%02x".format(byte) }
    }

    private fun encrypt(plaintext: ByteArray): EncryptedRecord {
        val iv = ByteArray(GCM_IV_BYTES)
        secureRandom.nextBytes(iv)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
        return EncryptedRecord(iv, cipher.doFinal(plaintext))
    }

    private fun decrypt(iv: ByteArray, ciphertext: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            getOrCreateKey(),
            GCMParameterSpec(GCM_TAG_BITS, iv)
        )
        return cipher.doFinal(ciphertext)
    }

    private fun appendLine(record: EncryptedRecord) {
        vaultFile.parentFile?.mkdirs()
        FileOutputStream(vaultFile, true).bufferedWriter(Charsets.UTF_8).use { writer ->
            val iv = android.util.Base64.encodeToString(
                record.iv,
                android.util.Base64.NO_WRAP
            )
            val ciphertext = android.util.Base64.encodeToString(
                record.ciphertext,
                android.util.Base64.NO_WRAP
            )
            writer.append(iv).append('.').append(ciphertext).append('\n')
        }
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (keyStore.getKey(keyAlias, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )
        generator.init(
            KeyGenParameterSpec.Builder(
                keyAlias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUserAuthenticationRequired(false)
                .build()
        )
        return generator.generateKey()
    }

    private data class EncryptedRecord(
        val iv: ByteArray,
        val ciphertext: ByteArray
    )

    data class BatchReceipt(
        val packetCount: Int,
        val totalBytes: Int,
        val batchDigestSha256: String
    )

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val GCM_TAG_BITS = 128
        const val GCM_IV_BYTES = 12
        const val MAX_PACKET_BYTES = 65_535
        const val DEFAULT_BATCH_SIZE = 64
        const val MAX_BATCH_SIZE = 256
        const val NETWORK_TIMEOUT_MS = 5_000
        const val GATEWAY_KDF = "PBKDF2WithHmacSHA256"
        const val GATEWAY_CIPHER = "AES/CBC/PKCS5Padding"
        const val GATEWAY_MAC = "HmacSHA256"
        const val GATEWAY_KDF_ITERATIONS = 390_000
        const val GATEWAY_KEY_BITS = 512
        const val GATEWAY_AES_KEY_BYTES = 32
        const val GATEWAY_KEY_BYTES = 64
        const val GATEWAY_SALT_BYTES = 16
        const val GATEWAY_IV_BYTES = 16
        val GATEWAY_MAGIC = "GGG-AESCBC-HMAC1\u0000".toByteArray(Charsets.US_ASCII)
        const val VAULT_FILE_NAME = "zero_pii_telemetry.jsonl.enc"
        const val SYNCED_FILE_NAME = "zero_pii_telemetry.synced"
        const val SCHEMA = "ggg.zero-pii.telemetry.v1"
    }
}
