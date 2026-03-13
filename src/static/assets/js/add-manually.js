const openCameraBtn = document.getElementById('openCameraBtn');
const closeCameraBtn = document.getElementById('closeCameraBtn');
const cameraModal = document.getElementById('cameraModal');
const confirmModal = document.getElementById('confirmModal');

const video = document.getElementById('cameraVideo');
const canvas = document.getElementById('cameraCanvas');
const captureBtn = document.getElementById('captureButton');
const resultCanvas = document.getElementById('resultCanvas');
const retakeBtn = document.getElementById('retakeButton');
const sendBtn = document.getElementById('sendButton');

let currentStream = null;
let scanner = null;
let requestAnimFrameId = null;
let finalExtractedCanvas = null;

// Aguarda OpenCV carregar
function waitForOpenCv(callback) {
    const check = setInterval(() => {
        if (typeof cv !== 'undefined' && cv.Mat) {
            clearInterval(check);
            scanner = new jscanify();
            callback();
        }
    }, 100);
}

// Inicia a câmera
async function startCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(t => t.stop());
    }

    try {
        currentStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            }
        });
        video.srcObject = currentStream;

        video.onloadedmetadata = () => {
            video.play();
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            drawHUD();
        };
    } catch (err) {
        console.error("Erro ao acessar a câmera:", err);
    }
}

function stopCamera() {
    if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);
    if (currentStream) {
        currentStream.getTracks().forEach(t => t.stop());
        currentStream = null;
    }
    video.srcObject = null;
}

// Loop do HUD JScanify
function drawHUD() {
    if (!scanner || video.paused) return;

    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    try {
        const highlighted = scanner.highlightPaper(canvas, { color: 'orange', thickness: 4 });
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(highlighted, 0, 0);
    } catch (e) { }

    requestAnimFrameId = requestAnimationFrame(drawHUD);
}

// Abrir modal da câmera
openCameraBtn.addEventListener('click', () => {
    cameraModal.style.display = 'flex';
    waitForOpenCv(() => startCamera());
});

// Fechar modal da câmera
closeCameraBtn.addEventListener('click', () => {
    cameraModal.style.display = 'none';
    stopCamera();
});

// Capturar foto
captureBtn.addEventListener('click', () => {
    if (!scanner || !currentStream) return;
    captureBtn.disabled = true;
    if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    tempCanvas.getContext('2d').drawImage(video, 0, 0);

    try {
        finalExtractedCanvas = scanner.extractPaper(tempCanvas, tempCanvas.width, tempCanvas.height);
    } catch (e) {
        finalExtractedCanvas = tempCanvas;
    }

    // Mostra na modal de confirmação
    const resCtx = resultCanvas.getContext('2d');
    const maxW = 800;
    const scale = Math.min(1.0, maxW / finalExtractedCanvas.width);
    resultCanvas.width = finalExtractedCanvas.width * scale;
    resultCanvas.height = finalExtractedCanvas.height * scale;
    resCtx.drawImage(finalExtractedCanvas, 0, 0, resultCanvas.width, resultCanvas.height);

    video.pause();
    cameraModal.style.display = 'none';
    confirmModal.style.display = 'flex';
    captureBtn.disabled = false;
});

// Tirar outra
retakeBtn.addEventListener('click', () => {
    confirmModal.style.display = 'none';
    cameraModal.style.display = 'flex';
    finalExtractedCanvas = null;
    video.play();
    drawHUD();
});

// Enviar nota e Adicionar barras
sendBtn.addEventListener('click', async () => {
    if (!finalExtractedCanvas) return;

    sendBtn.disabled = true;
    sendBtn.innerText = "Salvando...";

    const blob = await new Promise(resolve => {
        finalExtractedCanvas.toBlob(resolve, 'image/jpeg', 1.0);
    });

    const formData = new FormData();
    formData.append("file", blob, "nota_" + Date.now() + ".jpg");

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            console.log("Salvo:", data.path);
            confirmModal.style.display = 'none';
            stopCamera();
        } else {
            throw new Error("Erro no servidor");
        }
    } catch (e) {
        console.error(e);
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerText = "Enviar nota e Adicionar barras";
    }
});
