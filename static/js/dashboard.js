/**
 * SAVEWISE - Main Dashboard Controller
 * Connects UI events to API, manages state, renders tables and cards safely.
 * Security: Uses textContent and safe DOM creation; ZERO innerHTML for API data.
 */

import { api } from "./api.js";
import { formatINR, getCurrentMonth, getCurrentDate, formatDateDisplay, formatMonthDisplay, formatMonthShort, createSafeElement, showToast } from "./utils.js";
import { loadUdhar, initUdharEventListeners } from "./udhar.js";
import { loadInsights, initInsightsEventListeners } from "./insights.js";

// ========================================================
// 1. Application State
// ========================================================
const state = {
    activeMonth: getCurrentMonth(),
    expenseFilter: "all"
};

// ========================================================
// 2. DOM Elements Cache
// ========================================================
const DOM = {
    // Toolbar & Month
    monthPicker: document.getElementById("monthPicker"),
    currentMonthBtn: document.getElementById("currentMonthBtn"),

    // Summary Cards
    cardTotalIncome: document.getElementById("cardTotalIncome"),
    cardIncomeCount: document.getElementById("cardIncomeCount"),
    cardTotalDaily: document.getElementById("cardTotalDaily"),
    cardTotalFaltu: document.getElementById("cardTotalFaltu"),
    cardFaltuPercentage: document.getElementById("cardFaltuPercentage"),
    cardFaltuIncomePercent: document.getElementById("cardFaltuIncomePercent"),
    cardTotalBalance: document.getElementById("cardTotalBalance"),
    cardBalanceStatus: document.getElementById("cardBalanceStatus"),

    // Tables & Empty States
    incomesTableBody: document.getElementById("incomesTableBody"),
    incomesEmptyState: document.getElementById("incomesEmptyState"),
    expensesTableBody: document.getElementById("expensesTableBody"),
    expensesEmptyState: document.getElementById("expensesEmptyState"),

    // Filter Buttons
    filterAll: document.getElementById("filterAll"),
    filterDaily: document.getElementById("filterDaily"),
    filterFaltu: document.getElementById("filterFaltu"),

    // Income Modal & Form
    openAddIncomeBtn: document.getElementById("openAddIncomeBtn"),
    closeIncomeModalBtn: document.getElementById("closeIncomeModalBtn"),
    cancelIncomeBtn: document.getElementById("cancelIncomeBtn"),
    incomeModal: document.getElementById("incomeModal"),
    incomeModalTitle: document.getElementById("incomeModalTitle"),
    incomeForm: document.getElementById("incomeForm"),
    incomeId: document.getElementById("incomeId"),
    incomeAmount: document.getElementById("incomeAmount"),
    incomeSource: document.getElementById("incomeSource"),
    incomeDate: document.getElementById("incomeDate"),
    incomeNote: document.getElementById("incomeNote"),
    saveIncomeBtn: document.getElementById("saveIncomeBtn"),

    // Expense Modal & Form
    openAddExpenseBtn: document.getElementById("openAddExpenseBtn"),
    closeExpenseModalBtn: document.getElementById("closeExpenseModalBtn"),
    cancelExpenseBtn: document.getElementById("cancelExpenseBtn"),
    expenseModal: document.getElementById("expenseModal"),
    expenseModalTitle: document.getElementById("expenseModalTitle"),
    expenseForm: document.getElementById("expenseForm"),
    expenseId: document.getElementById("expenseId"),
    expenseCategory: document.getElementById("expenseCategory"),
    expenseAmount: document.getElementById("expenseAmount"),
    expenseDate: document.getElementById("expenseDate"),
    expenseNote: document.getElementById("expenseNote"),
    saveExpenseBtn: document.getElementById("saveExpenseBtn"),

    // Phase 2 - Faltu Limit card
    faltuLimitEmpty:   document.getElementById("faltuLimitEmpty"),
    faltuLimitData:    document.getElementById("faltuLimitData"),
    faltuLimitUsed:    document.getElementById("faltuLimitUsed"),
    faltuLimitMax:     document.getElementById("faltuLimitMax"),
    faltuLimitBar:     document.getElementById("faltuLimitBar"),
    faltuLimitMessage: document.getElementById("faltuLimitMessage"),
    openSetLimitBtn:   document.getElementById("openSetLimitBtn"),
    limitModal:        document.getElementById("limitModal"),
    limitForm:         document.getElementById("limitForm"),
    limitAmount:       document.getElementById("limitAmount"),
    saveLimitBtn:      document.getElementById("saveLimitBtn"),
    closeLimitModalBtn:document.getElementById("closeLimitModalBtn"),
    cancelLimitBtn:    document.getElementById("cancelLimitBtn"),

    // Phase 2 - Savings Goal card
    savingsGoalEmpty:   document.getElementById("savingsGoalEmpty"),
    savingsGoalData:    document.getElementById("savingsGoalData"),
    savingsGoalLabel:   document.getElementById("savingsGoalLabel"),
    savingsGoalBalance: document.getElementById("savingsGoalBalance"),
    savingsGoalTarget:  document.getElementById("savingsGoalTarget"),
    savingsGoalBar:     document.getElementById("savingsGoalBar"),
    savingsGoalMessage: document.getElementById("savingsGoalMessage"),
    openSetGoalBtn:     document.getElementById("openSetGoalBtn"),
    goalModal:          document.getElementById("goalModal"),
    goalForm:           document.getElementById("goalForm"),
    goalTitle:          document.getElementById("goalTitle"),
    goalTarget:         document.getElementById("goalTarget"),
    saveGoalBtn:        document.getElementById("saveGoalBtn"),
    closeGoalModalBtn:  document.getElementById("closeGoalModalBtn"),
    cancelGoalBtn:      document.getElementById("cancelGoalBtn"),

    // Chart.js elements
    doughnutChartCard:     document.getElementById("doughnutChartCard"),
    expenseDoughnutChart:  document.getElementById("expenseDoughnutChart"),
    doughnutEmptyState:    document.getElementById("doughnutEmptyState"),
    doughnutCanvasWrapper: document.getElementById("doughnutCanvasWrapper"),
    doughnutMonthLabel:    document.getElementById("doughnutMonthLabel"),
    historyChartCard:      document.getElementById("historyChartCard"),
    historyBarChart:       document.getElementById("historyBarChart"),
    historyEmptyState:     document.getElementById("historyEmptyState"),
    historyCanvasWrapper:  document.getElementById("historyCanvasWrapper"),

    // Quick Presets elements
    quickAddContainer:      document.getElementById("quickAddContainer"),
    quickAddButtonsRow:     document.getElementById("quickAddButtonsRow"),
    quickAddEmpty:          document.getElementById("quickAddEmpty"),
    openManagePresetsBtn:   document.getElementById("openManagePresetsBtn"),
    addSuggestedPresetsBtn: document.getElementById("addSuggestedPresetsBtn"),
    presetModal:            document.getElementById("presetModal"),
    closePresetModalBtn:    document.getElementById("closePresetModalBtn"),
    closePresetDialogBtn:   document.getElementById("closePresetDialogBtn"),
    presetForm:             document.getElementById("presetForm"),
    presetFormSubtitle:     document.getElementById("presetFormSubtitle"),
    presetId:               document.getElementById("presetId"),
    presetTitle:            document.getElementById("presetTitle"),
    presetAmount:           document.getElementById("presetAmount"),
    presetRadioFaltu:       document.getElementById("presetRadioFaltu"),
    presetRadioDaily:       document.getElementById("presetRadioDaily"),
    presetCategory:         document.getElementById("presetCategory"),
    presetIcon:             document.getElementById("presetIcon"),
    savePresetBtn:          document.getElementById("savePresetBtn"),
    cancelPresetEditBtn:    document.getElementById("cancelPresetEditBtn"),
    presetsListContainer:   document.getElementById("presetsListContainer"),
    presetCountBadge:       document.getElementById("presetCountBadge"),

    // Wishlist elements
    wishlistMoneySavedBadge: document.getElementById("wishlistMoneySavedBadge"),
    addWishlistForm:         document.getElementById("addWishlistForm"),
    wishlistItemName:        document.getElementById("wishlistItemName"),
    wishlistAmount:          document.getElementById("wishlistAmount"),
    wishlistCategory:        document.getElementById("wishlistCategory"),
    saveWishlistBtn:         document.getElementById("saveWishlistBtn"),
    wishlistItemsContainer:  document.getElementById("wishlistItemsContainer"),
    wishlistEmptyState:      document.getElementById("wishlistEmptyState")
};

