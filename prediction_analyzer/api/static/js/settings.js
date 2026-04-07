/**
 * Settings page - user profile management
 */
const Settings = (() => {
    async function render(container) {
        container.innerHTML = `
            <div class="page-header">
                <h1>Settings</h1>
            </div>
            <div class="settings-layout">
                <div class="card">
                    <h2>Profile</h2>
                    <div id="settings-loading" class="loading-state">Loading profile...</div>
                    <form id="profile-form" class="hidden">
                        <div class="form-group">
                            <label for="settings-username">Username</label>
                            <input type="text" id="settings-username" minlength="3" maxlength="50">
                        </div>
                        <div class="form-group">
                            <label for="settings-email">Email</label>
                            <input type="email" id="settings-email">
                        </div>
                        <button type="submit" class="btn btn-primary">Save Changes</button>
                        <div id="profile-message" class="form-message"></div>
                    </form>
                </div>
                <div class="card">
                    <h2>Account Stats</h2>
                    <div id="settings-stats" class="loading-state">Loading stats...</div>
                </div>
                <div class="card danger-card">
                    <h2>Delete Account</h2>
                    <p class="muted">Permanently delete your account and all associated data. This cannot be undone.</p>
                    <button id="delete-account-btn" class="btn btn-danger">Delete My Account</button>
                </div>
            </div>
        `;

        await loadProfile();
        loadStats();
        setupDeleteAccount();
    }

    async function loadProfile() {
        try {
            const user = await API.getMe();
            document.getElementById('settings-loading').classList.add('hidden');
            const form = document.getElementById('profile-form');
            form.classList.remove('hidden');

            document.getElementById('settings-username').value = user.username;
            document.getElementById('settings-email').value = user.email;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const msg = document.getElementById('profile-message');
                msg.textContent = '';
                msg.className = 'form-message';

                const username = document.getElementById('settings-username').value.trim();
                const email = document.getElementById('settings-email').value.trim();

                const updates = {};
                if (username !== user.username) updates.username = username;
                if (email !== user.email) updates.email = email;

                if (!Object.keys(updates).length) {
                    msg.textContent = 'No changes to save.';
                    msg.classList.add('info');
                    return;
                }

                try {
                    const updated = await API.updateProfile(updates);
                    user.username = updated.username;
                    user.email = updated.email;
                    msg.textContent = 'Profile updated!';
                    msg.classList.add('success');
                    // Update sidebar
                    App.updateUserDisplay(updated);
                } catch (err) {
                    msg.textContent = err.message;
                    msg.classList.add('error');
                }
            });
        } catch (err) {
            document.getElementById('settings-loading').innerHTML =
                `<div class="error-state">${escapeHtml(err.message)}</div>`;
        }
    }

    async function loadStats() {
        const el = document.getElementById('settings-stats');
        try {
            const stats = await API.getMyStats();
            el.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">${stats.trade_count.toLocaleString()}</span>
                        <span class="stat-label">Total Trades</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${stats.market_count}</span>
                        <span class="stat-label">Markets</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${stats.upload_count}</span>
                        <span class="stat-label">Uploads</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${stats.saved_analysis_count}</span>
                        <span class="stat-label">Saved Analyses</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value ${stats.total_pnl >= 0 ? 'positive' : 'negative'}">${formatCurrency(stats.total_pnl)}</span>
                        <span class="stat-label">Total PnL</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">${new Date(stats.member_since).toLocaleDateString()}</span>
                        <span class="stat-label">Member Since</span>
                    </div>
                </div>
            `;
        } catch (err) {
            el.innerHTML = `<div class="error-state">${escapeHtml(err.message)}</div>`;
        }
    }

    function setupDeleteAccount() {
        document.getElementById('delete-account-btn').addEventListener('click', async () => {
            if (!confirm('Are you sure? This will permanently delete your account and ALL data.')) return;
            if (!prompt('Type DELETE to confirm:')?.toUpperCase().startsWith('DELETE')) return;

            try {
                await API.deleteAccount();
                API.logout();
                App.onLogout();
                App.toast('Account deleted', 'success');
            } catch (err) {
                App.toast(err.message, 'error');
            }
        });
    }

    return { render };
})();
