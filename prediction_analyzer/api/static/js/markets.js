/**
 * Markets page - market breakdown and per-market analysis
 */
const Markets = (() => {
    let marketChart = null;

    async function render(container) {
        container.innerHTML = `
            <div class="page-header">
                <h1>Markets</h1>
            </div>
            <div id="markets-loading" class="loading-state">Loading markets...</div>
            <div id="markets-empty" class="empty-state hidden">
                <h2>No markets yet</h2>
                <p><a href="#upload">Upload trades</a> to see your market breakdown.</p>
            </div>
            <div id="markets-content" class="hidden">
                <div class="chart-card full-width" id="markets-chart-card">
                    <h3>PnL by Market</h3>
                    <div class="chart-wrap chart-wrap-tall"><canvas id="chart-markets"></canvas></div>
                </div>
                <div id="markets-list" class="markets-grid"></div>
            </div>
            <!-- Market detail modal -->
            <div id="market-modal" class="modal hidden">
                <div class="modal-backdrop"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 id="modal-market-title"></h2>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div id="modal-body" class="modal-body"></div>
                </div>
            </div>
        `;

        // Close modal
        container.querySelector('.modal-backdrop').addEventListener('click', closeModal);
        container.querySelector('.modal-close').addEventListener('click', closeModal);

        await loadData();
    }

    async function loadData() {
        const loading = document.getElementById('markets-loading');
        const empty = document.getElementById('markets-empty');
        const content = document.getElementById('markets-content');

        try {
            const [markets, breakdown] = await Promise.all([
                API.getMarkets(),
                API.getMarketBreakdown(),
            ]);

            loading.classList.add('hidden');

            if (!markets.length) {
                empty.classList.remove('hidden');
                return;
            }

            content.classList.remove('hidden');
            renderChart(breakdown);
            renderMarketList(markets);
        } catch (err) {
            if (err.message.includes('No trades found')) {
                loading.classList.add('hidden');
                empty.classList.remove('hidden');
            } else {
                loading.innerHTML = `<div class="error-state">${escapeHtml(err.message)}</div>`;
            }
        }
    }

    function renderChart(breakdown) {
        const ctx = document.getElementById('chart-markets');
        if (!ctx || !breakdown.length) return;
        if (marketChart) marketChart.destroy();

        const sorted = [...breakdown].sort((a, b) => b.pnl - a.pnl);
        const labels = sorted.map(m => truncate(m.market, 30));
        const values = sorted.map(m => m.pnl);
        const colors = values.map(v => v >= 0 ? '#22c55e' : '#ef4444');

        marketChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'PnL',
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `PnL: ${formatCurrency(ctx.raw)}`
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8', maxRotation: 45 },
                        grid: { display: false },
                    },
                    y: {
                        ticks: { color: '#94a3b8', callback: (v) => formatCurrency(v) },
                        grid: { color: 'rgba(148,163,184,0.1)' },
                    },
                },
            },
        });
    }

    function renderMarketList(markets) {
        const el = document.getElementById('markets-list');
        // Sort by trade count descending
        const sorted = [...markets].sort((a, b) => b.trade_count - a.trade_count);

        el.innerHTML = sorted.map(m => `
            <div class="market-card" data-slug="${escapeHtml(m.slug)}">
                <div class="market-card-header">
                    <h3 class="market-title" title="${escapeHtml(m.title)}">${escapeHtml(truncate(m.title, 50))}</h3>
                    <span class="badge badge-source">${m.trade_count} trades</span>
                </div>
                <div class="market-card-body">
                    <div class="market-stat">
                        <span class="market-stat-label">Total PnL</span>
                        <span class="market-stat-value ${m.total_pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(m.total_pnl)}</span>
                    </div>
                </div>
                <button class="btn btn-outline btn-small btn-full market-detail-btn">View Details</button>
            </div>
        `).join('');

        // Click handlers
        el.querySelectorAll('.market-detail-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const slug = btn.closest('.market-card').dataset.slug;
                const market = markets.find(m => m.slug === slug);
                openMarketDetail(slug, market ? market.title : slug);
            });
        });
    }

    async function openMarketDetail(slug, title) {
        const modal = document.getElementById('market-modal');
        const titleEl = document.getElementById('modal-market-title');
        const body = document.getElementById('modal-body');

        titleEl.textContent = title;
        body.innerHTML = '<div class="loading-state">Loading analysis...</div>';
        modal.classList.remove('hidden');

        try {
            const [analysis, pnlData] = await Promise.all([
                API.getMarketAnalysis(slug),
                API.getPnlChart(slug),
            ]);

            const pnlClass = analysis.total_pnl >= 0 ? 'positive' : 'negative';
            const roiClass = analysis.roi >= 0 ? 'positive' : 'negative';

            body.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card small">
                        <div class="metric-label">Total PnL</div>
                        <div class="metric-value ${pnlClass}">${formatCurrency(analysis.total_pnl)}</div>
                    </div>
                    <div class="metric-card small">
                        <div class="metric-label">ROI</div>
                        <div class="metric-value ${roiClass}">${formatPercent(analysis.roi)}</div>
                    </div>
                    <div class="metric-card small">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">${formatPercent(analysis.win_rate)}</div>
                    </div>
                    <div class="metric-card small">
                        <div class="metric-label">Trades</div>
                        <div class="metric-value">${analysis.total_trades}</div>
                    </div>
                    <div class="metric-card small">
                        <div class="metric-label">Invested</div>
                        <div class="metric-value">${formatCurrency(analysis.total_invested)}</div>
                    </div>
                    <div class="metric-card small">
                        <div class="metric-label">Returned</div>
                        <div class="metric-value">${formatCurrency(analysis.total_returned)}</div>
                    </div>
                </div>
                <div class="chart-card" style="margin-top:1rem">
                    <h3>Cumulative PnL</h3>
                    <div class="chart-wrap"><canvas id="chart-market-pnl"></canvas></div>
                </div>
            `;

            // Render chart
            if (pnlData && pnlData.times.length) {
                const ctx = document.getElementById('chart-market-pnl');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: pnlData.times.map(t => new Date(t).toLocaleDateString()),
                        datasets: [{
                            label: 'Cumulative PnL',
                            data: pnlData.cumulative_pnl,
                            borderColor: pnlData.final_pnl >= 0 ? '#22c55e' : '#ef4444',
                            backgroundColor: pnlData.final_pnl >= 0 ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                            fill: true,
                            tension: 0.3,
                            pointRadius: 0,
                            borderWidth: 2,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { maxTicksLimit: 6, color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.1)' } },
                            y: { ticks: { color: '#94a3b8', callback: (v) => formatCurrency(v) }, grid: { color: 'rgba(148,163,184,0.1)' } },
                        },
                    },
                });
            }
        } catch (err) {
            body.innerHTML = `<div class="error-state">${escapeHtml(err.message)}</div>`;
        }
    }

    function closeModal() {
        document.getElementById('market-modal').classList.add('hidden');
    }

    function destroy() {
        if (marketChart) { marketChart.destroy(); marketChart = null; }
    }

    return { render, destroy };
})();
