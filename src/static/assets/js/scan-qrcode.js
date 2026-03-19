const qrInput = document.getElementById('qrcode-input');
const inputSpinner = document.getElementById('inputSpinner');
const resultModal = document.getElementById('resultModal');
const nfceResult = document.getElementById('nfceResult');
const closeModalBtn = document.getElementById('closeModalBtn');
const addBarrasBtn = document.getElementById('addBarrasBtn');
const container = document.getElementById('container');
const btnVoltar = document.getElementById('btn-voltar');

let lastResult = null;

// Garante foco permanente no input (exceto quando modal aberta)
qrInput.focus();
container.addEventListener('click', () => {
    if (resultModal.style.display === 'none' || !resultModal.style.display) {
        qrInput.focus();
    }
});
container.addEventListener('keydown', () => {
    if (resultModal.style.display === 'none' || !resultModal.style.display) {
        qrInput.focus();
    }
});

// Ao pressionar Enter no input, inicia o scraping
qrInput.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const url = qrInput.value.trim();
    if (!url) return;

    // Mostra spinner, esconde input
    qrInput.style.display = 'none';
    inputSpinner.style.display = 'flex';

    try {
        const response = await fetch('/api/nfce/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Erro ao processar nota');
        }

        lastResult = await response.json();
        renderResult(lastResult);
        resultModal.style.display = 'flex';
    } catch (err) {
        console.error(err);
        document.getElementById('errorModal').style.display = 'flex';
    } finally {
        // Volta o input
        inputSpinner.style.display = 'none';
        qrInput.style.display = 'block';
        qrInput.value = '';
        qrInput.focus();
    }
});

// Error modal buttons
document.getElementById('retryBtn').addEventListener('click', () => {
    document.getElementById('errorModal').style.display = 'none';
    qrInput.focus();
});
document.getElementById('addManualBtn').addEventListener('click', () => {
    window.location.href = '/pages/add-manually';
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

// Fechar modal
closeModalBtn.addEventListener('click', () => {
    resultModal.style.display = 'none';
    lastResult = null;
    qrInput.focus();
});

// Adicionar barras (soma a quantidade das linhas verdes/selecionadas)
addBarrasBtn.addEventListener('click', () => {
    const selectedRows = nfceResult.querySelectorAll('.item-row.item-selected');
    if (selectedRows.length > 0) {
        let totalQtd = 0;
        selectedRows.forEach(row => {
            const rawQtd = row.getAttribute('data-qtd') || '1';
            // Troca possível vírgula por ponto para virar float
            const qtdNum = parseFloat(rawQtd.replace(',', '.')) || 1;
            totalQtd += qtdNum;
        });
        
        // Garante que é um inteiro arredondado (ex. 5.0 -> 5)
        addBarras(Math.floor(totalQtd));
    }
    resultModal.style.display = 'none';
    lastResult = null;
    window.location.href = '/pages/more-receipts';
});

btnVoltar.addEventListener('click', () => {
    window.location.href = '/pages/';
});
