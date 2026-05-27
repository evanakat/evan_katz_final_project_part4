const REFRESH_MS = 60_000;

const SIGNAL_LABELS = {
    book_imbalance: "Order book",
    arb_divergence: "Cross-platform gap",
    momentum_acceleration: "Momentum",
    vol_acceleration: "Volume share",
};

function fmtPct(x) {
    if (x === null || x === undefined) return "—";
    return (x * 100).toFixed(1) + "%";
}

function fmtMoney(x) {
    if (!x) return "$0";
    if (x >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
    if (x >= 1e3) return `$${(x / 1e3).toFixed(1)}K`;
    return `$${x.toFixed(0)}`;
}

function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);
}

function directionClass(label) {
    if (!label) return "neutral";
    const s = label.toLowerCase();
    if (s.includes("likely up")) return "strong-up";
    if (s.includes("lean up")) return "lean-up";
    if (s.includes("likely down")) return "strong-down";
    if (s.includes("lean down")) return "lean-down";
    return "neutral";
}

function renderSignalBar(name, weighted, raw) {
    const pct = Math.min(weighted * 200, 100);
    return `
        <div class="signal-row">
            <span class="signal-name">${escapeHtml(SIGNAL_LABELS[name] || name)}</span>
            <div class="signal-bar"><div class="signal-fill" style="width: ${pct}%"></div></div>
            <span class="signal-val" title="raw ${raw.toFixed(2)} · weighted ${weighted.toFixed(2)}">${weighted.toFixed(2)}</span>
        </div>
    `;
}

function renderMarkets(markets) {
    const container = document.getElementById("markets");
    if (!markets.length) {
        container.innerHTML = `<p class="empty">No markets pass the current filters. Try lowering Min Pre-Move Score or Min Volume.</p>`;
        return;
    }

    container.innerHTML = markets.map((m) => {
        const score = m.pre_move_score ?? 0;
        const dir = m.direction ?? 0;
        const dirLabel = m.direction_label || "No bias";
        const dirCls = directionClass(dirLabel);
        const feats = m.features || {};
        const contribs = m.signal_contribs || {};
        const signals = m.signals || {};

        const signalBars = Object.keys(SIGNAL_LABELS)
            .map((k) => renderSignalBar(k, contribs[k] || 0, signals[k] || 0))
            .join("");

        const paired = m.paired_title
            ? `<div class="paired">↔ paired with <a href="${escapeHtml(m.paired_url || "#")}" target="_blank" rel="noopener noreferrer">${escapeHtml(m.paired_platform)}: ${escapeHtml(m.paired_title)}</a> · gap ${(feats.arb_gap * 100).toFixed(1)}c</div>`
            : "";

        const change24 = m.price_change_24h ?? 0;
        const change1 = m.price_change_1h;
        const change24Cls = change24 >= 0 ? "up" : "down";
        const change1Display = change1 == null
            ? "<span class='value muted'>—</span>"
            : `<span class="value ${change1 >= 0 ? 'up' : 'down'}">${change1 >= 0 ? '▲' : '▼'} ${fmtPct(Math.abs(change1))}</span>`;

        const hasBook = feats.has_book;
        const imb = feats.book_imbalance ?? 0;
        const bookCell = hasBook
            ? `<span class="value">${imb >= 0 ? '+' : ''}${imb.toFixed(2)}</span>`
            : "<span class='value muted'>n/a</span>";

        return `
            <article class="market">
                <div class="meta">
                    <span class="platform ${m.platform.toLowerCase()}">${escapeHtml(m.platform)}</span>
                    <span class="direction ${dirCls}">${escapeHtml(dirLabel)} (${dir >= 0 ? '+' : ''}${dir.toFixed(2)})</span>
                    <span class="score" title="weighted sum of signal contributions">score ${score.toFixed(2)}</span>
                </div>
                <a class="title" href="${escapeHtml(m.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(m.title)}</a>
                <div class="explanation">${escapeHtml(m.explanation || "")}</div>
                ${paired}
                <div class="row">
                    <div class="stat">
                        <span class="label">Price (Yes)</span>
                        <span class="value">${fmtPct(m.price)}</span>
                    </div>
                    <div class="stat">
                        <span class="label">1h Change</span>
                        ${change1Display}
                    </div>
                    <div class="stat ${change24Cls}">
                        <span class="label">24h Change</span>
                        <span class="value">${change24 >= 0 ? '▲' : '▼'} ${fmtPct(Math.abs(change24))}</span>
                    </div>
                    <div class="stat">
                        <span class="label">24h Volume</span>
                        <span class="value">${fmtMoney(feats.volume_24h)}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Book Imbalance</span>
                        ${bookCell}
                    </div>
                </div>
                <details class="signals-detail">
                    <summary>Signal breakdown</summary>
                    <div class="signal-bars">${signalBars}</div>
                </details>
            </article>
        `;
    }).join("");
}

async function loadPredictions() {
    const status = document.getElementById("status");
    const platform = document.getElementById("platform").value;
    const direction = document.getElementById("direction").value;
    const minVol = document.getElementById("min_vol").value || "0";
    const minScore = document.getElementById("min_score").value || "0";
    const limit = document.getElementById("limit").value || "50";

    status.textContent = "Loading…";

    try {
        const url = `/api/predictions?platform=${encodeURIComponent(platform)}&direction=${encodeURIComponent(direction)}&min_vol=${encodeURIComponent(minVol)}&min_score=${encodeURIComponent(minScore)}&limit=${encodeURIComponent(limit)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderMarkets(data.markets);
        const ts = new Date(data.cached_at * 1000).toLocaleTimeString();
        let line = `Updated ${ts} · ${data.markets.length} of ${data.total_unfiltered} markets · ${data.orderbooks_fetched} order books · ${data.pairs_found} cross-platform pairs`;
        if (data.snapshot_rows) line += ` · ${data.snapshot_rows} snapshots logged`;
        if (data.errors && data.errors.length) {
            line += ` · errors: ${data.errors.join("; ")}`;
        }
        status.textContent = line;
    } catch (err) {
        status.textContent = `Error: ${err.message}`;
    }
}

document.getElementById("refresh").addEventListener("click", loadPredictions);
["platform", "direction", "min_vol", "min_score", "limit"].forEach((id) => {
    document.getElementById(id).addEventListener("change", loadPredictions);
});

loadPredictions();
setInterval(loadPredictions, REFRESH_MS);
