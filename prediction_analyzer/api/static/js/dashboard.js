/**
 * Dashboard page - overview with charts and key metrics
 */
const Dashboard = (() => {
    let pnlChart = null;
    let breakdownChart = null;

    async function render(container) {
        container.innerHTML = `
            <div class="page-header">
                <h1>Dashboard</h1>
                <div class="header-actions">
                    <button id="dash-refresh" class="btn btn-outline btn-small">Refresh</button>
                </div>
            </div>
            <div id="dash-loading" class="loading-state">Loading your portfolio...</div>
            <div id="dash-empty" class="empty-state hidden">
                <h2>No trades yet</h2>
                <p>Upload your trade files or connect a provider to get started.</p>
                <a href="#upload" class="btn btn-primary">Upload Trades</a>
            </div>
            <div id="dash-content" class="hidden">
                <div class="metrics-grid" id="dash-metrics"></div>
                <div class="chart-row">
                    <div class="chart-card">
                        <h3>Cumulative PnL</h3>
                        <div class="chart-wrap"><canvas id="chart-pnl"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <h3>PnL by Market</h3>
                        <div class="chart-wrap"><canvas id="chart-breakdown"></canvas></div>
                    </div>
                </div>
                <div class="chart-row">
                    <div class="chart-card full-width">
                        <h3>Advanced Metrics</h3>
                        <div id="dash-advanced" class="metrics-grid"></div>
                    </div>
                </div>
                <div class="chart-row">
                    <div class="chart-card full-width">
                        <h3>Recent Trades</h3>
                        <div id="dash-recent-trades"></div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('dash-refresh').addEventListener('click', () => render(container));
        await loadData();
    }

    async function loadData() {
        const loading = document.getElementById('dash-loading');
        const empty = document.getElementById('dash-empty');
        const content = document.getElementById('dash-content');

        try {
            let summary;
            try {
                summary = await API.getGlobalAnalysis();
            } catch (e) {
                if (e.message.includes('No trades found')) {
                    loading.classList.add('hidden');
                    empty.classList.remove('hidden');
                    return;
                }
                throw e;
            }

            loading.classList.add('hidden');
            content.classList.remove('hidden');

            renderMetrics(summary);

            // Load remaining data in parallel
            const [pnlData, breakdownData, metricsData, recentTrades] = await Promise.allSettled([
                API.getPnlChart(),
                API.getMarketBreakdown(),
                API.getAdvancedMetrics(),
                API.getTrades(10, 0),
            ]);

            if (pnlData.status === 'fulfilled') renderPnlChart(pnlData.value);
            if (breakdownData.status === 'fulfilled') renderBreakdownChart(breakdownData.value);
            if (metricsData.status === 'fulfilled') renderAdvancedMetrics(metricsData.value);
            if (recentTrades.status === 'fulfilled') renderRecentTrades(recentTrades.value.trades);
        } catch (err) {
            loading.innerHTML = `<div class="error-state">Failed to load dashboard: ${escapeHtml(err.message)}</div>`;
        }
    }

    function renderMetrics(s) {
        const el = document.getElementById('dash-metrics');
        const pnlClass = s.total_pnl >= 0 ? 'positive' : 'negative';
        const roiClass = s.roi >= 0 ? 'positive' : 'negative';

        el.innerHTML = `
            <div class="metric-card highlight">
                <div class="metric-label">Total PnL</div>
                <div class="metric-value ${pnlClass}">${formatCurrency(s.total_pnl)}</div>
                <div class="metric-sub">${s.currency || 'USD'}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">ROI</div>
                <div class="metric-value ${roiClass}">${formatPercent(s.roi)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">${formatPercent(s.win_rate)}</div>
                <div class="metric-sub">${s.winning_trades}W / ${s.losing_trades}L</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">${s.total_trades.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Invested</div>
                <div class="metric-value">${formatCurrency(s.total_invested)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Returned</div>
                <div class="metric-value">${formatCurrency(s.total_returned)}</div>
            </div>
        `;
    }

    function renderPnlChart(data) {
        const ctx = document.getElementById('chart-pnl');
        if (!ctx) return;
        if (pnlChart) pnlChart.destroy();

        const times = data.times.map(t => new Date(t).toLocaleDateString());
        const values = data.cumulative_pnl;

        // Color gradient: green above zero, red below
        pnlChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: times,
                datasets: [{
                    label: 'Cumulative PnL',
                    data: values,
                    borderColor: data.final_pnl >= 0 ? '#22c55e' : '#ef4444',
                    backgroundColor: data.final_pnl >= 0 ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: values.length > 50 ? 0 : 3,
                    borderWidth: 2,
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
                        display: true,
                        ticks: { maxTicksLimit: 8, color: '#94a3b8' },
                        grid: { color: 'rgba(148,163,184,0.1)' },
                    },
                    y: {
                        ticks: {
                            color: '#94a3b8',
                            callback: (v) => formatCurrency(v),
                        },
                        grid: { color: 'rgba(148,163,184,0.1)' },
                    },
                },
            },
        });
    }

    function renderBreakdownChart(data) {
        const ctx = document.getElementById('chart-breakdown');
        if (!ctx || !data.length) return;
        if (breakdownChart) breakdownChart.destroy();

        // Sort by absolute PnL and take top 10
        const sorted = [...data].sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl)).slice(0, 10);
        const labels = sorted.map(m => truncate(m.market, 25));
        const values = sorted.map(m => m.pnl);
        const colors = values.map(v => v >= 0 ? '#22c55e' : '#ef4444');

        breakdownChart = new Chart(ctx, {
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
                indexAxis: 'y',
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
                        ticks: { color: '#94a3b8', callback: (v) => formatCurrency(v) },
                        grid: { color: 'rgba(148,163,184,0.1)' },
                    },
                    y: {
                        ticks: { color: '#94a3b8' },
                        grid: { display: false },
                    },
                },
            },
        });
    }

    function renderAdvancedMetrics(m) {
        const el = document.getElementById('dash-advanced');
        if (!el) return;

        const sharpe = m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : 'N/A';
        const sortino = m.sortino_ratio != null ? m.sortino_ratio.toFixed(2) : 'N/A';
        const maxDd = m.max_drawdown != null ? formatPercent(m.max_drawdown) : 'N/A';
        const profitFactor = m.profit_factor != null ? m.profit_factor.toFixed(2) : 'N/A';
        const expectancy = m.expectancy != null ? formatCurrency(m.expectancy) : 'N/A';
        const winStreak = m.max_win_streak != null ? m.max_win_streak : 'N/A';
        const loseStreak = m.max_loss_streak != null ? m.max_loss_streak : 'N/A';

        el.innerHTML = `
            <div class="metric-card small">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">${sharpe}</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Sortino Ratio</div>
                <div class="metric-value">${sortino}</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value negative">${maxDd}</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Profit Factor</div>
                <div class="metric-value">${profitFactor}</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Expectancy</div>
                <div class="metric-value">${expectancy}</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Best Streak</div>
                <div class="metric-value positive">${winStreak} wins</div>
            </div>
            <div class="metric-card small">
                <div class="metric-label">Worst Streak</div>
                <div class="metric-value negative">${loseStreak} losses</div>
            </div>
        `;
    }

    function renderRecentTrades(trades) {
        const el = document.getElementById('dash-recent-trades');
        if (!el || !trades.length) {
            if (el) el.innerHTML = '<p class="muted">No recent trades</p>';
            return;
        }

        el.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Market</th>
                        <th>Type</th>
                        <th>Side</th>
                        <th>Price</th>
                        <th>Shares</th>
                        <th>PnL</th>
                    </tr>
                </thead>
                <tbody>
                    ${trades.map(t => `
                        <tr>
                            <td>${new Date(t.timestamp).toLocaleDateString()}</td>
                            <td class="truncate">${escapeHtml(truncate(t.market, 40))}</td>
                            <td><span class="badge badge-${t.type.toLowerCase()}">${t.type}</span></td>
                            <td><span class="badge badge-${t.side.toLowerCase()}">${t.side}</span></td>
                            <td>${t.price.toFixed(2)}</td>
                            <td>${t.shares.toFixed(2)}</td>
                            <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(t.pnl)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    function destroy() {
        if (pnlChart) { pnlChart.destroy(); pnlChart = null; }
        if (breakdownChart) { breakdownChart.destroy(); breakdownChart = null; }
    }

    return { render, destroy };
})();
