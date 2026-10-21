/**
 * SAVEWISE - API Fetch Client
 * Communicates with Flask backend under /api/v1/.
 * Handles JSON envelope unpacking and clean error handling.
 */

const BASE_URL = "/api/v1";

async function request(endpoint, options = {}) {
    const config = {
        headers: {
            "Accept": "application/json",
            ...options.headers
        },
        ...options
    };

    if (config.body && typeof config.body === "object") {
        config.headers["Content-Type"] = "application/json";
        config.body = JSON.stringify(config.body);
    }

    let response;
    try {
        response = await fetch(`${BASE_URL}${endpoint}`, config);
    } catch (networkError) {
        throw new Error("Unable to connect to Savewise server. Please check your connection.");
    }

    let result;
    try {
        result = await response.json();
    } catch (parseError) {
        throw new Error("Server returned an invalid non-JSON response.");
    }

    if (!response.ok || !result.success) {
        // NOTE: When a session expires or an unauthenticated user accesses protected app data,
        // the server responds with 401, requiring an immediate redirect to /login.
        // However, this redirect must NOT apply to /auth/login or /auth/register, or when
        // the user is already on the /login page.
        // Why: Bad credentials during login return 401 by design; redirecting would wipe
        // the form state, reload the page, or cause a redirect loop instead of allowing
        // the login UI to display "Invalid email or password." to the user.
        const isAuthCall = endpoint.startsWith("/auth/login") || endpoint.startsWith("/auth/register");
        const isOnLoginPage = typeof window !== "undefined" && window.location && window.location.pathname.startsWith("/login");

        if (response.status === 401 && !isAuthCall && !isOnLoginPage) {
            window.location.href = "/login";
        }
        const errorMsg = (result && result.error) ? result.error : `HTTP ${response.status} error`;
        throw new Error(errorMsg);
    }

    return result.data;
}

export const api = {
    // Auth
    login: (credentials) => request("/auth/login", { method: "POST", body: credentials }),
    register: (data) => request("/auth/register", { method: "POST", body: data }),
    logout: () => request("/auth/logout", { method: "POST" }),
    getCurrentUser: () => request("/auth/me"),

    // Dashboard
    getDashboardSummary: (month) => {
        const query = month ? `?month=${encodeURIComponent(month)}` : "";
        return request(`/dashboard/summary${query}`);
    },
    getDashboardHistory: (months = 6, month = null) => {
        const params = new URLSearchParams();
        if (months) params.append("months", months);
        if (month) params.append("month", month);
        const query = params.toString() ? `?${params.toString()}` : "";
        return request(`/dashboard/history${query}`);
    },

    // Incomes
    getIncomes: (month) => {
        const query = month ? `?month=${encodeURIComponent(month)}` : "";
        return request(`/incomes${query}`);
    },
    getIncomeById: (id) => request(`/incomes/${id}`),
    createIncome: (data) => request("/incomes", { method: "POST", body: data }),
    updateIncome: (id, data) => request(`/incomes/${id}`, { method: "PUT", body: data }),
    deleteIncome: (id) => request(`/incomes/${id}`, { method: "DELETE" }),

    // Expenses
    getExpenses: (month, type = null) => {
        const params = new URLSearchParams();
        if (month) params.append("month", month);
        if (type && type !== "all") params.append("type", type);
        const query = params.toString() ? `?${params.toString()}` : "";
        return request(`/expenses${query}`);
    },
    getExpenseById: (id) => request(`/expenses/${id}`),
    createExpense: (data) => request("/expenses", { method: "POST", body: data }),
    updateExpense: (id, data) => request(`/expenses/${id}`, { method: "PUT", body: data }),
    deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" }),

    // Budgets (Faltu Limit)
    getBudget: (month) => request(`/budgets/${encodeURIComponent(month)}`),
    setBudget: (month, data) => request(`/budgets/${encodeURIComponent(month)}`, { method: "PUT", body: data }),

    // Savings Goals
    getGoal: (month) => request(`/goals/${encodeURIComponent(month)}`),
    setGoal: (month, data) => request(`/goals/${encodeURIComponent(month)}`, { method: "PUT", body: data }),

    // Quick Presets
    getPresets: () => request("/presets"),
    createPreset: (data) => request("/presets", { method: "POST", body: data }),
    updatePreset: (id, data) => request(`/presets/${id}`, { method: "PUT", body: data }),
    deletePreset: (id) => request(`/presets/${id}`, { method: "DELETE" }),
    usePreset: (id) => request(`/presets/${id}/use`, { method: "POST" }),

    // Wishlist (24-Hour Wait Rule)
    getWishlist: (status = "waiting") => request(`/wishlist?status=${encodeURIComponent(status)}`),
    getWishlistSummary: () => request("/wishlist/summary"),
    createWishlist: (data) => request("/wishlist", { method: "POST", body: data }),
    updateWishlist: (id, data) => request(`/wishlist/${id}`, { method: "PUT", body: data }),
    buyWishlist: (id) => request(`/wishlist/${id}/buy`, { method: "POST" }),
    dropWishlist: (id) => request(`/wishlist/${id}/drop`, { method: "POST" }),

    // Udhar (Money Lent / Borrowed)
    getUdhar: (status = "pending", type = null) => {
        const params = new URLSearchParams({ status });
        if (type) params.append("type", type);
        return request(`/udhar?${params.toString()}`);
    },
    getUdharSummary: () => request("/udhar/summary"),
    createUdhar: (data) => request("/udhar", { method: "POST", body: data }),
    updateUdhar: (id, data) => request(`/udhar/${id}`, { method: "PUT", body: data }),
    settleUdhar: (id) => request(`/udhar/${id}/settle`, { method: "POST" }),
    reopenUdhar: (id) => request(`/udhar/${id}/reopen`, { method: "POST" }),
    deleteUdhar: (id) => request(`/udhar/${id}`, { method: "DELETE" }),

    // Phase 3 Insights (Simulator, Balance Prediction, Summary, Weekly Report)
    getSimulator: (month, annualReturn = 12) => {
        const params = new URLSearchParams({ month });
        if (annualReturn !== undefined && annualReturn !== null) {
            params.append("annual_return", annualReturn);
        }
        return request(`/insights/simulator?${params.toString()}`);
    },
    getPrediction: (month) => request(`/insights/prediction?month=${encodeURIComponent(month)}`),
    getInsightsSummary: (month) => request(`/insights/summary?month=${encodeURIComponent(month)}`),
    getWeeklyReport: (weekStart = null) => {
        const url = weekStart ? `/insights/weekly?week_start=${encodeURIComponent(weekStart)}` : "/insights/weekly";
        return request(url);
    }
};
