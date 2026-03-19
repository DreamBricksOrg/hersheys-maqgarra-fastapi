const tagVirtual = document.getElementById("tag-virtual"); 
const tagFisica = document.getElementById("tag-fisica"); 
const buttonsContainer = document.getElementById("buttonsContainer");
const loadingSpinner = document.getElementById("loadingSpinner");

const AUTH_HEADERS = {
    'Content-Type': 'application/json',
    'x-api-key': 'capibarra-tablet-01',
    'x-device-id': 'tablet-01'
};

function showLoading() {
    buttonsContainer.style.display = 'none';
    loadingSpinner.style.display = 'flex';
}

function hideLoading() {
    loadingSpinner.style.display = 'none';
    buttonsContainer.style.display = 'flex';
}

const confirmTypeModal = document.getElementById("confirmTypeModal");
const confirmTypeTitle = document.getElementById("confirmTypeTitle");
const confirmTypeDesc = document.getElementById("confirmTypeDesc");
const cancelTypeBtn = document.getElementById("cancelTypeBtn");
const confirmTypeBtn = document.getElementById("confirmTypeBtn");

let selectedTagType = null;

tagVirtual.addEventListener('click', () => {
    selectedTagType = 'virtual';
    confirmTypeTitle.textContent = 'Tag Virtual';
    confirmTypeDesc.textContent = 'Você escolheu a TAG Virtual. Um QR Code será gerado para disponibilizar a tag. Deseja continuar?';
    confirmTypeModal.style.display = 'flex';
});

tagFisica.addEventListener('click', () => {
    selectedTagType = 'fisica';
    confirmTypeTitle.textContent = 'Tag Física';
    confirmTypeDesc.textContent = 'Você escolheu a TAG Física. Será necessário aproximar as tags ao leitor. Deseja continuar?';
    confirmTypeModal.style.display = 'flex';
});

cancelTypeBtn.addEventListener('click', () => {
    confirmTypeModal.style.display = 'none';
    selectedTagType = null;
});

confirmTypeBtn.addEventListener('click', async () => {
    confirmTypeModal.style.display = 'none';

    if (selectedTagType === 'virtual') {
        const sessionId = getSessionId();
        const totalPlays = getTags() || 1;
        const receiptIds = getReceiptIds();
        const receiptId = receiptIds[0];

        if (sessionId && receiptId) {
            showLoading();
            try {
                const response = await fetch(`/api/queue/intake?receipt_id=${receiptId}&total_plays=${totalPlays}`, {
                    method: 'POST',
                    headers: AUTH_HEADERS
                });
                if (response.ok) {
                    const data = await response.json();
                    console.log('[DEBUG] Intake sucesso:', data);
                    localStorage.setItem('virtual_qr_url', data.mobile_payload.qr_url);
                    window.location.href = '/pages/associate-tag';
                } else {
                    console.error('[ERRO] Falha no intake HTTP:', response.status);
                    hideLoading();
                }
            } catch (error) {
                console.error('[ERRO] Falha ao chamar /intake:', error);
                hideLoading();
            }
        }
    } else if (selectedTagType === 'fisica') {
        const sessionId = getSessionId();
        const totalPlays = getTags() || 1;

        if (sessionId) {
            showLoading();
            try {
                const response = await fetch('/api/queue/join', {
                    method: 'POST',
                    headers: AUTH_HEADERS,
                    body: JSON.stringify({
                        session_id: sessionId,
                        total_plays: totalPlays
                    })
                });
                if (response.ok) {
                    console.log('[DEBUG] Join sucesso');
                    window.location.href = '/pages/associate-tag-physical';
                } else {
                    console.error('[ERRO] Falha no join HTTP:', response.status);
                    hideLoading();
                }
            } catch (error) {
                console.error('[ERRO] Falha ao chamar /join:', error);
                hideLoading();
            }
        }
    }
});