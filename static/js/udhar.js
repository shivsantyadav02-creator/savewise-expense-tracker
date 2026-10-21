/**
 * SAVEWISE - Udhar (Money Lent / Borrowed) Section
 * Security: Zero innerHTML with API data. Uses createSafeElement + textContent throughout.
 */

import { api } from "./api.js";
import { formatINR, formatDateDisplay, createSafeElement, showToast, getCurrentDate } from "./utils.js";

// ────────────────────────────────────────────────────────────────────────────
// DOM Cache
// ────────────────────────────────────────────────────────────────────────────
const UDOM = {
    // Summary badges
    summaryReceive:   () => document.getElementById("udharReceiveBadge"),
    summaryPay:       () => document.getElementById("udharPayBadge"),
    overdueCount:     () => document.getElementById("udharOverdueCount"),

    // Add form
    addForm:          () => document.getElementById("addUdharForm"),
    personName:       () => document.getElementById("udharPersonName"),
    amount:           () => document.getElementById("udharAmount"),
    typeToggleLent:   () => document.getElementById("udharTypeLent"),
    typeToggleBorrow: () => document.getElementById("udharTypeBorrowed"),
    dueDate:          () => document.getElementById("udharDueDate"),
    note:             () => document.getElementById("udharNote"),
    submitBtn:        () => document.getElementById("udharSubmitBtn"),

    // Pending list
    pendingContainer: () => document.getElementById("udharPendingList"),
    emptyState:       () => document.getElementById("udharEmptyState"),

    // Settled toggle
    toggleSettledBtn: () => document.getElementById("udharToggleSettledBtn"),
    settledContainer: () => document.getElementById("udharSettledList"),
    settledSection:   () => document.getElementById("udharSettledSection"),

    // Edit modal
    editModal:        () => document.getElementById("udharEditModal"),
    editForm:         () => document.getElementById("udharEditForm"),
    editId:           () => document.getElementById("udharEditId"),
    editPersonName:   () => document.getElementById("udharEditPersonName"),
    editAmount:       () => document.getElementById("udharEditAmount"),
    editDueDate:      () => document.getElementById("udharEditDueDate"),
    editNote:         () => document.getElementById("udharEditNote"),
    closeEditModal:   () => document.getElementById("closeUdharEditModal"),
    cancelEditBtn:    () => document.getElementById("cancelUdharEditBtn"),
    saveEditBtn:      () => document.getElementById("saveUdharEditBtn"),
};

let _settledVisible = false;

// ────────────────────────────────────────────────────────────────────────────
// Render helpers
// ────────────────────────────────────────────────────────────────────────────

function renderSummary(summary) {
    const receive = UDOM.summaryReceive();
    const pay = UDOM.summaryPay();
    const overdue = UDOM.overdueCount();

    if (receive) receive.textContent = `To Receive: ${formatINR(summary.total_to_receive_inr)}`;
    if (pay)     pay.textContent     = `To Pay: ${formatINR(summary.total_to_pay_inr)}`;
    if (overdue) {
        const cnt = summary.overdue_count;
        overdue.textContent = cnt > 0 ? `${cnt} overdue` : "";
        overdue.style.display = cnt > 0 ? "inline-flex" : "none";
    }
}

