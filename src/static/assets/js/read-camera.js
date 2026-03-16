const video = document.getElementById('cameraVideo');
const canvas = document.getElementById('cameraCanvas');
const captureBtn = document.getElementById('captureButton');
const switchCameraBtn = document.getElementById('switchCameraButton');

const modal = document.getElementById('confirmationModal');
const resultCanvas = document.getElementById('resultCanvas');
const retakeBtn = document.getElementById('retakeButton');
const confirmBtn = document.getElementById('confirmButton');

const cameraModal = document.getElementById('cameraModal');
const openCameraBtn = document.getElementById('openCameraBtn');
const closeCameraBtn = document.getElementById('closeCameraBtn');

let currentStream = null;
let useRearCamera = true;
let scanner = null;
let requestAnimFrameId = null;
let finalExtractedCanvas = null;

// Aguarda OpenCV carregar e inicializa o jscanify
window.onload = () => {
    const checkOpenCv = setInterval(() => {
        if (typeof cv !== 'undefined' && cv.Mat) {
            clearInterval(checkOpenCv);
            scanner = new jscanify();
        }
    }, 100);
};

openCameraBtn.addEventListener('click', () => {
    cameraModal.style.display = 'flex';
    startCamera();
});

closeCameraBtn.addEventListener('click', () => {
    cameraModal.style.display = 'none';
    if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
    video.pause();
});

async function startCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
    }

    const constraints = {
        video: {
            facingMode: useRearCamera ? 'environment' : 'user',
            width: { ideal: 1920 },
            height: { ideal: 1080 }
        }
    };

    try {
        currentStream = await navigator.mediaDevices.getUserMedia(constraints);
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

// Loop do HUD: desenha o vídeo + contorno laranja do documento detectado
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
    } catch (e) { /* documento não detectado neste frame */ }

    requestAnimFrameId = requestAnimationFrame(drawHUD);
}

// Troca câmera
switchCameraBtn.addEventListener('click', () => {
    useRearCamera = !useRearCamera;
    if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);
    startCamera();
});

// Captura
captureBtn.addEventListener('click', () => {
    if (!scanner || !currentStream) return;
    captureBtn.disabled = true;
    if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);

    // Pega o frame atual em alta resolução direto do vídeo
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    tempCanvas.getContext('2d').drawImage(video, 0, 0);

    try {
        // Extrai o papel usando as dimensões reais do frame (sem forçar proporção A4)
        finalExtractedCanvas = scanner.extractPaper(tempCanvas, tempCanvas.width, tempCanvas.height);
    } catch (e) {
        // Fallback: usa o frame inteiro se não detectar bordas
        finalExtractedCanvas = tempCanvas;
    }

    // Mostra na modal (escala visual apenas para caber na tela)
    const resCtx = resultCanvas.getContext('2d');
    const maxVisualW = 800;
    const scale = Math.min(1.0, maxVisualW / finalExtractedCanvas.width);
    resultCanvas.width = finalExtractedCanvas.width * scale;
    resultCanvas.height = finalExtractedCanvas.height * scale;
    resCtx.drawImage(finalExtractedCanvas, 0, 0, resultCanvas.width, resultCanvas.height);

    video.pause();
    cameraModal.style.display = 'none';
    modal.style.display = 'flex';
    captureBtn.disabled = false;
});

// Tentar novamente
retakeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    cameraModal.style.display = 'flex';
    finalExtractedCanvas = null;
    video.play();
    drawHUD();
});

// Confirmar e salvar
confirmBtn.addEventListener('click', async () => {
    if (!finalExtractedCanvas) return;

    confirmBtn.disabled = true;
    confirmBtn.innerText = "Salvando...";

    // Converte o canvas extraído em blob JPEG na qualidade máxima
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
            console.log("Salvo em:", data.path);
            modal.style.display = 'none';
            if (requestAnimFrameId) cancelAnimationFrame(requestAnimFrameId);
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
                currentStream = null;
            }
        } else {
            throw new Error("Erro no servidor");
        }
    } catch (e) {
        console.error(e);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerText = "Ficou Boa (Salvar)";
    }
});
