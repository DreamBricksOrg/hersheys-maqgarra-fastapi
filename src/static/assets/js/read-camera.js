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

const errorModal = document.getElementById('errorModal');
const errorTitle = document.getElementById('errorTitle');
const errorSubtitle = document.getElementById('errorSubtitle');
const errorDefaultActions = document.getElementById('errorDefaultActions');
const errorDuplicateActions = document.getElementById('errorDuplicateActions');

let currentFile = null;       // arquivo original da câmera
let processedCdn = null;      // URL CDN da imagem processada
let processedPath = null;     // path do servidor da imagem processada
let matchedItems = null;      // resultado do /api/products/match (array com matched)
let webmaniaData = null;      // JSON bruto da Webmania

const AUTH_HEADERS = {
    "x-api-key": "capibarra-tablet-01",
    "x-device-id": "tablet-01"
};

function showError(title, subtitle, isDuplicate) {
    errorTitle.textContent = title || 'Erro ao ler nota';
    if (subtitle) {
        errorSubtitle.textContent = subtitle;
        errorSubtitle.style.display = 'block';
    } else {
        errorSubtitle.style.display = 'none';
    }
    errorDefaultActions.style.display = isDuplicate ? 'none' : 'flex';
    errorDuplicateActions.style.display = isDuplicate ? 'flex' : 'none';
    errorModal.style.display = 'flex';
}

async function parseApiError(resp) {
    try {
        const body = await resp.json();
        if (body?.error) return body.error;
        if (body?.detail) return { message: body.detail };
    } catch (_) { /* ignore parse failure */ }
    return null;
}

// Acionar input nativo
openCameraBtn.addEventListener('click', () => cameraInput.click());

// Tentar novamente
retakeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    cameraInput.value = '';
    currentFile = null;
    processedCdn = null;
    matchedItems = null;
    webmaniaData = null;
    cameraInput.click();
});

// Passo 1: foto capturada → document_scanner → preview
cameraInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    currentFile = file;
    processedCdn = null;
    matchedItems = null;
    webmaniaData = null;

    loadingModal.style.display = 'flex';

    try {
        const form = new FormData();
        form.append("file", file);

        const resp = await fetch("/api/upload/process", { method: "POST", body: form });
        if (!resp.ok) throw new Error("Erro ao processar imagem");

        const data = await resp.json();
        processedCdn = data.processed_cdn;
        processedPath = data.processed_path;

        previewImage.src = processedCdn + "?t=" + Date.now();
        loadingModal.style.display = 'none';
        modal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        loadingModal.style.display = 'none';
        showError('Erro ao processar imagem', err.message);
    }
});

// Passo 2: "Enviar" → Webmania → /api/products/match → abre modal NFC-e
confirmBtn.addEventListener('click', async () => {
    if (!processedCdn) return;

    modal.style.display = 'none';
    loadingModal.style.display = 'flex';

    try {
        // 2a. Chama Webmania
        const imageUrl = window.location.origin + processedCdn;
        const webmaniaResp = await fetch("/api/webmanianfe/validar/imagem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ imagens: [imageUrl], modelo: "nfce", antifraude: false })
        });

        if (!webmaniaResp.ok) {
            const apiErr = await parseApiError(webmaniaResp);
            throw new Error(apiErr?.message || "Erro ao validar nota");
        }

        webmaniaData = await webmaniaResp.json();
        console.log("[DEBUG] Webmania:", webmaniaData);

        // 2b. Verifica quais produtos são Hersheys via backend
        const matchResp = await fetch("/api/products/match", {
            method: "POST",
            headers: { "Content-Type": "application/json", ...AUTH_HEADERS },
            body: JSON.stringify({ produtos: webmaniaData.produtos || [] })
        });

        if (!matchResp.ok) {
            const apiErr = await parseApiError(matchResp);
            throw new Error(apiErr?.message || "Erro ao verificar produtos");
        }

        const matchData = await matchResp.json();
        matchedItems = matchData.items;
        console.log("[DEBUG] Match result:", matchedItems);

        loadingModal.style.display = 'none';
        renderNfceResult(matchedItems, webmaniaData);
        resultModal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        loadingModal.style.display = 'none';
        showError('Erro ao validar nota', err.message);
    }
});

// Error modal buttons
function resetErrorModal() {
    errorModal.style.display = 'none';
    errorTitle.textContent = 'Erro ao ler nota';
    errorSubtitle.style.display = 'none';
    errorDefaultActions.style.display = 'flex';
    errorDuplicateActions.style.display = 'none';
}

