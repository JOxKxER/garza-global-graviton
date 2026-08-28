package com.garza.globalgraviton

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import com.garza.globalgraviton.network.GravitonVpnService

/**
 * Minimal launcher activity: obtains VPN consent, then starts the tunnel service.
 *
 * GravitonVpnService is intentionally not exported and requires
 * android.permission.BIND_VPN_SERVICE, so it can only be started from within
 * this app's own process (e.g. via `adb shell am start -n .../.MainActivity`),
 * never directly from another app or from `adb shell am startservice`.
 */
class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val gatewayUrl = intent?.getStringExtra("gateway_url")
        val consentIntent = VpnService.prepare(this)
        if (consentIntent != null) {
            pendingGatewayUrl = gatewayUrl
            startActivityForResult(consentIntent, VPN_CONSENT_REQUEST_CODE)
        } else {
            startVpnService(gatewayUrl)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == VPN_CONSENT_REQUEST_CODE && resultCode == RESULT_OK) {
            startVpnService(pendingGatewayUrl)
        }
    }

    private fun startVpnService(gatewayUrl: String?) {
        val serviceIntent = Intent(this, GravitonVpnService::class.java)
        if (!gatewayUrl.isNullOrEmpty()) {
            serviceIntent.putExtra("gateway_url", gatewayUrl)
        }
        startForegroundService(serviceIntent)
    }

    private var pendingGatewayUrl: String? = null

    private companion object {
        const val VPN_CONSENT_REQUEST_CODE = 1
    }
}
