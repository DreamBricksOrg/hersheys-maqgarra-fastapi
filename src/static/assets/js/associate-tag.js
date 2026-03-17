const btnVoltar = document.getElementById('btn-voltar');
const remainingCount = document.getElementById('remainingCount');

let totalTags = getTags() || 0;

function updateRemaining() {
    if (remainingCount) {
        remainingCount.textContent = totalTags;
    }

    const dynamicQRCode = document.getElementById('dynamicQRCode');
    if (dynamicQRCode) {
        const baseUrl = window.location.origin;
        dynamicQRCode.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${baseUrl}/pages/user-qrcode?tags=${totalTags}`;
    }
}

updateRemaining();

btnVoltar.addEventListener('click', () => {
    resetCounters();
    window.location.href = '/pages/';
});
