const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');
const sorryModal = document.getElementById('sorryModal');
const sessionErrorModal = document.getElementById('sessionErrorModal');
const sessionErrorMessage = document.getElementById('sessionErrorMessage');
const sessionErrorOkButton = document.getElementById('sessionErrorOkButton');
const sorryUnderstoodButton = document.getElementById('sorryUnderstoodButton');

const confirmReceiptsModal = document.getElementById('confirmReceiptsModal');
const confirmReceiptsCount = document.getElementById('confirm-receipts-count');
const cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
const proceedConfirmBtn = document.getElementById('proceedConfirmBtn');

function showSessionError(msg) {
    sessionErrorMessage.textContent = msg;
    sessionErrorModal.style.display = 'flex';
}

sessionErrorOkButton.addEventListener('click', () => {
    sessionErrorModal.style.display = 'none';
});

sorryUnderstoodButton.addEventListener('click', () => {
    resetCounters();
    clearReceiptIds();
    clearSessionId();
    clearQrUrl();
    clearPlayerId();
    clearQueueId();
    clearQueueNumber();
    window.location.href = '/pages/';
});

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/';
});

async function createSessionAndProceed() {
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

    window.location.href = '/pages/tag-type';
}

// function unusedTags() {
//     const receiptIds = getReceiptIds();
//     fetch('/api/receipts/unused', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'x-api-key': 'capibarra-tablet-01',
//             'x-device-id': 'tablet-01'
//         },
//         body: JSON.stringify({
//             receipt_ids: receiptIds
//         })
//     }).then(resp => {
//         if (!resp.ok) {
//             throw new Error('Erro na rede');
//         }
//         return resp.json();
//     }).then(data => {
//         console.log(data); // Manipula os dados finais
//     }).catch(error => {
//         console.error('Houve um problema:', error); // Trata erros
//     });
// }


btnNao.addEventListener('click', () => {
    const tags = getTags();

    if (tags <= 0) {
        sorryModal.style.display = 'flex';
        //unusedTags();
        return;
    }

    const receiptIds = getReceiptIds();
    const count = receiptIds ? receiptIds.length : 0;

    confirmReceiptsCount.textContent = count;
    confirmReceiptsModal.style.display = 'flex';
});

cancelConfirmBtn.addEventListener('click', () => {
    confirmReceiptsModal.style.display = 'none';
});

proceedConfirmBtn.addEventListener('click', async () => {
    confirmReceiptsModal.style.display = 'none';
    await createSessionAndProceed();
});
