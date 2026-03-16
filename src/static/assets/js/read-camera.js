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

let lastResult = null;
let currentProcessedCdn = null;

// Acionar input nativo
openCameraBtn.addEventListener('click', () => {
    cameraInput.click();
});

// Tentar novamente (reabre input)
retakeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    cameraInput.value = ''; // reseta
    cameraInput.click();
});

// Quando o usuário tira a foto ou escolhe da galeria
cameraInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Mostrar modal de loading
    loadingModal.style.display = 'flex';
    modal.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append("file", file);

        // Upload para endpoint de processamento (CamScanner like)
        const response = await fetch("/api/upload/process", {
            method: "POST",
            body: formData
        });

        if (!response.ok) throw new Error("Erro ao processar imagem");
        const data = await response.json();

        // Salvar URL da imagem processada
        currentProcessedCdn = data.processed_cdn;

        // Mostrar no modal de confirmação
        previewImage.src = currentProcessedCdn + "?t=" + Date.now(); // cache bust
        loadingModal.style.display = 'none';
        modal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        alert("Erro ao processar a nota: " + err.message);
        loadingModal.style.display = 'none';
    }
});

// Confirmar foto processada e enviar pra Webmania
confirmBtn.addEventListener('click', async () => {
    if (!currentProcessedCdn) return;

    confirmBtn.disabled = true;
    confirmBtn.innerText = "Validando NFC-e...";

    try {
        const imageUrl = window.location.origin + currentProcessedCdn;
        const payloadJson = {
            imagens: [imageUrl],
            modelo: "nfce",
            antifraude: false
        };

        console.log("[DEBUG] Payload enviado:", JSON.stringify(payloadJson, null, 2));
        
        const nfceResponse = await fetch("/api/webmanianfe/validar/imagem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payloadJson)
        });

        console.log("[DEBUG] Response status:", nfceResponse.status, nfceResponse.statusText);

        if (!nfceResponse.ok) {
            const errText = await nfceResponse.text();
            console.error("[DEBUG] Response body (erro):", errText);
            let detail = "Erro ao validar NFC-e";
            try { detail = JSON.parse(errText).detail || detail; } catch(e) {}
            throw new Error(detail);
        }

        lastResult = await nfceResponse.json();
        console.log("[DEBUG] Validação sucesso:", JSON.stringify(lastResult, null, 2));

        // Sucesso -> exibe resultados
        modal.style.display = 'none';
        renderResult(lastResult);
        resultModal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        nfceResult.innerHTML = `<p class="error-msg">❌ ${err.message}</p>`;
        modal.style.display = 'none';
        resultModal.style.display = 'flex';
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerText = "Ficou Boa (Salvar)";
    }
});

function isHersheys(nome) {
    return (nome || '').toLowerCase().includes('her');
}

function renderResult(data) {
    const emitente = data.emitente || {};
    const produtos = data.produtos || [];
    const total = data.total || '0';

    let produtosHtml = produtos.map(p => {
        const highlighted = isHersheys(p.nome);
        return `
        <tr class="item-row ${highlighted ? 'item-selected' : ''}" data-qtd="${p.quantidade || 1}">
            <td>${p.nome || ''}</td>
            <td>${p.quantidade || ''} ${p.unidade || ''}</td>
            <td>R$ ${p.total || '0'}</td>
        </tr>`;
    }).join('');

    nfceResult.innerHTML = `
        <div class="nfce-emitente">
            <strong>${emitente.razao_social || 'Emitente desconhecido'}</strong>
            <span>CNPJ: ${emitente.cnpj || 'N/A'}</span>
        </div>
        <div class="nfce-info">
            <span>Nota: ${data.numero || 'N/A'} | Série: ${data.serie || 'N/A'}</span>
            <span>Data: ${data.data_emissao || 'N/A'}</span>
            <span>Status: <strong>${data.status || 'N/A'}</strong></span>
        </div>
        <div class="table-wrapper">
            <table class="nfce-table">
                <thead>
                    <tr><th>Produto</th><th>Qtd</th><th>Total</th></tr>
                </thead>
                <tbody>${produtosHtml}</tbody>
            </table>
        </div>
        <div class="nfce-total">
            <strong>TOTAL: R$ ${total}</strong>
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
    lastResult = null;
});

// Adicionar barras (soma a quantidade das linhas verdes/selecionadas)
addBarrasBtn.addEventListener('click', () => {
    const selectedRows = nfceResult.querySelectorAll('.item-row.item-selected');
    if (selectedRows.length > 0) {
        let totalQtd = 0;
        selectedRows.forEach(row => {
            const rawQtd = row.getAttribute('data-qtd') || '1';
            const qtdNum = parseFloat(rawQtd.replace(',', '.')) || 1;
            totalQtd += qtdNum;
        });
        
        addBarras(Math.floor(totalQtd));
    }
    resultModal.style.display = 'none';
    lastResult = null;
    window.location.href = '/pages/more-receipts';
});
