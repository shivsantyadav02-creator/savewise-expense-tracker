/**
 * SAVEWISE - Phase 3 Insights Controller
 * - Simulator
 * - Balance Prediction
 * - Smart Insights Summary
 * - Weekly Report
 *
 * Security: ZERO innerHTML with API data. Uses createSafeElement & textContent throughout.
 * All financial math is computed on the backend.
 */

import { api } from "./api.js";
import { formatINR, formatDateDisplay, createSafeElement, showToast } from "./utils.js";

const IDOM = {
    // Simulator
    simulatorReturnInput: () => document.getElementById("simulatorReturnInput"),
    simulatorFaltuAmount: () => document.getElementById("simulatorFaltuAmount"),
    simulatorResultsGrid: () => document.getElementById("simulatorResultsGrid"),
    simulatorEmptyState: () => document.getElementById("simulatorEmptyState"),
    simulatorDisclaimer: () => document.getElementById("simulatorDisclaimer"),

    // Prediction
    predictionSection: () => document.getElementById("insightsPredictionCard"),
    predictionStatusBadge: () => document.getElementById("predictionStatusBadge"),
    predictionConfidenceBadge: () => document.getElementById("predictionConfidenceBadge"),
    predictionProjectedBalance: () => document.getElementById("predictionProjectedBalance"),
    predictionSafeBudget: () => document.getElementById("predictionSafeBudget"),
    predictionDaysInfo: () => document.getElementById("predictionDaysInfo"),
    predictionWarningBanner: () => document.getElementById("predictionWarningBanner"),
    predictionWarningText: () => document.getElementById("predictionWarningText"),
    predictionDetails: () => document.getElementById("predictionDetails"),
    predictionEmptyState: () => document.getElementById("predictionEmptyState"),
    predictionEmptyText: () => document.getElementById("predictionEmptyText"),

    // Smart Insights
    insightsCountBadge: () => document.getElementById("insightsCountBadge"),
    insightsSummaryList: () => document.getElementById("insightsSummaryList"),
    insightsSummaryEmpty: () => document.getElementById("insightsSummaryEmpty"),

    // Weekly Report
    weeklyReportRange: () => document.getElementById("weeklyReportRange"),
    weeklySpendBadge: () => document.getElementById("weeklySpendBadge"),
    weeklyReportBody: () => document.getElementById("weeklyReportBody"),
    weeklyDailySpend: () => document.getElementById("weeklyDailySpend"),
    weeklyFaltuSpend: () => document.getElementById("weeklyFaltuSpend"),
    weeklyNoSpendDays: () => document.getElementById("weeklyNoSpendDays"),
    weeklyPrevComparison: () => document.getElementById("weeklyPrevComparison"),
    weeklyHighestDayBar: () => document.getElementById("weeklyHighestDayBar"),
    weeklyHighestDayText: () => document.getElementById("weeklyHighestDayText"),
    weeklyTopCatList: () => document.getElementById("weeklyTopCatList"),
    weeklyReportEmpty: () => document.getElementById("weeklyReportEmpty"),
};

let _currentMonth = "";

// ────────────────────────────────────────────────────────────────────────────
// Simulator Rendering
// ────────────────────────────────────────────────────────────────────────────

