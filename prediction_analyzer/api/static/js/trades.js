/**
 * Trades page - browse, filter, search, and manage trades
 */
const Trades = (() => {
    let currentOffset = 0;
    let currentLimit = 50;
    let currentTotal = 0;
    let currentSource = '';
    let currentMarket = '';

    async function render(container) {
        container.innerHTML = `
            <div class="page-header">
                <h1>Trades</h1>
                <div class="header-actions">
                    <a href="${API.getExportUrl('csv')}" class="btn btn-outline btn-small" id="export-csv-btn">Export CSV</a>
                    <a href="${API.getExportUrl('json')}" class="btn btn-outline btn-small" id="export-json-btn">Export JSON</a>
                </div>
            </div>
            <div class="filters-bar">
                <div class="filter-group">
                    <label>Provider</label>
                    <select id="trade-filter-source" class="form-select">
                        <option value="">All Providers</option>
                        <option value="polymarket">Polymarket</option>
                        <option value="kalshi">Kalshi</option>
                        <option value="limitless">Limitless</option>
                        <option value="manifold">Manifold</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Market</label>
                    <select id="trade-filter-market" class="form-select">
                        <option value="">All Markets</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Per Page</label>
                    <select id="trade-per-page" class="form-select">
                        <option value="25">25</option>
                        <option value="50" selected>50</option>
                        <option value="100">100</option>
                        <option value="250">250</option>
                    </select>
                </div>
            </div>
            <div id="trades-loading" class="loading-state">Loading trades...</div>
            <div id="trades-empty" class="empty-state hidden">
                <h2>No trades found</h2>
                <p>Try changing your filters or <a href="#upload">upload some trades</a>.</p>
            </div>
            <div id="trades-content" class="hidden">
                <div id="trades-table-wrap"></div>
                <div class="pagination" id="trades-pagination"></div>
            </div>
        `;

        // Event listeners
        document.getElementById('trade-filter-source').addEventListener('change', (e) => {
            currentSource = e.target.value;
            currentOffset = 0;
            loadTrades();
        });
        document.getElementById('trade-filter-market').addEventListener('change', (e) => {
            currentMarket = e.target.value;
            currentOffset = 0;
            loadTrades();
        });
        document.getElementById('trade-per-page').addEventListener('change', (e) => {
            currentLimit = parseInt(e.target.value);
            currentOffset = 0;
            loadTrades();
        });

        // Add auth header to export links
        const token = API.getToken();
        document.getElementById('export-csv-btn').addEventListener('click', (e) => {
            e.preventDefault();
            downloadExport('csv');
        });
        document.getElementById('export-json-btn').addEventListener('click', (e) => {
            e.preventDefault();
            downloadExport('json');
        });

        // Load markets for filter dropdown
        loadMarketFilter();
        currentOffset = 0;
        await loadTrades();
    }

    async function downloadExport(format) {
        try {
            const url = API.getExportUrl(format, currentMarket || null);
            const resp = await fetch(url, {
                headers: { 'Authorization': `Bearer ${API.getToken()}` }
            });
            if (!resp.ok) throw new Error('Export failed');
            const blob = await resp.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `trades.${format}`;
            a.click();
            URL.revokeObjectURL(a.href);
            App.toast('Export downloaded', 'success');
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

    async function loadMarketFilter() {
        try {
            const markets = await API.getMarkets();
            const select = document.getElementById('trade-filter-market');
            if (!select) return;
            markets.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.slug;
                opt.textContent = truncate(m.title, 50);
                select.appendChild(opt);
            });
        } catch (_) { /* ignore */ }
    }

    async function loadTrades() {
        const loading = document.getElementById('trades-loading');
        const empty = document.getElementById('trades-empty');
        const content = document.getElementById('trades-content');

        loading.classList.remove('hidden');
        empty.classList.add('hidden');
        content.classList.add('hidden');

        try {
            const data = await API.getTrades(
                currentLimit,
                currentOffset,
                currentMarket || null,
                currentSource || null,
            );

            loading.classList.add('hidden');
            currentTotal = data.total;

            if (data.total === 0) {
                empty.classList.remove('hidden');
                return;
            }

            content.classList.remove('hidden');
            renderTable(data.trades);
            renderPagination();
        } catch (err) {
            loading.innerHTML = `<div class="error-state">${escapeHtml(err.message)}</div>`;
        }
    }

    function renderTable(trades) {
        const wrap = document.getElementById('trades-table-wrap');
        wrap.innerHTML = `
            <div class="table-scroll">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Market</th>
                            <th>Type</th>
                            <th>Side</th>
                            <th>Price</th>
                            <th>Shares</th>
                            <th>Cost</th>
                            <th>PnL</th>
                            <th>Source</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${trades.map(t => `
                            <tr>
                                <td class="nowrap">${new Date(t.timestamp).toLocaleString()}</td>
                                <td class="truncate" title="${escapeHtml(t.market)}">${escapeHtml(truncate(t.market, 35))}</td>
                                <td><span class="badge badge-${escapeHtml(t.type).toLowerCase()}">${escapeHtml(t.type)}</span></td>
                                <td><span class="badge badge-${escapeHtml(t.side).toLowerCase()}">${escapeHtml(t.side)}</span></td>
                                <td>${t.price.toFixed(4)}</td>
                                <td>${t.shares.toFixed(2)}</td>
                                <td>${formatCurrency(t.cost)}</td>
                                <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(t.pnl)}</td>
                                <td><span class="badge badge-source">${escapeHtml(t.source)}</span></td>
                                <td>
                                    <button class="btn-icon delete-trade" data-id="${t.id}" title="Delete trade">&times;</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // Delete buttons
        wrap.querySelectorAll('.delete-trade').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (!confirm('Delete this trade?')) return;
                try {
                    await API.deleteTrade(btn.dataset.id);
                    App.toast('Trade deleted', 'success');
                    loadTrades();
                } catch (err) {
                    App.toast(err.message, 'error');
                }
            });
        });
    }

    function renderPagination() {
        const el = document.getElementById('trades-pagination');
        const totalPages = Math.ceil(currentTotal / currentLimit);
        const currentPage = Math.floor(currentOffset / currentLimit) + 1;

        el.innerHTML = `
            <span class="pagination-info">
                Showing ${currentOffset + 1}-${Math.min(currentOffset + currentLimit, currentTotal)} of ${currentTotal.toLocaleString()}
            </span>
            <div class="pagination-buttons">
                <button class="btn btn-outline btn-small" id="page-prev" ${currentPage <= 1 ? 'disabled' : ''}>Prev</button>
                <span class="pagination-page">Page ${currentPage} of ${totalPages}</span>
                <button class="btn btn-outline btn-small" id="page-next" ${currentPage >= totalPages ? 'disabled' : ''}>Next</button>
            </div>
        `;

        document.getElementById('page-prev').addEventListener('click', () => {
            currentOffset = Math.max(0, currentOffset - currentLimit);
            loadTrades();
        });
        document.getElementById('page-next').addEventListener('click', () => {
            currentOffset += currentLimit;
            loadTrades();
        });
    }

    return { render };
})();
