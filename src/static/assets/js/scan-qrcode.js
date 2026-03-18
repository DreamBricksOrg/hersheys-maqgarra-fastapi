const qrInput = document.getElementById('qrcode-input');
const inputSpinner = document.getElementById('inputSpinner');
const resultModal = document.getElementById('resultModal');
const nfceResult = document.getElementById('nfceResult');
const closeModalBtn = document.getElementById('closeModalBtn');
const addBarrasBtn = document.getElementById('addBarrasBtn');
const container = document.getElementById('container');
const btnVoltar = document.getElementById('btn-voltar');

let scrapedData = null;   // JSON completo do scrapper
let matchedItems = null;  // itens classificados pelo /api/products/match
let qrUrl = null;         // URL original escaneada do QR Code

const AUTH_HEADERS = {
    'x-api-key': 'capibarra-tablet-01',
    'x-device-id': 'tablet-01'
};

// Foco permanente no input (exceto quando modal aberta)
qrInput.focus();
container.addEventListener('click', () => {
    if (resultModal.style.display === 'none' || !resultModal.style.display) qrInput.focus();
});
container.addEventListener('keydown', () => {
    if (resultModal.style.display === 'none' || !resultModal.style.display) qrInput.focus();
});

// Ao pressionar Enter: scrape → match → modal
qrInput.addEventListener('keydown', async (e) => {
    if (e.key !== 'Enter') return;
    const url = qrInput.value.trim();
    if (!url) return;
    qrUrl = url;

    qrInput.style.display = 'none';
    inputSpinner.style.display = 'flex';

    try {
        // Passo 1: Scrape da NFC-e
        const scrapeResp = await fetch('/api/nfce/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        if (!scrapeResp.ok) {
            const err = await scrapeResp.json().catch(() => ({}));
            throw new Error(err.detail || 'Erro ao processar nota');
        }

        scrapedData = await scrapeResp.json();
        console.log('[DEBUG] Scrape:', scrapedData);

        // Passo 2: Classificar produtos via backend
        const matchResp = await fetch('/api/products/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...AUTH_HEADERS },
            body: JSON.stringify({ produtos: scrapedData.produtos || [] }),
        });

        if (!matchResp.ok) throw new Error('Erro ao verificar produtos');

        const matchData = await matchResp.json();
        matchedItems = matchData.items;
        console.log('[DEBUG] Match:', matchedItems);

        renderResult(matchedItems, scrapedData);
        resultModal.style.display = 'flex';

    } catch (err) {
        console.error(err);
        document.getElementById('errorModal').style.display = 'flex';
    } finally {
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

// Renderiza com itens já classificados pelo backend
function renderResult(items, wData = {}) {
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
            <span>Nota: ${wData.numero || 'N/A'} | Série: ${wData.serie || 'N/A'}</span>
            <span>Data: ${wData.data_emissao || 'N/A'}</span>
            <span>Chave: <strong>${wData.chave || 'N/A'}</strong></span>
        </div>
        <div class="table-wrapper">
            <table class="nfce-table">
                <thead><tr><th>Produto</th><th>Qtd</th></tr></thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        </div>
    `;

    // Toggle visual apenas (learn acontece ao enviar)
    nfceResult.querySelectorAll('.item-row').forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => row.classList.toggle('item-selected'));
    });
}

// Fechar modal
closeModalBtn.addEventListener('click', () => {
    resultModal.style.display = 'none';
    scrapedData = null;
    matchedItems = null;
    qrInput.focus();
});

// "Adicionar Barras": learn nomes novos + salvar no backend
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

    try {
        // Learn: nomes novos selecionados manualmente
        const learnPromises = finalItems
            .filter(i => !i._wasMatched)
            .map(i => fetch('/api/products/learn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...AUTH_HEADERS },
                body: JSON.stringify({ name: i.name })
            }).catch(err => console.warn('[DEBUG] Erro learn:', i.name, err)));
        await Promise.all(learnPromises);

        // Salvar nota via novo endpoint
        const savePayload = {
            scraped_payload: scrapedData,
            matched_items: finalItems.map(({ _wasMatched, ...item }) => item),
            qr_url: qrUrl,
        };

        const saveResp = await fetch('/api/receipts/qr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...AUTH_HEADERS },
            body: JSON.stringify(savePayload),
        });

        if (!saveResp.ok) {
            const err = await saveResp.json().catch(() => ({}));
            console.error('[DEBUG] Erro ao salvar:', err.detail);
        } else {
            console.log('[DEBUG] Nota salva:', await saveResp.json());
        }

        addBarras(totalBars);

    } catch (err) {
        console.error('[DEBUG] Erro:', err);
    } finally {
        scrapedData = null;
        matchedItems = null;
        qrUrl = null;
        window.location.href = '/pages/more-receipts';
    }
});

btnVoltar.addEventListener('click', () => {
    window.location.href = '/pages/';
});
