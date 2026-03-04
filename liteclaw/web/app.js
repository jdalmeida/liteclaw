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
    }

    function setStatus(text) {
        statusEl.textContent = text;
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
                        const last = messagesEl.lastElementChild;
                        if (last && last.classList.contains('model') && currentRunId) {
                            last.textContent += pl.text;
                        } else {
                            addMsg('model', pl.text);
                        }
                        messagesEl.scrollTop = messagesEl.scrollHeight;
                    } else if (evt === 'tool' && pl.phase === 'start') {
                        addMsg('tool', 'Tool: ' + (pl.name || '') + '...', true);
                    } else if (evt === 'lifecycle' && (pl.phase === 'end' || pl.phase === 'error')) {
                        currentRunId = null;
                        sendBtn.disabled = false;
                        setStatus('Conectado');
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
        div.className = 'msg model';
        div.textContent = '';
        messagesEl.appendChild(div);
        currentRunId = 'pending';
    }

    sendBtn.addEventListener('click', send);
    inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
    connect();
})();
