const btnTermos = document.getElementById("btn_termos");
const btnVoltar = document.getElementById("btn_voltar")
btnTermos.addEventListener("click", function(){
    window.location.href = '/pages/user-phone';
})

btnVoltar.addEventListener('click', () => {
    window.location.href = '/pages/user-qrcode';
});