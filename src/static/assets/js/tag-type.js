const tagVirtual = document.getElementById("tag-virtual"); 
const tagFisica = document.getElementById("tag-fisica"); 

tagVirtual.addEventListener('click', () => {
    window.location.href = '/pages/associate-tag';
});

tagFisica.addEventListener('click', () => {
    window.location.href = '/pages/associate-tag-physical';
});