const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');
const sorryModal = document.getElementById('sorryModal');

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
                    receipt_ids: receiptIds
                })
            });

            if (response.ok) {
                const data = await response.json();
                setSessionId(data.session_id);
                console.log('[DEBUG] Sessão criada com sucesso:', data.session_id);
            } else {
                console.error('[ERRO] Falha ao criar sessão HTTP:', response.status);
            }
        } catch (error) {
            console.error('[DEBUG] Falha ao criar sessão:', error);
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
