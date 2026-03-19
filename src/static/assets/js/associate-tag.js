const btnVoltar = document.getElementById('btn-voltar');
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

btnVoltar.addEventListener('click', () => {
    resetCounters();
    clearReceiptIds();
    clearSessionId();
    localStorage.removeItem('virtual_qr_url');
    window.location.href = '/pages/';
});
