const openCameraBtn = document.getElementById('openCameraBtn');
const cameraInput = document.getElementById('cameraInput');
const successModal = document.getElementById('successModal');
const warningModal = document.getElementById('warningModal');
const qtdDisplay = document.getElementById('qtd-display');
const btnMinus = document.getElementById('btn-minus');
const btnPlus = document.getElementById('btn-plus');

let currentQtd = 0;

function updateDisplay() {
    qtdDisplay.innerText = currentQtd;
}

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

// Quando tira a foto
cameraInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (currentQtd === 0) {
        warningModal.style.display = 'flex';
        return;
    }

    console.log("Adicionando manualmente:", currentQtd, "barras.");
    addBarras(currentQtd);
    
    document.getElementById('added-qtd').innerText = currentQtd;
    successModal.style.display = 'flex';
    
    setTimeout(() => {
        window.location.href = "/pages/more-receipts";
    }, 2000);
});