let doughnutChartInstance = null;
let historyChartInstance = null;
let wishlistTimer = null;
let currentWishlistItems = [];

// ========================================================
// 3. Render Helpers
// ========================================================

/**
 * Updates the 4 Summary Financial Cards on the dashboard.
 */
function renderSummaryCards(summary) {
    if (!summary) return;

    // 1. Total Income
    DOM.cardTotalIncome.textContent = formatINR(summary.total_income_inr);
    DOM.cardIncomeCount.textContent = `${summary.income_count || 0} transaction${summary.income_count === 1 ? "" : "s"} recorded`;

    // 2. Daily Expenses
    DOM.cardTotalDaily.textContent = formatINR(summary.total_daily_inr);

    // 3. Faltu Expenses
    DOM.cardTotalFaltu.textContent = formatINR(summary.total_faltu_inr);
    DOM.cardFaltuPercentage.textContent = `${summary.faltu_percentage}% of expenses`;
    DOM.cardFaltuIncomePercent.textContent = `${summary.faltu_percent_of_income}% of income`;

    // 4. Net Balance
    DOM.cardTotalBalance.textContent = formatINR(summary.balance_inr);
    DOM.cardTotalBalance.classList.remove("balance-positive", "balance-negative");

    if (summary.balance_inr >= 0) {
        DOM.cardTotalBalance.classList.add("balance-positive");
        DOM.cardBalanceStatus.textContent = "Positive surplus this month";
    } else {
        DOM.cardTotalBalance.classList.add("balance-negative");
        DOM.cardBalanceStatus.textContent = "Deficit: spending exceeds income";
    }
}

/**
 * Safely renders the list of Incomes in the table.
 * Strictly uses textContent to prevent XSS.
 */
function renderIncomesTable(incomes) {
    DOM.incomesTableBody.replaceChildren();

    if (!incomes || incomes.length === 0) {
        DOM.incomesEmptyState.style.display = "block";
        return;
    }

    DOM.incomesEmptyState.style.display = "none";

    incomes.forEach((income) => {
        const tr = document.createElement("tr");

        // Date
        const tdDate = createSafeElement("td", { text: formatDateDisplay(income.date) });

        // Source
        const tdSource = createSafeElement("td", {
            className: "font-semibold",
            text: income.source
        });

        // Note
        const tdNote = createSafeElement("td", {
            className: "note-cell",
            text: income.note || "—"
        });

        // Amount (using API's amount_inr)
        const tdAmount = createSafeElement("td", {
            className: "text-right table-amount income-amount",
            text: `+${formatINR(income.amount_inr)}`
        });

        // Actions (Edit & Delete)
        const tdActions = createSafeElement("td", { className: "text-center" });
        const actionsWrapper = createSafeElement("div", { className: "actions-cell" });

        const editBtn = createSafeElement("button", {
            className: "btn-action edit-btn",
            text: "Edit",
            attrs: { "type": "button", "title": "Edit this income" },
            events: {
                click: () => openEditIncomeModal(income)
            }
        });

        const deleteBtn = createSafeElement("button", {
            className: "btn-action delete-btn",
            text: "Delete",
            attrs: { "type": "button", "title": "Delete this income" },
            events: {
                click: () => handleDeleteIncome(income.id, income.source, income.amount_inr)
            }
        });

        actionsWrapper.appendChild(editBtn);
        actionsWrapper.appendChild(deleteBtn);
        tdActions.appendChild(actionsWrapper);

        tr.appendChild(tdDate);
        tr.appendChild(tdSource);
        tr.appendChild(tdNote);
        tr.appendChild(tdAmount);
        tr.appendChild(tdActions);

        DOM.incomesTableBody.appendChild(tr);
    });
}

/**
 * Safely renders the list of Expenses in the table.
 * Includes Daily vs Faltu badge.
 */