function renderSimulator(data) {
    const faltuEl = IDOM.simulatorFaltuAmount();
    const gridEl = IDOM.simulatorResultsGrid();
    const emptyEl = IDOM.simulatorEmptyState();
    const disclaimerEl = IDOM.simulatorDisclaimer();

    if (!data || !data.has_faltu) {
        if (faltuEl) faltuEl.textContent = "₹0.00 / month";
        if (gridEl) {
            gridEl.textContent = "";
            gridEl.style.display = "none";
        }
        if (emptyEl) {
            emptyEl.style.display = "flex";
            const desc = emptyEl.querySelector(".empty-desc");
            if (desc) {
                desc.textContent = "No faltu spending recorded for this month. You didn't waste anything to simulate!";
            }
        }
        if (disclaimerEl) disclaimerEl.style.display = "none";
        return;
    }

    if (emptyEl) emptyEl.style.display = "none";
    if (faltuEl) faltuEl.textContent = `${formatINR(data.monthly_investment_inr)} / month`;
    if (disclaimerEl) {
        disclaimerEl.style.display = "block";
        disclaimerEl.textContent = data.disclaimer || "This is an illustration with an assumed return, not a guarantee and not financial advice.";
    }

    if (gridEl) {
        gridEl.textContent = "";
        gridEl.style.display = "grid";

        data.projections.forEach((proj) => {
            const card = createSafeElement("div", { className: "simulator-proj-card" });

            const header = createSafeElement("div", { className: "simulator-proj-header" },
                createSafeElement("span", {
                    className: "simulator-proj-year",
                    text: `${proj.years} Year${proj.years > 1 ? "s" : ""}`
                }),
                createSafeElement("span", {
                    className: "simulator-proj-months",
                    text: `(${proj.months} months)`
                })
            );

            const fvRow = createSafeElement("div", { className: "simulator-proj-fv" },
                createSafeElement("div", { className: "proj-label", text: "Future Value" }),
                createSafeElement("div", { className: "proj-value proj-value--fv", text: formatINR(proj.future_value_inr) })
            );

            const metaRow = createSafeElement("div", { className: "simulator-proj-meta" },
                createSafeElement("div", { className: "proj-meta-item" },
                    createSafeElement("span", { className: "meta-label", text: "Total Saved: " }),
                    createSafeElement("span", { className: "meta-val", text: formatINR(proj.total_invested_inr) })
                ),
                createSafeElement("div", { className: "proj-meta-item" },
                    createSafeElement("span", { className: "meta-label", text: "Wealth Gain: " }),
                    createSafeElement("span", {
                        className: `meta-val ${proj.gain_inr >= 0 ? "gain-positive" : "gain-neutral"}`,
                        text: `+${formatINR(proj.gain_inr)}`
                    })
                )
            );

            card.appendChild(header);
            card.appendChild(fvRow);
            card.appendChild(metaRow);
            gridEl.appendChild(card);
        });
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Prediction Rendering
// ────────────────────────────────────────────────────────────────────────────

function renderPrediction(data) {
    const statusBadge = IDOM.predictionStatusBadge();
    const confBadge = IDOM.predictionConfidenceBadge();
    const balEl = IDOM.predictionProjectedBalance();
    const safeEl = IDOM.predictionSafeBudget();
    const daysEl = IDOM.predictionDaysInfo();
    const warnBanner = IDOM.predictionWarningBanner();
    const warnText = IDOM.predictionWarningText();
    const detailsEl = IDOM.predictionDetails();
    const emptyEl = IDOM.predictionEmptyState();
    const emptyText = IDOM.predictionEmptyText();

    if (!data) return;

    if (data.status === "future") {
        if (detailsEl) detailsEl.style.display = "none";
        if (emptyEl) {
            emptyEl.style.display = "flex";
            if (emptyText) emptyText.textContent = "This month is in the future. Prediction will activate once the month begins.";
        }
        if (statusBadge) {
            statusBadge.textContent = "Future";
            statusBadge.className = "badge-status badge-status--future";
        }
        if (confBadge) confBadge.style.display = "none";
        if (warnBanner) warnBanner.style.display = "none";
        return;
    }

    if (data.status === "completed") {
        if (emptyEl) emptyEl.style.display = "none";
        if (detailsEl) detailsEl.style.display = "block";

        if (statusBadge) {
            statusBadge.textContent = "Completed";
            statusBadge.className = "badge-status badge-status--completed";
        }
        if (confBadge) {
            confBadge.style.display = "inline-flex";
            confBadge.textContent = "Final";
            confBadge.className = "badge-confidence badge-confidence--high";
        }
        if (daysEl) {
            daysEl.textContent = `Month ended (${data.days_in_month} days) • Actual daily average: ${formatINR(data.average_daily_spend_inr)}/day`;
        }
        if (balEl) {
            const bal = data.projected_balance_inr || 0;
            balEl.textContent = formatINR(bal);
            balEl.className = `prediction-metric-val ${bal >= 0 ? "text-income" : "text-faltu"}`;
        }
        if (safeEl) {
            safeEl.textContent = "— (Month Ended)";
            safeEl.className = "prediction-metric-val text-muted";
        }
        if (warnBanner) {
            if (data.will_overspend) {
                warnBanner.style.display = "flex";
                if (warnText) warnText.textContent = `Deficit month: Final spending exceeded income by ${formatINR(Math.abs(data.projected_balance_inr))}.`;
            } else {
                warnBanner.style.display = "none";
            }
        }
        return;
    }

    // Current month
    if (emptyEl) emptyEl.style.display = "none";
    if (detailsEl) detailsEl.style.display = "block";

    if (statusBadge) {
        statusBadge.textContent = "Active";
        statusBadge.className = "badge-status badge-status--active";
    }

    if (confBadge) {
        confBadge.style.display = "inline-flex";
        confBadge.textContent = `${data.confidence.toUpperCase()} CONFIDENCE`;
        confBadge.className = `badge-confidence badge-confidence--${data.confidence}`;
    }

    if (daysEl) {
        daysEl.textContent = `Day ${data.days_elapsed} of ${data.days_in_month} • ${data.days_remaining} day${data.days_remaining === 1 ? "" : "s"} remaining • Current spend: ${formatINR(data.average_daily_spend_inr)}/day`;
    }

    if (balEl) {
        const bal = data.projected_balance_inr || 0;
        balEl.textContent = formatINR(bal);
        balEl.className = `prediction-metric-val ${bal >= 0 ? "text-income" : "text-faltu"}`;
    }

    if (safeEl) {
        safeEl.textContent = `${formatINR(data.safe_daily_budget_inr)} / day`;
        safeEl.className = "prediction-metric-val";
    }

    if (warnBanner) {
        if (data.will_overspend) {
            warnBanner.style.display = "flex";
            if (warnText) {
                warnText.textContent = `⚠️ At your current rate of ${formatINR(data.average_daily_spend_inr)}/day, you are projected to overspend by ${formatINR(Math.abs(data.projected_balance_inr))} by month end!`;
            }
        } else {
            warnBanner.style.display = "none";
        }
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Smart Insights Summary Rendering
// ────────────────────────────────────────────────────────────────────────────

function renderSmartInsights(insights) {
    const listEl = IDOM.insightsSummaryList();
    const emptyEl = IDOM.insightsSummaryEmpty();
    const badgeEl = IDOM.insightsCountBadge();

    if (!listEl) return;
    listEl.textContent = "";

    const count = Array.isArray(insights) ? insights.length : 0;
    if (badgeEl) badgeEl.textContent = `${count} Insight${count === 1 ? "" : "s"}`;

    if (!insights || insights.length === 0) {
        if (emptyEl) emptyEl.style.display = "flex";
        return;
    }

    if (emptyEl) emptyEl.style.display = "none";

    const iconMap = {
        warning: "⚠️",
        good: "🌟",
        info: "ℹ️"
    };

    insights.forEach((item) => {
        const itemEl = createSafeElement("div", {
            className: `insight-summary-item insight-item--${item.severity || "info"}`
        });

        const iconEl = createSafeElement("span", {
            className: "insight-item-icon",
            text: iconMap[item.severity] || "💡"
        });

        const msgEl = createSafeElement("span", {
            className: "insight-item-message",
            text: item.message
        });

        itemEl.appendChild(iconEl);
        itemEl.appendChild(msgEl);
        listEl.appendChild(itemEl);
    });
}

// ────────────────────────────────────────────────────────────────────────────
// Weekly Report Rendering
// ────────────────────────────────────────────────────────────────────────────

function renderWeeklyReport(data) {
    const rangeEl = IDOM.weeklyReportRange();
    const badgeEl = IDOM.weeklySpendBadge();
    const bodyEl = IDOM.weeklyReportBody();
    const emptyEl = IDOM.weeklyReportEmpty();
    const dailyEl = IDOM.weeklyDailySpend();
    const faltuEl = IDOM.weeklyFaltuSpend();
    const noSpendEl = IDOM.weeklyNoSpendDays();
    const compEl = IDOM.weeklyPrevComparison();
    const highDayBar = IDOM.weeklyHighestDayBar();
    const highDayText = IDOM.weeklyHighestDayText();
    const topCatList = IDOM.weeklyTopCatList();

    if (!data) return;

    if (rangeEl) {
        rangeEl.textContent = `${formatDateDisplay(data.start_date)} – ${formatDateDisplay(data.end_date)}`;
    }

    if (badgeEl) {
        badgeEl.textContent = `${formatINR(data.total_spent_inr)} spent`;
    }

    if (dailyEl) dailyEl.textContent = formatINR(data.daily_inr);
    if (faltuEl) faltuEl.textContent = formatINR(data.faltu_inr);
    if (noSpendEl) noSpendEl.textContent = `${data.no_spend_days} / 7`;

    if (compEl) {
        const change = data.change_versus_previous_week_percent;
        if (change === null || change === undefined) {
            compEl.textContent = "— (No prev data)";
            compEl.className = "chip-val text-muted";
        } else if (change > 0) {
            compEl.textContent = `+${change}%`;
            compEl.className = "chip-val text-faltu";
        } else if (change < 0) {
            compEl.textContent = `${change}%`;
            compEl.className = "chip-val text-income";
        } else {
            compEl.textContent = "0.0%";
            compEl.className = "chip-val text-muted";
        }
    }

    if (highDayBar && highDayText) {
        if (data.highest_spending_day && data.highest_spending_day.amount_inr > 0) {
            highDayBar.style.display = "flex";
            highDayText.textContent = `${formatDateDisplay(data.highest_spending_day.date)} (${formatINR(data.highest_spending_day.amount_inr)})`;
        } else {
            highDayBar.style.display = "none";
        }
    }

    if (topCatList) {
        topCatList.textContent = "";
        const cats = data.top_3_sub_categories || [];
        if (cats.length === 0) {
            topCatList.appendChild(createSafeElement("div", {
                className: "top-cat-empty",
                text: "No category spending this week."
            }));
        } else {
            cats.forEach((cat) => {
                const item = createSafeElement("div", { className: "top-cat-item" },
                    createSafeElement("span", { className: "top-cat-name", text: cat.sub_category }),
                    createSafeElement("span", { className: "top-cat-amount", text: formatINR(cat.amount_inr) })
                );
                topCatList.appendChild(item);
            });
        }
    }

    // Toggle empty state vs body
    if (data.total_spent_inr <= 0 && (!data.top_3_sub_categories || data.top_3_sub_categories.length === 0)) {
        if (bodyEl) bodyEl.style.display = "none";
        if (emptyEl) emptyEl.style.display = "flex";
    } else {
        if (bodyEl) bodyEl.style.display = "block";
        if (emptyEl) emptyEl.style.display = "none";
    }
}

// ────────────────────────────────────────────────────────────────────────────
// Public Loaders & Events
// ────────────────────────────────────────────────────────────────────────────

export async function loadInsights(month) {
    if (month) _currentMonth = month;
    if (!_currentMonth) return;

    const returnInput = IDOM.simulatorReturnInput();
    const annualReturn = returnInput ? (parseFloat(returnInput.value) || 12) : 12;

    try {
        const [simData, predData, summaryData, weeklyData] = await Promise.all([
            api.getSimulator(_currentMonth, annualReturn),
            api.getPrediction(_currentMonth),
            api.getInsightsSummary(_currentMonth),
            api.getWeeklyReport()
        ]);
        renderSimulator(simData);
        renderPrediction(predData);
        renderSmartInsights(summaryData);
        renderWeeklyReport(weeklyData);
    } catch (err) {
        showToast("Failed to load insights: " + err.message, "error");
    }
}

export function initInsightsEventListeners() {
    const returnInput = IDOM.simulatorReturnInput();
    if (returnInput) {
        returnInput.addEventListener("input", () => {
            const val = parseFloat(returnInput.value);
            if (!isNaN(val) && val >= 0 && val <= 30 && _currentMonth) {
                api.getSimulator(_currentMonth, val)
                    .then(renderSimulator)
                    .catch((err) => showToast(err.message, "error"));
            }
        });
    }
}
