/**
 * API client module - handles all communication with the backend
 */
const API = (() => {
    const BASE = '/api/v1';
    let _handlingExpiry = false; // guard against concurrent 401 handlers

    function getToken() {
        return localStorage.getItem('pa_token');
    }

    function setToken(token) {
        localStorage.setItem('pa_token', token);
    }

    function clearToken() {
        localStorage.removeItem('pa_token');
    }

    function isLoggedIn() {
        return !!getToken();
    }

    async function request(method, path, body = null, isFormData = false) {
        const headers = {};
        const token = getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const opts = { method, headers };

        if (body) {
            if (isFormData) {
                opts.body = body; // Let browser set Content-Type with boundary
            } else {
                headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(body);
            }
        }

        const resp = await fetch(`${BASE}${path}`, opts);

        if (resp.status === 204) {
            return null;
        }

        if (resp.status === 401) {
            clearToken();
            if (!_handlingExpiry) {
                _handlingExpiry = true;
                window.location.hash = '';
                window.dispatchEvent(new Event('auth-expired'));
                setTimeout(() => { _handlingExpiry = false; }, 1000);
            }
            throw new Error('Session expired. Please log in again.');
        }

        // Parse response - handle non-JSON error bodies (e.g. 500 plain text)
        if (!resp.ok) {
            let detail = `Request failed (${resp.status})`;
            try {
                const data = await resp.json();
                detail = data.detail || detail;
            } catch (_) { /* response wasn't JSON */ }
            throw new Error(detail);
        }

        return await resp.json();
    }

    // Auth
    async function login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email); // OAuth2 uses 'username' field
        formData.append('password', password);

        const resp = await fetch(`${BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (!resp.ok) {
            let detail = 'Login failed';
            try {
                const err = await resp.json();
                detail = err.detail || detail;
            } catch (_) { /* response wasn't JSON */ }
            throw new Error(detail);
        }

        const data = await resp.json();
        setToken(data.access_token);
        return data;
    }

    async function signup(username, email, password) {
        const data = await request('POST', '/auth/signup', { username, email, password });
        setToken(data.access_token);
        return data;
    }

    function logout() {
        clearToken();
    }

    // User
    function getMe() { return request('GET', '/users/me'); }
    function getMyStats() { return request('GET', '/users/me/stats'); }
    function updateProfile(data) { return request('PATCH', '/users/me', data); }
    function deleteAccount() { return request('DELETE', '/users/me'); }

    // Trades
    function getTrades(limit = 100, offset = 0, marketSlug = null, source = null) {
        let path = `/trades?limit=${limit}&offset=${offset}`;
        if (marketSlug) path += `&market_slug=${encodeURIComponent(marketSlug)}`;
        if (source) path += `&source=${encodeURIComponent(source)}`;
        return request('GET', path);
    }

    function getMarkets() { return request('GET', '/trades/markets'); }
    function getProviders() { return request('GET', '/trades/providers'); }

    function uploadFile(file) {
        const fd = new FormData();
        fd.append('file', file);
        return request('POST', '/trades/upload', fd, true);
    }

    function deleteTrade(id) { return request('DELETE', `/trades/${id}`); }
    function deleteAllTrades() { return request('DELETE', '/trades'); }

    // Analysis
    function getGlobalAnalysis(filters = null) {
        return request('POST', '/analysis/global', filters);
    }

    function getMarketAnalysis(slug, filters = null) {
        return request('POST', `/analysis/market/${encodeURIComponent(slug)}`, filters);
    }

    function getAdvancedMetrics(filters = null) {
        return request('POST', '/analysis/metrics', filters);
    }

    function getMarketBreakdown(filters = null) {
        return request('POST', '/analysis/breakdown', filters);
    }

    function getTimeseries(marketSlug = null, filters = null) {
        let path = '/analysis/timeseries';
        if (marketSlug) path += `?market_slug=${encodeURIComponent(marketSlug)}`;
        return request('POST', path, filters);
    }

    // Charts
    function getPnlChart(marketSlug = null, filters = null) {
        let path = '/charts/pnl';
        if (marketSlug) path += `?market_slug=${encodeURIComponent(marketSlug)}`;
        return request('POST', path, filters);
    }

    function getPriceChart(marketSlug = null, filters = null) {
        let path = '/charts/price';
        if (marketSlug) path += `?market_slug=${encodeURIComponent(marketSlug)}`;
        return request('POST', path, filters);
    }

    function getExposureChart(marketSlug = null, filters = null) {
        let path = '/charts/exposure';
        if (marketSlug) path += `?market_slug=${encodeURIComponent(marketSlug)}`;
        return request('POST', path, filters);
    }

    function getDashboard(filters = null) {
        return request('POST', '/charts/dashboard', filters);
    }

    // Export
    function getExportUrl(format, marketSlug = null) {
        let path = `${BASE}/trades/export/${format}`;
        if (marketSlug) path += `?market_slug=${encodeURIComponent(marketSlug)}`;
        return path;
    }

    return {
        isLoggedIn, getToken, setToken, clearToken, login, signup, logout,
        getMe, getMyStats, updateProfile, deleteAccount,
        getTrades, getMarkets, getProviders, uploadFile, deleteTrade, deleteAllTrades,
        getGlobalAnalysis, getMarketAnalysis, getAdvancedMetrics, getMarketBreakdown, getTimeseries,
        getPnlChart, getPriceChart, getExposureChart, getDashboard,
        getExportUrl,
    };
})();
