// counter.js — Gerenciador de contadores BARRAS e TAGS via localStorage

const STORAGE_KEYS = {
    BARRAS: 'counter_barras',
    TAGS: 'counter_tags',
    RECEIPT_IDS: 'receipt_ids',
    PLAYER_ID: 'player_id',
    SESSION_ID: 'session_id',
};

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
    localStorage.setItem(STORAGE_KEYS.TAGS, Math.floor(newBarras / 6).toString());
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
    localStorage.setItem(STORAGE_KEYS.TAGS, Math.floor(getBarras() / 6).toString());
}

// Atualiza o display assim que o DOM carregar
document.addEventListener('DOMContentLoaded', updateCounterDisplay);
