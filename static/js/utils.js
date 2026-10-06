/**
 * SAVEWISE - Client-Side Utility Helpers
 * Enforces security (no innerHTML with dynamic data) & standard formatting.
 */

/**
 * Formats a monetary number in Indian Rupees (INR) using Indian numbering system.
 * e.g. 15000.5 -> "₹15,000.50"
 * Note: Never perform floating-point money calculations on client. Always use API *_inr values.
 */
export function formatINR(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return "₹0.00";
    }
    const num = Number(amount);
    return "₹" + num.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Converts integer paise to formatted INR string if needed.
 */
export function paiseToINR(paise) {
    if (paise === null || paise === undefined || isNaN(paise)) {
        return "₹0.00";
    }
    return formatINR(Number(paise) / 100);
}

/**
 * Returns current month in ISO "YYYY-MM" format.
 */
export function getCurrentMonth() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
}

/**
 * Returns today's date in "YYYY-MM-DD" format.
 */
export function getCurrentDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

/**
 * Formats a "YYYY-MM-DD" string into a readable date (e.g. "05 Oct 2026").
 */
export function formatDateDisplay(dateStr) {
    if (!dateStr || typeof dateStr !== "string") return "";
    const parts = dateStr.split("-");
    if (parts.length !== 3) return dateStr;
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    const dateObj = new Date(year, month, day);
    if (isNaN(dateObj.getTime())) return dateStr;
    return dateObj.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

/**
 * Safe DOM Element Factory to prevent Cross-Site Scripting (XSS).
 * Strictly uses textContent and setAttribute; NEVER uses innerHTML.
 */
export function createSafeElement(tag, options = {}, ...children) {
    const el = document.createElement(tag);

    if (options.className) {
        el.className = options.className;
    }

    if (options.text !== undefined && options.text !== null) {
        el.textContent = String(options.text);
    }

    if (options.attrs) {
        for (const [key, value] of Object.entries(options.attrs)) {
            if (value !== null && value !== undefined) {
                el.setAttribute(key, String(value));
            }
        }
    }

    if (options.events) {
        for (const [evt, handler] of Object.entries(options.events)) {
            el.addEventListener(evt, handler);
        }
    }

    for (const child of children) {
        if (child instanceof Node) {
            el.appendChild(child);
        } else if (child !== null && child !== undefined) {
            el.appendChild(document.createTextNode(String(child)));
        }
    }

    return el;
}

/**
 * Displays friendly, non-blocking toast notifications for user feedback.
 */
export function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = createSafeElement("div", {
        className: `toast toast-${type}`,
        text: message
    });

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
