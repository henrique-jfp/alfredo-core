document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elInteractions = document.getElementById('kpi-interactions');
    const elTimers = document.getElementById('kpi-timers');
    const elDevices = document.getElementById('kpi-devices');
    const elTokens = document.getElementById('kpi-tokens');
    const elHistory = document.getElementById('history-container');
    const elShopping = document.getElementById('shopping-list');
    const elTodo = document.getElementById('todo-list');
    const btnRefresh = document.getElementById('refresh-btn');

    // Fetch Stats
    async function fetchStats() {
        try {
            const res = await fetch('/api/dashboard/stats');
            const data = await res.json();
            elInteractions.textContent = data.interactions;
            elTimers.textContent = data.active_timers;
            elDevices.textContent = data.devices;
            elTokens.textContent = data.tokens_used.toLocaleString();
        } catch (error) {
            console.error('Erro ao buscar stats:', error);
        }
    }

    // Fetch History
    async function fetchHistory() {
        try {
            const res = await fetch('/api/dashboard/history');
            const data = await res.json();
            
            elHistory.innerHTML = '';
            
            if (data.length === 0) {
                elHistory.innerHTML = '<div class="loading">Nenhuma conversa registrada ainda.</div>';
                return;
            }

            data.forEach(item => {
                const date = new Date(item.timestamp);
                const timeString = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                
                const logItem = document.createElement('div');
                logItem.className = 'log-item';
                
                logItem.innerHTML = `
                    <div class="log-meta">
                        <span>${item.room_id} (${item.device_id})</span>
                        <span>${timeString}</span>
                    </div>
                    <div class="log-user">${item.input_text}</div>
                    <div class="log-alfredo">${item.output_text || '...'}</div>
                `;
                
                elHistory.appendChild(logItem);
            });
        } catch (error) {
            console.error('Erro ao buscar histórico:', error);
            elHistory.innerHTML = '<div class="loading" style="color:#ef4444;">Erro ao carregar histórico. Servidor offline?</div>';
        }
    }

    // Fetch Lists
    async function fetchLists() {
        try {
            const res = await fetch('/api/dashboard/lists');
            const data = await res.json();
            
            // Render Compras
            elShopping.innerHTML = '';
            if (data.compras.length === 0) {
                elShopping.innerHTML = '<li class="empty-list">Nenhum item adicionado.</li>';
            } else {
                data.compras.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item.content;
                    elShopping.appendChild(li);
                });
            }

            // Render Tarefas
            elTodo.innerHTML = '';
            if (data.tarefas.length === 0) {
                elTodo.innerHTML = '<li class="empty-list">Nenhuma tarefa pendente.</li>';
            } else {
                data.tarefas.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item.content;
                    elTodo.appendChild(li);
                });
            }
        } catch (error) {
            console.error('Erro ao buscar listas:', error);
        }
    }

    // Main Update Loop
    function updateAll() {
        fetchStats();
        fetchHistory();
        fetchLists();
        
        // Atualiza status do app se a aba estiver ativa ou modal aberto
        const tabIntegracoes = document.getElementById('tab-integracoes');
        const modalSpotify = document.getElementById('spotify-modal');
        if (tabIntegracoes && (tabIntegracoes.style.display !== 'none' || modalSpotify.style.display === 'flex')) {
            fetchIntegrations();
        }
    }

    // Bind Refresh button
    btnRefresh.addEventListener('click', () => {
        btnRefresh.textContent = "Atualizando...";
        updateAll();
        setTimeout(() => btnRefresh.textContent = "Atualizar", 800);
    });

    // Initial load
    updateAll();

    // Auto-refresh a cada 5 segundos para parecer Real-Time
    setInterval(updateAll, 5000);

    // ==========================================
    // TAB NAVIGATION
    // ==========================================
    const menuItems = document.querySelectorAll('.menu-item[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active de todos
            menuItems.forEach(mi => mi.classList.remove('active'));
            tabContents.forEach(tc => tc.style.display = 'none');
            
            // Adiciona ativo no clicado
            item.classList.add('active');
            const targetTab = document.getElementById(`tab-${item.dataset.tab}`);
            if (targetTab) {
                targetTab.style.display = 'block';
            }
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
    
    // Check Integrations Status
    async function fetchIntegrations() {
        try {
            const res = await fetch('/api/dashboard/integrations');
            const data = await res.json();
            
            currentLocalIp = data.local_ip;
            if(ipHint) ipHint.textContent = currentLocalIp;
            
            if (data.spotify.is_connected) {
                statusBadge.textContent = "Conectado";
                statusBadge.className = "status-badge connected";
                btnConnectSpotify.textContent = "Reconfigurar";
                
                // Se o modal estiver aberto na tela 2 (QR code) e conectou via cel
                if (modalSpotify.style.display === 'flex' && document.getElementById('spotify-step-2').style.display === 'block') {
                    alert("Sucesso! O Spotify foi autenticado pelo seu celular.");
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

    // Open Modal
    btnConnectSpotify.addEventListener('click', () => {
        modalSpotify.style.display = 'flex';
        
        if (statusBadge.textContent === "Chaves Salvas") {
            showQrCodeStep();
        } else {
            document.getElementById('spotify-step-1').style.display = 'block';
            document.getElementById('spotify-step-2').style.display = 'none';
        }
    });

    // Close Modal
    btnCloseSpotify.addEventListener('click', () => {
        modalSpotify.style.display = 'none';
    });
    btnBackSpotify.addEventListener('click', () => {
        document.getElementById('spotify-step-1').style.display = 'block';
        document.getElementById('spotify-step-2').style.display = 'none';
    });

    // Save Keys and Show QR Code
    btnSaveSpotify.addEventListener('click', async () => {
        const clientId = document.getElementById('spotify-client-id').value.trim();
        const clientSecret = document.getElementById('spotify-client-secret').value.trim();
        
        if (!clientId || !clientSecret) {
            alert("Preencha as duas chaves para continuar.");
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
            alert("Erro ao salvar chaves");
        } finally {
            btnSaveSpotify.textContent = "Salvar e Gerar QR Code";
        }
    });

    function showQrCodeStep() {
        document.getElementById('spotify-step-1').style.display = 'none';
        document.getElementById('spotify-step-2').style.display = 'block';
        
        // Clear and Generate QR Code
        qrContainer.innerHTML = '';
        const loginUrl = `http://${currentLocalIp}:10001/api/spotify/login`;
        
        new QRCode(qrContainer, {
            text: loginUrl,
            width: 180,
            height: 180,
            colorDark : "#000000",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        });
    }

    // ==========================================
    // ROUTINES (ROTINAS AUTOMÁTICAS)
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
                routinesList.innerHTML = '<div class="empty-list">Nenhuma rotina criada ainda.</div>';
                return;
            }
            
            data.forEach(rt => {
                const rtEl = document.createElement('div');
                rtEl.className = 'routine-item glass-panel';
                rtEl.style.marginBottom = '10px';
                rtEl.style.padding = '15px';
                rtEl.style.display = 'flex';
                rtEl.style.justifyContent = 'space-between';
                rtEl.style.alignItems = 'center';
                
                rtEl.innerHTML = `
                    <div>
                        <h3 style="margin: 0; font-size: 16px;">${rt.name}</h3>
                        <p style="margin: 5px 0 0; font-size: 13px; color: var(--text-secondary);">
                            ⏰ ${rt.trigger_value} - ${rt.room_id} <br>
                            🗣️ "<em>${rt.action_value}</em>"
                        </p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="glass-btn btn-test-rt" data-id="${rt.id}">Testar Agora</button>
                        <button class="glass-btn btn-del-rt" data-id="${rt.id}" style="color: #ef4444;">Excluir</button>
                    </div>
                `;
                routinesList.appendChild(rtEl);
            });
            
            // Attach Events
            document.querySelectorAll('.btn-test-rt').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    e.target.textContent = "...";
                    await fetch(`/api/dashboard/routines/${id}/test`, { method: 'POST' });
                    e.target.textContent = "Testado!";
                    setTimeout(() => fetchRoutines(), 2000);
                });
            });
            
            document.querySelectorAll('.btn-del-rt').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.dataset.id;
                    if(confirm('Tem certeza que deseja excluir esta rotina?')) {
                        await fetch(`/api/dashboard/routines/${id}`, { method: 'DELETE' });
                        fetchRoutines();
                    }
                });
            });
            
        } catch (error) {
            console.error('Erro ao buscar rotinas:', error);
            routinesList.innerHTML = '<div class="empty-list">Erro ao carregar rotinas.</div>';
        }
    }

    if (btnSaveRoutine) {
        btnSaveRoutine.addEventListener('click', async () => {
            const name = document.getElementById('rt-name').value.trim();
            const time = document.getElementById('rt-time').value;
            const room = document.getElementById('rt-room').value.trim();
            const action = document.getElementById('rt-action').value.trim();
            
            if (!name || !time || !room || !action) {
                alert("Preencha todos os campos da rotina.");
                return;
            }
            
            btnSaveRoutine.textContent = "Salvando...";
            
            const payload = {
                name: name,
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
                
                // Limpa form
                document.getElementById('rt-name').value = '';
                document.getElementById('rt-action').value = '';
                document.getElementById('rt-time').value = '';
                
                fetchRoutines();
            } catch (e) {
                alert("Erro ao criar rotina");
            } finally {
                btnSaveRoutine.textContent = "Salvar Rotina";
            }
        });
    }

    // Adicionar fetchRoutines no updateAll
    const oldUpdateAll = updateAll;
    updateAll = function() {
        oldUpdateAll();
        const tabRotinas = document.getElementById('tab-rotinas');
        if (tabRotinas && tabRotinas.style.display !== 'none') {
            fetchRoutines();
        }
    };
    
    // ==========================================
    // SETTINGS (CONFIGURAÇÕES GERAIS)
    // ==========================================
    const btnSaveSettings = document.getElementById('btn-save-settings');

    async function fetchSettings() {
        try {
            const res = await fetch('/api/dashboard/settings');
            const data = await res.json();
            
            document.getElementById('set-assistant-name').value = data.assistant_name || 'alfredo';
            document.getElementById('set-assistant-voice').value = data.assistant_voice || 'pt_BR-faber-medium';
            
            document.getElementById('set-city').value = data.weather_city || '';
            document.getElementById('set-home-lat').value = data.home_lat || '';
            document.getElementById('set-home-lon').value = data.home_lon || '';
            document.getElementById('set-work-lat').value = data.work_lat || '';
            document.getElementById('set-work-lon').value = data.work_lon || '';
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
                    home_lat: document.getElementById('set-home-lat').value.trim(),
                    home_lon: document.getElementById('set-home-lon').value.trim(),
                    work_lat: document.getElementById('set-work-lat').value.trim(),
                    work_lon: document.getElementById('set-work-lon').value.trim(),
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
                alert("Configurações salvas com sucesso!");
            } catch (e) {
                alert("Erro ao salvar configurações.");
            } finally {
                btnSaveSettings.textContent = "Salvar Configurações";
            }
        });
    }

    // Carregar configurações quando a aba for aberta
    document.querySelector('.menu-item[data-tab="configuracoes"]').addEventListener('click', () => {
        fetchSettings();
    });

    // Lógica para Testar a Voz do Assistente
    const btnTestVoice = document.getElementById('btn-test-voice');
    const audioPreview = document.getElementById('audio-preview');
    
    if (btnTestVoice) {
        btnTestVoice.addEventListener('click', async () => {
            const selectedVoice = document.getElementById('set-assistant-voice').value;
            const originalText = btnTestVoice.textContent;
            
            btnTestVoice.textContent = "Baixando/Gerando... (pode demorar se for voz nova)";
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
                    btnTestVoice.textContent = "▶ Reproduzindo...";
                    
                    audioPreview.onended = () => {
                        btnTestVoice.textContent = originalText;
                        btnTestVoice.disabled = false;
                    };
                } else {
                    alert("Erro ao testar voz. Veja os logs do servidor.");
                    btnTestVoice.textContent = originalText;
                    btnTestVoice.disabled = false;
                }
            } catch (e) {
                console.error(e);
                alert("Erro ao conectar com a API de voz.");
                btnTestVoice.textContent = originalText;
                btnTestVoice.disabled = false;
            }
        });
    }

});
