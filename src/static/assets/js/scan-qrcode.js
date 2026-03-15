const qrInput = document.getElementById('qrcode-input');
const inputSpinner = document.getElementById('inputSpinner');
const resultModal = document.getElementById('resultModal');
const nfceResult = document.getElementById('nfceResult');
const closeModalBtn = document.getElementById('closeModalBtn');
const addBarrasBtn = document.getElementById('addBarrasBtn');

let lastResult = null;

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
        nfceResult.innerHTML = `<p class="error-msg">❌ ${err.message}</p>`;
        resultModal.style.display = 'flex';
    } finally {
        // Volta o input
        inputSpinner.style.display = 'none';
        qrInput.style.display = 'block';
        qrInput.value = '';
        qrInput.focus();
    }
});

function renderResult(data) {
    const emitente = data.emitente || {};
    const produtos = data.produtos || [];
    const total = data.total || '0';

    let produtosHtml = produtos.map(p => `
        <tr>
            <td>${p.nome || ''}</td>
            <td>${p.quantidade || ''} ${p.unidade || ''}</td>
            <td>R$ ${p.total || '0'}</td>
        </tr>
    `).join('');

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
        <table class="nfce-table">
            <thead>
                <tr><th>Produto</th><th>Qtd</th><th>Total</th></tr>
            </thead>
            <tbody>${produtosHtml}</tbody>
        </table>
        <div class="nfce-total">
            <strong>TOTAL: R$ ${total}</strong>
        </div>
    `;
}

// Fechar modal
closeModalBtn.addEventListener('click', () => {
    resultModal.style.display = 'none';
    lastResult = null;
    qrInput.focus();
});

// Adicionar barras (conta produtos)
addBarrasBtn.addEventListener('click', () => {
    if (lastResult && lastResult.produtos) {
        const totalBarras = lastResult.produtos.length;
        addBarras(totalBarras);
    }
    resultModal.style.display = 'none';
    lastResult = null;
    qrInput.focus();
});
