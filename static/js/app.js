/**
 * Data Scraper & IM Pusher - Web Interface
 * Refactored with DaisyUI
 */

const API_BASE = '';

// ==================== Utility Functions ====================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const template = document.getElementById('toast-template');
    if (!template) return; // Guard
    
    const clone = template.content.cloneNode(true);
    const toastEl = clone.querySelector('.alert');
    
    // Alert types: alert-info, alert-success, alert-warning, alert-error
    let alertType = 'alert-info';
    if (type === 'success') alertType = 'alert-success';
    if (type === 'error') alertType = 'alert-error';
    if (type === 'warning') alertType = 'alert-warning';
    toastEl.classList.add(alertType);

    if (type === 'success') {
        const icon = clone.querySelector('.icon-success');
        if (icon) icon.classList.remove('hidden');
    }
    if (type === 'error') {
        const icon = clone.querySelector('.icon-error');
        if (icon) icon.classList.remove('hidden');
    }

    clone.querySelector('.toast-message').textContent = message;

    container.appendChild(clone);

    // Auto remove
    setTimeout(() => {
        toastEl.classList.add('opacity-0', 'transition-opacity', 'duration-500');
        setTimeout(() => toastEl.remove(), 500);
    }, 3000);
}

async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(API_BASE + url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }
        return await response.json();
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

function parseJSON(str, defaultValue = {}) {
    if (!str || !str.trim()) return defaultValue;
    try {
        return JSON.parse(str);
    } catch {
        return defaultValue;
    }
}

function parseHeadersRaw(text) {
    const obj = {};
    if (!text) return obj;
    const lines = text.split('\n');
    for (let line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        const idx = trimmed.indexOf(':');
        if (idx === -1) continue;
        const key = trimmed.slice(0, idx).trim();
        const value = trimmed.slice(idx + 1).trim();
        if (!key) continue;
        obj[key] = value;
    }
    return obj;
}

function buildHeadersRaw(obj) {
    if (!obj || typeof obj !== 'object') return '';
    const lines = [];
    for (const k of Object.keys(obj)) {
        lines.push(`${k}: ${obj[k]}`);
    }
    return lines.join('\n');
}

// ==================== Tab Navigation ====================

function showTab(tabName) {
    // Hide all content
    document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
    
    // Remove active from all menu items
    document.querySelectorAll('[id^="menu-"]').forEach(el => el.classList.remove('active'));

    // Show selected content
    const content = document.getElementById(`content-${tabName}`);
    if (content) content.classList.remove('hidden');

    // Activate menu item
    const menu = document.getElementById(`menu-${tabName}`);
    if (menu) menu.classList.add('active');

    // Close drawer on mobile if open
    const drawerCheckbox = document.getElementById('my-drawer-2');
    if (window.innerWidth < 1024 && drawerCheckbox.checked) {
        drawerCheckbox.checked = false;
    }

    // Load data for the tab
    if (tabName === 'templates') loadTemplates();
    else if (tabName === 'push') loadPushConfigs();
    else if (tabName === 'history') {
        const startInput = document.getElementById('hist-start-time');
        const endInput = document.getElementById('hist-end-time');
        if (startInput && endInput && (!startInput.value || !endInput.value)) {
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, '0');
            const d = String(now.getDate()).padStart(2, '0');
            startInput.value = `${y}-${m}-${d}T00:00`;
            endInput.value = `${y}-${m}-${d}T23:59`;
        }
        loadHistory();
    }
    else if (tabName === 'test') loadTestTemplates();
    else if (tabName === 'settings') { loadProxies(); loadHeaderGroups(); }
    else if (tabName === 'batch') loadBatchTasks();
}

// ==================== Templates ====================

let templates = [];

async function loadTemplates() {
    try {
        const singles = await fetchAPI('/api/templates');
        let workflows = [];
        try {
            workflows = await fetchAPI('/api/workflows');
        } catch (e) { workflows = []; }
        templates = [
            ...singles.map(t => ({...t, __type: 'single'})),
            ...workflows.map(w => ({...w, __type: 'workflow'})),
        ];
        renderTemplates();
    } catch (e) {
        console.error('Failed to load templates:', e);
    }
}

function renderTemplates() {
    const container = document.getElementById('templates-list');
    container.innerHTML = '';

    if (templates.length === 0) {
        const tpl = document.getElementById('template-empty');
        if (tpl) container.appendChild(tpl.content.cloneNode(true));
        return;
    }

    const tpl = document.getElementById('template-card');
    if (!tpl) return;

    templates.forEach(t => {
        const clone = tpl.content.cloneNode(true);
        
        const nameEl = clone.querySelector('.template-name');
        nameEl.textContent = t.name;
        nameEl.title = t.name;
        
        const methodEl = clone.querySelector('.template-method');
        if (t.__type === 'workflow') {
            methodEl.textContent = 'WORKFLOW';
            methodEl.classList.add('badge-warning');
        } else {
            methodEl.textContent = t.method;
            methodEl.classList.add(t.method === 'GET' ? 'badge-success' : 'badge-info');
        }
        
        const descEl = clone.querySelector('.template-desc');
        descEl.textContent = t.description || '无描述';
        
        const urlEl = clone.querySelector('.template-url');
        if (t.__type === 'workflow') {
            urlEl.textContent = '(组合模板)';
            urlEl.title = 'Workflow composed of templates';
        } else {
            urlEl.textContent = t.url;
            urlEl.title = t.url;
        }
        
        clone.querySelector('.btn-edit').onclick = () => editTemplate(t.id, t.__type);
        clone.querySelector('.btn-delete').onclick = () => deleteTemplate(t.id, t.__type);
        
        container.appendChild(clone);
    });
}

// ==================== Settings (Proxies Management) ====================

async function loadProxies() {
    try {
        const listEl = document.getElementById('proxies-list');
        if (!listEl) return;
        const proxies = await fetchAPI('/api/configs/proxies');
        listEl.innerHTML = '';
        if (!proxies || proxies.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-base-content/60';
            empty.textContent = '暂无代理';
            listEl.appendChild(empty);
            return;
        }
        proxies.forEach(p => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-3 border border-base-200 rounded-box';
            const left = document.createElement('div');
            left.innerHTML = `<div class="font-medium">${p.name}</div><div class="text-xs opacity-70 font-mono">${p.scheme}://${p.ip}:${p.port} ${p.enabled ? '' : '[禁用]'}</div>`;
            const actions = document.createElement('div');
            actions.className = 'flex gap-2';
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm';
            editBtn.textContent = '编辑';
            editBtn.onclick = () => fillProxyForm(p);
            const delBtn = document.createElement('button');
            delBtn.className = 'btn btn-sm btn-error';
            delBtn.textContent = '删除';
            delBtn.onclick = () => deleteProxyItem(p.id);
            actions.appendChild(editBtn);
            actions.appendChild(delBtn);
            item.appendChild(left);
            item.appendChild(actions);
            listEl.appendChild(item);
        });
    } catch (e) {
        console.error('Failed to load proxies:', e);
    }
}

