const openCameraBtn = document.getElementById('openCameraBtn');
const cameraInput = document.getElementById('cameraInput');

const loadingModal = document.getElementById('loadingModal');
const modal = document.getElementById('confirmationModal');
const previewImage = document.getElementById('previewImage');
const retakeBtn = document.getElementById('retakeButton');
const confirmBtn = document.getElementById('confirmButton');

const resultModal = document.getElementById('resultModal');
const nfceResult = document.getElementById('nfceResult');
const closeResultModalBtn = document.getElementById('closeResultModalBtn');
const addBarrasBtn = document.getElementById('addBarrasBtn');

let lastReceiptResult = null;   // ReceiptResponse do backend
let webmaniaData = null;        // JSON da Webmania
let currentFile = null;         // Arquivo original da câmera
let processedCdn = null;        // URL CDN da imagem processada pelo scanner

// Acionar input nativo
openCameraBtn.addEventListener('click', () => {
    cameraInput.click();
});

// Tentar novamente (reabre input)
retakeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    cameraInput.value = '';
    currentFile = null;
    processedCdn = null;
    webmaniaData = null;
    cameraInput.click();
});

// Passo 1: foto capturada → processa com document_scanner → preview
cameraInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    currentFile = file;
    processedCdn = null;
    webmaniaData = null;

    loadingModal.style.display = 'flex';
    modal.style.display = 'none';

    try {
        const uploadForm = new FormData();
        uploadForm.append("file", file);

        const uploadResponse = await fetch("/api/upload/process", {
            method: "POST",
            body: uploadForm
        });

        if (!uploadResponse.ok) throw new Error("Erro ao processar imagem");
        const uploadData = await uploadResponse.json();

        processedCdn = uploadData.processed_cdn;

        // Mostrar preview no modal de confirmação
        previewImage.src = processedCdn + "?t=" + Date.now();
        loadingModal.style.display = 'none';
        modal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        loadingModal.style.display = 'none';
        document.getElementById('errorModal').style.display = 'flex';
    }
});

// Passo 2: "Enviar" → chama Webmania com URL processada → abre modal NFC-e
confirmBtn.addEventListener('click', async () => {
    if (!processedCdn) return;

    modal.style.display = 'none';
    loadingModal.style.display = 'flex';

    try {
        const imageUrl = window.location.origin + processedCdn;
        console.log("[DEBUG] Chamando Webmania com:", imageUrl);

        const webmaniaResponse = await fetch("/api/webmanianfe/validar/imagem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                imagens: [imageUrl],
                modelo: "nfce",
                antifraude: false
            })
        });

        if (!webmaniaResponse.ok) {
            const errText = await webmaniaResponse.text();
            let detail = "Erro ao validar nota na Webmania";
            try { detail = JSON.parse(errText).detail || detail; } catch (e) {}
            throw new Error(detail);
        }

        webmaniaData = await webmaniaResponse.json();
        console.log("[DEBUG] Webmania retornou:", JSON.stringify(webmaniaData, null, 2));

        loadingModal.style.display = 'none';
        renderNfceResult(webmaniaData);
        resultModal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        loadingModal.style.display = 'none';
        document.getElementById('errorModal').style.display = 'flex';
    }
});

// Error modal buttons
document.getElementById('retryBtn').addEventListener('click', () => {
    document.getElementById('errorModal').style.display = 'none';
});
document.getElementById('addManualBtn').addEventListener('click', () => {
    window.location.href = '/pages/add-manually';
});

function isHersheys(nome) {
    return (nome || '').toLowerCase().includes('her');
}

