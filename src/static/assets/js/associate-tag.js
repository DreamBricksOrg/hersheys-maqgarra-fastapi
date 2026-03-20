const btnVoltar = document.getElementById('btn-voltar');
const btnInicio = document.getElementById('btn-inicio');
const remainingCount = document.getElementById('remainingCount');
const dynamicQRCode = document.getElementById('dynamicQRCode');
const qrLoader = document.getElementById('qrLoader');
const qrStatusText = document.getElementById('qrStatusText');

const AUTH_HEADERS = {
    'Content-Type': 'application/json',
    'x-api-key': 'capibarra-tablet-01',
    'x-device-id': 'tablet-01'
};

let totalTags = getTags() || 0;

async function generateVirtualTags() {
    const sessionId = getSessionId();
    const queueId = getQueueId();

    if (!sessionId || !queueId) {
        console.error('Session or Player ID missing');
        qrStatusText.textContent = 'Erro: Sessão não encontrada';
        qrLoader.style.display = 'none';
        return;
    }

    try {
        // Verifica tags existentes para a sessão
        const existingTagsResp = await fetch(`/api/tags/session/${sessionId}`, { headers: AUTH_HEADERS });
        const existingData = await existingTagsResp.json();
        const existingCount = existingData.tags ? existingData.tags.length : 0;

        console.log(`[DEBUG] Tags existentes: ${existingCount}, Necessárias: ${totalTags}`);

        // Gera as tags que faltam
        for (let i = existingCount; i < totalTags; i++) {
            qrStatusText.textContent = `Gerando tag ${i + 1} de ${totalTags}...`;
            const resp = await fetch('/api/tags/generate', {
                method: 'POST',
                headers: AUTH_HEADERS,
                body: JSON.stringify({
                    session_id: sessionId,
                    delivery_mode: 'digital'
                })
            });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                console.error('Erro ao gerar tag:', err);
                // Se for limite atingido, podemos parar
                if (err.error?.code === 'session_tag_limit_reached') break;
            }
        }

        // Sucesso: mostra o QR Code
        qrLoader.style.display = 'none';
        qrStatusText.style.display = 'none';
        

        const baseUrl = window.location.origin;
        const finalUrl = `${baseUrl}/pages/user-qrcode?pid=${queueId}`;
        dynamicQRCode.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(finalUrl)}`;
        dynamicQRCode.style.display = 'block';

    } catch (err) {
        console.error('Erro no fluxo de geração:', err);
        qrStatusText.textContent = 'Erro ao processar tags digitais';
        qrLoader.style.display = 'none';
    }
}

function updateUI() {
    if (remainingCount) {
        remainingCount.textContent = totalTags;
    }
}

updateUI();
generateVirtualTags();

btnInicio.addEventListener('click', () => {
    document.getElementById('confirmResetModal').style.display = 'flex';
});

document.getElementById('cancelResetBtn').addEventListener('click', () => {
    document.getElementById('confirmResetModal').style.display = 'none';
});

document.getElementById('confirmResetBtn').addEventListener('click', () => {
    resetCounters();
    clearReceiptIds();
    clearSessionId();
    clearQrUrl();
    clearPlayerId();
    clearQueueId();
    clearQueueNumber();
    window.location.href = '/pages/';
});

btnVoltar.addEventListener('click', () => {
    window.history.back();
});
