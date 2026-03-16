const tagModal = document.getElementById('tagModal');
const tagValue = document.getElementById('tagValue');
const cancelBtn = document.getElementById('cancelButton');
const associateBtn = document.getElementById('associateButton');
const tagInput = document.getElementById('tag-input');
const btnVoltar = document.getElementById('btn-voltar');
const container = document.getElementById('container');

// Garante foco permanente no input (exceto quando modal aberta)
tagInput.focus();
container.addEventListener('click', () => {
    if (tagModal.style.display === 'none' || !tagModal.style.display) {
        tagInput.focus();
    }
});
container.addEventListener('keydown', () => {
    if (tagModal.style.display === 'none' || !tagModal.style.display) {
        tagInput.focus();
    }
});

// Ao pressionar Enter no input
tagInput.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const tagText = tagInput.value.trim();
    if (!tagText) return;

    // Exibe o texto na modal
    tagValue.innerText = tagText;
    tagModal.style.display = 'flex';
});

function closeModal() {
    tagModal.style.display = 'none';
    tagValue.innerText = '';
    tagInput.value = '';
    tagInput.focus();
}

// Botões da modal
cancelBtn.addEventListener('click', closeModal);
associateBtn.addEventListener('click', () => {
    resetCounters();
    window.location.href = '/pages/';
});

// Botão voltar
btnVoltar.addEventListener('click', () => {
    window.location.href = '/pages/';
});
