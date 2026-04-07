/**
 * Main application - routing, state management, initialization
 */

// Utility functions (global)
function formatCurrency(val) {
    if (val == null || isNaN(val)) return '$0.00';
    const sign = val < 0 ? '-' : '';
    return `${sign}$${Math.abs(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(val) {
    if (val == null || isNaN(val)) return '0.00%';
    return `${val.toFixed(2)}%`;
}

function truncate(str, max) {
    if (!str) return '';
    return str.length > max ? str.substring(0, max) + '...' : str;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

const App = (() => {
    let currentPage = 'dashboard';
    let currentUser = null;

    function init() {
        Auth.init();

        // Check if already logged in
        if (API.isLoggedIn()) {
            showApp();
        } else {
            showAuth();
        }

        // Routing
        window.addEventListener('hashchange', handleRoute);
        handleRoute();

        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => {
            API.logout();
            onLogout();
        });

        // Auth expired event
        window.addEventListener('auth-expired', () => {
            onLogout();
            toast('Session expired. Please log in again.', 'error');
        });

        // Mobile menu toggle
        document.getElementById('menu-toggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });

        // Close sidebar on nav click (mobile)
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                document.getElementById('sidebar').classList.remove('open');
            });
        });
    }

    function handleRoute() {
        if (!API.isLoggedIn()) return;

        const hash = window.location.hash.replace('#', '') || 'dashboard';
        const page = hash.split('/')[0]; // Support #markets/slug later

        const validPages = ['dashboard', 'trades', 'markets', 'upload', 'settings'];
        if (!validPages.includes(page)) {
            window.location.hash = 'dashboard';
            return;
        }

        navigateTo(page);
    }

    function navigateTo(page) {
        // Cleanup previous page
        if (currentPage === 'dashboard') Dashboard.destroy?.();
        if (currentPage === 'markets') Markets.destroy?.();

        currentPage = page;

        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.page === page);
        });

        // Show correct page
        document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
        const pageEl = document.getElementById(`page-${page}`);
        pageEl.classList.remove('hidden');

        // Render page
        switch (page) {
            case 'dashboard': Dashboard.render(pageEl); break;
            case 'trades': Trades.render(pageEl); break;
            case 'markets': Markets.render(pageEl); break;
            case 'upload': Upload.render(pageEl); break;
            case 'settings': Settings.render(pageEl); break;
        }
    }

    async function showApp() {
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('app-screen').classList.remove('hidden');

        try {
            currentUser = await API.getMe();
            updateUserDisplay(currentUser);
        } catch (_) {
            // Token might be expired
            API.clearToken();
            showAuth();
            return;
        }

        handleRoute();
    }

    function showAuth() {
        document.getElementById('auth-screen').classList.remove('hidden');
        document.getElementById('app-screen').classList.add('hidden');
    }

    function onLoginSuccess() {
        showApp();
    }

    function onLogout() {
        currentUser = null;
        showAuth();
        window.location.hash = '';
    }

    function updateUserDisplay(user) {
        currentUser = user;
        const display = escapeHtml(user.username);
        document.getElementById('sidebar-user').textContent = display;
        document.getElementById('mobile-user').textContent = display;
    }

    function toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => toast.classList.add('visible'));

        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    return { init, onLoginSuccess, onLogout, updateUserDisplay, toast };
})();

// Boot
document.addEventListener('DOMContentLoaded', App.init);
