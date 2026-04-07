/**
 * Upload page - file upload and provider info
 */
const Upload = (() => {
    async function render(container) {
        container.innerHTML = `
            <div class="page-header">
                <h1>Upload Trades</h1>
            </div>
            <div class="upload-layout">
                <div class="upload-section">
                    <div class="card">
                        <h2>Upload Trade File</h2>
                        <p class="muted">Supported formats: JSON, CSV, XLSX (max 10 MB)</p>
                        <div class="upload-zone" id="upload-zone">
                            <div class="upload-zone-content">
                                <span class="upload-icon">&#8593;</span>
                                <p>Drag & drop your file here, or click to browse</p>
                                <input type="file" id="file-input" accept=".json,.csv,.xlsx" class="hidden">
                            </div>
                        </div>
                        <div id="upload-progress" class="hidden">
                            <div class="progress-bar">
                                <div class="progress-fill" id="progress-fill"></div>
                            </div>
                            <p id="upload-status" class="muted"></p>
                        </div>
                        <div id="upload-result" class="hidden"></div>
                    </div>
                </div>
                <div class="upload-section">
                    <div class="card">
                        <h2>Supported Providers</h2>
                        <p class="muted">Export your trades from any of these platforms and upload the file.</p>
                        <div id="provider-list" class="provider-list">
                            <div class="provider-card">
                                <div class="provider-header">
                                    <strong>Polymarket</strong>
                                    <span class="badge badge-source">USDC</span>
                                </div>
                                <p class="muted">Export from Polymarket using your wallet address. Trades with <code>0x</code> prefix are auto-detected.</p>
                                <div class="provider-steps">
                                    <p><strong>How to export:</strong></p>
                                    <ol>
                                        <li>Go to your Polymarket profile</li>
                                        <li>Click on Trade History</li>
                                        <li>Export as CSV or JSON</li>
                                        <li>Upload the file here</li>
                                    </ol>
                                </div>
                            </div>
                            <div class="provider-card">
                                <div class="provider-header">
                                    <strong>Kalshi</strong>
                                    <span class="badge badge-source">USD</span>
                                </div>
                                <p class="muted">Export your fill history from Kalshi. Files with <code>kalshi_</code> prefix are auto-detected.</p>
                                <div class="provider-steps">
                                    <p><strong>How to export:</strong></p>
                                    <ol>
                                        <li>Go to Kalshi Portfolio page</li>
                                        <li>Navigate to Trade History</li>
                                        <li>Download as CSV</li>
                                        <li>Upload the file here</li>
                                    </ol>
                                </div>
                            </div>
                            <div class="provider-card">
                                <div class="provider-header">
                                    <strong>Limitless Exchange</strong>
                                    <span class="badge badge-source">USDC</span>
                                </div>
                                <p class="muted">Export from Limitless Exchange. Files with <code>lmts_</code> prefix are auto-detected.</p>
                            </div>
                            <div class="provider-card">
                                <div class="provider-header">
                                    <strong>Manifold Markets</strong>
                                    <span class="badge badge-source">MANA</span>
                                </div>
                                <p class="muted">Export from Manifold Markets. Play-money (MANA) trades are tracked separately.</p>
                            </div>
                        </div>
                    </div>
                    <div class="card" style="margin-top:1rem">
                        <h2>Danger Zone</h2>
                        <p class="muted">Permanently delete all your trades. This cannot be undone.</p>
                        <button id="delete-all-btn" class="btn btn-danger btn-small">Delete All Trades</button>
                    </div>
                </div>
            </div>
        `;

        setupUpload();
        setupDeleteAll();
    }

    function setupUpload() {
        const zone = document.getElementById('upload-zone');
        const input = document.getElementById('file-input');

        zone.addEventListener('click', () => input.click());

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                handleFile(e.dataTransfer.files[0]);
            }
        });

        input.addEventListener('change', () => {
            if (input.files.length) {
                handleFile(input.files[0]);
            }
        });
    }

    async function handleFile(file) {
        const maxSize = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxSize) {
            App.toast('File too large (max 10 MB)', 'error');
            return;
        }

        const validExts = ['.json', '.csv', '.xlsx'];
        const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
        if (!validExts.includes(ext)) {
            App.toast('Unsupported file type. Use JSON, CSV, or XLSX.', 'error');
            return;
        }

        const progress = document.getElementById('upload-progress');
        const fill = document.getElementById('progress-fill');
        const statusEl = document.getElementById('upload-status');
        const result = document.getElementById('upload-result');

        progress.classList.remove('hidden');
        result.classList.add('hidden');
        fill.style.width = '30%';
        statusEl.textContent = `Uploading ${file.name}...`;

        try {
            fill.style.width = '60%';
            const data = await API.uploadFile(file);
            fill.style.width = '100%';
            statusEl.textContent = 'Upload complete!';

            result.classList.remove('hidden');
            result.innerHTML = `
                <div class="upload-success">
                    <strong>${data.message}</strong>
                    <p>File: ${escapeHtml(data.filename)}</p>
                    <div class="upload-actions">
                        <a href="#dashboard" class="btn btn-primary btn-small">View Dashboard</a>
                        <a href="#trades" class="btn btn-outline btn-small">View Trades</a>
                    </div>
                </div>
            `;
        } catch (err) {
            fill.style.width = '100%';
            fill.classList.add('error');
            statusEl.textContent = 'Upload failed';
            result.classList.remove('hidden');
            result.innerHTML = `<div class="upload-error">${escapeHtml(err.message)}</div>`;
        }
    }

    function setupDeleteAll() {
        document.getElementById('delete-all-btn').addEventListener('click', async () => {
            if (!confirm('Are you sure you want to delete ALL your trades? This cannot be undone.')) return;
            if (!confirm('Really? This will permanently remove all trade data.')) return;

            try {
                const data = await API.deleteAllTrades();
                App.toast(data.message, 'success');
            } catch (err) {
                App.toast(err.message, 'error');
            }
        });
    }

    return { render };
})();