// Renderiza o JSON da Webmania no modal NFC-e
function renderNfceResult(data) {
    const emitente = data.emitente || {};
    const produtos = data.produtos || [];

    const produtosHtml = produtos.length > 0
        ? produtos.map(p => {
            const highlighted = isHersheys(p.nome);
            return `
            <tr class="item-row ${highlighted ? 'item-selected' : ''}" data-qtd="${p.quantidade || 1}">
                <td>${p.nome || ''}</td>
                <td>${p.quantidade || ''} ${p.unidade || ''}</td>
            </tr>`;
        }).join('')
        : '<tr><td colspan="2">Nenhum produto encontrado</td></tr>';

    nfceResult.innerHTML = `
        <div class="nfce-emitente">
            <strong>${emitente.razao_social || 'Emitente desconhecido'}</strong>
            <span>CNPJ: ${emitente.cnpj || 'N/A'}</span>
        </div>
        <div class="nfce-info">
            <span>Nota: ${data.numero || 'N/A'} | Série: ${data.serie || 'N/A'}</span>
            <span>Data: ${data.data_emissao || 'N/A'}</span>
            <span>Chave: <strong>${data.chave || 'N/A'}</strong></span>
        </div>
        <div class="table-wrapper">
            <table class="nfce-table">
                <thead>
                    <tr><th>Produto</th><th>Qtd</th></tr>
                </thead>
                <tbody>${produtosHtml}</tbody>
            </table>
        </div>
    `;

    // Toggle ao clicar na linha
    nfceResult.querySelectorAll('.item-row').forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => {
            row.classList.toggle('item-selected');
        });
    });
}

// Fechar modal de resultado
closeResultModalBtn.addEventListener('click', () => {
    resultModal.style.display = 'none';
    webmaniaData = null;
    lastReceiptResult = null;
});

// Passo 3: "Adicionar Barras" → salva no backend com imagem + JSON Webmania
addBarrasBtn.addEventListener('click', async () => {
    if (!currentFile || !webmaniaData) {
        // Sem dados Webmania: adiciona barras manualmente das linhas selecionadas
        const selectedRows = nfceResult.querySelectorAll('.item-row.item-selected');
        let totalQtd = 0;
        selectedRows.forEach(row => {
            totalQtd += parseFloat((row.getAttribute('data-qtd') || '1').replace(',', '.')) || 1;
        });
        if (totalQtd > 0) addBarras(Math.floor(totalQtd));

        resultModal.style.display = 'none';
        webmaniaData = null;
        window.location.href = '/pages/more-receipts';
        return;
    }

    // Desabilitar botão durante o envio
    addBarrasBtn.disabled = true;
    loadingModal.style.display = 'flex';
    resultModal.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append("image", currentFile);
        formData.append("webmania_payload", JSON.stringify(webmaniaData));

        console.log("[DEBUG] Salvando nota em /api/receipts/image...");

        const receiptResponse = await fetch("/api/receipts/image", {
            method: "POST",
            headers: {
                "x-api-key": "capibarra-tablet-01",
                "x-device-id": "tablet-01"
            },
            body: formData
        });

        if (!receiptResponse.ok) {
            const errText = await receiptResponse.text();
            let detail = "Erro ao salvar nota";
            try { detail = JSON.parse(errText).detail || detail; } catch (e) {}
            throw new Error(detail);
        }

        lastReceiptResult = await receiptResponse.json();
        console.log("[DEBUG] Nota salva:", JSON.stringify(lastReceiptResult, null, 2));

        // Adiciona barras: usa found_bars ou linhas selecionadas
        const selectedRows = nfceResult.querySelectorAll('.item-row.item-selected');
        if (selectedRows.length > 0) {
            let totalQtd = 0;
            selectedRows.forEach(row => {
                totalQtd += parseFloat((row.getAttribute('data-qtd') || '1').replace(',', '.')) || 1;
            });
            addBarras(Math.floor(totalQtd));
        } else {
            addBarras(lastReceiptResult.found_bars || 0);
        }

    } catch (err) {
        console.error(err);
    } finally {
        addBarrasBtn.disabled = false;
        loadingModal.style.display = 'none';
        webmaniaData = null;
        lastReceiptResult = null;
        window.location.href = '/pages/more-receipts';
    }
});
