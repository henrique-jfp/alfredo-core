document.addEventListener('DOMContentLoaded', () => {
    // ==========================================
    // RELÓGIO AO VIVO (painel de parede)
    // ==========================================
    const elClockTime = document.getElementById('clock-time');
    const elClockDate = document.getElementById('clock-date');

    function updateLiveClock() {
        if (!elClockTime || !elClockDate) return;
        const now = new Date();
        elClockTime.textContent = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        elClockDate.textContent = now.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' });
    }
    updateLiveClock();
    setInterval(updateLiveClock, 1000 * 30);

    // ==========================================
    // TOAST NOTIFICATION SYSTEM
    // ==========================================
    const toastContainer = document.getElementById('toast-container');

    function showToast(message, type = 'success', duration = 3500) {
        const icons = { success: '✓', error: '✕', info: 'ℹ' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('toast-exit');
            toast.addEventListener('animationend', () => toast.remove());
        }, duration);
    }

    // ==========================================
    // ICON MAPPING FOR LOCATIONS
    // ==========================================
    const LOCATION_ICONS = {
        'casa': '🏠', 'home': '🏠', 'lar': '🏠',
        'trabalho': '💼', 'work': '💼', 'escritório': '💼', 'escritorio': '💼', 'office': '💼',
        'escola': '🏫', 'school': '🏫', 'faculdade': '🎓', 'universidade': '🎓',
        'estádio': '🏟️', 'estadio': '🏟️', 'stadium': '🏟️',
        'academia': '🏋️', 'gym': '🏋️',
        'hospital': '🏥', 'médico': '🏥', 'medico': '🏥',
        'mercado': '🛒', 'supermercado': '🛒',
        'restaurante': '🍽️', 'praia': '🏖️', 'aeroporto': '✈️',
        'igreja': '⛪', 'museu': '🏛️', 'parque': '🌳', 'shopping': '🏬',
    };

    function getLocationIcon(name) {
        const key = name.toLowerCase().trim();
        return LOCATION_ICONS[key] || '📍';
    }

    // ==========================================
    // DOM ELEMENTS
    // ==========================================
    const elInteractions = document.getElementById('kpi-interactions');
    const elTimers = document.getElementById('kpi-timers');
    const elDevices = document.getElementById('kpi-devices');
    const elTokens = document.getElementById('kpi-tokens');
    const elHistory = document.getElementById('history-container');
    const elShopping = document.getElementById('shopping-list');
    const elTodo = document.getElementById('todo-list');
    const elTimersList = document.getElementById('timers-list');
    const btnRefresh = document.getElementById('refresh-btn');

    // ==========================================
    // FETCH STATS
    // ==========================================
    async function fetchStats() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            animateValue(elInteractions, data.interactions);
            animateValue(elTimers, data.active_timers);
            animateValue(elDevices, data.devices);
            animateValue(elTokens, data.tokens_used.toLocaleString('pt-BR'));
        } catch (error) {
            console.error('Erro ao buscar stats:', error);
        }
    }

    function animateValue(el, newValue) {
        if (el.textContent === String(newValue)) return;
        el.style.transition = 'opacity 150ms, transform 150ms';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-4px)';
        setTimeout(() => {
            el.textContent = newValue;
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, 150);
    }

    // ==========================================
    // FETCH HISTORY
    // ==========================================
    async function fetchHistory() {
        try {
            const res = await fetch('/api/dashboard/history');
            const data = await res.json();

            elHistory.innerHTML = '';

            if (data.length === 0) {
                elHistory.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">💬</div>
                        <p>Nenhuma conversa registrada ainda.</p>
                    </div>`;
                return;
            }

            data.forEach(item => {
                const date = new Date(item.timestamp);
                const timeString = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

                const logItem = document.createElement('div');
                logItem.className = 'log-item';

                logItem.innerHTML = `
                    <div class="log-meta">
                        <span>${item.room_id} · ${item.device_id}</span>
                        <span>${timeString}</span>
                    </div>
                    <div class="log-user">${item.input_text}</div>
                    <div class="log-alfredo">${item.output_text || '...'}</div>
                `;

                elHistory.appendChild(logItem);
            });
        } catch (error) {
            console.error('Erro ao buscar histórico:', error);
            elHistory.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <p>Erro ao carregar histórico. Servidor offline?</p>
                </div>`;
        }
    }

    // ==========================================
    // VIRTUAL MIC
    // ==========================================
    const virtualMicInput = document.getElementById('virtual-mic-input');
    const btnVirtualMic = document.getElementById('btn-virtual-mic');
    const virtualMicPlayer = document.getElementById('virtual-mic-player');
    const virtualMicContainer = document.getElementById('virtual-mic-audio-container');

    async function sendVirtualMic() {
        const text = virtualMicInput.value.trim();
        if (!text) return;

        btnVirtualMic.textContent = 'Processando...';
        btnVirtualMic.disabled = true;

        try {
            const res = await fetch('/api/voice/text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            if (res.ok) {
                const blob = await res.blob();
                const audioUrl = URL.createObjectURL(blob);
                virtualMicContainer.style.display = 'block';
                virtualMicPlayer.src = audioUrl;
                virtualMicInput.value = '';
                showToast('Comando processado com sucesso!', 'success');
                setTimeout(fetchHistory, 1000);
            } else {
                showToast('Erro no processamento do comando.', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Erro de conexão ao enviar comando.', 'error');
        } finally {
            btnVirtualMic.textContent = 'Enviar';
            btnVirtualMic.disabled = false;
        }
    }

    if (btnVirtualMic && virtualMicInput) {
        btnVirtualMic.addEventListener('click', sendVirtualMic);
        virtualMicInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendVirtualMic();
        });
    }

    // ==========================================
    // FETCH LISTS
    // ==========================================
    async function fetchLists() {
        try {
            const res = await fetch('/api/dashboard/lists');
            const data = await res.json();

            renderList(elShopping, data.compras, 'Nenhum item adicionado.');
            renderList(elTodo, data.tarefas, 'Nenhuma tarefa pendente.');
        } catch (error) {
            console.error('Erro ao buscar listas:', error);
        }
    }

    function renderList(el, items, emptyMsg) {
        el.innerHTML = '';
        if (items.length === 0) {
            el.innerHTML = `<li class="empty-list">${emptyMsg}</li>`;
        } else {
            items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item.content;
                el.appendChild(li);
            });
        }
    }

    // ==========================================
    // FETCH TIMERS (REMIDERS)
    // ==========================================
    async function fetchTimers() {
        try {
            const res = await fetch('/api/dashboard/timers');
            const data = await res.json();

            elTimersList.innerHTML = '';

            if (data.length === 0) {
                elTimersList.innerHTML = `<li class="empty-list">Nenhum lembrete ativo.</li>`;
                return;
            }

            data.forEach(t => {
                const li = document.createElement('li');
                li.style.display = 'flex';
                li.style.justifyContent = 'space-between';
                li.style.alignItems = 'center';
                li.style.gap = '8px';

                const isAlarm = t.timer_type === 'alarm';
                const msg = t.message || (isAlarm ? 'Alarme' : 'Timer');

                // Formatar hora
                const expDate = new Date(t.expires_at + "Z"); // Add Z to parse UTC correctly
                const timeStr = expDate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

                li.innerHTML = `
                    <div>
                        <strong>${timeStr}</strong>: ${msg}
                    </div>
                    <button class="glass-btn icon-btn danger-btn btn-del-timer" data-id="${t.id}" title="Excluir Lembrete">🗑️</button>
                `;
                elTimersList.appendChild(li);
            });

            // Attach delete events
            document.querySelectorAll('.btn-del-timer').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.closest('.btn-del-timer').dataset.id;
                    if (confirm('Cancelar este lembrete/alarme?')) {
                        try {
                            await fetch(`/api/dashboard/timers/${id}`, { method: 'DELETE' });
                            showToast('Lembrete cancelado.', 'success');
                            fetchTimers();
                        } catch (err) {
                            showToast('Erro ao cancelar lembrete.', 'error');
                        }
                    }
                });
            });

        } catch (error) {
            console.error('Erro ao buscar timers:', error);
        }
    }

    // ==========================================
    // UPDATE ALL
    // ==========================================
    function updateAll() {
        fetchStats();
        fetchHistory();
        fetchLists();
        fetchTimers();

        const tabIntegracoes = document.getElementById('tab-integracoes');
        const modalSpotify = document.getElementById('spotify-modal');
        if (tabIntegracoes && (tabIntegracoes.style.display !== 'none' || modalSpotify.style.display === 'flex')) {
            fetchIntegrations();
        }
    }

    btnRefresh.addEventListener('click', () => {
        btnRefresh.innerHTML = '↻ Atualizando...';
        updateAll();
        setTimeout(() => btnRefresh.innerHTML = '↻ Atualizar', 800);
    });

    updateAll();
    setInterval(updateAll, 5000);

    // ==========================================
    // TAB NAVIGATION
    // ==========================================
    const menuItems = document.querySelectorAll('.menu-item[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();

            menuItems.forEach(mi => mi.classList.remove('active'));
            tabContents.forEach(tc => tc.style.display = 'none');

            item.classList.add('active');
            const targetTab = document.getElementById(`tab-${item.dataset.tab}`);
            if (targetTab) {
                targetTab.style.display = 'block';
                // Re-trigger animation
                targetTab.style.animation = 'none';
                targetTab.offsetHeight; // force reflow
                targetTab.style.animation = '';
            }

            // Lazy load tab data
            if (item.dataset.tab === 'rotinas') fetchRoutines();
            if (item.dataset.tab === 'configuracoes') { fetchSettings(); fetchLocations(); }
            if (item.dataset.tab === 'inteligencia') { fetchMemories(); fetchApiStatus(); }
            if (item.dataset.tab === 'satelites') fetchSatellites();
            if (item.dataset.tab === 'integracoes') fetchIntegrations();
            if (item.dataset.tab === 'sonhos') fetchDreams();
        });
    });

    // ==========================================
    // INTEGRATIONS & SPOTIFY MODAL
    // ==========================================
    const modalSpotify = document.getElementById('spotify-modal');
    const btnCloseSpotify = document.getElementById('close-spotify-modal');
    const btnConnectSpotify = document.getElementById('btn-connect-spotify');
    const btnSaveSpotify = document.getElementById('btn-save-spotify');
    const btnBackSpotify = document.getElementById('btn-back-spotify');
    const qrContainer = document.getElementById('spotify-qrcode');
    const statusBadge = document.getElementById('spotify-status-badge');
    const ipHint = document.getElementById('local-ip-hint');

    let currentLocalIp = "localhost";

    async function fetchIntegrations() {
        try {
            const res = await fetch('/api/dashboard/integrations');
            const data = await res.json();

            currentLocalIp = data.local_ip;
            if (ipHint) ipHint.textContent = currentLocalIp;

            if (data.spotify.is_connected) {
                statusBadge.textContent = "Conectado";
                statusBadge.className = "status-badge connected";
                btnConnectSpotify.textContent = "Reconfigurar";

                if (modalSpotify.style.display === 'flex' && document.getElementById('spotify-step-2').style.display === 'block') {
                    showToast('Spotify autenticado com sucesso!', 'success');
                    modalSpotify.style.display = 'none';
                }
            } else if (data.spotify.is_configured) {
                statusBadge.textContent = "Chaves Salvas";
                statusBadge.className = "status-badge disconnected";
                btnConnectSpotify.textContent = "Gerar QR Code Login";
            } else {
                statusBadge.textContent = "Desconectado";
                statusBadge.className = "status-badge disconnected";
                btnConnectSpotify.textContent = "Configurar";
            }
        } catch (e) {
            console.error("Erro fetchIntegrations", e);
        }
    }

    btnConnectSpotify.addEventListener('click', () => {
        modalSpotify.style.display = 'flex';
        if (statusBadge.textContent === "Chaves Salvas") {
            showQrCodeStep();
        } else {
            document.getElementById('spotify-step-1').style.display = 'block';
            document.getElementById('spotify-step-2').style.display = 'none';
        }
    });

    btnCloseSpotify.addEventListener('click', () => {
        modalSpotify.style.display = 'none';
    });
    btnBackSpotify.addEventListener('click', () => {
        document.getElementById('spotify-step-1').style.display = 'block';
        document.getElementById('spotify-step-2').style.display = 'none';
    });

    btnSaveSpotify.addEventListener('click', async () => {
        const clientId = document.getElementById('spotify-client-id').value.trim();
        const clientSecret = document.getElementById('spotify-client-secret').value.trim();

        if (!clientId || !clientSecret) {
            showToast('Preencha as duas chaves para continuar.', 'error');
            return;
        }

        btnSaveSpotify.textContent = "Salvando...";

        try {
            await fetch('/api/dashboard/integrations/spotify/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_id: clientId, client_secret: clientSecret })
            });
            showQrCodeStep();
        } catch (e) {
            showToast('Erro ao salvar chaves.', 'error');
        } finally {
            btnSaveSpotify.textContent = "Salvar e Gerar QR Code";
        }
    });

    function showQrCodeStep() {
        document.getElementById('spotify-step-1').style.display = 'none';
        document.getElementById('spotify-step-2').style.display = 'block';

        qrContainer.innerHTML = '';
        const loginUrl = `http://${currentLocalIp}:10001/api/spotify/login`;

        new QRCode(qrContainer, {
            text: loginUrl,
            width: 180,
            height: 180,
            colorDark: "#000000",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.H
        });
    }

    // ==========================================
    // ROUTINES
    // ==========================================
    const routinesList = document.getElementById('routines-list');
    const btnSaveRoutine = document.getElementById('btn-save-routine');

    async function fetchRoutines() {
        if (!routinesList) return;
        try {
            const res = await fetch('/api/dashboard/routines');
            const data = await res.json();

            routinesList.innerHTML = '';

            if (data.length === 0) {
                routinesList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">⏰</div>
                        <p>Nenhuma rotina criada ainda. Crie sua primeira rotina ao lado!</p>
                    </div>`;
                return;
            }

            data.forEach(rt => {
                const isActive = rt.is_active !== false;
                const rtEl = document.createElement('div');
                rtEl.className = `routine-item glass-panel ${isActive ? '' : 'inactive'}`;

                rtEl.innerHTML = `
                    <div class="routine-icon-wrap">⏰</div>
                    <div class="routine-info">
                        <h3>${rt.name}</h3>
                        <p>
                            <span class="routine-tag">🕐 ${rt.trigger_value}</span>
                            <span class="routine-tag">📍 ${rt.room_id}</span>
                        </p>
                        <p style="margin-top: 4px; font-size: 12px; color: var(--text-muted);">
                            🗣️ "${rt.action_value}"
                        </p>
                    </div>
                    <div class="routine-actions">
                        <label class="toggle-switch" title="Ativar/Desativar">
                            <input type="checkbox" ${isActive ? 'checked' : ''} data-id="${rt.id}" class="toggle-routine">
                            <span class="toggle-slider"></span>
                        </label>
                        <button class="glass-btn icon-btn btn-test-rt" data-id="${rt.id}" title="Testar Agora">▶</button>
                        <button class="glass-btn icon-btn danger-btn btn-del-rt" data-id="${rt.id}" title="Excluir">🗑️</button>
                    </div>
                `;
                routinesList.appendChild(rtEl);
            });

            // Attach Events
            document.querySelectorAll('.toggle-routine').forEach(input => {
                input.addEventListener('change', async (e) => {
                    const id = e.target.dataset.id;
                    try {
                        await fetch(`/api/dashboard/routines/${id}/toggle`, { method: 'PATCH' });
                        fetchRoutines();
                    } catch (err) {
                        showToast('Erro ao alterar rotina.', 'error');
                    }
                });
            });

            document.querySelectorAll('.btn-test-rt').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    e.target.textContent = "...";
                    try {
                        await fetch(`/api/dashboard/routines/${id}/test`, { method: 'POST' });
                        showToast('Rotina testada com sucesso!', 'info');
                    } catch (err) {
                        showToast('Erro ao testar rotina.', 'error');
                    }
                    setTimeout(() => { e.target.textContent = "▶"; fetchRoutines(); }, 2000);
                });
            });

            document.querySelectorAll('.btn-del-rt').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.closest('.btn-del-rt').dataset.id;
                    if (confirm('Tem certeza que deseja excluir esta rotina?')) {
                        await fetch(`/api/dashboard/routines/${id}`, { method: 'DELETE' });
                        showToast('Rotina excluída.', 'success');
                        fetchRoutines();
                    }
                });
            });

        } catch (error) {
            console.error('Erro ao buscar rotinas:', error);
            routinesList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <p>Erro ao carregar rotinas.</p>
                </div>`;
        }
    }

    if (btnSaveRoutine) {
        btnSaveRoutine.addEventListener('click', async () => {
            const name = document.getElementById('rt-name').value.trim();
            const time = document.getElementById('rt-time').value;
            const room = document.getElementById('rt-room').value.trim();
            const action = document.getElementById('rt-action').value.trim();

            if (!name || !time || !room || !action) {
                showToast('Preencha todos os campos da rotina.', 'error');
                return;
            }

            btnSaveRoutine.textContent = "Salvando...";

            const payload = {
                name,
                trigger_type: "time",
                trigger_value: time,
                action_type: "simulate_command",
                action_value: action,
                room_id: room
            };

            try {
                await fetch('/api/dashboard/routines', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                document.getElementById('rt-name').value = '';
                document.getElementById('rt-action').value = '';
                document.getElementById('rt-time').value = '';

                showToast('Rotina criada com sucesso!', 'success');
                fetchRoutines();
            } catch (e) {
                showToast('Erro ao criar rotina.', 'error');
            } finally {
                btnSaveRoutine.textContent = "Salvar Rotina";
            }
        });
    }

    // ==========================================
    // SETTINGS
    // ==========================================
    const btnSaveSettings = document.getElementById('btn-save-settings');

    async function fetchSettings() {
        try {
            const res = await fetch('/api/dashboard/settings');
            const data = await res.json();

            document.getElementById('set-assistant-name').value = data.assistant_name || 'alfredo';
            document.getElementById('set-assistant-voice').value = data.assistant_voice || 'pt-BR-FranciscaNeural';
            document.getElementById('set-city').value = data.weather_city || '';
            document.getElementById('set-gmaps-key').value = data.google_maps_api_key || '';
            document.getElementById('set-news-rss').value = data.news_rss_url || '';
        } catch (error) {
            console.error('Erro ao buscar configurações:', error);
        }
    }

    if (btnSaveSettings) {
        btnSaveSettings.addEventListener('click', async () => {
            btnSaveSettings.textContent = "Salvando...";

            const payload = {
                settings: {
                    assistant_name: document.getElementById('set-assistant-name').value.trim(),
                    assistant_voice: document.getElementById('set-assistant-voice').value,
                    weather_city: document.getElementById('set-city').value.trim(),
                    google_maps_api_key: document.getElementById('set-gmaps-key').value.trim(),
                    news_rss_url: document.getElementById('set-news-rss').value.trim()
                }
            };

            try {
                await fetch('/api/dashboard/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                showToast('Configurações salvas com sucesso!', 'success');
            } catch (e) {
                showToast('Erro ao salvar configurações.', 'error');
            } finally {
                btnSaveSettings.textContent = "Salvar Configurações";
            }
        });
    }

    // Voice preview
    const btnTestVoice = document.getElementById('btn-test-voice');
    const audioPreview = document.getElementById('audio-preview');

    if (btnTestVoice) {
        btnTestVoice.addEventListener('click', async () => {
            const selectedVoice = document.getElementById('set-assistant-voice').value;
            const originalText = btnTestVoice.textContent;

            btnTestVoice.textContent = "⏳ Gerando...";
            btnTestVoice.disabled = true;

            try {
                const res = await fetch('/api/dashboard/tts/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ voice_name: selectedVoice })
                });

                if (res.ok) {
                    const blob = await res.blob();
                    const audioUrl = URL.createObjectURL(blob);
                    audioPreview.src = audioUrl;
                    audioPreview.play();
                    btnTestVoice.textContent = "🔊 Reproduzindo...";

                    audioPreview.onended = () => {
                        btnTestVoice.textContent = originalText;
                        btnTestVoice.disabled = false;
                    };
                } else {
                    showToast('Erro ao testar voz. Verifique os logs.', 'error');
                    btnTestVoice.textContent = originalText;
                    btnTestVoice.disabled = false;
                }
            } catch (e) {
                console.error(e);
                showToast('Erro ao conectar com a API de voz.', 'error');
                btnTestVoice.textContent = originalText;
                btnTestVoice.disabled = false;
            }
        });
    }

    // ==========================================
    // SAVED LOCATIONS (CRUD)
    // ==========================================
    const locationsList = document.getElementById('locations-list');
    const btnAddLocation = document.getElementById('btn-add-location');
    const addLocationForm = document.getElementById('add-location-form');
    const btnCancelLocation = document.getElementById('btn-cancel-location');
    const btnSaveLocation = document.getElementById('btn-save-location');

    async function fetchLocations() {
        try {
            const res = await fetch('/api/dashboard/locations');
            const data = await res.json();

            locationsList.innerHTML = '';

            if (data.length === 0) {
                locationsList.innerHTML = `
                    <div class="locations-empty">
                        📍 Nenhum endereço salvo. Adicione seu primeiro endereço abaixo.
                    </div>`;
                return;
            }

            data.forEach(loc => {
                const icon = getLocationIcon(loc.name);
                const item = document.createElement('div');
                item.className = 'location-item';

                item.innerHTML = `
                    <div class="location-icon">${icon}</div>
                    <div class="location-info">
                        <div class="location-name">${loc.name}</div>
                        <div class="location-coords">${loc.latitude}, ${loc.longitude}</div>
                    </div>
                    <button class="location-delete" data-id="${loc.id}" title="Excluir endereço">🗑️</button>
                `;
                locationsList.appendChild(item);
            });

            // Attach delete events
            document.querySelectorAll('.location-delete').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.dataset.id;
                    if (confirm('Excluir este endereço?')) {
                        try {
                            await fetch(`/api/dashboard/locations/${id}`, { method: 'DELETE' });
                            showToast('Endereço excluído.', 'success');
                            fetchLocations();
                        } catch (err) {
                            showToast('Erro ao excluir endereço.', 'error');
                        }
                    }
                });
            });
        } catch (error) {
            console.error('Erro ao buscar locations:', error);
            locationsList.innerHTML = '<div class="locations-empty">Erro ao carregar endereços.</div>';
        }
    }

    // Toggle add-location form
    btnAddLocation.addEventListener('click', () => {
        addLocationForm.classList.toggle('visible');
        btnAddLocation.style.display = addLocationForm.classList.contains('visible') ? 'none' : '';
    });

    btnCancelLocation.addEventListener('click', () => {
        addLocationForm.classList.remove('visible');
        btnAddLocation.style.display = '';
        document.getElementById('loc-name').value = '';
        document.getElementById('loc-lat').value = '';
        document.getElementById('loc-lon').value = '';
    });

    btnSaveLocation.addEventListener('click', async () => {
        const name = document.getElementById('loc-name').value.trim();
        const lat = document.getElementById('loc-lat').value.trim();
        const lon = document.getElementById('loc-lon').value.trim();

        if (!name || !lat || !lon) {
            showToast('Preencha todos os campos do endereço.', 'error');
            return;
        }

        btnSaveLocation.textContent = 'Salvando...';

        try {
            const icon = getLocationIcon(name);
            await fetch('/api/dashboard/locations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, latitude: lat, longitude: lon, icon: name.toLowerCase() })
            });

            showToast(`Endereço "${name}" salvo com sucesso!`, 'success');

            // Reset form
            document.getElementById('loc-name').value = '';
            document.getElementById('loc-lat').value = '';
            document.getElementById('loc-lon').value = '';
            addLocationForm.classList.remove('visible');
            btnAddLocation.style.display = '';

            fetchLocations();
        } catch (err) {
            showToast('Erro ao salvar endereço.', 'error');
        } finally {
            btnSaveLocation.textContent = 'Salvar';
        }
    });

    // ==========================================
    // DREAMS tab logic
    // ==========================================
    async function fetchDreams() {
        const dreamsList = document.getElementById('dreams-list');
        const wordCloud = document.getElementById('word-cloud-container');

        try {
            const res = await fetch('/api/dashboard/dreams');
            const data = await res.json();

            // Render Timeline
            if (!data.history || data.history.length === 0) {
                dreamsList.innerHTML = '<div class="empty-list">Nenhum sonho registrado ainda.</div>';
            } else {
                dreamsList.innerHTML = data.history.map(d => `
                    <div class="dream-card glass-panel" style="margin-bottom: 12px; padding: 16px;">
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">${new Date(d.created_at).toLocaleString('pt-BR')}</div>
                        <div style="font-size: 0.95rem; line-height: 1.5; color: var(--text-main); margin-bottom: 12px;">${d.interpretation}</div>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                            ${(d.themes || []).map(t => `<span class="status-badge" style="background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo);">${t}</span>`).join('')}
                        </div>
                    </div>
                `).join('');
            }

            // Render Word Cloud
            if (!data.word_freq || Object.keys(data.word_freq).length === 0) {
                wordCloud.innerHTML = '<div class="empty-list">Nenhuma palavra-chave.</div>';
            } else {
                let maxFreq = Math.max(...Object.values(data.word_freq));
                let minFreq = Math.min(...Object.values(data.word_freq));

                wordCloud.innerHTML = Object.entries(data.word_freq).map(([word, freq]) => {
                    // Calculate font size between 1.0rem and 3.0rem
                    let size = 1.0;
                    if (maxFreq > minFreq) {
                        size = 1.0 + ((freq - minFreq) / (maxFreq - minFreq)) * 2.0;
                    }
                    return `<span class="cloud-tag" style="font-size: ${size}rem; opacity: ${0.6 + (size / 5)}; color: rgba(255,255,255,0.9); font-weight: 500; margin: 6px; display: inline-block;">${word}</span>`;
                }).join(' ');
            }
        } catch (err) {
            console.error('Erro ao carregar sonhos:', err);
            dreamsList.innerHTML = '<div class="empty-list">Erro ao carregar diário.</div>';
            wordCloud.innerHTML = '<div class="empty-list">Erro.</div>';
        }
    }

    // ==========================================
    // ROUTINES tab lazy load
    // ==========================================
    const oldUpdateAll = updateAll;
    updateAll = function () {
        oldUpdateAll();
        const tabRotinas = document.getElementById('tab-rotinas');
        if (tabRotinas && tabRotinas.style.display !== 'none') {
            fetchRoutines();
        }
        const tabInteligencia = document.getElementById('tab-inteligencia');
        if (tabInteligencia && tabInteligencia.style.display !== 'none') {
            fetchMemories();
            fetchApiStatus();
        }
        const tabSatelites = document.getElementById('tab-satelites');
        if (tabSatelites && tabSatelites.style.display !== 'none') {
            fetchSatellites();
        }
    };

    // ==========================================
    // SATÉLITES: LIVE AUDIO E WEBSOCKET
    // ==========================================
    let dashboardWs = null;
    let audioContext = null;
    let selectedSatellite = null;
    let isListening = false;
    const btnListen = document.getElementById('btn-live-listen');
    const audioTargetDisplay = document.getElementById('audio-target-display');
    const audioIndicator = document.getElementById('audio-monitor-indicator');

    async function fetchSatellites() {
        try {
            const res = await fetch('/api/satellite/devices');
            const devices = await res.json();
            const list = document.getElementById('satellites-list');
            list.innerHTML = '';

            if (devices.length === 0) {
                list.innerHTML = `
                    <div class="empty-list" style="text-align: center; opacity: 0.5;">
                        Nenhum satélite pareado no banco de dados.
                    </div>
                `;
                return;
            }

            devices.forEach(sat => {
                const card = document.createElement('div');
                card.className = 'kpi-card glass-panel';
                card.style.cssText = 'background: rgba(255,255,255,0.02); padding: 15px; cursor: pointer; border: 1px solid transparent; transition: 0.2s; display: block;';

                const statusColor = sat.is_online ? '#00e676' : '#ffb74d';
                const statusText = sat.is_online ? '● Online' : '○ Offline';

                card.innerHTML = `
                    <div class="kpi-title" style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="font-size: 1.1rem; color: #fff;">${sat.hardware || sat.device_id}</span>
                        <span style="color: ${statusColor}; font-size: 0.85rem; font-weight: 500;">${statusText}</span>
                    </div>
                    <div style="font-size: 0.85rem; opacity: 0.6; display: flex; justify-content: space-between;">
                        <span>Cômodo: ${sat.room_id || 'Não definido'}</span>
                        <span style="font-family: monospace;">ID: ${sat.device_id.substring(0, 8)}</span>
                    </div>
                `;
                // Store data for click
                card.dataset.satObj = JSON.stringify(sat);
                card.onclick = () => selectSatellite(sat, card);
                list.appendChild(card);
            });
        } catch (err) {
            console.error('Erro ao buscar satélites:', err);
        }
    }
    window.fetchSatellites = fetchSatellites;

    function selectSatellite(sat, cardElement) {
        selectedSatellite = sat.device_id;

        // Remove highlight from others
        document.querySelectorAll('#satellites-list .kpi-card').forEach(c => {
            c.style.borderColor = 'transparent';
            c.style.background = 'rgba(255,255,255,0.02)';
        });
        if (cardElement) {
            cardElement.style.borderColor = 'var(--accent-purple)';
            cardElement.style.background = 'rgba(255,255,255,0.05)';
        }

        // Enable and populate detail panel
        const panel = document.getElementById('satellite-details-panel');
        panel.style.opacity = '1';
        panel.style.pointerEvents = 'auto';

        document.getElementById('det-sat-name').textContent = sat.hardware || sat.device_id;

        const statusEl = document.getElementById('det-sat-status');
        if (sat.is_online) {
            statusEl.textContent = "● Online (WS)";
            statusEl.style.color = "#00e676";
            statusEl.style.background = "rgba(0, 230, 118, 0.1)";
        } else {
            statusEl.textContent = "○ Offline (HTTP)";
            statusEl.style.color = "#ffb74d";
            statusEl.style.background = "rgba(255, 183, 77, 0.1)";
        }

        document.getElementById('det-sat-hardware').textContent = sat.hardware || 'N/A';
        document.getElementById('det-sat-firmware').textContent = sat.firmware_version || '1.0.0';
        document.getElementById('det-sat-id').textContent = sat.device_id;
        document.getElementById('det-sat-room').textContent = sat.room_id || 'N/A';

        // Listen Button logic
        btnListen.disabled = false;

        // Setup slider events just for show
        const sliderVol = document.getElementById('slider-vol');
        const valVol = document.getElementById('val-vol');
        sliderVol.oninput = (e) => valVol.textContent = `${e.target.value}%`;

        const sliderBri = document.getElementById('slider-bri');
        const valBri = document.getElementById('val-bri');
        sliderBri.oninput = (e) => valBri.textContent = `${e.target.value}%`;
    }
    window.selectSatellite = selectSatellite;

    function initAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === 'suspended') {
            audioContext.resume();
        }
    }

    function connectDashboardWs() {
        if (dashboardWs) return;
        const host = window.location.host;
        dashboardWs = new WebSocket(`ws://${host}/api/ws/dashboard`);

        dashboardWs.onopen = () => console.log('Dashboard WS Connected');
        dashboardWs.onclose = () => {
            console.log('Dashboard WS Disconnected, retrying...');
            dashboardWs = null;
            setTimeout(connectDashboardWs, 3000);
        };
        dashboardWs.onerror = (e) => console.error('Dashboard WS Error', e);

        let nextStartTime = 0;

        dashboardWs.onmessage = async (event) => {
            if (event.data instanceof Blob) {
                // We received binary audio data (raw PCM S16_LE 16000Hz from arecord)
                if (!isListening) return;
                try {
                    const arrayBuffer = await event.data.arrayBuffer();
                    const int16Array = new Int16Array(arrayBuffer);
                    const float32Array = new Float32Array(int16Array.length);
                    for (let i = 0; i < int16Array.length; i++) {
                        float32Array[i] = int16Array[i] / 32768.0;
                    }

                    const buffer = audioContext.createBuffer(1, float32Array.length, 16000);
                    buffer.getChannelData(0).set(float32Array);

                    const source = audioContext.createBufferSource();
                    source.buffer = buffer;
                    source.connect(audioContext.destination);

                    // Schedule sequentially to avoid stuttering/clicking
                    const currentTime = audioContext.currentTime;
                    if (nextStartTime < currentTime) {
                        nextStartTime = currentTime; // Reset if we fell behind
                    }
                    source.start(nextStartTime);
                    nextStartTime += buffer.duration;
                } catch (e) {
                    console.error('Erro tocando PCM:', e);
                }
            }
        };
    }

    if (btnListen) {
        // Mousedown / Touchstart para escutar
        const startListening = () => {
            if (!selectedSatellite || isListening) return;
            initAudioContext();
            connectDashboardWs();
            isListening = true;
            btnListen.textContent = "Escutando...";
            btnListen.style.background = "var(--error-red)";
            audioIndicator.style.borderColor = "var(--error-red)";
            audioIndicator.style.color = "var(--error-red)";
            audioIndicator.classList.add('pulse-animation');

            if (dashboardWs && dashboardWs.readyState === WebSocket.OPEN) {
                dashboardWs.send(`START_STREAM:${selectedSatellite}`);
            }
        };

        const stopListening = () => {
            if (!isListening) return;
            isListening = false;
            btnListen.textContent = "Segure para Escutar";
            btnListen.style.background = "";
            audioIndicator.style.borderColor = "rgba(255,255,255,0.1)";
            audioIndicator.style.color = "";
            audioIndicator.classList.remove('pulse-animation');

            if (dashboardWs && dashboardWs.readyState === WebSocket.OPEN) {
                dashboardWs.send(`STOP_STREAM:${selectedSatellite}`);
            }
        };

        btnListen.addEventListener('mousedown', startListening);
        btnListen.addEventListener('touchstart', startListening);
        window.addEventListener('mouseup', stopListening);
        window.addEventListener('touchend', stopListening);
    }

    // ==========================================
    // INTELIGÊNCIA: MEMÓRIAS & API STATUS
    // ==========================================
    async function fetchMemories() {
        try {
            const res = await fetch('/api/dashboard/memories');
            const data = await res.json();
            const list = document.getElementById('memory-list');
            list.innerHTML = '';

            if (data.length === 0) {
                list.innerHTML = '<li style="text-align: center; color: rgba(255,255,255,0.5);">Nenhuma memória encontrada.</li>';
                return;
            }

            data.forEach(mem => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div style="flex: 1;">
                        <strong style="color: var(--accent-purple);">#${mem.id}</strong> - ${mem.fact}
                    </div>
                    <button class="delete-btn" onclick="deleteMemory(${mem.id})">🗑️</button>
                `;
                list.appendChild(li);
            });
        } catch (err) {
            console.error('Erro ao buscar memórias:', err);
        }
    }
    window.fetchMemories = fetchMemories;

    window.addMemory = async function () {
        const input = document.getElementById('new-memory-input');
        if (!input.value.trim()) return;

        try {
            const res = await fetch('/api/dashboard/memories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fact: input.value.trim(), room_id: "default" })
            });
            if (res.ok) {
                input.value = '';
                showToast("Fato salvo na memória!");
                fetchMemories();
            }
        } catch (err) {
            console.error(err);
            showToast("Erro ao salvar", "error");
        }
    };

    window.deleteMemory = async function (id) {
        if (!confirm("Tem certeza que deseja esquecer esse fato?")) return;
        try {
            const res = await fetch(`/api/dashboard/memories/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast("Memória apagada!");
                fetchMemories();
            }
        } catch (err) {
            console.error(err);
            showToast("Erro ao deletar", "error");
        }
    };

    async function fetchApiStatus() {
        try {
            const res = await fetch('/api/dashboard/status');
            const data = await res.json();

            document.getElementById('api-model-name').textContent = data.model;
            document.getElementById('api-key-idx').textContent = `${data.current_key_idx} de ${data.keys_total}`;
            document.getElementById('api-global-reqs').textContent = data.global_requests;
            document.getElementById('api-status-text').textContent = "Sistema de IA Online e Roteando";

        } catch (err) {
            console.error('Erro ao buscar status API:', err);
            document.getElementById('api-status-text').textContent = "Erro de conexão com o Cérebro";
            document.querySelector('.api-indicator .pulse-dot').style.backgroundColor = "var(--error-red)";
        }
    }
    window.fetchApiStatus = fetchApiStatus;

});