function mascaraTelefone(event) {
    let input = event;
    let valor = input.value;

    // Remove tudo que não é dígito
    valor = valor.replace(/\D/g, "");

    // Formata o valor
    valor = valor.replace(/^(\d{2})(\d)/g, "($1) $2"); // Coloca parênteses no DDD
    valor = valor.replace(/(\d)(\d{4})$/, "$1-$2");    // Coloca hífen no número

    input.value = valor;
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get('sid');
    const qid = params.get('qid');

    const phoneInput = document.getElementById('phone-input');
    const btnProcessar = document.getElementById('btnProcessar');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const successModal = document.getElementById('successModal');
    const errorModal = document.getElementById('errorModal');
    const errorMessage = document.getElementById('errorMessage');
    const btnSuccess = document.getElementById('btnSuccess');
    const btnError = document.getElementById('btnError');

    if (!sid || !qid) {
        console.error('Missing sid or qid parameters');
    }

    btnProcessar.addEventListener('click', async () => {
        const phone = phoneInput.value.replace(/\D/g, "");
        const qrCodeUrl = `${window.location.origin}/pages/user-qrcode?sid=${sid}&qid=${qid}`;

        if (phone.length < 10) {
            errorMessage.textContent = 'Por favor, insira um número de telefone válido com DDD.';
            errorModal.style.display = 'flex';
            return;
        }

        loadingOverlay.style.display = 'flex';

        try {
            const response = await fetch(`/api/sessions/${sid}/phone`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': 'capibarra-tablet-01',
                    'x-device-id': 'tablet-01'
                },
                body: JSON.stringify({ 
                    phone: phone,
                    qr_code_url: qrCodeUrl
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Falha ao atualizar o telefone');
            }

            // Sucesso
            loadingOverlay.style.display = 'none';
            successModal.style.display = 'flex';

        } catch (error) {
            loadingOverlay.style.display = 'none';
            errorMessage.textContent = error.message || 'Ocorreu um erro inesperado. Tente novamente.';
            errorModal.style.display = 'flex';
        }
    });

    btnSuccess.addEventListener('click', () => {
        window.location.href = `/pages/user-qrcode?sid=${sid}&qid=${qid}`;
    });

    btnError.addEventListener('click', () => {
        errorModal.style.display = 'none';
    });
});