// counter.js — Gerenciador de contadores BARRAS e TAGS via localStorage

const STORAGE_KEYS = {
    BARRAS: 'counter_barras',
    TAGS: 'counter_tags',
    RECEIPT_IDS: 'receipt_ids',
    PLAYER_ID: 'player_id',
    SESSION_ID: 'session_id',
    QUEUE_ID: 'queue_id',
    QUEUE_NUMBER: 'queue_number',
};

const COUNT_BARS = 6;

// ── Receipt IDs ──────────────────────────────────────────────────────────────

function getReceiptIds() {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.RECEIPT_IDS) || '[]');
}

function addReceiptId(receiptId) {
    if (!receiptId) return;
    const ids = getReceiptIds();
    if (!ids.includes(receiptId)) {
        ids.push(receiptId);
        localStorage.setItem(STORAGE_KEYS.RECEIPT_IDS, JSON.stringify(ids));
    }
}

function clearReceiptIds() {
    localStorage.removeItem(STORAGE_KEYS.RECEIPT_IDS);
}

// ── Player ID ────────────────────────────────────────────────────────────────

function generateObjectId() {
    const timestamp = Math.floor(new Date().getTime() / 1000).toString(16);
    return timestamp + 'xxxxxxxxxxxxxxxx'.replace(/[x]/g, () => {
        return Math.floor(Math.random() * 16).toString(16);
    }).toLowerCase();
}

function getPlayerId() {
    return localStorage.getItem(STORAGE_KEYS.PLAYER_ID);
}

function setPlayerId(id) {
    if (id) {
        localStorage.setItem(STORAGE_KEYS.PLAYER_ID, id);
    } else {
        localStorage.removeItem(STORAGE_KEYS.PLAYER_ID);
    }
}

function clearPlayerId() {
    localStorage.removeItem(STORAGE_KEYS.PLAYER_ID);
}

// ── Session ID ───────────────────────────────────────────────────────────────

function getSessionId() {
    return localStorage.getItem(STORAGE_KEYS.SESSION_ID);
}

function setSessionId(id) {
    if (id) {
        localStorage.setItem(STORAGE_KEYS.SESSION_ID, id);
    } else {
        localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
    }
}

function clearSessionId() {
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
}

// ── Queue ID ─────────────────────────────────────────────────────────────────

function getQueueId() {
    return localStorage.getItem(STORAGE_KEYS.QUEUE_ID);
}

function setQueueId(id) {
    if (id) {
        localStorage.setItem(STORAGE_KEYS.QUEUE_ID, id);
    } else {
        localStorage.removeItem(STORAGE_KEYS.QUEUE_ID);
    }
}

function clearQueueId() {
    localStorage.removeItem(STORAGE_KEYS.QUEUE_ID);
}

// ── Queue Number ─────────────────────────────────────────────────────────────

function getQueueNumber() {
    return localStorage.getItem(STORAGE_KEYS.QUEUE_NUMBER);
}

function setQueueNumber(num) {
    if (num !== undefined && num !== null) {
        localStorage.setItem(STORAGE_KEYS.QUEUE_NUMBER, num.toString());
    } else {
        localStorage.removeItem(STORAGE_KEYS.QUEUE_NUMBER);
    }
}

function clearQueueNumber() {
    localStorage.removeItem(STORAGE_KEYS.QUEUE_NUMBER);
}

// ── Barras / Tags ─────────────────────────────────────────────────────────────

function getBarras() {
    return parseInt(localStorage.getItem(STORAGE_KEYS.BARRAS) || '0', 10);
}

function getTags() {
    return parseInt(localStorage.getItem(STORAGE_KEYS.TAGS) || '0', 10);
}

function setBarras(value) {
    localStorage.setItem(STORAGE_KEYS.BARRAS, value.toString());
    updateCounterDisplay();
}

function setTags(value) {
    localStorage.setItem(STORAGE_KEYS.TAGS, value.toString());
    updateCounterDisplay();
}

function addBarras(amount = 1) {
    const newBarras = getBarras() + amount;
    localStorage.setItem(STORAGE_KEYS.BARRAS, newBarras.toString());
    // A cada 6 barras = 1 tag
    localStorage.setItem(STORAGE_KEYS.TAGS, Math.floor(newBarras / COUNT_BARS).toString());
    updateCounterDisplay();
}

function addTags(amount = 1) {
    setTags(getTags() + amount);
}

function resetCounters() {
    localStorage.setItem(STORAGE_KEYS.BARRAS, '0');
    localStorage.setItem(STORAGE_KEYS.TAGS, '0');
    updateCounterDisplay();
}

function updateCounterDisplay() {
    const barrasEl = document.getElementById('barrasCount');
    const tagsEl = document.getElementById('tagsCount');
    if (barrasEl) barrasEl.textContent = getBarras();
    if (tagsEl) tagsEl.textContent = getTags();
    localStorage.setItem(STORAGE_KEYS.TAGS, Math.floor(getBarras() / COUNT_BARS).toString());
}

function getQrUrl() {
    return localStorage.getItem('virtual_qr_url');
}

function setQrUrl(url) {
    localStorage.setItem('virtual_qr_url', url);
}

function clearQrUrl() {
    localStorage.removeItem('virtual_qr_url');
}

function setupLogoReset() {
    const logos = document.querySelectorAll('.logo-container, .logo-container img, img.page-logo');
    let pressTimer;

    logos.forEach(logo => {
        // Função para iniciar o contador
        const startPress = () => {
            pressTimer = setTimeout(() => {
                if (confirm('Deseja realmente zerar todos os dados locais?')) {
                    localStorage.clear();
                    alert('Todos os dados foram removidos.');
                    window.location.href = '/pages/';
                }
            }, 3000); // 3 segundos
        };

        // Função para cancelar o contador
        const cancelPress = () => {
            clearTimeout(pressTimer);
        };

        // Eventos para Desktop
        logo.addEventListener('mousedown', startPress);
        logo.addEventListener('mouseup', cancelPress);
        logo.addEventListener('mouseleave', cancelPress);

        // Eventos para Mobile (Touch)
        logo.addEventListener('touchstart', (e) => {
            // e.preventDefault(); // Opcional: evita menu de contexto, mas pode travar scroll se não for cuidadoso
            startPress();
        }, { passive: true });
        logo.addEventListener('touchend', cancelPress);
        logo.addEventListener('touchcancel', cancelPress);
    });
}

// Atualiza o display e configura o reset assim que o DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    updateCounterDisplay();
    setupLogoReset();
});
