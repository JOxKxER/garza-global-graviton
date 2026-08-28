# Graviton Android Network Prototype

`GravitonVpnService.kt` is a source skeleton for an offline-first Android
network optimizer. It is not a complete VPN forwarding implementation yet:
the packet loop needs an authenticated local proxy/tunnel protocol that parses
IP packets and writes valid response packets back to the TUN descriptor.

## Integration

Add the Kotlin coroutines dependency to the Android module:

```kotlin
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:<version>")
implementation("androidx.work:work-runtime-ktx:<version>")
implementation("androidx.security:security-crypto:<version>")
```

Declare the service in `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />

<!-- Prototype only; prefer HTTPS for a production gateway. -->
<application android:usesCleartextTraffic="true">

<service
    android:name=".network.GravitonVpnService"
    android:exported="false"
    android:permission="android.permission.BIND_VPN_SERVICE">
    <intent-filter>
        <action android:name="android.net.VpnService" />
    </intent-filter>
    <meta-data
        android:name="android.net.VpnService.SUPPORTS_ALWAYS_ON"
        android:value="false" />
</service>
</application>
```

Before starting the service, the app must call `VpnService.prepare(context)` and
launch the returned consent intent when it is not `null`. The service should
also be promoted to a foreground service with a user-visible notification on
Android versions that require it.

The implementation uses `ConnectivityManager.registerNetworkCallback` to track
Wi-Fi and cellular `Network` handles. Each proxy socket is protected from the
VPN loop and bound with `Network.bindSocket`; transport selection prefers a
validated Wi-Fi link, then validated cellular, with retry across remaining
links when a connection fails.

## Zero-PII telemetry vault

`ZeroPiiTelemetryVault.kt` accepts packet byte arrays from the TUN reader and
stores only aggregate packet lengths, a count, and a batch digest. It does not
persist packet contents, IP addresses, ports, timestamps, device identifiers,
or application payloads. Records are encrypted with AES-GCM using a key held in
the Android Keystore and writes are serialized on `Dispatchers.IO`.

Example from a coroutine owned by the service:

```kotlin
val vault = ZeroPiiTelemetryVault(this)
val receipt = vault.appendPacketBatch(listOf(packet.copyOf(packetLength)))
```

The vault key is generated locally on first use and is never exported. Decrypt
records only for local diagnostics with the same app installation and key.

Provision the shared gateway passphrase into the app's
`EncryptedSharedPreferences` under file `ggg_gateway_secrets` and key
`gateway_passphrase` before scheduling synchronization. Do not place the
passphrase in WorkManager input data, source code, logs, or APK resources.

## Local PC gateway

`GravitonGatewayConfig.kt` points the prototype at
`http://10.238.126.142:5000/api/v1/sensory/telemetry`. The VPN proxy socket
target uses the same PC host and port. `streamEncryptedBatch()` sends only a
Base64-encoded AES-CBC/HMAC envelope containing aggregate counts and the batch
digest. The outbound key is derived from the injected shared passphrase; the
Android Keystore key is never transmitted. The gateway must be
implemented to accept this `application/octet-stream` envelope and return a
2xx response. Android also requires the `INTERNET` permission. The cleartext
HTTP application setting above is for this trusted-LAN prototype only; replace
it with a TLS endpoint and a network security policy before production use.

The TUN proxy path currently targets the same gateway host and port, but its
`forwardThroughProxy` method remains a protocol stub: it must be replaced with
the authenticated gateway framing protocol before raw TUN packets are sent.

Schedule periodic sync from application startup with
`TelemetrySyncWorker.schedule(context)`. WorkManager supplies a connected
network constraint; the worker additionally requires an active, unsuspended
Wi-Fi or Ethernet transport and uses `Network.openConnection()` to bind each
HTTP request to that transport.