function renderExpensesTable(expenses) {
    DOM.expensesTableBody.replaceChildren();

    if (!expenses || expenses.length === 0) {
        DOM.expensesEmptyState.style.display = "block";
        return;
    }

    DOM.expensesEmptyState.style.display = "none";

    expenses.forEach((expense) => {
        const tr = document.createElement("tr");

        // Date
        const tdDate = createSafeElement("td", { text: formatDateDisplay(expense.date) });

        // Type Badge
        const tdType = createSafeElement("td");
        const isFaltu = expense.type === "faltu";
        const badge = createSafeElement("span", {
            className: isFaltu ? "badge badge-faltu" : "badge badge-daily",
            text: isFaltu ? "Faltu" : "Daily"
        });
        tdType.appendChild(badge);

        // Sub-Category
        const tdCategory = createSafeElement("td", {
            className: "font-semibold",
            text: expense.sub_category
        });

        // Note
        const tdNote = createSafeElement("td", {
            className: "note-cell",
            text: expense.note || "—"
        });

        // Amount
        const tdAmount = createSafeElement("td", {
            className: "text-right table-amount expense-amount",
            text: `-${formatINR(expense.amount_inr)}`
        });

        // Actions
        const tdActions = createSafeElement("td", { className: "text-center" });
        const actionsWrapper = createSafeElement("div", { className: "actions-cell" });

        const editBtn = createSafeElement("button", {
            className: "btn-action edit-btn",
            text: "Edit",
            attrs: { "type": "button", "title": "Edit this expense" },
            events: {
                click: () => openEditExpenseModal(expense)
            }
        });

        const deleteBtn = createSafeElement("button", {
            className: "btn-action delete-btn",
            text: "Delete",
            attrs: { "type": "button", "title": "Delete this expense" },
            events: {
                click: () => handleDeleteExpense(expense.id, expense.sub_category, expense.amount_inr)
            }
        });

        actionsWrapper.appendChild(editBtn);
        actionsWrapper.appendChild(deleteBtn);
        tdActions.appendChild(actionsWrapper);

        tr.appendChild(tdDate);
        tr.appendChild(tdType);
        tr.appendChild(tdCategory);
        tr.appendChild(tdNote);
        tr.appendChild(tdAmount);
        tr.appendChild(tdActions);

        DOM.expensesTableBody.appendChild(tr);
    });
}

// ========================================================
// 4. Data Fetching / Coordinator
// ========================================================
async function loadDashboard() {
    try {
        const [summary, incomes, expenses, history, presets, wishlistItems, wishlistSummary] = await Promise.all([
            api.getDashboardSummary(state.activeMonth),
            api.getIncomes(state.activeMonth),
            api.getExpenses(state.activeMonth, state.expenseFilter),
            api.getDashboardHistory(6, state.activeMonth),
            api.getPresets(),
            api.getWishlist("waiting"),
            api.getWishlistSummary()
        ]);

        renderSummaryCards(summary);
        renderIncomesTable(incomes);
        renderExpensesTable(expenses);

        // Phase 2: render limit & goal progress cards from the enriched summary
        renderFaltuLimitCard(summary);
        renderSavingsGoalCard(summary);

        // Charts: Doughnut & 6-month history bar chart
        renderDoughnutChart(summary);
        renderHistoryChart(history);

        // Quick Presets bar
        renderQuickAddBar(presets);

        // 24-Hour Wait Wishlist
        renderWishlist(wishlistItems, wishlistSummary);

        // Phase 3: Insights & Balance Prediction
        loadInsights(state.activeMonth);
    } catch (err) {
        showToast(err.message || "Failed to load dashboard data", "error");
    }
}

// ========================================================
// 5. Income Modal & Action Handlers
// ========================================================
function openAddIncomeModal() {
    DOM.incomeForm.reset();
    DOM.incomeId.value = "";
    DOM.incomeDate.value = getCurrentDate();
    DOM.incomeModalTitle.textContent = "Add Income";
    DOM.saveIncomeBtn.textContent = "Save Income";
    DOM.incomeModal.classList.add("open");
    DOM.incomeAmount.focus();
}

function openEditIncomeModal(income) {
    DOM.incomeId.value = income.id;
    DOM.incomeAmount.value = income.amount_inr;
    DOM.incomeSource.value = income.source;
    DOM.incomeDate.value = income.date;
    DOM.incomeNote.value = income.note || "";
    DOM.incomeModalTitle.textContent = "Edit Income";
    DOM.saveIncomeBtn.textContent = "Update Income";
    DOM.incomeModal.classList.add("open");
    DOM.incomeAmount.focus();
}

function closeIncomeModal() {
    DOM.incomeModal.classList.remove("open");
}

async function handleIncomeFormSubmit(e) {
    e.preventDefault();

    const amount = parseFloat(DOM.incomeAmount.value);
    const source = DOM.incomeSource.value.trim();
    const date = DOM.incomeDate.value;
    const note = DOM.incomeNote.value.trim();
    const id = DOM.incomeId.value;

    if (!amount || amount <= 0) {
        showToast("Please enter a valid amount greater than ₹0", "error");
        DOM.incomeAmount.focus();
        return;
    }
    if (!source) {
        showToast("Income source cannot be empty", "error");
        DOM.incomeSource.focus();
        return;
    }
    if (!date) {
        showToast("Please select a transaction date", "error");
        return;
    }

    const payload = {
        amount_inr: amount,
        source: source,
        date: date,
        note: note
    };

    DOM.saveIncomeBtn.disabled = true;
    try {
        if (id) {
            await api.updateIncome(id, payload);
            showToast("Income record updated successfully!", "success");
        } else {
            await api.createIncome(payload);
            showToast("Income record added successfully!", "success");
        }
        closeIncomeModal();
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.saveIncomeBtn.disabled = false;
    }
}

