const tagModal = document.getElementById('tagModal');
const cancelBtn = document.getElementById('cancelButton');
const associateBtn = document.getElementById('associateButton');
const tagInput = document.getElementById('tag-input');
const btnVoltar = document.getElementById('btn-voltar');
const btnInicio = document.getElementById('btn-inicio');
const container = document.getElementById('container');

const progressModal = document.getElementById('progressModal');
const progressTitle = document.getElementById('progressTitle');
const successModal = document.getElementById('successModal');
const remainingCount = document.getElementById('remainingCount');

const errorModal = document.getElementById('errorModal');
const errorModalMessage = document.getElementById('errorModalMessage');
const errorOkButton = document.getElementById('errorOkButton');

function showErrorModal(msg) {
    errorModalMessage.textContent = msg;
    errorModal.style.display = 'flex';
}

errorOkButton.addEventListener('click', () => {
    errorModal.style.display = 'none';
    tagInput.value = '';
    tagInput.focus();
});

// Total de tags que precisam ser associadas (lê do localStorage)
let totalTags = getTags() || 0;
let associatedTags = 0;
let collectedTags = [];
let currentTag = '';

const AUTH_HEADERS = {
    'Content-Type': 'application/json',
    'x-api-key': 'capibarra-tablet-01',
    'x-device-id': 'tablet-01'
};

// Atualiza o texto de "Faltam associar X tag(s)"
function updateRemaining() {
    const remaining = totalTags - associatedTags;
    remainingCount.textContent = remaining;
}

updateRemaining();

// Garante foco permanente no input (exceto quando modal aberta)
tagInput.focus();
container.addEventListener('click', () => {
    if (tagModal.style.display === 'none' || !tagModal.style.display) {
        tagInput.focus();
    }
});
container.addEventListener('keydown', () => {
    if (tagModal.style.display === 'none' || !tagModal.style.display) {
        if (errorModal.style.display === 'none' || !errorModal.style.display) {
            tagInput.focus();
        }
    }
});

// Ao pressionar Enter no input
tagInput.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const tagText = tagInput.value.trim();
    if (!tagText) return;

    if (collectedTags.includes(tagText)) {
        showErrorModal('Esta TAG já foi escaneada nesta sessão!');
        return;
    }

    currentTag = tagText;

    // Exibe a modal de confirmação
    tagModal.style.display = 'flex';
});

function closeModal() {
    tagModal.style.display = 'none';
    tagInput.value = '';
    tagInput.focus();
    currentTag = '';
}

// Botões da modal
cancelBtn.addEventListener('click', closeModal);

associateBtn.addEventListener('click', async () => {
    if (!currentTag) return;
    
    // Desabilita para não duplicar requests
    associateBtn.disabled = true;

    try {
        // Valida/Ativa a tag chamando a API
        const actResp = await fetch(`/api/tags/${currentTag}/activate`, {
            method: 'POST',
            headers: AUTH_HEADERS,
            body: JSON.stringify({ reason: "associated_for_play" })
        });

        if (!actResp.ok) {
            const err = await actResp.json().catch(() => ({}));
            // Como no backend o texto amigável está sendo passado como o 2º parâmetro (que vira 'code' no JSON)
            throw new Error(err.error?.code || err.error?.message || err.detail || 'Erro ao validar a TAG');
        }

        // Sucesso: adiciona na lista
        collectedTags.push(currentTag);
        associatedTags++;

        const remaining = totalTags - associatedTags;
        updateRemaining();

        if (remaining <= 0) {
            // Associa todas as tags aos receipts no backend antes de finalizar
            try {
                const receiptIds = getReceiptIds();
                await fetch('/api/tags/associate', {
                    method: 'POST',
                    headers: AUTH_HEADERS,
                    body: JSON.stringify({
                        receipt_ids: receiptIds,
                        tags: collectedTags
                    })
                });
                console.log('[DEBUG] Tags associadas aos receipts:', receiptIds);
            } catch (assocError) {
                console.error('Erro ao associar tags aos receipts:', assocError);
            }

            // Todas as tags associadas!
            tagModal.style.display = 'none';
            successModal.style.display = 'flex';
            resetCounters();
            clearReceiptIds();
            setTimeout(() => {
                window.location.href = '/pages/';
            }, 2500);
        } else {
            // Ainda faltam tags
            tagModal.style.display = 'none';
            progressTitle.textContent = `Faltam associar ${remaining} tag(s)`;
            progressModal.style.display = 'flex';
            setTimeout(() => {
                progressModal.style.display = 'none';
                tagInput.value = '';
                tagInput.focus();
            }, 2000);
        }
    } catch (err) {
        console.error(err);
        showErrorModal(err.message || 'Erro ao ativar a TAG. Tente novamente.');
    } finally {
        associateBtn.disabled = false;
        currentTag = '';
        tagModal.style.display = 'none';
    }
});

btnInicio.addEventListener('click', () => {
    document.getElementById('confirmResetModal').style.display = 'flex';
});

document.getElementById('cancelResetBtn').addEventListener('click', () => {
    document.getElementById('confirmResetModal').style.display = 'none';
});

document.getElementById('confirmResetBtn').addEventListener('click', () => {
    resetCounters();
    clearReceiptIds();
    clearSessionId();
    clearQrUrl();
    clearPlayerId();
    window.location.href = '/pages/';
});

btnVoltar.addEventListener('click', () => {
    window.history.back();
});
