const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');
const sorryModal = document.getElementById('sorryModal');

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/';
});

btnNao.addEventListener('click', () => {
    const tags = getTags();
    if (tags <= 0) {
        sorryModal.style.display = 'flex';
        resetCounters();
        setTimeout(() => {
            window.location.href = '/pages/';
        }, 3000);
    } else {
        window.location.href = '/pages/associate-tag';
    }
});