function resetProxyForm() {
    const idEl = document.getElementById('proxy-id');
    const nameEl = document.getElementById('proxy-name');
    const schemeEl = document.getElementById('proxy-scheme');
    const enabledEl = document.getElementById('proxy-enabled');
    const ipEl = document.getElementById('proxy-ip');
    const portEl = document.getElementById('proxy-port');
    if (!idEl) return;
    idEl.value = '';
    nameEl.value = '';
    schemeEl.value = 'http';
    enabledEl.checked = true;
    ipEl.value = '';
    portEl.value = '';
}

function fillProxyForm(p) {
    document.getElementById('proxy-id').value = p.id;
    document.getElementById('proxy-name').value = p.name;
    document.getElementById('proxy-scheme').value = p.scheme || 'http';
    document.getElementById('proxy-enabled').checked = !!p.enabled;
    document.getElementById('proxy-ip').value = p.ip || '';
    document.getElementById('proxy-port').value = p.port || '';
}

async function saveProxyItem() {
    const id = document.getElementById('proxy-id').value;
    const name = document.getElementById('proxy-name').value.trim();
    const scheme = document.getElementById('proxy-scheme').value || 'http';
    const enabled = document.getElementById('proxy-enabled').checked;
    const ip = document.getElementById('proxy-ip').value.trim();
    const port = Number(document.getElementById('proxy-port').value);
    if (!name || !ip || !port) {
        showToast('请填写名称、IP 和端口', 'error');
        return;
    }
    try {
        const payload = { name, scheme, enabled, ip, port };
        if (id) {
            await fetchAPI(`/api/configs/proxies/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            showToast('代理已更新');
        } else {
            await fetchAPI('/api/configs/proxies', { method: 'POST', body: JSON.stringify(payload) });
            showToast('代理已创建');
        }
        resetProxyForm();
        loadProxies();
    } catch (e) {
        console.error('Save proxy failed:', e);
    }
}

async function deleteProxyItem(id) {
    if (!await showConfirm('确定要删除这个代理吗？')) return;
    try {
        await fetchAPI(`/api/configs/proxies/${id}`, { method: 'DELETE' });
        showToast('代理已删除');
        loadProxies();
    } catch (e) {
        console.error('Delete proxy failed:', e);
    }
}

// ==================== Settings (Header Groups Management) ====================

async function loadHeaderGroups() {
    try {
        const listEl = document.getElementById('header-groups-list');
        const proxySelect = document.getElementById('header-group-proxy');
        if (proxySelect) {
            proxySelect.innerHTML = '<option value="">不关联代理</option>';
            const proxies = await fetchAPI('/api/configs/proxies');
            proxies.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.scheme}://${p.ip}:${p.port})${p.enabled ? '' : ' [禁用]'}`;
                proxySelect.appendChild(opt);
            });
        }
        if (!listEl) return;
        const groups = await fetchAPI('/api/configs/header-groups');
        listEl.innerHTML = '';
        if (!groups || groups.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-base-content/60';
            empty.textContent = '暂无 Header 组';
            listEl.appendChild(empty);
            return;
        }
        groups.forEach(g => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-3 border border-base-200 rounded-box';
            const left = document.createElement('div');
            const proxyMark = g.proxy_config_id ? ' [已关联代理]' : '';
            const headersText = buildHeadersRaw(g.headers || {});
            left.innerHTML = `<div class="font-medium">${g.name}${proxyMark}</div><div class="text-xs opacity-70 font-mono break-all whitespace-pre-wrap">${headersText || ''}</div>`;
            const actions = document.createElement('div');
            actions.className = 'flex gap-2';
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm';
            editBtn.textContent = '编辑';
            editBtn.onclick = () => fillHeaderGroupForm(g);
            const delBtn = document.createElement('button');
            delBtn.className = 'btn btn-sm btn-error';
            delBtn.textContent = '删除';
            delBtn.onclick = () => deleteHeaderGroupItem(g.id);
            actions.appendChild(editBtn);
            actions.appendChild(delBtn);
            item.appendChild(left);
            item.appendChild(actions);
            listEl.appendChild(item);
        });
    } catch (e) {
        console.error('Failed to load header groups:', e);
    }
}

function resetHeaderGroupForm() {
    const idEl = document.getElementById('header-group-id');
    if (!idEl) return;
    document.getElementById('header-group-name').value = '';
    document.getElementById('header-group-headers').value = '';
    document.getElementById('header-group-proxy').value = '';
    idEl.value = '';
}

function fillHeaderGroupForm(g) {
    document.getElementById('header-group-id').value = g.id;
    document.getElementById('header-group-name').value = g.name || '';
    document.getElementById('header-group-headers').value = buildHeadersRaw(g.headers || {});
    const proxyEl = document.getElementById('header-group-proxy');
    if (proxyEl) proxyEl.value = g.proxy_config_id || '';
}