async function handleDeleteIncome(id, source, amount) {
    const formatted = formatINR(amount);
    const confirmed = window.confirm(`Are you sure you want to delete this income entry?\n\nSource: ${source}\nAmount: ${formatted}`);
    if (!confirmed) return;

    try {
        await api.deleteIncome(id);
        showToast("Income record deleted.", "success");
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ========================================================
// 6. Expense Modal & Action Handlers
// ========================================================
function openAddExpenseModal() {
    DOM.expenseForm.reset();
    DOM.expenseId.value = "";
    document.getElementById("radioTypeDaily").checked = true;
    DOM.expenseDate.value = getCurrentDate();
    DOM.expenseModalTitle.textContent = "Add Expense";
    DOM.saveExpenseBtn.textContent = "Save Expense";
    DOM.expenseModal.classList.add("open");
    DOM.expenseAmount.focus();
}

function openEditExpenseModal(expense) {
    DOM.expenseId.value = expense.id;
    if (expense.type === "faltu") {
        document.getElementById("radioTypeFaltu").checked = true;
    } else {
        document.getElementById("radioTypeDaily").checked = true;
    }
    DOM.expenseCategory.value = expense.sub_category;
    DOM.expenseAmount.value = expense.amount_inr;
    DOM.expenseDate.value = expense.date;
    DOM.expenseNote.value = expense.note || "";
    DOM.expenseModalTitle.textContent = "Edit Expense";
    DOM.saveExpenseBtn.textContent = "Update Expense";
    DOM.expenseModal.classList.add("open");
    DOM.expenseAmount.focus();
}

function closeExpenseModal() {
    DOM.expenseModal.classList.remove("open");
}

async function handleExpenseFormSubmit(e) {
    e.preventDefault();

    const selectedRadio = document.querySelector('input[name="expenseTypeRadio"]:checked');
    const expenseType = selectedRadio ? selectedRadio.value : "daily";
    const subCategory = DOM.expenseCategory.value.trim();
    const amount = parseFloat(DOM.expenseAmount.value);
    const date = DOM.expenseDate.value;
    const note = DOM.expenseNote.value.trim();
    const id = DOM.expenseId.value;

    if (!amount || amount <= 0) {
        showToast("Please enter a valid expense amount greater than ₹0", "error");
        DOM.expenseAmount.focus();
        return;
    }
    if (!subCategory) {
        showToast("Sub-category cannot be empty", "error");
        DOM.expenseCategory.focus();
        return;
    }
    if (!date) {
        showToast("Please select a transaction date", "error");
        return;
    }

    const payload = {
        type: expenseType,
        sub_category: subCategory,
        amount_inr: amount,
        date: date,
        note: note
    };

    DOM.saveExpenseBtn.disabled = true;
    try {
        if (id) {
            await api.updateExpense(id, payload);
            showToast("Expense record updated successfully!", "success");
        } else {
            await api.createExpense(payload);
            showToast("Expense record logged successfully!", "success");
        }
        closeExpenseModal();
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.saveExpenseBtn.disabled = false;
    }
}

async function handleDeleteExpense(id, subCategory, amount) {
    const formatted = formatINR(amount);
    const confirmed = window.confirm(`Are you sure you want to delete this expense entry?\n\nCategory: ${subCategory}\nAmount: ${formatted}`);
    if (!confirmed) return;

    try {
        await api.deleteExpense(id);
        showToast("Expense record deleted.", "success");
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ========================================================
// 7. Event Listeners Initialization
// ========================================================
function initEventListeners() {
    // Month Picker
    DOM.monthPicker.value = state.activeMonth;
    DOM.monthPicker.addEventListener("change", (e) => {
        if (e.target.value) {
            state.activeMonth = e.target.value;
            loadDashboard();
        }
    });

    DOM.currentMonthBtn.addEventListener("click", () => {
        state.activeMonth = getCurrentMonth();
        DOM.monthPicker.value = state.activeMonth;
        loadDashboard();
    });

    // Filter Buttons
    [DOM.filterAll, DOM.filterDaily, DOM.filterFaltu].forEach((btn) => {
        btn.addEventListener("click", () => {
            [DOM.filterAll, DOM.filterDaily, DOM.filterFaltu].forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.expenseFilter = btn.dataset.type;
            api.getExpenses(state.activeMonth, state.expenseFilter)
                .then(renderExpensesTable)
                .catch(err => showToast(err.message, "error"));
        });
    });

    // Income Modal triggers
    DOM.openAddIncomeBtn.addEventListener("click", openAddIncomeModal);
    DOM.closeIncomeModalBtn.addEventListener("click", closeIncomeModal);
    DOM.cancelIncomeBtn.addEventListener("click", closeIncomeModal);
    DOM.incomeForm.addEventListener("submit", handleIncomeFormSubmit);

    // Expense Modal triggers
    DOM.openAddExpenseBtn.addEventListener("click", openAddExpenseModal);
    DOM.closeExpenseModalBtn.addEventListener("click", closeExpenseModal);
    DOM.cancelExpenseBtn.addEventListener("click", closeExpenseModal);
    DOM.expenseForm.addEventListener("submit", handleExpenseFormSubmit);

    // Close modals on clicking outside dialog
    [DOM.incomeModal, DOM.expenseModal].forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.classList.remove("open");
            }
        });
    });

    // Close modals on Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeIncomeModal();
            closeExpenseModal();
        }
    });
}

// ========================================================
// 8. Bootstrapping
// ========================================================
document.addEventListener("DOMContentLoaded", () => {
    initEventListeners();
    initPhase2EventListeners();
    initPresetEventListeners();
    initWishlistEventListeners();
    initUdharEventListeners();
    initInsightsEventListeners();
    loadCurrentUser();
    loadDashboard();
    loadUdhar();
    loadInsights(state.activeMonth);
});

async function loadCurrentUser() {
    try {
        const res = await fetch("/api/v1/auth/me");
        if (res.ok) {
            const json = await res.json();
            if (json.success && json.data) {
                const el = document.getElementById("currentUserName");
                if (el) el.textContent = json.data.username;
            }
        }
    } catch (_) {}
}

// ========================================================
// 9. Phase 2 - Faltu Limit Card Renderer
// ========================================================

/**
 * Renders the Faltu Limit progress card from the dashboard summary.
 * Shows an empty state when faltu_status is 'none' (no limit set).
 * Colors the bar: green < 80%, orange 80-99%, red >= 100%.
 */
function renderFaltuLimitCard(summary) {
    if (!summary || summary.faltu_status === "none") {
        DOM.faltuLimitEmpty.style.display = "block";
        DOM.faltuLimitData.style.display  = "none";
        return;
    }

    DOM.faltuLimitEmpty.style.display = "none";
    DOM.faltuLimitData.style.display  = "block";

    const used    = summary.total_faltu_inr;
    const limit   = summary.faltu_limit_inr;
    const pct     = Math.min(100, Math.max(0, summary.faltu_used_percent_of_limit));
    const status  = summary.faltu_status;  // 'normal' | 'warning' | 'critical'

    DOM.faltuLimitUsed.textContent = formatINR(used);
    DOM.faltuLimitMax.textContent  = formatINR(limit);

    // Update progress bar width and colour class
    DOM.faltuLimitBar.style.width = `${pct}%`;
    DOM.faltuLimitBar.className = "progress-bar-fill";
    if (status === "critical") DOM.faltuLimitBar.classList.add("critical");
    else if (status === "warning") DOM.faltuLimitBar.classList.add("warn");

    // Message text and colour class
    DOM.faltuLimitMessage.className = "progress-card-message";
    if (status === "critical") {
        DOM.faltuLimitMessage.textContent = `⚠️ Limit exceeded! You have used ${summary.faltu_used_percent_of_limit.toFixed(1)}% of your faltu limit.`;
        DOM.faltuLimitMessage.classList.add("msg-critical");
    } else if (status === "warning") {
        DOM.faltuLimitMessage.textContent = `You have used ${summary.faltu_used_percent_of_limit.toFixed(1)}% of your faltu limit — getting close!`;
        DOM.faltuLimitMessage.classList.add("msg-warn");
    } else {
        DOM.faltuLimitMessage.textContent = `You have used ${summary.faltu_used_percent_of_limit.toFixed(1)}% of your faltu limit.`;
    }
}

