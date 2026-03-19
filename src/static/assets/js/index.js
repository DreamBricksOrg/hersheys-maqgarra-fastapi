const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/scan-qrcode';
});

btnNao.addEventListener('click', () => {
    window.location.href = '/pages/read-camera';
});