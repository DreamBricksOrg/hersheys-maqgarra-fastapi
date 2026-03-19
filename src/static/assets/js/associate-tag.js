const btnVoltar = document.getElementById('btn-voltar');
const remainingCount = document.getElementById('remainingCount');

let totalTags = getTags() || 0;

async function updateRemaining() {
    if (remainingCount) {
        remainingCount.textContent = totalTags;
    }

    const dynamicQRCode = document.getElementById('dynamicQRCode');
    if (dynamicQRCode && totalTags > 0) {
        try {
            const response = await fetch(`/api/tags?amount=${totalTags}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': 'capibarra-tablet-01',
                    'x-device-id': 'tablet-01'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }

            const data = await response.json();

            // Activating each tag as requested
            for (const tagKey of data.tags) {
                try {
                    await fetch(`/api/tags/${tagKey}/activate`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'x-api-key': 'capibarra-tablet-01',
                            'x-device-id': 'tablet-01'
                        },
                        body: JSON.stringify({ reason: "associated_for_play" })
                    });
                } catch (activationError) {
                    console.error(`Failed to activate tag ${tagKey}:`, activationError);
                }
            }

            // Atrela as tags aos receipts atuais
            try {
                const receiptIds = getReceiptIds();
                if (receiptIds.length > 0) {
                    await fetch('/api/tags/associate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'x-api-key': 'capibarra-tablet-01',
                            'x-device-id': 'tablet-01'
                        },
                        body: JSON.stringify({
                            receipt_ids: receiptIds,
                            tags: data.tags
                        })
                    });
                    console.log('[DEBUG] Tags associadas aos receipts:', receiptIds);
                }
            } catch (assocError) {
                console.error('Erro ao associar tags aos receipts:', assocError);
            }

            const tagKeys = data.tags.join(','); // Create comma-separated string

            const baseUrl = window.location.origin;
            const targetUrl = `${baseUrl}/pages/user-qrcode?tags=${tagKeys}`;
            dynamicQRCode.src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(targetUrl)}`;
        } catch (error) {
            console.error("Failed to fetch tags for QR Code:", error);
        }
    }
}

updateRemaining();

btnVoltar.addEventListener('click', () => {
    resetCounters();
    clearReceiptIds();
    window.location.href = '/pages/';
});