function buildUdharCard(item, isSettled = false) {
    const isLent = item.type === "lent";
    const colorClass = isLent ? "udhar-card--lent" : "udhar-card--borrowed";

    const card = createSafeElement("div", {
        className: `udhar-card ${colorClass}${item.is_overdue ? " udhar-card--overdue" : ""}`,
        attrs: { "data-id": item.id }
    });

    // Top row: person name + type label + overdue badge
    const topRow = createSafeElement("div", { className: "udhar-card-top" });

    const nameEl = createSafeElement("span", {
        className: "udhar-person-name",
        text: item.person_name
    });

    const typeLabel = createSafeElement("span", {
        className: `udhar-type-label ${isLent ? "label--lent" : "label--borrowed"}`,
        text: isLent ? "📤 To Receive" : "📥 To Pay"
    });

    topRow.appendChild(nameEl);
    topRow.appendChild(typeLabel);

    if (item.is_overdue) {
        topRow.appendChild(createSafeElement("span", {
            className: "badge-overdue",
            text: "⚠ Overdue"
        }));
    }
    if (isSettled) {
        topRow.appendChild(createSafeElement("span", {
            className: "badge-settled-label",
            text: "✓ Settled"
        }));
    }

    card.appendChild(topRow);

    // Amount row
    const amountEl = createSafeElement("div", {
        className: "udhar-amount",
        text: formatINR(item.amount_inr)
    });
    card.appendChild(amountEl);

    // Meta row: due date, note
    const metaRow = createSafeElement("div", { className: "udhar-meta" });

    if (item.due_date) {
        metaRow.appendChild(createSafeElement("span", {
            className: `udhar-due${item.is_overdue ? " udhar-due--overdue" : ""}`,
            text: `Due: ${formatDateDisplay(item.due_date)}`
        }));
    }
    if (item.note) {
        metaRow.appendChild(createSafeElement("span", {
            className: "udhar-note",
            text: item.note
        }));
    }
    if (metaRow.children.length > 0) card.appendChild(metaRow);

    // Action buttons
    const actions = createSafeElement("div", { className: "udhar-card-actions" });

    if (!isSettled) {
        // Settle button
        const settleBtn = createSafeElement("button", {
            className: "btn btn-success btn-sm",
            text: "✓ Settle",
            attrs: { type: "button", "data-action": "settle", "data-id": String(item.id) }
        });
        settleBtn.addEventListener("click", () => handleSettle(item.id, item.person_name));

        // Edit button
        const editBtn = createSafeElement("button", {
            className: "btn btn-secondary btn-sm",
            text: "✏ Edit",
            attrs: { type: "button" }
        });
        editBtn.addEventListener("click", () => openEditModal(item));

        actions.appendChild(settleBtn);
        actions.appendChild(editBtn);
    } else {
        // Reopen button
        const reopenBtn = createSafeElement("button", {
            className: "btn btn-secondary btn-sm",
            text: "↩ Reopen",
            attrs: { type: "button" }
        });
        reopenBtn.addEventListener("click", () => handleReopen(item.id));
        actions.appendChild(reopenBtn);
    }

    // Delete always visible
    const deleteBtn = createSafeElement("button", {
        className: "btn btn-danger btn-sm",
        text: "🗑 Delete",
        attrs: { type: "button" }
    });
    deleteBtn.addEventListener("click", () => handleDelete(item.id, item.person_name));
    actions.appendChild(deleteBtn);

    card.appendChild(actions);
    return card;
}

function renderPendingList(items) {
    const container = UDOM.pendingContainer();
    const emptyState = UDOM.emptyState();
    if (!container) return;

    container.textContent = "";

    if (!items || items.length === 0) {
        if (emptyState) emptyState.style.display = "flex";
        return;
    }
    if (emptyState) emptyState.style.display = "none";

    // Separate lent / borrowed for grouping
    const lent = items.filter(i => i.type === "lent");
    const borrowed = items.filter(i => i.type === "borrowed");

    if (lent.length > 0) {
        container.appendChild(createSafeElement("h4", {
            className: "udhar-group-label udhar-group-label--lent",
            text: `💚 You lent (${lent.length})`
        }));
        lent.forEach(item => container.appendChild(buildUdharCard(item, false)));
    }

    if (borrowed.length > 0) {
        container.appendChild(createSafeElement("h4", {
            className: "udhar-group-label udhar-group-label--borrowed",
            text: `🔴 You borrowed (${borrowed.length})`
        }));
        borrowed.forEach(item => container.appendChild(buildUdharCard(item, false)));
    }
}

function renderSettledList(items) {
    const container = UDOM.settledContainer();
    if (!container) return;
    container.textContent = "";

    if (!items || items.length === 0) {
        container.appendChild(createSafeElement("p", {
            className: "udhar-settled-empty",
            text: "No settled records yet."
        }));
        return;
    }

    items.forEach(item => container.appendChild(buildUdharCard(item, true)));
}

// ────────────────────────────────────────────────────────────────────────────
// Load data
// ────────────────────────────────────────────────────────────────────────────

