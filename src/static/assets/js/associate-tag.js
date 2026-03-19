const btnVoltar = document.getElementById('btn-voltar');
const btnInicio = document.getElementById('btn-inicio');
const remainingCount = document.getElementById('remainingCount');
const dynamicQRCode = document.getElementById('dynamicQRCode');

let totalTags = getTags() || 0;

function updateRemaining() {
    if (remainingCount) {
        remainingCount.textContent = totalTags;
    }

    const qrUrl = localStorage.getItem('virtual_qr_url');
    if (dynamicQRCode && qrUrl) {
        dynamicQRCode.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(qrUrl)}`;
    }
}

updateRemaining();

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