async function saveHeaderGroupItem() {
    const id = document.getElementById('header-group-id').value;
    const name = document.getElementById('header-group-name').value.trim();
    const headers = parseHeadersRaw(document.getElementById('header-group-headers').value);
    const proxy_config_id = (function () {
        const v = document.getElementById('header-group-proxy')?.value;
        return v ? v : null;
    })();
    if (!name) {
        showToast('请填写名称', 'error');
        return;
    }
    try {
        const payload = { name, headers, proxy_config_id };
        if (id) {
            await fetchAPI(`/api/configs/header-groups/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            showToast('Header 组已更新');
        } else {
            await fetchAPI('/api/configs/header-groups', { method: 'POST', body: JSON.stringify(payload) });
            showToast('Header 组已创建');
        }
        resetHeaderGroupForm();
        loadHeaderGroups();
    } catch (e) {
        console.error('Save header group failed:', e);
    }
}

async function deleteHeaderGroupItem(id) {
    if (!await showConfirm('确定要删除这个 Header 组吗？')) return;
    try {
        await fetchAPI(`/api/configs/header-groups/${id}`, { method: 'DELETE' });
        showToast('Header 组已删除');
        loadHeaderGroups();
    } catch (e) {
        console.error('Delete header group failed:', e);
    }
}
// Modal Helpers
function getModal(id) {
    return document.getElementById(id);
}

function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirm_modal');
        const msgEl = document.getElementById('confirm-message');
        const okBtn = document.getElementById('confirm-ok-btn');
        const cancelBtn = document.getElementById('confirm-cancel-btn');
        
        msgEl.textContent = message || '确定要执行此操作吗？';
        
        let resolved = false;
        
        const finish = (result) => {
            if (resolved) return;
            resolved = true;
            modal.close();
            resolve(result);
        };
        
        okBtn.onclick = () => finish(true);
        cancelBtn.onclick = () => finish(false);
        
        // Handle backdrop click / ESC
        modal.onclose = () => {
            if (!resolved) {
                resolved = true;
                resolve(false);
            }
        };
        
        modal.showModal();
    });
}

function openTemplateModal(template = null) {
    const modal = getModal('template_modal');
    document.getElementById('template-modal-title').textContent = template ? '编辑业务模板' : '新建业务模板';

    document.getElementById('template-id').value = template?.id || '';
    const type = template?.__type || document.querySelector('input[name="template-type"]:checked')?.value || 'single';
    const typeRadio = document.querySelector(`input[name="template-type"][value="${type}"]`);
    if (typeRadio) typeRadio.checked = true;
    toggleTemplateType();

    if (type === 'workflow') {
        document.getElementById('workflow-name').value = template?.name || '';
        document.getElementById('workflow-description').value = template?.description || '';
        document.getElementById('workflow-definition').value = template?.definition ? JSON.stringify(template.definition, null, 2) : '';
    } else {
        document.getElementById('template-name').value = template?.name || '';
        document.getElementById('template-description').value = template?.description || '';
        document.getElementById('template-url').value = template?.url || '';
        document.getElementById('template-method').value = template?.method || 'GET';
        document.getElementById('template-headers').value = template?.headers ? buildHeadersRaw(template.headers) : '';
        document.getElementById('template-params').value = template?.default_params ? JSON.stringify(template.default_params, null, 2) : '';
        document.getElementById('template-body').value = typeof template?.body_template === 'object' ? JSON.stringify(template.body_template, null, 2) : (template?.body_template || '');
    }

    // Init body type from headers or body content
    (function () {
        if (type === 'workflow') return;
        let bodyType = 'json';
        const headers = template?.headers || {};
        for (const k in headers) {
            if (k && k.toLowerCase() === 'content-type') {
                const v = (headers[k] || '').toLowerCase();
                if (v.includes('application/x-www-form-urlencoded')) bodyType = 'form';
                else bodyType = 'json';
                break;
            }
        }
        if (!template) {
            bodyType = 'json';
        } else if (!headers || Object.keys(headers).length === 0) {
            const val = document.getElementById('template-body').value.trim();
            try { JSON.parse(val); bodyType = 'json'; } catch { bodyType = 'form'; }
        }
        const radio = document.querySelector(`input[name="body-type"][value="${bodyType}"]`);
        if (radio) radio.checked = true;
    })();

    // Set extract type (only for single template)
    if (type === 'single') {
        const extractType = template?.extract_type || 'python';
        document.querySelector(`input[name="extract-type"][value="${extractType}"]`).checked = true;
        document.getElementById('template-jsonpath').value = template?.json_path || '';
        document.getElementById('template-parser').value = template?.parser_code || '';
        toggleExtractType();
    }
    
    // Load proxy options and set selected
    (async function () {
        try {
            if (type === 'workflow') return;
            const selectEl = document.getElementById('template-header-group');
            if (!selectEl) return;
            selectEl.innerHTML = '<option value="">不使用 Header 组</option>';
            const groups = await fetchAPI('/api/configs/header-groups');
            groups.forEach(g => {
                const opt = document.createElement('option');
                opt.value = g.id;
                opt.textContent = g.proxy_config_id ? `${g.name} [关联代理]` : g.name;
                selectEl.appendChild(opt);
            });
            if (template?.header_group_id) {
                selectEl.value = template.header_group_id;
            }
        } catch (e) {
            console.error('Failed to load header groups:', e);
        }
    })();
    
    modal.showModal();
}

function closeTemplateModal(event) {
    if (event) event.preventDefault();
    getModal('template_modal').close();
}

async function saveTemplate() {
    const id = document.getElementById('template-id').value;
    const type = document.querySelector('input[name="template-type"]:checked')?.value || 'single';
    if (type === 'workflow') {
        const name = document.getElementById('workflow-name').value.trim();
        const description = document.getElementById('workflow-description').value.trim();
        const definition = parseJSON(document.getElementById('workflow-definition').value, null);
        if (!name || !definition || typeof definition !== 'object') {
            showToast('请填写工作流名称与合法的定义JSON', 'error');
            return;
        }
        try {
            const payload = { name, description, definition };
            if (id) {
                await fetchAPI(`/api/workflows/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
                showToast('工作流模板已更新');
            } else {
                await fetchAPI('/api/workflows', { method: 'POST', body: JSON.stringify(payload) });
                showToast('工作流模板已创建');
            }
            closeTemplateModal();
            loadTemplates();
        } catch (e) {
            console.error('Save workflow failed:', e);
        }
        return;
    }
    const bodyType = document.querySelector('input[name="body-type"]:checked')?.value || 'json';
    let headersObj = parseHeadersRaw(document.getElementById('template-headers').value);
    if (typeof headersObj !== 'object' || headersObj === null) headersObj = {};
    headersObj['Content-Type'] = bodyType === 'form' ? 'application/x-www-form-urlencoded' : 'application/json';
    const data = {
        name: document.getElementById('template-name').value,
        description: document.getElementById('template-description').value,
        url: document.getElementById('template-url').value,
        method: document.getElementById('template-method').value,
        headers: headersObj,
        default_params: parseJSON(document.getElementById('template-params').value),
        body_template: (function () {
            const val = document.getElementById('template-body').value.trim();
            try { return JSON.parse(val); } catch { return val || null; }
        })(),
        extract_type: document.querySelector('input[name="extract-type"]:checked').value,
        json_path: document.getElementById('template-jsonpath').value || null,
        parser_code: document.getElementById('template-parser').value || null,
        header_group_id: (function () {
            const v = document.getElementById('template-header-group')?.value;
            return v ? v : null;
        })()
    };

    try {
        if (id) {
            await fetchAPI(`/api/templates/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('模板更新成功');
        } else {
            await fetchAPI('/api/templates', { method: 'POST', body: JSON.stringify(data) });
            showToast('模板创建成功');
        }
        closeTemplateModal();
        loadTemplates();
    } catch (e) {
        console.error('Save failed:', e);
    }
}

async function editTemplate(id, type = 'single') {
    const template = templates.find(t => t.id === id && t.__type === type);
    if (template) openTemplateModal(template);
}

async function deleteTemplate(id, type = 'single') {
    if (!await showConfirm('确定要删除这个模板吗？')) return;
    try {
        if (type === 'workflow') {
            await fetchAPI(`/api/workflows/${id}`, { method: 'DELETE' });
            showToast('工作流模板已删除');
        } else {
            await fetchAPI(`/api/templates/${id}`, { method: 'DELETE' });
            showToast('模板已删除');
        }
        loadTemplates();
    } catch (e) {
        console.error('Delete failed:', e);
    }
}

function toggleExtractType() {
    const checkedInput = document.querySelector('input[name="extract-type"]:checked');
    const type = checkedInput ? checkedInput.value : 'python';

    const pythonArea = document.getElementById('parser-python-area');
    const jsonPathArea = document.getElementById('parser-jsonpath-area');

    if (type === 'python') {
        pythonArea.classList.remove('hidden');
        jsonPathArea.classList.add('hidden');
    } else {
        pythonArea.classList.add('hidden');
        jsonPathArea.classList.remove('hidden');
    }
}

function toggleTemplateType() {
    const type = document.querySelector('input[name="template-type"]:checked')?.value || 'single';
    const singleArea = document.getElementById('single-template-area');
    const wfArea = document.getElementById('workflow-template-area');
    if (singleArea) singleArea.classList.toggle('hidden', type !== 'single');
    if (wfArea) wfArea.classList.toggle('hidden', type !== 'workflow');
    const parserPy = document.getElementById('parser-python-area');
    const parserJson = document.getElementById('parser-jsonpath-area');
    const extractTypeRadios = document.querySelectorAll('input[name="extract-type"]');
    if (type === 'workflow') {
        if (parserPy) parserPy.classList.add('hidden');
        if (parserJson) parserJson.classList.add('hidden');
        extractTypeRadios.forEach(r => r.disabled = true);
    } else {
        extractTypeRadios.forEach(r => r.disabled = false);
        toggleExtractType();
    }
}

// ==================== cURL Parser ====================

function toggleCurlInput() {
    const area = document.getElementById('curl-parser-area');
    area.classList.toggle('hidden');
    if (!area.classList.contains('hidden')) {
        document.getElementById('curl-input').focus();
    }
}

function parseAndFillCurl() {
    const curl = document.getElementById('curl-input').value.trim();
    if (!curl) {
        showToast('请输入 cURL 内容', 'error');
        return;
    }

    try {
        // 1. Normalize line breaks and backslashes
        let normalized = curl.replace(/\\\n/g, ' ').replace(/\n/g, ' ');

        // 2. Tokenize (respecting quotes)
        const tokens = [];
        let current = '';
        let inQuote = false;
        let quoteChar = '';

        for (let i = 0; i < normalized.length; i++) {
            const char = normalized[i];
            if (char === "'" || char === '"') {
                if (!inQuote) {
                    inQuote = true;
                    quoteChar = char;
                } else if (char === quoteChar) {
                    inQuote = false;
                    quoteChar = '';
                } else {
                    current += char;
                }
            } else if (char === ' ' && !inQuote) {
                if (current) {
                    tokens.push(current);
                    current = '';
                }
            } else {
                current += char;
            }
        }
        if (current) tokens.push(current);

        // 3. Extract info
        let url = '';
        let method = 'GET';
        let headers = {};
        let body = null;
        let cookies = [];

        for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];
            const nextToken = tokens[i + 1];

            if (token === '-X' || token === '--request') {
                method = nextToken.toUpperCase();
                i++;
            } else if (token === '-H' || token === '--header') {
                const headerParts = nextToken.split(':');
                if (headerParts.length >= 2) {
                    const key = headerParts[0].trim();
                    const value = headerParts.slice(1).join(':').trim();
                    headers[key] = value;
                }
                i++;
            } else if (token === '-b' || token === '--cookie') {
                if (nextToken) {
                    let val = nextToken.trim();
                    if (val.toLowerCase().startsWith('cookie:')) val = val.slice(7).trim();
                    cookies.push(val);
                }
                i++;
            } else if (token.startsWith('-b=')) {
                let val = token.slice(3).trim();
                if (val.toLowerCase().startsWith('cookie:')) val = val.slice(7).trim();
                cookies.push(val);
            } else if (token.startsWith('--cookie=')) {
                let val = token.slice(9).trim();
                if (val.toLowerCase().startsWith('cookie:')) val = val.slice(7).trim();
                cookies.push(val);
            } else if (token === '-d' || token === '--data' || token === '--data-raw' || token === '--data-binary') {
                body = nextToken;
                method = 'POST'; // Usually data implies POST unless specified
                i++;
            } else if (token.startsWith('http') && !url) {
                url = token;
            } else if (i === 1 && !url && !token.startsWith('-')) {
                // Curl command often has URL as the second token if first is 'curl'
                url = token;
            }
        }

        if (cookies.length > 0) {
            const normalizedCookies = cookies.join('; ').split(';').map(s => s.trim()).filter(Boolean).join('; ');
            headers['Cookie'] = normalizedCookies;
        }

        // 4. Fill form
        if (url) document.getElementById('template-url').value = url;
        document.getElementById('template-method').value = method;
        if (Object.keys(headers).length > 0) {
            document.getElementById('template-headers').value = buildHeadersRaw(headers);
        }
        if (body) {
            try {
                // Try to parse body as JSON for better display
                const jsonBody = JSON.parse(body);
                document.getElementById('template-body').value = JSON.stringify(jsonBody, null, 2);
                const radio = document.querySelector('input[name="body-type"][value="json"]');
                if (radio) radio.checked = true;
            } catch {
                // If not JSON, just put as is (Form format)
                document.getElementById('template-body').value = body;
                const radio = document.querySelector('input[name="body-type"][value="form"]');
                if (radio) radio.checked = true;
            }
        }
        (function () {
            for (const k in headers) {
                if (k && k.toLowerCase() === 'content-type') {
                    const v = (headers[k] || '').toLowerCase();
                    const t = v.includes('application/x-www-form-urlencoded') ? 'form' : 'json';
                    const radio = document.querySelector(`input[name="body-type"][value="${t}"]`);
                    if (radio) radio.checked = true;
                    break;
                }
            }
        })();

        showToast('cURL 解析成功，已填充表单');
        toggleCurlInput(); // Hide area
        document.getElementById('curl-input').value = ''; // Clear input
    } catch (e) {
        console.error('Parsing failed:', e);
        showToast('cURL 解析失败: ' + e.message, 'error');
    }
}

// ==================== Push Configs ====================

let pushConfigs = [];

async function loadPushConfigs() {
    try {
        pushConfigs = await fetchAPI('/api/configs/push');
        renderPushConfigs();
    } catch (e) {
        console.error('Failed to load push configs:', e);
    }
}

function renderPushConfigs() {
    const container = document.getElementById('push-list');
    container.innerHTML = '';

    if (pushConfigs.length === 0) {
        const tpl = document.getElementById('push-empty');
        if (tpl) container.appendChild(tpl.content.cloneNode(true));
        return;
    }

    const tpl = document.getElementById('push-card');
    if (!tpl) return;

    pushConfigs.forEach(p => {
        const clone = tpl.content.cloneNode(true);
        
        clone.querySelector('.push-name').textContent = p.name;
        
        const badge = clone.querySelector('.push-channel');
        badge.textContent = p.channel === 'feishu' ? '飞书' : 'Discord';
        badge.classList.add(p.channel === 'feishu' ? 'badge-info' : 'badge-secondary');
        
        const urlEl = clone.querySelector('.push-url');
        urlEl.textContent = p.webhook_url;
        urlEl.title = p.webhook_url;
        
        clone.querySelector('.btn-edit').onclick = () => openPushModal(p);
        clone.querySelector('.btn-test').onclick = () => openPushTestModal(p.id);
        clone.querySelector('.btn-delete').onclick = () => deletePushConfig(p.id);
        
        container.appendChild(clone);
    });
}

function openPushModal(config) {
    const modal = getModal('push_modal');
    const titleEl = document.getElementById('push-modal-title');
    if (config) {
        titleEl.textContent = '编辑推送配置';
        document.getElementById('push-id').value = config.id;
        document.getElementById('push-name').value = config.name || '';
        document.getElementById('push-channel').value = config.channel || 'feishu';
        document.getElementById('push-webhook').value = config.webhook_url || '';
    } else {
        titleEl.textContent = '新建推送配置';
        document.getElementById('push-id').value = '';
        document.getElementById('push-name').value = '';
        document.getElementById('push-channel').value = 'feishu';
        document.getElementById('push-webhook').value = '';
    }
    modal.showModal();
}

function closePushModal(event) {
    if (event) event.preventDefault();
    getModal('push_modal').close();
}

async function savePushConfig() {
    const id = document.getElementById('push-id').value;
    const data = {
        name: document.getElementById('push-name').value,
        channel: document.getElementById('push-channel').value,
        webhook_url: document.getElementById('push-webhook').value
    };

    try {
        if (id) {
            await fetchAPI(`/api/configs/push/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            showToast('推送配置更新成功');
        } else {
            await fetchAPI('/api/configs/push', { method: 'POST', body: JSON.stringify(data) });
            showToast('推送配置创建成功');
        }
        closePushModal();
        loadPushConfigs();
    } catch (e) {
        console.error('Save failed:', e);
    }
}

async function deletePushConfig(id) {
    if (!await showConfirm('确定要删除这个推送配置吗？')) return;
    try {
        await fetchAPI(`/api/configs/push/${id}`, { method: 'DELETE' });
        showToast('推送配置已删除');
        loadPushConfigs();
    } catch (e) {
        console.error('Delete failed:', e);
    }
}

function openPushTestModal(id) {
    const modal = getModal('push_test_modal');
    document.getElementById('push-test-id').value = id;
    document.getElementById('push-test-content').value = 'Test message from Scraper Admin';
    modal.showModal();
}

function closePushTestModal(event) {
    if (event) event.preventDefault();
    getModal('push_test_modal').close();
}

async function sendPushTest() {
    const id = document.getElementById('push-test-id').value;
    const content = document.getElementById('push-test-content').value;
    
    if (!content) {
        showToast('请输入测试消息内容', 'warning');
        return;
    }

    try {
        await fetchAPI('/api/push', {
            method: 'POST',
            body: JSON.stringify({
                config_id: id,
                message: content
            })
        });
        showToast('测试消息推送成功');
        closePushTestModal();
    } catch (e) {
        console.error('Test push failed:', e);
    }
}

// ==================== History ====================

let scrapeHistory = [];
let historyPage = 1;
let historyPageSize = 10;
let historyTotal = 0;
let historyTotalPages = 1;

async function loadHistory(page = 1) {
    try {
        historyPage = page;
        
        // Get filters
        const keyword = document.getElementById('hist-search-keyword')?.value || '';
        const method = document.getElementById('hist-filter-method')?.value || '';
        const status = document.getElementById('hist-filter-status')?.value || '';
        const startTime = document.getElementById('hist-start-time')?.value || '';
        const endTime = document.getElementById('hist-end-time')?.value || '';
        
        const params = new URLSearchParams({
            page: historyPage,
            size: historyPageSize
        });
        
        if (keyword) params.append('keyword', keyword);
        if (method) params.append('method', method);
        if (status) params.append('status', status);
        if (startTime) params.append('start_time', startTime);
        if (endTime) params.append('end_time', endTime);
        
        const res = await fetchAPI(`/api/scrape/history?${params.toString()}`);
        
        // Handle response
        scrapeHistory = res.items;
        historyTotal = res.total;
        historyTotalPages = res.pages;
        
        renderHistory();
        renderHistoryPagination();
        
    } catch (e) {
        console.error('Failed to load history:', e);
        showToast('加载历史记录失败', 'error');
    }
}

function renderHistoryPagination() {
    const prevBtn = document.getElementById('hist-prev-btn');
    const nextBtn = document.getElementById('hist-next-btn');
    const currentEl = document.getElementById('hist-current-page');
    const totalPagesEl = document.getElementById('hist-total-pages');
    const totalCountEl = document.getElementById('hist-total-count');
    
    if (prevBtn) prevBtn.disabled = historyPage <= 1;
    if (nextBtn) nextBtn.disabled = historyPage >= historyTotalPages;
    if (currentEl) currentEl.textContent = historyPage;
    if (totalPagesEl) totalPagesEl.textContent = Math.max(1, historyTotalPages);
    if (totalCountEl) totalCountEl.textContent = historyTotal;
}

function changeHistoryPage(delta) {
    const newPage = historyPage + delta;
    if (newPage >= 1 && newPage <= historyTotalPages) {
        loadHistory(newPage);
    }
}

async function clearHistory() {
    if (!await showConfirm('确定要清空所有抓取历史吗？此操作不可恢复。')) return;
    try {
        await fetchAPI('/api/scrape/history', { method: 'DELETE' });
        showToast('历史记录已清空');
        loadHistory(1);
    } catch (e) {
        console.error('Failed to clear history:', e);
    }
}

function renderHistory() {
    const container = document.getElementById('history-list');
    container.innerHTML = '';

    if (scrapeHistory.length === 0) {
        const tpl = document.getElementById('history-empty');
        if (tpl) container.appendChild(tpl.content.cloneNode(true));
        return;
    }

    const tpl = document.getElementById('history-row');
    if (!tpl) return;

    scrapeHistory.forEach(h => {
        const clone = tpl.content.cloneNode(true);
        
        const statusBadge = clone.querySelector('.hist-status');
        statusBadge.textContent = h.success ? '成功' : '失败';
        statusBadge.classList.add(h.success ? 'badge-success' : 'badge-error');
        
        clone.querySelector('.hist-name').textContent = h.template_name || '高级模式';
        
        const urlEl = clone.querySelector('.hist-url');
        urlEl.textContent = h.url;
        urlEl.title = h.url;
        
        clone.querySelector('.hist-method').textContent = h.method;
        clone.querySelector('.hist-time').textContent = new Date(h.created_at).toLocaleString();
        
        clone.querySelector('.btn-view').onclick = () => viewHistoryResult(h.id);
        
        container.appendChild(clone);
    });
}

function viewHistoryResult(id) {
    const item = scrapeHistory.find(h => h.id === id);
    if (!item) return;

    const modal = getModal('history_modal');
    
    document.getElementById('hist-tpl-name').textContent = item.template_name || '高级模式 (自定义)';
    document.getElementById('hist-method').textContent = item.method;
    document.getElementById('hist-time').textContent = new Date(item.created_at).toLocaleString();
    
    const statusEl = document.getElementById('hist-status');
    if (item.success) {
        statusEl.innerHTML = '<span class="badge badge-success">成功</span>';
    } else {
        statusEl.innerHTML = '<span class="badge badge-error">失败</span>';
    }
    
    document.getElementById('hist-url').textContent = item.url;

    // Error
    const errorArea = document.getElementById('hist-error-area');
    if (item.error_message) {
        errorArea.classList.remove('hidden');
        document.getElementById('hist-error-msg').textContent = item.error_message;
    } else {
        errorArea.classList.add('hidden');
    }

    // Data
    const dataArea = document.getElementById('hist-data-area');
    const dataCode = document.getElementById('hist-data-code');
    
    if (item.success && item.response_data) {
        dataArea.classList.remove('hidden');
        try {
            const jsonObj = typeof item.response_data === 'string' ? JSON.parse(item.response_data) : item.response_data;
            dataCode.textContent = JSON.stringify(jsonObj, null, 2);
        } catch {
            dataCode.textContent = item.response_data;
        }
        if (window.Prism) {
            Prism.highlightElement(dataCode);
        }
    } else {
        dataArea.classList.add('hidden');
    }

    const reqHeadersCode = document.getElementById('hist-req-headers-code');
    const reqParamsCode = document.getElementById('hist-req-params-code');
    const reqBodyCode = document.getElementById('hist-req-body-code');
    const rawArea = document.getElementById('hist-raw-area');
    const rawCode = document.getElementById('hist-raw-code');

    try {
        const headersObj = typeof item.request_headers === 'string' ? JSON.parse(item.request_headers) : (item.request_headers || {});
        reqHeadersCode.textContent = JSON.stringify(headersObj, null, 2);
    } catch {
        reqHeadersCode.textContent = item.request_headers || '';
    }
    if (window.Prism) Prism.highlightElement(reqHeadersCode);

    try {
        const paramsObj = typeof item.request_params === 'string' ? JSON.parse(item.request_params) : (item.request_params || {});
        reqParamsCode.textContent = JSON.stringify(paramsObj, null, 2);
    } catch {
        reqParamsCode.textContent = item.request_params || '';
    }
    if (window.Prism) Prism.highlightElement(reqParamsCode);

    try {
        const bodyVal = item.request_body;
        if (typeof bodyVal === 'string') {
            try {
                reqBodyCode.textContent = JSON.stringify(JSON.parse(bodyVal), null, 2);
            } catch {
                reqBodyCode.textContent = bodyVal;
            }
        } else {
            reqBodyCode.textContent = JSON.stringify(bodyVal || {}, null, 2);
        }
    } catch {
        reqBodyCode.textContent = '';
    }
    if (window.Prism) Prism.highlightElement(reqBodyCode);

    if (item.raw_response) {
        rawArea.classList.remove('hidden');
        try {
            const rawObj = typeof item.raw_response === 'string' ? JSON.parse(item.raw_response) : item.raw_response;
            rawCode.textContent = JSON.stringify(rawObj, null, 2);
        } catch {
            rawCode.textContent = item.raw_response;
        }
        if (window.Prism) Prism.highlightElement(rawCode);
    } else {
        rawArea.classList.add('hidden');
    }

    const apiHeadersCode = document.getElementById('hist-api-headers-code');
    const apiParamsCode = document.getElementById('hist-api-params-code');
    const apiBodyCode = document.getElementById('hist-api-body-code');

    try {
        const apiHeadersObj = typeof item.api_request_headers === 'string' ? JSON.parse(item.api_request_headers) : (item.api_request_headers || {});
        apiHeadersCode.textContent = JSON.stringify(apiHeadersObj, null, 2);
    } catch {
        apiHeadersCode.textContent = item.api_request_headers || '';
    }
    if (window.Prism) Prism.highlightElement(apiHeadersCode);

    try {
        const apiParamsObj = typeof item.api_request_params === 'string' ? JSON.parse(item.api_request_params) : (item.api_request_params || {});
        apiParamsCode.textContent = JSON.stringify(apiParamsObj, null, 2);
    } catch {
        apiParamsCode.textContent = item.api_request_params || '';
    }
    if (window.Prism) Prism.highlightElement(apiParamsCode);

    try {
        const apiBodyVal = item.api_request_body;
        if (typeof apiBodyVal === 'string') {
            try {
                apiBodyCode.textContent = JSON.stringify(JSON.parse(apiBodyVal), null, 2);
            } catch {
                apiBodyCode.textContent = apiBodyVal;
            }
        } else {
            apiBodyCode.textContent = JSON.stringify(apiBodyVal || {}, null, 2);
        }
    } catch {
        apiBodyCode.textContent = '';
    }
    if (window.Prism) Prism.highlightElement(apiBodyCode);

    modal.showModal();
}

function closeHistoryModal(event) {
    if (event) event.preventDefault();
    getModal('history_modal').close();
}

function copyHistoryResult() {
    const text = document.getElementById('hist-data-code').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast('结果已复制到剪贴板');
    });
}

