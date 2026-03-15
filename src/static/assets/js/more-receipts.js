const btnSim = document.getElementById('btn-sim');
const btnNao = document.getElementById('btn-nao');

btnSim.addEventListener('click', () => {
    window.location.href = '/pages/';
});

btnNao.addEventListener('click', () => {
    window.location.href = '/pages/associate-tag';
});