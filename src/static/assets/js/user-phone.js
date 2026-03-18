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