// ========================================================
// 10. Phase 2 - Savings Goal Card Renderer
// ========================================================

/**
 * Renders the Savings Goal progress card from the dashboard summary.
 * Shows an empty state when savings_status is 'none' (no goal set).
 * Bar progresses from 0 to 100%; turns green when goal is achieved.
 */
function renderSavingsGoalCard(summary) {
    if (!summary || summary.savings_status === "none") {
        DOM.savingsGoalEmpty.style.display = "block";
        DOM.savingsGoalData.style.display  = "none";
        DOM.savingsGoalLabel.textContent   = "Savings Goal";
        return;
    }

    DOM.savingsGoalEmpty.style.display = "none";
    DOM.savingsGoalData.style.display  = "block";

    const balance = summary.balance_inr;
    const target  = summary.savings_goal_inr;
    const pct     = summary.savings_progress_percent;  // already capped 0-100
    const status  = summary.savings_status;            // 'deficit'|'not_started'|'in_progress'|'achieved'
    const title   = summary.savings_goal_title || "Savings Goal";

    DOM.savingsGoalLabel.textContent   = title;
    DOM.savingsGoalBalance.textContent = formatINR(Math.max(0, balance));
    DOM.savingsGoalTarget.textContent  = formatINR(target);

    DOM.savingsGoalBar.style.width = `${pct}%`;
    DOM.savingsGoalBar.className = "progress-bar-fill";
    if (status === "achieved") DOM.savingsGoalBar.classList.add("achieved");

    DOM.savingsGoalMessage.className = "progress-card-message";
    if (status === "achieved") {
        DOM.savingsGoalMessage.textContent = `🎉 Goal achieved! You saved ${formatINR(balance)} this month.`;
        DOM.savingsGoalMessage.classList.add("msg-achieved");
    } else if (status === "deficit") {
        DOM.savingsGoalMessage.textContent = `Balance is negative this month — spending exceeds income.`;
        DOM.savingsGoalMessage.classList.add("msg-critical");
    } else if (status === "not_started") {
        DOM.savingsGoalMessage.textContent = `No savings yet this month.`;
    } else {
        DOM.savingsGoalMessage.textContent = `${pct.toFixed(1)}% of your savings goal achieved.`;
    }
}

// ========================================================
// 11. Phase 2 - Faltu Limit Modal
// ========================================================
function openLimitModal() {
    DOM.limitAmount.value = "";
    // Pre-fill current limit if available
    const bar = DOM.faltuLimitBar;
    // We read from the DOM amount spans
    DOM.limitModal.classList.add("open");
    DOM.limitAmount.focus();
}

function closeLimitModal() {
    DOM.limitModal.classList.remove("open");
}

async function handleLimitFormSubmit(e) {
    e.preventDefault();
    const raw = DOM.limitAmount.value.trim();
    const amount = parseFloat(raw);
    if (raw === "" || isNaN(amount) || amount < 0) {
        showToast("Please enter a valid limit (0 or more)", "error");
        DOM.limitAmount.focus();
        return;
    }
    DOM.saveLimitBtn.disabled = true;
    try {
        await api.setBudget(state.activeMonth, { faltu_limit_inr: amount });
        showToast("Faltu spending limit saved!", "success");
        closeLimitModal();
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.saveLimitBtn.disabled = false;
    }
}

// ========================================================
// 12. Phase 2 - Savings Goal Modal
// ========================================================
function openGoalModal() {
    DOM.goalTitle.value  = "";
    DOM.goalTarget.value = "";
    DOM.goalModal.classList.add("open");
    DOM.goalTarget.focus();
}

function closeGoalModal() {
    DOM.goalModal.classList.remove("open");
}

async function handleGoalFormSubmit(e) {
    e.preventDefault();
    const target = parseFloat(DOM.goalTarget.value);
    if (!target || target <= 0) {
        showToast("Please enter a target amount greater than ₹0", "error");
        DOM.goalTarget.focus();
        return;
    }
    const title = DOM.goalTitle.value.trim();
    DOM.saveGoalBtn.disabled = true;
    try {
        await api.setGoal(state.activeMonth, { target_inr: target, title: title });
        showToast("Savings goal saved!", "success");
        closeGoalModal();
        await loadDashboard();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.saveGoalBtn.disabled = false;
    }
}

// ========================================================
// 13. Phase 2 - Event Listeners
// ========================================================
function initPhase2EventListeners() {
    DOM.openSetLimitBtn.addEventListener("click", openLimitModal);
    DOM.closeLimitModalBtn.addEventListener("click", closeLimitModal);
    DOM.cancelLimitBtn.addEventListener("click", closeLimitModal);
    DOM.limitForm.addEventListener("submit", handleLimitFormSubmit);

    DOM.openSetGoalBtn.addEventListener("click", openGoalModal);
    DOM.closeGoalModalBtn.addEventListener("click", closeGoalModal);
    DOM.cancelGoalBtn.addEventListener("click", closeGoalModal);
    DOM.goalForm.addEventListener("submit", handleGoalFormSubmit);

    // Close Phase 2 modals on backdrop click or Escape
    [DOM.limitModal, DOM.goalModal].forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("open");
        });
    });
}

// ========================================================
// 14. Charts Renderers (Chart.js)
// ========================================================

/**
 * Renders or updates the Doughnut chart of Daily vs Faltu for the active month.
 * Shows friendly empty state if there is zero spending.
 */
function renderDoughnutChart(summary) {
    if (DOM.doughnutMonthLabel) {
        DOM.doughnutMonthLabel.textContent = formatMonthDisplay(state.activeMonth);
    }

    const daily = summary ? (summary.total_daily_inr || 0) : 0;
    const faltu = summary ? (summary.total_faltu_inr || 0) : 0;
    const total = daily + faltu;

    if (total <= 0) {
        if (doughnutChartInstance) {
            doughnutChartInstance.destroy();
            doughnutChartInstance = null;
        }
        DOM.doughnutCanvasWrapper.style.display = "none";
        DOM.doughnutEmptyState.style.display = "flex";
        return;
    }

    DOM.doughnutEmptyState.style.display = "none";
    DOM.doughnutCanvasWrapper.style.display = "block";

    if (typeof Chart === "undefined") {
        return;
    }

    if (doughnutChartInstance) {
        doughnutChartInstance.data.datasets[0].data = [daily, faltu];
        doughnutChartInstance.update();
        return;
    }

    const ctx = DOM.expenseDoughnutChart.getContext("2d");
    doughnutChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Daily Essentials", "Faltu Spending"],
            datasets: [{
                data: [daily, faltu],
                backgroundColor: ["#2563eb", "#dc2626"],
                hoverBackgroundColor: ["#1d4ed8", "#b91c1c"],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        boxWidth: 12,
                        padding: 16,
                        font: { family: "Plus Jakarta Sans", size: 12, weight: "600" }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ₹${Number(context.raw).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    }
                }
            },
            cutout: "68%"
        }
    });
}

