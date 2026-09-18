//! Global Graviton Gauntlet (#GGG) — Tauri desktop shell.
//!
//! Air-gapped wrapper around the root `index.html`:
//!  * pings the local Ollama daemon at http://localhost:11434 on startup and
//!    completes that check BEFORE the native window is revealed;
//!  * injects a tactical-red offline banner into the page when the daemon is
//!    unreachable, with the exact `ollama serve` / `ollama pull` commands;
//!  * lives in the system tray (Show / Recheck Ollama / Quit) and closes to
//!    the tray instead of exiting.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::time::Duration;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager};

const OLLAMA_TAGS_URL: &str = "http://localhost:11434/api/tags";
const OLLAMA_TIMEOUT_SECS: u64 = 2;

/// Ping the local Ollama daemon. Any HTTP response — even an error status —
/// proves the daemon is alive; only transport-level failure means "offline".
fn ollama_reachable() -> bool {
    match ureq::get(OLLAMA_TAGS_URL)
        .timeout(Duration::from_secs(OLLAMA_TIMEOUT_SECS))
        .call()
    {
        Ok(_) => true,
        Err(ureq::Error::Status(_, _)) => true,
        Err(_) => false,
    }
}

/// Inject (or clear) the tactical-red offline banner inside the webview.
/// Pure DOM manipulation — no privileged IPC, no frontend permissions needed.
fn inject_status_banner(window: &tauri::WebviewWindow, online: bool) {
    let js = if online {
        r#"document.getElementById('ggg-ollama-banner')?.remove();"#.to_string()
    } else {
        r#"(() => {
            if (document.getElementById('ggg-ollama-banner')) return;
            const b = document.createElement('div');
            b.id = 'ggg-ollama-banner';
            b.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:99999;background:#7f1d1d;color:#fecaca;font:13px/1.6 monospace;padding:10px 14px;text-align:center;border-bottom:2px solid #ef4444;';
            b.innerHTML = '&#9888; LOCAL OLLAMA NOT DETECTED &mdash; run <code style="background:rgba(0,0,0,.4);padding:2px 6px;border-radius:4px;color:#fff">ollama serve</code> then <code style="background:rgba(0,0,0,.4);padding:2px 6px;border-radius:4px;color:#fff">ollama pull qwen2.5-coder:latest</code>';
            document.body.prepend(b);
        })();"#
        .to_string()
    };
    let _ = window.eval(&js);
}

/// System tray hooks: Show, Recheck Ollama, Quit.
fn build_tray(app: &AppHandle) -> tauri::Result<()> {
    let show = MenuItem::with_id(app, "show", "Show Gauntlet", true, None::<&str>)?;
    let recheck = MenuItem::with_id(app, "recheck", "Recheck Ollama", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &recheck, &quit])?;

    let mut tray = TrayIconBuilder::with_id("ggg-tray")
        .menu(&menu)
        .tooltip("Global Graviton Gauntlet (#GGG)")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.show();
                    let _ = w.set_focus();
                }
            }
            "recheck" => {
                let online = ollama_reachable();
                if let Some(w) = app.get_webview_window("main") {
                    inject_status_banner(&w, online);
                }
            }
            "quit" => app.exit(0),
            _ => {}
        });

    // Icons are optional until `cargo tauri icon` has been run (see BUILD_INSTRUCTIONS.md).
    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }
    tray.build(app)?;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Verify the loopback Ollama daemon BEFORE revealing the UI.
            let online = ollama_reachable();

            build_tray(app.handle())?;

            if let Some(window) = app.get_webview_window("main") {
                // The window starts hidden (visible:false in tauri.conf.json) and
                // is only revealed once the connectivity check has completed.
                window.show()?;
                window.set_focus()?;

                if !online {
                    // Give the local page a beat to parse, then stamp the banner.
                    let w = window.clone();
                    std::thread::spawn(move || {
                        std::thread::sleep(Duration::from_millis(1200));
                        inject_status_banner(&w, false);
                    });
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            // Close to tray instead of exiting — Quit lives on the tray menu.
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Global Graviton Gauntlet");
}
