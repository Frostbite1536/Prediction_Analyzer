/**
 * Authentication page logic
 */
const Auth = (() => {
    function init() {
        // Tab switching
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const isLogin = tab.dataset.tab === 'login';
                document.getElementById('login-form').classList.toggle('hidden', !isLogin);
                document.getElementById('signup-form').classList.toggle('hidden', isLogin);
                clearErrors();
            });
        });

        // Login form
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            clearErrors();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Logging in...';

            try {
                const email = document.getElementById('login-email').value.trim();
                const password = document.getElementById('login-password').value;
                await API.login(email, password);
                App.onLoginSuccess();
            } catch (err) {
                showError('login-error', err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Log In';
            }
        });

        // Signup form
        document.getElementById('signup-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            clearErrors();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Creating account...';

            try {
                const username = document.getElementById('signup-username').value.trim();
                const email = document.getElementById('signup-email').value.trim();
                const password = document.getElementById('signup-password').value;
                await API.signup(username, email, password);
                App.onLoginSuccess();
            } catch (err) {
                showError('signup-error', err.message);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Create Account';
            }
        });
    }

    function showError(id, msg) {
        const el = document.getElementById(id);
        el.textContent = msg;
        el.classList.add('visible');
    }

    function clearErrors() {
        document.querySelectorAll('.form-error').forEach(el => {
            el.textContent = '';
            el.classList.remove('visible');
        });
    }

    return { init };
})();