document.getElementById('retryBtn').addEventListener('click', () => {
    resetErrorModal();
});
document.getElementById('dismissBtn').addEventListener('click', () => {
    resetErrorModal();
});
document.getElementById('addManualBtn').addEventListener('click', () => {
    window.location.href = '/pages/add-manually';
});

// Renderiza modal NFC-e com items já classificados pelo backend
function renderNfceResult(items, wData = {}) {
    const emitente = wData.emitente || {};

    const rowsHtml = items.map(item => {
        const cls = item.matched ? 'item-selected' : '';
        return `
        <tr class="item-row ${cls}" data-name="${encodeURIComponent(item.name)}" data-qtd="${item.quantity}" data-matched="${item.matched}">
            <td>${item.name}</td>
            <td>${item.quantity}</td>
        </tr>`;
    }).join('') || '<tr><td colspan="2">Nenhum produto encontrado</td></tr>';

    nfceResult.innerHTML = `
        ${emitente.razao_social ? `<div class="nfce-emitente">
            <strong>${emitente.razao_social}</strong>
            <span>CNPJ: ${emitente.cnpj || 'N/A'}</span>
        </div>` : ''}
        <div class="nfce-info">
            <span>Chave: <strong>${wData.chave || 'N/A'}</strong></span>
        </div>
        <div class="table-wrapper">
            <table class="nfce-table">
                <thead><tr><th>Produto</th><th>Qtd</th></tr></thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        </div>
    `;

    // Toggle: clicar numa linha não-matched → apenas seleciona visualmente
    nfceResult.querySelectorAll('.item-row').forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => {
            row.classList.toggle('item-selected');
        });
    });
}

// Fechar modal
closeResultModalBtn.addEventListener('click', () => {
    resultModal.style.display = 'none';
    matchedItems = null;
    webmaniaData = null;
});

// Passo 3: "Adicionar Barras" → coleta selecionados, salva no backend
addBarrasBtn.addEventListener('click', async () => {
    const selectedRows = nfceResult.querySelectorAll('.item-row.item-selected');
    const finalItems = [];

    selectedRows.forEach(row => {
        finalItems.push({
            name: decodeURIComponent(row.dataset.name),
            quantity: parseInt(row.dataset.qtd, 10) || 1,
            matched: true,
            _wasMatched: row.dataset.matched === 'true',
        });
    });

    const totalBars = finalItems.reduce((acc, i) => acc + i.quantity, 0);

    resultModal.style.display = 'none';
    loadingModal.style.display = 'flex';

    let saveSuccess = false;

    try {
        // Aprende nomes novos (itens selecionados que não eram matched originalmente)
        const learnPromises = finalItems
            .filter(item => !item._wasMatched)
            .map(item =>
                fetch("/api/products/learn", {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...AUTH_HEADERS },
                    body: JSON.stringify({ name: item.name })
                }).catch(e => console.warn("[DEBUG] Erro ao aprender:", item.name, e))
            );
        await Promise.all(learnPromises);

        const formData = new FormData();
        formData.append("image", currentFile);
        if (webmaniaData) formData.append("webmania_payload", JSON.stringify(webmaniaData));
        formData.append("matched_items", JSON.stringify(finalItems));
        if (processedPath) formData.append("processed_path", processedPath);

        const resp = await fetch("/api/receipts/image", {
            method: "POST",
            headers: AUTH_HEADERS,
            body: formData
        });

        if (!resp.ok) {
            const apiErr = await parseApiError(resp);
            const code = apiErr?.code || '';
            const message = apiErr?.message || 'Erro ao salvar nota';

            if (code === 'receipt_duplicate') {
                throw { title: 'Nota duplicada', subtitle: message, isDuplicate: true };
            }
            throw { title: 'Erro ao salvar nota', subtitle: message };
        }

        const receipt = await resp.json();
        console.log("[DEBUG] Nota salva:", receipt);
        addReceiptId(receipt.receipt_id);
        addBarras(totalBars);
        saveSuccess = true;

    } catch (err) {
        console.error("[DEBUG] Erro ao salvar nota:", err);
        loadingModal.style.display = 'none';
        showError(err.title || 'Erro ao salvar nota', err.subtitle || err.message, !!err.isDuplicate);
    } finally {
        loadingModal.style.display = 'none';
        matchedItems = null;
        webmaniaData = null;
        currentFile = null;
        if (saveSuccess) window.location.href = '/pages/more-receipts';
    }
});