// ==================== Test Scrape ====================

async function loadTestTemplates() {
    const select = document.getElementById('test-template');
    try {
        // Only load if not loaded or empty
        if (select.options.length <= 1) {
            const tpls = await fetchAPI('/api/templates');
            select.innerHTML = '<option value="">请选择模板...</option>';
            tpls.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.name;
                opt.textContent = t.name;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error(e);
    }
}

let currentTestMode = 'template';

function switchTestMode(mode, tabElement) {
    currentTestMode = mode;
    
    // Update tabs
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab-active'));
    tabElement.classList.add('tab-active');
    
    // Toggle content
    if (mode === 'template') {
        document.getElementById('test-mode-template').classList.remove('hidden');
        document.getElementById('test-mode-manual').classList.add('hidden');
    } else {
        document.getElementById('test-mode-template').classList.add('hidden');
        document.getElementById('test-mode-manual').classList.remove('hidden');
    }
}

async function testScrape() {
    const resultArea = document.getElementById('test-result');
    const pre = document.getElementById('test-result-code');
    
    resultArea.classList.remove('hidden');
    pre.textContent = '正在执行抓取...';

    try {
        let result;
        
        if (currentTestMode === 'template') {
            const templateName = document.getElementById('test-template').value;
            const paramsStr = document.getElementById('test-params').value;
            let params = {};

            if (paramsStr && paramsStr.trim()) {
                try {
                    params = JSON.parse(paramsStr);
                } catch {
                    showToast('自定义参数 JSON 格式错误', 'error');
                    pre.textContent = '参数错误';
                    return;
                }
            }
            
            if (!templateName) {
                showToast('请选择一个模板', 'warning');
                pre.textContent = '请选择模板';
                return;
            }

            result = await fetchAPI('/api/scrape/simple', {
                method: 'POST',
                body: JSON.stringify({
                    template_name: templateName,
                    params: params
                })
            });
        } else {
            // Manual Mode
            const url = document.getElementById('manual-url').value;
            if (!url) {
                showToast('请输入 URL', 'warning');
                pre.textContent = 'URL 不能为空';
                return;
            }
            
            const method = document.getElementById('manual-method').value;
            const headersStr = document.getElementById('manual-headers').value;
            const bodyStr = document.getElementById('manual-body').value;
            
            const payload = {
                url: url,
                method: method,
                headers: parseJSON(headersStr),
                body: bodyStr // Server handles string or JSON
            };
            
            result = await fetchAPI('/api/scrape', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
        }

        pre.textContent = JSON.stringify(result, null, 2);
        if (window.Prism) {
            Prism.highlightElement(pre);
        }
        showToast('抓取测试成功');
    } catch (e) {
        pre.textContent = 'Error: ' + e.message;
    }
}

function copyTestResult() {
    const text = document.getElementById('test-result-code').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast('结果已复制');
    });
}

