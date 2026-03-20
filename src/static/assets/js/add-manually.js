const openCameraBtn = document.getElementById('openCameraBtn');
const cameraInput = document.getElementById('cameraInput');
const successModal = document.getElementById('successModal');
const warningModal = document.getElementById('warningModal');
const qtdDisplay = document.getElementById('qtd-display');
const btnMinus = document.getElementById('btn-minus');
const btnPlus = document.getElementById('btn-plus');
const loadingModal = document.getElementById('loadingModal');
const errorModal = document.getElementById('errorModal');
const errorTitle = document.getElementById('errorTitle');
const errorSubtitle = document.getElementById('errorSubtitle');
const retryBtn = document.getElementById('retryBtn');
const dismissBtn = document.getElementById('dismissBtn');

const AUTH_HEADERS = {
    'x-api-key': 'capibarra-tablet-01',
    'x-device-id': 'tablet-01'
};

let currentQtd = 0;

function updateDisplay() {
    qtdDisplay.innerText = currentQtd;
}

function showError(title, subtitle) {
    errorTitle.textContent = title || 'Erro ao enviar nota';
    if (subtitle) {
        errorSubtitle.textContent = subtitle;
        errorSubtitle.style.display = 'block';
    } else {
        errorSubtitle.style.display = 'none';
    }
    errorModal.style.display = 'flex';
}

retryBtn.addEventListener('click', () => {
    errorModal.style.display = 'none';
    cameraInput.click();
});

dismissBtn.addEventListener('click', () => {
    errorModal.style.display = 'none';
});

btnMinus.addEventListener('click', () => {
    if (currentQtd > 0) {
        currentQtd--;
        updateDisplay();
    }
});

btnPlus.addEventListener('click', () => {
    if (currentQtd < 99) {
        currentQtd++;
        updateDisplay();
    }
});

// Abrir câmera nativa
openCameraBtn.addEventListener('click', () => {
    if (currentQtd === 0) {
        warningModal.style.display = 'flex';
        return;
    }
    cameraInput.click();
});

// Fechar modal de aviso
document.getElementById('closeWarningBtn').addEventListener('click', () => {
    warningModal.style.display = 'none';
});

// Botão voltar
document.getElementById('btn-voltar').addEventListener('click', () => {
    window.history.back();
});

// Quando tira a foto → envia ao backend
cameraInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (currentQtd === 0) {
        warningModal.style.display = 'flex';
        return;
    }

    try {
        loadingModal.style.display = 'flex';
        const formData = new FormData();
        formData.append('image', file);
        formData.append('found_bars', currentQtd.toString());

        const resp = await fetch('/api/receipts/manual', {
            method: 'POST',
            headers: AUTH_HEADERS,
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            console.error('[DEBUG] Erro ao salvar manual:', err.detail);
            showError('Erro ao salvar nota', err.detail || 'Ocorreu um erro no servidor.');
        } else {
            const receipt = await resp.json();
            console.log('[DEBUG] Nota manual salva:', receipt);
            addReceiptId(receipt.receipt_id);
            addBarras(currentQtd);
            document.getElementById('added-qtd').innerText = currentQtd;
            successModal.style.display = 'flex';

            setTimeout(() => {
                window.location.href = '/pages/more-receipts';
            }, 2000);
        }

    } catch (err) {
        console.error('[DEBUG] Erro:', err);
        showError('Erro de conexão', 'Não foi possível se comunicar com o servidor.');
    } finally {
        loadingModal.style.display = 'none';
    }
});
