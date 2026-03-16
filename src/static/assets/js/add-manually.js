const openCameraBtn = document.getElementById('openCameraBtn');
const cameraInput = document.getElementById('cameraInput');
const successModal = document.getElementById('successModal');
const qrcodeInput = document.getElementById('qrcode-input');

// Abrir câmera nativa
openCameraBtn.addEventListener('click', () => {
    // Tenta pegar a quantidade caso já digitada
    const qtd = parseInt(qrcodeInput.value, 10);
    if (!qtd || qtd < 1 || qtd > 99) {
        alert("Por favor, informe a quantidade de barras (1 a 99) antes de tirar a foto.");
        qrcodeInput.focus();
        return;
    }
    cameraInput.click();
});

// Quando tira a foto
cameraInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const qtd = parseInt(qrcodeInput.value, 10);
    if (!qtd || qtd < 1 || qtd > 99) {
        alert("Houve um problema com a quantidade informada. Tente novamente.");
        return;
    }

    // Apenas acionamos a lógica global de contador de barras.
    console.log("Mock: Imagem capturada, ignorando upload.");
    console.log("Adicionando manualmente:", qtd, "barras.");

    addBarras(qtd);
    
    // Mostra mensagem de sucesso
    successModal.style.display = 'flex';
    
    // Volta para home após 2 segundos
    setTimeout(() => {
        window.location.href = "/pages/";
    }, 2000);
});