// ==================== Init ====================

document.addEventListener('DOMContentLoaded', () => {
    // Load default tab
    showTab('templates');
});

async function loadBatchTasks() {
    try {
        const container = document.getElementById('batch-list');
        if (!container) return;
        const tasks = await fetchAPI('/api/batch');
        container.innerHTML = '';
        if (!tasks || tasks.length === 0) {
            const tpl = document.getElementById('batch-empty');
            if (tpl) container.appendChild(tpl.content.cloneNode(true));
            return;
        }
        const tpl = document.getElementById('batch-card');
        tasks.forEach(t => {
            const clone = tpl.content.cloneNode(true);
            clone.querySelector('.batch-name').textContent = t.name;
            clone.querySelector('.batch-template').textContent = t.template_name;
            clone.querySelector('.batch-concurrency').textContent = t.concurrency;
            clone.querySelector('.batch-sleep').textContent = t.sleep_ms;
            clone.querySelector('.batch-out').textContent = t.output_dir;
            const st = clone.querySelector('.batch-status');
            st.textContent = t.status || 'pending';
            st.classList.add(t.status === 'running' ? 'badge-info' : (t.status === 'completed' ? 'badge-success' : 'badge-outline'));
            const btnEdit = clone.querySelector('.btn-edit');
            const btnView = clone.querySelector('.btn-view');
            const btnRun = clone.querySelector('.btn-run');
            const btnStop = clone.querySelector('.btn-stop');
            btnEdit.onclick = () => openBatchModal(t);
            btnView.onclick = () => openBatchViewModal(t);
            btnRun.onclick = () => runBatchTask(t.id);
            btnStop.onclick = () => stopBatchTask(t.id);
            clone.querySelector('.btn-items').onclick = () => openBatchItemsModal(t.id);
            clone.querySelector('.btn-delete').onclick = () => deleteBatchTask(t.id);
            // 状态控制按钮显示：
            if (t.status === 'pending') {
                btnEdit.classList.remove('hidden');
                btnRun.classList.remove('hidden');
                btnStop.classList.add('hidden');
            } else if (t.status === 'running') {
                btnEdit.classList.add('hidden');
                btnRun.classList.add('hidden');
                btnStop.classList.remove('hidden');
            } else { // completed
                btnEdit.classList.add('hidden');
                btnRun.classList.remove('hidden'); // 支持重新执行
                btnStop.classList.add('hidden');
            }
            container.appendChild(clone);
        });
    } catch (e) {
        console.error('Failed to load batch tasks:', e);
    }
}