/**
 * Renders or updates the 6-Month Income vs Expenses Bar Chart.
 * Shows friendly empty state if all months have zero transactions.
 */
function renderHistoryChart(history) {
    const hasAnyData = Array.isArray(history) && history.some(item => (item.income_inr > 0 || item.total_expense_inr > 0));

    if (!hasAnyData) {
        if (historyChartInstance) {
            historyChartInstance.destroy();
            historyChartInstance = null;
        }
        DOM.historyCanvasWrapper.style.display = "none";
        DOM.historyEmptyState.style.display = "flex";
        return;
    }

    DOM.historyEmptyState.style.display = "none";
    DOM.historyCanvasWrapper.style.display = "block";

    if (typeof Chart === "undefined") {
        return;
    }

    const labels = history.map(item => formatMonthShort(item.month));
    const incomeData = history.map(item => item.income_inr);
    const expenseData = history.map(item => item.total_expense_inr);

    if (historyChartInstance) {
        historyChartInstance.data.labels = labels;
        historyChartInstance.data.datasets[0].data = incomeData;
        historyChartInstance.data.datasets[1].data = expenseData;
        historyChartInstance.update();
        return;
    }

    const ctx = DOM.historyBarChart.getContext("2d");
    historyChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Income",
                    data: incomeData,
                    backgroundColor: "#059669",
                    borderRadius: 4
                },
                {
                    label: "Expenses",
                    data: expenseData,
                    backgroundColor: "#dc2626",
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => `₹${Number(value).toLocaleString("en-IN")}`
                    },
                    grid: { color: "#f1f5f9" }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        boxWidth: 12,
                        padding: 16,
                        font: { family: "Plus Jakarta Sans", size: 12, weight: "600" }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.dataset.label}: ₹${Number(context.raw).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    }
                }
            }
        }
    });
}

// ========================================================
// 15. Quick Presets Renderers & Action Handlers
// ========================================================

/**
 * Renders the row of Quick Add preset buttons above the expenses table.
 */
function renderQuickAddBar(presets) {
    if (!DOM.quickAddButtonsRow) return;

    // Clear existing buttons safely
    while (DOM.quickAddButtonsRow.firstChild) {
        DOM.quickAddButtonsRow.removeChild(DOM.quickAddButtonsRow.firstChild);
    }

    if (!Array.isArray(presets) || presets.length === 0) {
        DOM.quickAddButtonsRow.style.display = "none";
        DOM.quickAddEmpty.style.display = "flex";
        return;
    }

    DOM.quickAddEmpty.style.display = "none";
    DOM.quickAddButtonsRow.style.display = "flex";

    presets.forEach((preset) => {
        const btn = createSafeElement("button", {
            className: `quick-preset-btn btn-${preset.type}`,
            attrs: {
                type: "button",
                title: `Quick-add ${preset.title} (₹${preset.amount_inr.toFixed(2)})`
            }
        },
            createSafeElement("span", { className: "preset-icon", text: preset.icon || "⚡" }),
            createSafeElement("span", { className: "preset-title", text: preset.title }),
            createSafeElement("span", { className: "preset-amount", text: `₹${preset.amount_inr.toFixed(2)}` })
        );

        // One-tap add with double-click prevention
        btn.addEventListener("click", async () => {
            if (btn.disabled) return;
            btn.disabled = true;
            try {
                const expense = await api.usePreset(preset.id);
                showToast(`⚡ Added ${expense.type.toUpperCase()}: ${preset.title} (₹${expense.amount_inr.toFixed(2)})`, "success");
                await loadDashboard();
            } catch (err) {
                showToast(err.message || "Failed to use preset", "error");
            } finally {
                setTimeout(() => { btn.disabled = false; }, 500);
            }
        });

        DOM.quickAddButtonsRow.appendChild(btn);
    });
}

/**
 * Renders the configured presets inside the management modal.
 */
function renderPresetsManagementList(presets) {
    if (!DOM.presetsListContainer) return;

    while (DOM.presetsListContainer.firstChild) {
        DOM.presetsListContainer.removeChild(DOM.presetsListContainer.firstChild);
    }

    const count = Array.isArray(presets) ? presets.length : 0;
    if (DOM.presetCountBadge) {
        DOM.presetCountBadge.textContent = `${count} / 12`;
    }

    if (count === 0) {
        const emptyMsg = createSafeElement("p", {
            style: "font-size: 0.82rem; color: var(--text-muted); font-style: italic; margin: 0.25rem 0;",
            text: "No presets added yet. Create your first preset above."
        });
        DOM.presetsListContainer.appendChild(emptyMsg);
        return;
    }

    presets.forEach((preset) => {
        const item = createSafeElement("div", { className: "preset-management-item" });

        const info = createSafeElement("div", { className: "preset-item-info" },
            createSafeElement("span", { text: preset.icon || "⚡" }),
            createSafeElement("span", { text: preset.title }),
            createSafeElement("span", {
                className: `badge badge-${preset.type}`,
                style: "font-size:0.7rem; padding: 0.15rem 0.45rem;",
                text: preset.type
            }),
            createSafeElement("span", {
                style: "color: var(--text-muted); font-size: 0.8rem;",
                text: `₹${preset.amount_inr.toFixed(2)}`
            })
        );

        const editBtn = createSafeElement("button", {
            className: "btn btn-secondary btn-xs",
            attrs: { type: "button", title: "Edit Preset" },
            text: "Edit",
            events: {
                click: () => startEditPreset(preset)
            }
        });

        const deleteBtn = createSafeElement("button", {
            className: "btn btn-danger btn-xs",
            attrs: { type: "button", title: "Delete Preset" },
            text: "Delete",
            events: {
                click: async () => {
                    if (confirm(`Delete preset "${preset.title}"?`)) {
                        try {
                            await api.deletePreset(preset.id);
                            showToast(`Preset '${preset.title}' deleted`, "info");
                            const refreshed = await api.getPresets();
                            renderPresetsManagementList(refreshed);
                            renderQuickAddBar(refreshed);
                        } catch (err) {
                            showToast(err.message, "error");
                        }
                    }
                }
            }
        });

        const actions = createSafeElement("div", { className: "preset-item-actions" }, editBtn, deleteBtn);

        item.appendChild(info);
        item.appendChild(actions);
        DOM.presetsListContainer.appendChild(item);
    });
}

