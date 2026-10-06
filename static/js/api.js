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
        const errorMsg = (result && result.error) ? result.error : `HTTP ${response.status} error`;
        throw new Error(errorMsg);
    }

    return result.data;
}

export const api = {
    // Dashboard
    getDashboardSummary: (month) => {
        const query = month ? `?month=${encodeURIComponent(month)}` : "";
        return request(`/dashboard/summary${query}`);
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
    deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" })
};