function openBatchModal(task = null) {
    const modal = document.getElementById('batch_modal');
    document.getElementById('batch-modal-title').textContent = task ? '编辑批量任务' : '新建批量任务';
    document.getElementById('batch-id').value = task?.id || '';
    document.getElementById('batch-name').value = task?.name || '';
    document.getElementById('batch-concurrency').value = task?.concurrency ?? 1;
    document.getElementById('batch-sleep').value = task?.sleep_ms ?? 0;
    document.getElementById('batch-out').value = task?.output_dir || '';
    document.getElementById('batch-csv').value = task?.csv_text || '';
    // init save fields
    (function () {
        const checks = document.querySelectorAll('#batch_modal input[type="checkbox"]');
        const fields = task?.save_fields || ['success','error','data','request'];
        checks.forEach(ch => ch.checked = fields.includes(ch.value));
        document.getElementById('batch-data-jsonpath').value = task?.data_json_path || '';
    })();
    (async function () {
        try {
            const selectEl = document.getElementById('batch-template');
            selectEl.innerHTML = '<option value="">请选择模板...</option>';
            const tpls = await fetchAPI('/api/templates');
            tpls.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.name;
                opt.textContent = t.name;
                selectEl.appendChild(opt);
            });
            if (task?.template_name) selectEl.value = task.template_name;
        } catch (e) {
            console.error(e);
        }
    })();
    modal.showModal();
}