export async function loadUdhar() {
    try {
        const [summary, pending] = await Promise.all([
            api.getUdharSummary(),
            api.getUdhar("pending")
        ]);
        renderSummary(summary);
        renderPendingList(pending);

        if (_settledVisible) {
            const settled = await api.getUdhar("settled");
            renderSettledList(settled);
        }
    } catch (err) {
        showToast("Failed to load udhar data: " + err.message, "error");
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Event handlers
// ────────────────────────────────────────────────────────────────────────────

async function handleAddSubmit(e) {
    e.preventDefault();
    const nameEl   = UDOM.personName();
    const amtEl    = UDOM.amount();
    const lentEl   = UDOM.typeToggleLent();
    const dueEl    = UDOM.dueDate();
    const noteEl   = UDOM.note();
    const submitEl = UDOM.submitBtn();

    const name   = nameEl ? nameEl.value.trim() : "";
    const amount = amtEl  ? parseFloat(amtEl.value) : 0;
    const type   = lentEl && lentEl.checked ? "lent" : "borrowed";
    const due    = dueEl && dueEl.value ? dueEl.value : null;
    const note   = noteEl && noteEl.value.trim() ? noteEl.value.trim() : null;

    if (!name) { showToast("Person name is required.", "error"); return; }
    if (!amount || amount <= 0) { showToast("Amount must be greater than zero.", "error"); return; }

    if (submitEl) submitEl.disabled = true;
    try {
        await api.createUdhar({ person_name: name, amount_inr: amount, type, due_date: due, note });
        showToast(`Udhar recorded for ${name}!`, "success");
        const form = UDOM.addForm();
        if (form) form.reset();
        // Reset type toggle to Lent default
        if (lentEl) lentEl.checked = true;
        await loadUdhar();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        if (submitEl) submitEl.disabled = false;
    }
}

async function handleSettle(id, personName) {
    if (!confirm(`Mark udhar with ${personName} as settled?`)) return;
    try {
        await api.settleUdhar(id);
        showToast("Marked as settled!", "success");
        await loadUdhar();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleReopen(id) {
    try {
        await api.reopenUdhar(id);
        showToast("Record reopened.", "success");
        await loadUdhar();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleDelete(id, personName) {
    if (!confirm(`Delete udhar record with ${personName}? This cannot be undone.`)) return;
    try {
        await api.deleteUdhar(id);
        showToast("Record deleted.", "success");
        await loadUdhar();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleToggleSettled() {
    _settledVisible = !_settledVisible;
    const btn = UDOM.toggleSettledBtn();
    const section = UDOM.settledSection();
    if (btn) btn.textContent = _settledVisible ? "Hide Settled" : "Show Settled Records";
    if (section) section.style.display = _settledVisible ? "block" : "none";

    if (_settledVisible) {
        try {
            const settled = await api.getUdhar("settled");
            renderSettledList(settled);
        } catch (err) {
            showToast("Failed to load settled records: " + err.message, "error");
        }
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Edit Modal
// ────────────────────────────────────────────────────────────────────────────

function openEditModal(item) {
    const modal = UDOM.editModal();
    if (!modal) return;

    const idEl   = UDOM.editId();
    const nameEl = UDOM.editPersonName();
    const amtEl  = UDOM.editAmount();
    const dueEl  = UDOM.editDueDate();
    const noteEl = UDOM.editNote();

    if (idEl)   idEl.value   = item.id;
    if (nameEl) nameEl.value = item.person_name;
    if (amtEl)  amtEl.value  = item.amount_inr;
    if (dueEl)  dueEl.value  = item.due_date || "";
    if (noteEl) noteEl.value = item.note || "";

    modal.classList.add("modal-open");
    modal.setAttribute("aria-hidden", "false");
}

function closeEditModal() {
    const modal = UDOM.editModal();
    if (!modal) return;
    modal.classList.remove("modal-open");
    modal.setAttribute("aria-hidden", "true");
    const form = UDOM.editForm();
    if (form) form.reset();
}

async function handleEditSubmit(e) {
    e.preventDefault();
    const idEl   = UDOM.editId();
    const nameEl = UDOM.editPersonName();
    const amtEl  = UDOM.editAmount();
    const dueEl  = UDOM.editDueDate();
    const noteEl = UDOM.editNote();
    const saveEl = UDOM.saveEditBtn();

    const id     = idEl   ? parseInt(idEl.value, 10) : null;
    const name   = nameEl ? nameEl.value.trim() : "";
    const amount = amtEl  ? parseFloat(amtEl.value) : 0;
    const due    = dueEl  ? (dueEl.value || "") : "";
    const note   = noteEl ? noteEl.value.trim() : "";

    if (!id) return;
    if (!name)   { showToast("Person name is required.", "error"); return; }
    if (!amount || amount <= 0) { showToast("Amount must be greater than zero.", "error"); return; }

    if (saveEl) saveEl.disabled = true;
    try {
        await api.updateUdhar(id, {
            person_name: name,
            amount_inr: amount,
            due_date: due,
            note: note || null
        });
        showToast("Udhar record updated.", "success");
        closeEditModal();
        await loadUdhar();
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        if (saveEl) saveEl.disabled = false;
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Init
// ────────────────────────────────────────────────────────────────────────────

export function initUdharEventListeners() {
    const addForm = UDOM.addForm();
    if (addForm) addForm.addEventListener("submit", handleAddSubmit);

    const toggleBtn = UDOM.toggleSettledBtn();
    if (toggleBtn) toggleBtn.addEventListener("click", handleToggleSettled);

    const closeBtn = UDOM.closeEditModal();
    if (closeBtn) closeBtn.addEventListener("click", closeEditModal);

    const cancelBtn = UDOM.cancelEditBtn();
    if (cancelBtn) cancelBtn.addEventListener("click", closeEditModal);

    const editForm = UDOM.editForm();
    if (editForm) editForm.addEventListener("submit", handleEditSubmit);

    // Close modal on backdrop click
    const modal = UDOM.editModal();
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeEditModal();
        });
    }
}
