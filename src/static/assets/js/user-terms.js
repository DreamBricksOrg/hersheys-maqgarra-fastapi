const btnTermos = document.getElementById("btn_termos");
const btnVoltar = document.getElementById("btn_voltar")
const params = new URLSearchParams(window.location.search);
const sid = params.get('sid');
const qid = params.get('qid');

btnTermos.addEventListener("click", function(){
    window.location.href = `/pages/user-phone?sid=${sid}&qid=${qid}`;
})

btnVoltar.addEventListener('click', () => {
    window.location.href = `/pages/user-qrcode?sid=${sid}&qid=${qid}`;
});