function startEditPreset(preset) {
    DOM.presetId.value = preset.id;
    DOM.presetTitle.value = preset.title;
    DOM.presetAmount.value = preset.amount_inr;
    if (preset.type === "daily") {
        DOM.presetRadioDaily.checked = true;
    } else {
        DOM.presetRadioFaltu.checked = true;
    }
    DOM.presetCategory.value = preset.sub_category || "";
    DOM.presetIcon.value = preset.icon || "⚡";

    DOM.presetFormSubtitle.textContent = `Edit Preset: ${preset.title}`;
    DOM.savePresetBtn.textContent = "Update Preset";
    DOM.cancelPresetEditBtn.style.display = "inline-block";
    DOM.presetTitle.focus();
}

function resetPresetForm() {
    DOM.presetForm.reset();
    DOM.presetId.value = "";
    DOM.presetRadioFaltu.checked = true;
    DOM.presetIcon.value = "⚡";
    DOM.presetFormSubtitle.textContent = "Add New Preset";
    DOM.savePresetBtn.textContent = "Save Preset";
    DOM.cancelPresetEditBtn.style.display = "none";
}

async function openManagePresetsModal() {
    resetPresetForm();
    DOM.presetModal.classList.add("open");
    try {
        const presets = await api.getPresets();
        renderPresetsManagementList(presets);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function closeManagePresetsModal() {
    DOM.presetModal.classList.remove("open");
    resetPresetForm();
}

async function handlePresetFormSubmit(e) {
    e.preventDefault();
    const title = DOM.presetTitle.value.trim();
    if (!title) {
        showToast("Title is required", "error");
        DOM.presetTitle.focus();
        return;
    }
    if (title.length > 30) {
        showToast("Title cannot exceed 30 characters", "error");
        return;
    }

    const amount = parseFloat(DOM.presetAmount.value);
    if (!amount || amount <= 0) {
        showToast("Amount must be greater than ₹0", "error");
        DOM.presetAmount.focus();
        return;
    }

    const type = DOM.presetRadioDaily.checked ? "daily" : "faltu";
    const sub_category = DOM.presetCategory.value.trim() || title;
    const icon = DOM.presetIcon.value.trim() || "⚡";

    const payload = {
        title,
        amount_inr: amount,
        type,
        sub_category,
        icon
    };

    const presetId = DOM.presetId.value;
    DOM.savePresetBtn.disabled = true;

    try {
        if (presetId) {
            await api.updatePreset(presetId, payload);
            showToast("Preset updated successfully", "success");
        } else {
            await api.createPreset(payload);
            showToast("New preset created", "success");
        }
        resetPresetForm();
        const refreshed = await api.getPresets();
        renderPresetsManagementList(refreshed);
        renderQuickAddBar(refreshed);
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.savePresetBtn.disabled = false;
    }
}

async function handleAddSuggestedPresets() {
    DOM.addSuggestedPresetsBtn.disabled = true;
    try {
        const suggested = [
            { title: "Chai", amount_inr: 15, type: "faltu", icon: "☕", sub_category: "Chai & Snacks" },
            { title: "Auto", amount_inr: 30, type: "daily", icon: "🛺", sub_category: "Travel & Metro" },
            { title: "Snacks", amount_inr: 20, type: "faltu", icon: "🍟", sub_category: "Chai & Snacks" }
        ];

        for (const item of suggested) {
            await api.createPreset(item);
        }

        showToast("Suggested presets added successfully!", "success");
        const refreshed = await api.getPresets();
        renderQuickAddBar(refreshed);
    } catch (err) {
        showToast(err.message || "Failed to add suggested presets", "error");
    } finally {
        DOM.addSuggestedPresetsBtn.disabled = false;
    }
}

function initPresetEventListeners() {
    DOM.openManagePresetsBtn.addEventListener("click", openManagePresetsModal);
    DOM.closePresetModalBtn.addEventListener("click", closeManagePresetsModal);
    DOM.closePresetDialogBtn.addEventListener("click", closeManagePresetsModal);
    DOM.addSuggestedPresetsBtn.addEventListener("click", handleAddSuggestedPresets);
    DOM.cancelPresetEditBtn.addEventListener("click", resetPresetForm);
    DOM.presetForm.addEventListener("submit", handlePresetFormSubmit);

    DOM.presetModal.addEventListener("click", (e) => {
        if (e.target === DOM.presetModal) closeManagePresetsModal();
    });
}

// ========================================================
// 16. Wishlist (24-Hour Wait Rule) Renderers & Logic
// ========================================================

function formatCountdown(seconds) {
    if (seconds <= 0) return "0s";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

/**
 * Refreshes only the wishlist section and its summary badge.
 */
async function loadWishlistOnly() {
    try {
        const [items, summary] = await Promise.all([
            api.getWishlist("waiting"),
            api.getWishlistSummary()
        ]);
        renderWishlist(items, summary);
        loadInsights(state.activeMonth);
    } catch (err) {
        showToast(err.message, "error");
    }
}

/**
 * Renders the wishlist cards and sets up the live 1-second countdown clock.
 */
function renderWishlist(items, summary) {
    if (DOM.wishlistMoneySavedBadge && summary) {
        DOM.wishlistMoneySavedBadge.textContent = `Money saved by waiting: ${formatINR(summary.amount_saved_inr)}`;
    }

    if (wishlistTimer) {
        clearInterval(wishlistTimer);
        wishlistTimer = null;
    }

    currentWishlistItems = Array.isArray(items) ? items : [];

    if (!DOM.wishlistItemsContainer) return;

    while (DOM.wishlistItemsContainer.firstChild) {
        DOM.wishlistItemsContainer.removeChild(DOM.wishlistItemsContainer.firstChild);
    }

    if (currentWishlistItems.length === 0) {
        DOM.wishlistItemsContainer.style.display = "none";
        DOM.wishlistEmptyState.style.display = "flex";
        return;
    }

    DOM.wishlistEmptyState.style.display = "none";
    DOM.wishlistItemsContainer.style.display = "grid";

    currentWishlistItems.forEach((item) => {
        const card = createSafeElement("div", {
            className: `wishlist-card ${item.is_unlocked ? "unlocked" : ""}`,
            attrs: { "data-wishlist-id": item.id }
        });

        // Header: item name + estimated price
        const header = createSafeElement("div", { className: "wishlist-card-header" },
            createSafeElement("div", {},
                createSafeElement("h3", { className: "wishlist-card-title", text: item.item_name }),
                createSafeElement("span", {
                    className: "badge badge-daily",
                    style: "font-size:0.7rem; margin-top:0.25rem;",
                    text: item.sub_category || "Shopping"
                })
            ),
            createSafeElement("span", { className: "wishlist-card-amount", text: formatINR(item.estimated_amount_inr) })
        );

        card.appendChild(header);

        // Body: Status / Countdown or Prompt
        if (item.is_unlocked) {
            // Unlocked State: "Do you still want this?"
            const unlockedBox = createSafeElement("div", { className: "wishlist-unlocked-box" },
                createSafeElement("div", { text: "🎉 24 Hours Passed!" }),
                createSafeElement("div", { style: "font-size:0.8rem; font-weight:600; margin-top:0.2rem;", text: "Do you still want this?" })
            );
            card.appendChild(unlockedBox);

            const buyBtn = createSafeElement("button", {
                className: "btn btn-success btn-sm",
                attrs: { type: "button" },
                text: "Yes, buy",
                events: {
                    click: async () => {
                        if (confirm(`Buy "${item.item_name}" for ${formatINR(item.estimated_amount_inr)} and log as faltu expense?`)) {
                            try {
                                await api.buyWishlist(item.id);
                                showToast(`Bought "${item.item_name}"! Logged as expense.`, "success");
                                await loadDashboard();
                            } catch (err) {
                                showToast(err.message, "error");
                            }
                        }
                    }
                }
            });

            const dropBtn = createSafeElement("button", {
                className: "btn btn-secondary btn-sm",
                attrs: { type: "button" },
                text: "No, drop it",
                events: {
                    click: async () => {
                        try {
                            await api.dropWishlist(item.id);
                            showToast(`Dropped "${item.item_name}". Good decision!`, "info");
                            await loadWishlistOnly();
                        } catch (err) {
                            showToast(err.message, "error");
                        }
                    }
                }
            });

            const actions = createSafeElement("div", { className: "wishlist-card-actions" }, dropBtn, buyBtn);
            card.appendChild(actions);

        } else {
            // Locked State: Live countdown + Disabled Buy + Drop button
            const unlockDate = new Date(item.unlock_at);
            const localUnlockStr = isNaN(unlockDate.getTime()) ? "" : unlockDate.toLocaleString("en-IN", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });

            const timeSpan = createSafeElement("span", {
                className: "wishlist-countdown-time",
                text: formatCountdown(item.seconds_remaining)
            });

            const countdownBox = createSafeElement("div", { className: "wishlist-countdown-box" },
                createSafeElement("div", {},
                    createSafeElement("span", { text: "⏳ Unlocks in: " }),
                    timeSpan
                ),
                createSafeElement("div", { className: "wishlist-local-time", text: `(at ${localUnlockStr})` })
            );
            card.appendChild(countdownBox);

            const lockedBuyBtn = createSafeElement("button", {
                className: "btn btn-secondary btn-sm",
                attrs: { type: "button", disabled: "true", title: "Wait 24 hours before buying" },
                text: "Buy (Locked)"
            });

            const dropEarlyBtn = createSafeElement("button", {
                className: "btn btn-secondary btn-sm",
                attrs: { type: "button", title: "Drop item now and save money" },
                text: "Drop",
                events: {
                    click: async () => {
                        if (confirm(`Drop "${item.item_name}" from wishlist?`)) {
                            try {
                                await api.dropWishlist(item.id);
                                showToast(`Dropped "${item.item_name}". Money saved!`, "info");
                                await loadWishlistOnly();
                            } catch (err) {
                                showToast(err.message, "error");
                            }
                        }
                    }
                }
            });

            const actions = createSafeElement("div", { className: "wishlist-card-actions" }, dropEarlyBtn, lockedBuyBtn);
            card.appendChild(actions);
        }

        DOM.wishlistItemsContainer.appendChild(card);
    });

    // Start live 1-second countdown ticker for waiting locked items
    const hasLockedItems = currentWishlistItems.some(i => !i.is_unlocked && i.seconds_remaining > 0);
    if (hasLockedItems) {
        wishlistTimer = setInterval(() => {
            let anyUnlockedNow = false;
            currentWishlistItems.forEach((item) => {
                if (!item.is_unlocked && item.seconds_remaining > 0) {
                    item.seconds_remaining -= 1;
                    if (item.seconds_remaining <= 0) {
                        item.is_unlocked = true;
                        anyUnlockedNow = true;
                    } else {
                        const card = DOM.wishlistItemsContainer.querySelector(`[data-wishlist-id="${item.id}"]`);
                        if (card) {
                            const timeSpan = card.querySelector(".wishlist-countdown-time");
                            if (timeSpan) {
                                timeSpan.textContent = formatCountdown(item.seconds_remaining);
                            }
                        }
                    }
                }
            });
            if (anyUnlockedNow) {
                renderWishlist(currentWishlistItems);
            }
        }, 1000);
    }
}

async function handleAddWishlistSubmit(e) {
    e.preventDefault();
    const name = DOM.wishlistItemName.value.trim();
    if (!name) {
        showToast("Item name is required", "error");
        DOM.wishlistItemName.focus();
        return;
    }
    if (name.length > 60) {
        showToast("Item name cannot exceed 60 characters", "error");
        return;
    }

    const amount = parseFloat(DOM.wishlistAmount.value);
    if (!amount || amount <= 0) {
        showToast("Price must be greater than ₹0", "error");
        DOM.wishlistAmount.focus();
        return;
    }

    const sub_category = DOM.wishlistCategory.value.trim() || "Shopping";

    DOM.saveWishlistBtn.disabled = true;
    try {
        await api.createWishlist({
            item_name: name,
            estimated_amount_inr: amount,
            sub_category: sub_category
        });
        showToast(`Added "${name}" to 24-hour wait wishlist!`, "success");
        DOM.addWishlistForm.reset();
        await loadWishlistOnly();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        DOM.saveWishlistBtn.disabled = false;
    }
}

function initWishlistEventListeners() {
    if (DOM.addWishlistForm) {
        DOM.addWishlistForm.addEventListener("submit", handleAddWishlistSubmit);
    }
}



