package com.garza.globalgraviton.network

import java.net.URI

/** Local PC gateway targets for the Android proof-of-concept. */
object GravitonGatewayConfig {
    const val HOST = "10.238.126.142"
    const val PORT = 5000
    const val TELEMETRY_PATH = "/api/v1/sensory/telemetry"

    val telemetryUri: URI = URI.create("http://$HOST:$PORT$TELEMETRY_PATH")
}