function closeBatchModal(event) {
    if (event) event.preventDefault();
    document.getElementById('batch_modal').close();
}

function openBatchViewModal(task) {
    const modal = document.getElementById('batch_view_modal');
    document.getElementById('bv-name').textContent = task?.name || '';
    document.getElementById('bv-template').textContent = task?.template_name || '';
    document.getElementById('bv-concurrency').textContent = task?.concurrency ?? '';
    document.getElementById('bv-sleep').textContent = task?.sleep_ms ?? '';
    document.getElementById('bv-out').textContent = task?.output_dir || '';
    const fields = task?.save_fields || ['success','error','data','request'];
    document.getElementById('bv-fields').textContent = fields.join(', ');
    document.getElementById('bv-jsonpath').textContent = task?.data_json_path || '';
    document.getElementById('bv-csv').textContent = task?.csv_text || '';
    modal.showModal();
}

function closeBatchViewModal(event) {
    if (event) event.preventDefault();
    document.getElementById('batch_view_modal').close();
}

async function saveBatchTask() {
    const id = document.getElementById('batch-id').value;
    const name = document.getElementById('batch-name').value.trim();
    const template_name = document.getElementById('batch-template').value;
    const concurrency = Number(document.getElementById('batch-concurrency').value);
    const sleep_ms = Number(document.getElementById('batch-sleep').value);
    const output_dir = document.getElementById('batch-out').value.trim();
    const csv_text = document.getElementById('batch-csv').value;
    const save_fields = Array.from(document.querySelectorAll('#batch_modal input[type="checkbox"]:checked')).map(ch => ch.value);
    const data_json_path = document.getElementById('batch-data-jsonpath').value.trim() || null;
    if (!name || !template_name || !output_dir || !csv_text) {
        showToast('请完善任务信息', 'error');
        return;
    }
    try {
        const payload = { name, template_name, concurrency, sleep_ms, output_dir, csv_text, save_fields, data_json_path };
        if (id) {
            await fetchAPI(`/api/batch/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            showToast('任务已更新');
        } else {
            await fetchAPI('/api/batch', { method: 'POST', body: JSON.stringify(payload) });
            showToast('任务已创建');
        }
        closeBatchModal();
        loadBatchTasks();
    } catch (e) {
        console.error('Save batch task failed:', e);
    }
}

async function deleteBatchTask(id) {
    if (!await showConfirm('确定要删除这个批量任务吗？')) return;
    try {
        await fetchAPI(`/api/batch/${id}`, { method: 'DELETE' });
        showToast('任务已删除');
        loadBatchTasks();
    } catch (e) {
        console.error('Delete batch task failed:', e);
    }
}

async function runBatchTask(id) {
    try {
        showToast('开始执行批量任务');
        const res = await fetchAPI(`/api/batch/${id}/run`, { method: 'POST' });
        if (res && res.message) {
            showToast(res.message);
        } else {
            showToast('任务已开始执行');
        }
        loadBatchTasks();
    } catch (e) {
        console.error('Run batch task failed:', e);
    }
}

async function stopBatchTask(id) {
    try {
        await fetchAPI(`/api/batch/${id}/stop`, { method: 'POST' });
        showToast('任务已停止', 'warning');
        loadBatchTasks();
    } catch (e) {
        console.error('Stop batch failed:', e);
    }
}

let currentBatchIdForItems = null;
async function openBatchItemsModal(taskId) {
    currentBatchIdForItems = taskId;
    const modal = document.getElementById('batch_items_modal');
    await loadBatchItems(taskId);
    modal.showModal();
}

function closeBatchItemsModal(event) {
    if (event) event.preventDefault();
    document.getElementById('batch_items_modal').close();
}

async function loadBatchItems(taskId) {
    try {
        const items = await fetchAPI(`/api/batch/${taskId}/items`);
        const tbody = document.getElementById('batch-items-list');
        tbody.innerHTML = '';
        if (!items || items.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.className = 'text-center py-6 text-base-content/60';
            td.textContent = '暂无记录';
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }
        items.forEach(it => {
            const tr = document.createElement('tr');
            const tdSeq = document.createElement('td');
            tdSeq.textContent = it.seq_no;
            const tdStatus = document.createElement('td');
            tdStatus.textContent = it.status;
            const tdParams = document.createElement('td');
            tdParams.className = 'font-mono text-xs break-all';
            tdParams.textContent = JSON.stringify(it.params);
            const tdFile = document.createElement('td');
            tdFile.className = 'font-mono text-xs break-all';
            tdFile.textContent = it.output_file || '';
            const tdErr = document.createElement('td');
            tdErr.className = 'text-xs break-all';
            tdErr.textContent = it.error || '';
            tr.appendChild(tdSeq);
            tr.appendChild(tdStatus);
            tr.appendChild(tdParams);
            tr.appendChild(tdFile);
            tr.appendChild(tdErr);
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('load items failed:', e);
    }
}
