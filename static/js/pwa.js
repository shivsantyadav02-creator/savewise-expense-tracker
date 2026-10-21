/**
 * Savewise PWA Registration & Lifecycle Handler
 * Registers root service worker and displays non-blocking update notifications.
 */

(function () {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    let refreshing = false;

    // Reload page when new service worker takes control
    navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!refreshing) {
            refreshing = true;
            window.location.reload();
        }
    });

    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
            .then((registration) => {
                // If a worker is already waiting, prompt immediately
                if (registration.waiting) {
                    showUpdatePrompt(registration.waiting);
                    return;
                }

                // If a new worker is found installing
                registration.addEventListener("updatefound", () => {
                    const newWorker = registration.installing;
                    if (!newWorker) return;

                    newWorker.addEventListener("statechange", () => {
                        // If new worker installed and we already have a controller (i.e. not the very first install)
                        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
                            showUpdatePrompt(newWorker);
                        }
                    });
                });
            })
            .catch((error) => {
                console.warn("Savewise Service Worker registration failed:", error);
            });
    });

    function showUpdatePrompt(worker) {
        // Prevent duplicate prompts
        if (document.getElementById("pwaUpdateBanner")) return;

        const banner = document.createElement("div");
        banner.id = "pwaUpdateBanner";
        banner.setAttribute("role", "alert");
        banner.setAttribute("aria-live", "polite");

        // Inline resilient styles for non-blocking toast at the bottom right
        Object.assign(banner.style, {
            position: "fixed",
            bottom: "20px",
            right: "20px",
            zIndex: "10000",
            backgroundColor: "#0f172a",
            color: "#ffffff",
            padding: "12px 18px",
            borderRadius: "10px",
            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.3)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: "0.875rem",
            fontFamily: "var(--font-family, sans-serif)",
            animation: "fadeIn 0.3s ease"
        });

        const text = document.createElement("span");
        text.textContent = "Update available!";

        const refreshBtn = document.createElement("button");
        refreshBtn.textContent = "Refresh";
        Object.assign(refreshBtn.style, {
            background: "#2563eb",
            color: "#ffffff",
            border: "none",
            borderRadius: "6px",
            padding: "6px 12px",
            fontSize: "0.825rem",
            fontWeight: "600",
            cursor: "pointer"
        });
        refreshBtn.onclick = () => {
            if (worker) {
                worker.postMessage({ type: "SKIP_WAITING" });
            } else {
                window.location.reload();
            }
        };

        const closeBtn = document.createElement("button");
        closeBtn.textContent = "✕";
        closeBtn.setAttribute("aria-label", "Dismiss update prompt");
        Object.assign(closeBtn.style, {
            background: "transparent",
            color: "#94a3b8",
            border: "none",
            padding: "4px 8px",
            fontSize: "0.9rem",
            cursor: "pointer"
        });
        closeBtn.onclick = () => {
            banner.remove();
        };

        banner.appendChild(text);
        banner.appendChild(refreshBtn);
        banner.appendChild(closeBtn);
        document.body.appendChild(banner);
    }
})();
