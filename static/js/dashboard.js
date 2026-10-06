/**
 * SAVEWISE - Main Dashboard Controller
 * Connects UI events to API, manages state, renders tables and cards safely.
 * Security: Uses textContent and safe DOM creation; ZERO innerHTML for API data.
 */

import { api } from "./api.js";
import { formatINR, getCurrentMonth, getCurrentDate, formatDateDisplay, createSafeElement, showToast } from "./utils.js";

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
    saveExpenseBtn: document.getElementById("saveExpenseBtn")
};

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
        const [summary, incomes, expenses] = await Promise.all([
            api.getDashboardSummary(state.activeMonth),
            api.getIncomes(state.activeMonth),
            api.getExpenses(state.activeMonth, state.expenseFilter)
        ]);

        renderSummaryCards(summary);
        renderIncomesTable(incomes);
        renderExpensesTable(expenses);
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
    loadDashboard();
});
