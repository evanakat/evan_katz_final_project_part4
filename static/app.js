const REFRESH_MS = 60_000;

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

function signalClass(signal) {
    const s = (signal || "").toLowerCase();
    if (s.startsWith("major")) return "major";
    if (s.startsWith("moving")) return "moving";
    if (s.startsWith("slight")) return "slight";
    return "quiet";
}

function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[c]);
}

function renderMarkets(markets) {
    const container = document.getElementById("markets");
    if (!markets.length) {
        container.innerHTML = `<p class="empty">No markets match the current filters. Lower the volume or move threshold.</p>`;
        return;
    }

    container.innerHTML = markets.map((m) => {
        const change = m.price_change_24h || 0;
        const arrow = change >= 0 ? "▲" : "▼";
        const dirClass = change >= 0 ? "up" : "down";
        return `
            <article class="market">
                <div class="meta">
                    <span class="platform ${m.platform.toLowerCase()}">${escapeHtml(m.platform)}</span>
                    <span class="signal ${signalClass(m.signal)}">${escapeHtml(m.signal)}</span>
                    <span class="score">score ${m.score.toFixed(2)}</span>
                </div>
                <a class="title" href="${escapeHtml(m.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(m.title)}</a>
                <div class="row">
                    <div class="stat">
                        <span class="label">Price (Yes)</span>
                        <span class="value">${fmtPct(m.price)}</span>
                    </div>
                    <div class="stat ${dirClass}">
                        <span class="label">24h Change</span>
                        <span class="value">${arrow} ${fmtPct(Math.abs(change))}</span>
                    </div>
                    <div class="stat">
                        <span class="label">24h Volume</span>
                        <span class="value">${fmtMoney(m.volume_24h)}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Liquidity</span>
                        <span class="value">${fmtMoney(m.liquidity)}</span>
                    </div>
                </div>
                <div class="explanation">${escapeHtml(m.explanation)}</div>
            </article>
        `;
    }).join("");
}

async function loadTrends() {
    const status = document.getElementById("status");
    const platform = document.getElementById("platform").value;
    const minVol = document.getElementById("min_vol").value || "0";
    const minMovePct = parseFloat(document.getElementById("min_move").value || "0");
    const minMove = isNaN(minMovePct) ? 0 : minMovePct / 100;
    const limit = document.getElementById("limit").value || "50";

    status.textContent = "Loading…";

    try {
        const url = `/api/trends?platform=${encodeURIComponent(platform)}&min_vol=${encodeURIComponent(minVol)}&min_move=${encodeURIComponent(minMove)}&limit=${encodeURIComponent(limit)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderMarkets(data.markets);
        const ts = new Date(data.cached_at * 1000).toLocaleTimeString();
        let line = `Updated ${ts} · ${data.markets.length} of ${data.total_unfiltered} markets`;
        if (data.errors && data.errors.length) {
            line += ` · errors: ${data.errors.join("; ")}`;
        }
        status.textContent = line;
    } catch (err) {
        status.textContent = `Error: ${err.message}`;
    }
}

document.getElementById("refresh").addEventListener("click", loadTrends);
["platform", "min_vol", "min_move", "limit"].forEach((id) => {
    document.getElementById(id).addEventListener("change", loadTrends);
});

loadTrends();
setInterval(loadTrends, REFRESH_MS);
