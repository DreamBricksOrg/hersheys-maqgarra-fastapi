const tagModal = document.getElementById('tagModal');
const tagValue = document.getElementById('tagValue');
const cancelBtn = document.getElementById('cancelButton');
const associateBtn = document.getElementById('associateButton');
const switchCameraBtn = document.getElementById('switchCameraButton');

let html5QrCode = null;
let useRearCamera = true;
let scanning = false;

function startScanner() {
    if (html5QrCode && scanning) {
        html5QrCode.stop().then(() => {
            scanning = false;
            initScanner();
        }).catch(() => initScanner());
    } else {
        initScanner();
    }
}

function initScanner() {
    html5QrCode = new Html5Qrcode("qrReader");

    const config = {
        fps: 10,
        qrbox: { width: 300, height: 300 },
        disableFlip: false,
    };

    const cameraId = useRearCamera
        ? { facingMode: "environment" }
        : { facingMode: "user" };

    html5QrCode.start(
        cameraId,
        config,
        onQrCodeDetected,
        () => {} // Silencia erros de frames sem QR
    ).then(() => {
        scanning = true;
    }).catch(err => {
        console.error("Erro ao iniciar câmera:", err);
    });
}

function onQrCodeDetected(decodedText) {
    // Para o scanner ao encontrar QR
    if (html5QrCode && scanning) {
        html5QrCode.pause(true);
    }

    // Exibe o texto na modal
    tagValue.innerText = decodedText;
    tagModal.style.display = 'flex';
}

function closeModal() {
    tagModal.style.display = 'none';
    tagValue.innerText = '';

    // Retoma o scanner
    if (html5QrCode && scanning) {
        html5QrCode.resume();
    }
}

// Botões da modal
cancelBtn.addEventListener('click', closeModal);
associateBtn.addEventListener('click', closeModal);

// Trocar câmera
switchCameraBtn.addEventListener('click', () => {
    useRearCamera = !useRearCamera;
    startScanner();
});

// Inicia ao carregar a página
window.onload = startScanner;
