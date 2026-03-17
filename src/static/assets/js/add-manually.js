const openCameraBtn = document.getElementById('openCameraBtn');
const cameraInput = document.getElementById('cameraInput');
const successModal = document.getElementById('successModal');
const warningModal = document.getElementById('warningModal');
const qrcodeInput = document.getElementById('qrcode-input');

// Abrir câmera nativa
openCameraBtn.addEventListener('click', () => {
    const qtd = parseInt(qrcodeInput.value, 10);
    if (!qtd || qtd < 1 || qtd > 99) {
        warningModal.style.display = 'flex';
        return;
    }
    cameraInput.click();
});

// Fechar modal de aviso
document.getElementById('closeWarningBtn').addEventListener('click', () => {
    warningModal.style.display = 'none';
    qrcodeInput.focus();
});

// Botão voltar
document.getElementById('btn-voltar').addEventListener('click', () => {
    window.history.back();
});

// Quando tira a foto
cameraInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const qtd = parseInt(qrcodeInput.value, 10);
    if (!qtd || qtd < 1 || qtd > 99) {
        warningModal.style.display = 'flex';
        return;
    }

    console.log("Adicionando manualmente:", qtd, "barras.");
    addBarras(qtd);
    
    successModal.style.display = 'flex';
    
    setTimeout(() => {
        window.location.href = "/pages/more-receipts";
    }, 2000);
});

