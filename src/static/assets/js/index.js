const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');
const btnManual = document.getElementById('btn-manual');
const btnEnd = document.getElementById('btn-end');

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/scan-qrcode';
});

btnNao.addEventListener('click', () => {
    window.location.href = '/pages/read-camera';
});

btnManual.addEventListener('click', () => {
    window.location.href = '/pages/add-manually';
});

btnEnd.addEventListener('click', () => {
    window.location.href = '/pages/more-receipts';
});

receiptIds = getReceiptIds();
if (receiptIds && receiptIds.length > 0) {
    btnEnd.style.display= "block"
}
else{
    btnEnd.style.display= "none"
}