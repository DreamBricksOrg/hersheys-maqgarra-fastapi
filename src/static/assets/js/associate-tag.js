const tagModal = document.getElementById('tagModal');
const cancelBtn = document.getElementById('cancelButton');
const associateBtn = document.getElementById('associateButton');
const tagInput = document.getElementById('tag-input');
const btnVoltar = document.getElementById('btn-voltar');
const container = document.getElementById('container');

const progressModal = document.getElementById('progressModal');
const progressTitle = document.getElementById('progressTitle');
const successModal = document.getElementById('successModal');
const remainingCount = document.getElementById('remainingCount');

// Total de tags que precisam ser associadas (lê do localStorage)
let totalTags = getTags();
let associatedTags = 0;

// Atualiza o texto de "Faltam associar X tag(s)"
function updateRemaining() {
    const remaining = totalTags - associatedTags;
    remainingCount.textContent = remaining;
}

updateRemaining();

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
    tagModal.style.display = 'flex';
});

function closeModal() {
    tagModal.style.display = 'none';
    tagInput.value = '';
    tagInput.focus();
}

// Botões da modal
cancelBtn.addEventListener('click', closeModal);

associateBtn.addEventListener('click', () => {
    tagModal.style.display = 'none';
    tagInput.value = '';
    associatedTags++;

    const remaining = totalTags - associatedTags;
    updateRemaining();

    if (remaining <= 0) {
        // Todas as tags associadas!
        successModal.style.display = 'flex';
        resetCounters();
        setTimeout(() => {
            window.location.href = '/pages/';
        }, 2500);
    } else {
        // Ainda faltam tags
        progressTitle.textContent = `Faltam associar ${remaining} tag(s)`;
        progressModal.style.display = 'flex';
        setTimeout(() => {
            progressModal.style.display = 'none';
            tagInput.focus();
        }, 2000);
    }
});

// Botão voltar
btnVoltar.addEventListener('click', () => {
    window.location.href = '/pages/';
});

