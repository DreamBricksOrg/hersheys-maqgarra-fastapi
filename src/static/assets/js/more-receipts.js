const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');
const sorryModal = document.getElementById('sorryModal');
const sessionErrorModal = document.getElementById('sessionErrorModal');
const sessionErrorMessage = document.getElementById('sessionErrorMessage');
const sessionErrorOkButton = document.getElementById('sessionErrorOkButton');

function showSessionError(msg) {
    sessionErrorMessage.textContent = msg;
    sessionErrorModal.style.display = 'flex';
}

sessionErrorOkButton.addEventListener('click', () => {
    sessionErrorModal.style.display = 'none';
});

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/';
});

btnNao.addEventListener('click', async () => {
    const tags = getTags();
    const receiptIds = getReceiptIds();
    let playerId = getPlayerId();

    if (!playerId) {
        playerId = generateObjectId();
        setPlayerId(playerId);
    }

    if (receiptIds && receiptIds.length > 0) {
        try {
            const response = await fetch('/api/sessions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': 'capibarra-tablet-01',
                    'x-device-id': 'tablet-01'
                },
                body: JSON.stringify({
                    player_id: playerId,
                    receipt_ids: receiptIds,
                    total_plays: tags
                })
            });

            if (response.ok) {
                const data = await response.json();
                setSessionId(data.session_id);
                console.log('[DEBUG] Sessão criada com sucesso:', data.session_id);
            } else {
                const errData = await response.json().catch(() => ({}));
                const msg = errData.error?.message || errData.detail || 'Falha ao processar solicitação';
                showSessionError(msg);
                return; // Interrompe o fluxo para permitir correção
            }
        } catch (error) {
            console.error('[DEBUG] Falha ao criar sessão:', error);
            showSessionError('Ocorreu um erro de conexão. Verifique sua rede.');
            return;
        }
    }

    if (tags <= 0) {
        sorryModal.style.display = 'flex';
        resetCounters();
        clearReceiptIds();
        clearSessionId();
        setTimeout(() => {
            window.location.href = '/pages/';
        }, 3000);
    } else {
        window.location.href = '/pages/tag-type';
    }
});
