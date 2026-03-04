/**
 * @author João Gabriel de Almeida
 */

(function() {
    const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsProtocol + '//' + location.host + '/ws';
    const messagesEl = document.getElementById('messages');
    const inputEl = document.getElementById('input');
    const sendBtn = document.getElementById('send');
    const statusEl = document.getElementById('status');

    let ws = null;
    let reqId = 0;
    let connected = false;
    let currentRunId = null;

    function addMsg(role, text, isTool) {
        const div = document.createElement('div');
        div.className = 'msg ' + (isTool ? 'tool' : role);
        div.textContent = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function addToolMsg(name, args) {
        const div = document.createElement('div');
        div.className = 'msg tool';
        div.dataset.toolName = name || '';
        const nameEl = document.createElement('span');
        nameEl.className = 'tool-name';
        nameEl.textContent = '🔧 ' + (name || 'tool') + '(';
        const argsStr = typeof args === 'object' ? JSON.stringify(args) : String(args || '');
        const argsEl = document.createElement('span');
        argsEl.className = 'tool-args';
        argsEl.textContent = argsStr + ')';
        const statusEl = document.createElement('span');
        statusEl.className = 'tool-status';
        statusEl.textContent = ' ...';
        div.appendChild(nameEl);
        div.appendChild(argsEl);
        div.appendChild(statusEl);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    function updateToolResult(toolDiv, result) {
        const statusEl = toolDiv.querySelector('.tool-status');
        if (!statusEl) return;
        let out = '';
        if (result === undefined || result === null) {
            out = ' → ok';
        } else if (typeof result === 'string') {
            out = ' → ' + (result.length > 500 ? result.slice(0, 500) + '...' : result);
        } else {
            const str = JSON.stringify(result);
            out = ' → ' + (str.length > 500 ? str.slice(0, 500) + '...' : str);
        }
        statusEl.textContent = out;
        const pre = document.createElement('pre');
        pre.className = 'tool-output';
        pre.textContent = typeof result === 'object' ? JSON.stringify(result, null, 2) : String(result ?? '');
        toolDiv.appendChild(pre);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function setStatus(text) {
        statusEl.textContent = text;
    }

    function getOrCreateModelDiv() {
        let lastModel = messagesEl.querySelector('.msg.model:last-of-type');
        if (!lastModel || !currentRunId) {
            const div = document.createElement('div');
            div.className = 'msg model';
            div.textContent = '';
            messagesEl.appendChild(div);
            return div;
        }
        return lastModel;
    }

    function connect() {
        setStatus('Conectando...');
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'req',
                id: String(++reqId),
                method: 'connect',
                params: { role: 'webchat', deviceId: 'web-' + Date.now() }
            }));
        };
        ws.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                if (data.type === 'res') {
                    if (data.ok && data.id === String(reqId) && !connected) {
                        connected = true;
                        setStatus('Conectado');
                    }
                    return;
                }
                if (data.type === 'event') {
                    const evt = data.event;
                    const pl = data.payload || {};
                    if (evt === 'assistant' && pl.text) {
                        const modelDiv = getOrCreateModelDiv();
                        modelDiv.textContent += pl.text;
                        modelDiv.classList.remove('typing');
                        messagesEl.scrollTop = messagesEl.scrollHeight;
                    } else if (evt === 'tool') {
                        if (pl.phase === 'start') {
                            addToolMsg(pl.name, pl.args);
                        } else if (pl.phase === 'end') {
                            const tools = messagesEl.querySelectorAll('.msg.tool');
                            const lastTool = tools[tools.length - 1];
                            if (lastTool && lastTool.querySelector('.tool-output') === null) {
                                updateToolResult(lastTool, pl.result);
                            }
                        }
                    } else if (evt === 'lifecycle') {
                        if (pl.phase === 'start') {
                            setStatus('Pensando...');
                            const modelDiv = getOrCreateModelDiv();
                            modelDiv.classList.add('typing');
                        } else if (pl.phase === 'end' || pl.phase === 'error') {
                            currentRunId = null;
                            sendBtn.disabled = false;
                            setStatus(pl.phase === 'error' ? 'Erro: ' + (pl.error || '') : 'Conectado');
                            messagesEl.querySelectorAll('.msg.model.typing').forEach(el => el.classList.remove('typing'));
                        }
                    }
                }
            } catch (e) {}
        };
        ws.onclose = () => {
            connected = false;
            setStatus('Desconectado. Reconectando...');
            setTimeout(connect, 2000);
        };
        ws.onerror = () => {};
    }

    function send() {
        const text = inputEl.value.trim();
        if (!text || !connected || !ws || ws.readyState !== WebSocket.OPEN) return;
        addMsg('user', text);
        inputEl.value = '';
        sendBtn.disabled = true;
        setStatus('Enviando...');
        ws.send(JSON.stringify({
            type: 'req',
            id: String(++reqId),
            method: 'agent',
            params: { message: text, sessionKey: 'main' }
        }));
        const lastModel = messagesEl.querySelector('.msg.model:last-of-type');
        if (lastModel) lastModel.remove();
        const div = document.createElement('div');
        div.className = 'msg model typing';
        div.textContent = '';
        messagesEl.appendChild(div);
        currentRunId = 'pending';
    }

    sendBtn.addEventListener('click', send);
    inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
    connect();
})();
