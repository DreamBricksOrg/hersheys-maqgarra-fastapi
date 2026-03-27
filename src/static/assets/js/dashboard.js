document.addEventListener('DOMContentLoaded', async () => {
    
    // Elementos da DOM
    const elConcedidas = document.getElementById('val-concedidas');
    const elConsumidas = document.getElementById('val-consumidas');
    const elDate = document.getElementById('dashboard-date');

    // Utilitário formatação de data
    const formatDateBr = (dateString) => {
        if (!dateString) return '';
        const [year, month, day] = dateString.split('-');
        return `${day}/${month}/${year}`;
    };

    try {
        // Obter timezone da máquina/browser mas API é servidor. Como queremos 'hoje', a API resolve.
        const response = await fetch('/api/stats/daily', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': 'capibarra-tablet-01',
                'x-device-id': 'tablet-01'
            }
        });
        
        if (!response.ok) {
            throw new Error('Falha ao obter estatísticas');
        }
        
        const data = await response.json();

        // Atualizar interface
        elDate.textContent = `Estatísticas de Hoje (${formatDateBr(data.dia)})`;
        elConcedidas.textContent = data.jogadas_concedidas !== undefined ? data.jogadas_concedidas : '0';
        elConsumidas.textContent = data.jogadas_consumidas !== undefined ? data.jogadas_consumidas : '0';

    } catch (error) {
        console.error('Erro ao buscar estatísticas diárias:', error);
        elDate.textContent = 'Estatísticas Indisponíveis';
        elConcedidas.innerHTML = '<span style="color:red; font-size: 1.5rem;">Erro</span>';
        elConsumidas.innerHTML = '<span style="color:red; font-size: 1.5rem;">Erro</span>';
    }
});
