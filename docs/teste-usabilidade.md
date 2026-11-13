# Teste de usabilidade: 10 cenários fictícios

Todos os dados são inventados. Objetivo: ver se o roteiro **flui** e se o texto final é **bom o bastante para colar no Zendesk**. Isto valida a usabilidade, não o valor; o valor só se prova com atendimentos reais (ver critério em `backlog.md`).

## Como fazer
1. `cd pwa; npm start` e abra http://localhost:8080.
2. Para cada cenário, **leia o cenário como se fosse o cliente falando**, inicie um atendimento e cronometre do primeiro clique até copiar o texto.
3. Preencha a tabela do fim. Em "onde travou" escreva a pergunta ou tela que atrapalhou.

## Cenários

| # | Tipo esperado | Situação | O que o cliente diz | O que testar |
|---|---|---|---|---|
| 1 | Bug, escalado | Fiscal | Rodrigo (Mercado Bom Preço, CNPJ 45.723.174/0001-10, tel. 11 98888-1111, rodrigo@bompreco.exemplo) diz que, desde hoje de manhã, o PDV 2 rejeita NFC-e com "Rejeição 539 – duplicidade". Versão 5.2.1, só o caixa 2, sem print. Prioridade alta. Você escala para o N2 fiscal. | Fluxo completo de bug; "sem evidência" (pule); escalonamento |
| 2 | Dúvida, resolvida | Relatórios | Paula (Farmácia Saúde Viva) quer saber como tirar o relatório de vendas por forma de pagamento. Você a orienta em Relatórios > Financeiro > Formas de pagamento. | Dúvida não pergunta nada de bug; fechar com solução |
| 3 | Melhoria, aberto | Estoque | Anderson (Auto Peças Zé) pede um alerta de estoque mínimo por e-mail. Sem urgência. | Roteiro curto; nada de causa/solução |
| 4 | Bug, resolvido | Cadastro | Luciana (Boutique Aurora) não consegue salvar cliente: "CPF inválido", mas o CPF está certo. Era o campo preenchido com espaço no fim. Você orientou a apagar e digitar de novo; resolveu. | Causa raiz e solução; texto com desfecho |
| 5 | Bug, aberto | Impressão | Gilberto (Padaria Pão Quente) diz que a impressora de cupom corta a última linha. Não sabe a versão e não sabe quando começou. | **Pular** perguntas sem resposta; ver "NÃO INFORMADO" no texto |
| 6 | Customização, aberto | Etiquetas | Fernanda (Moda Bella) quer incluir o código de barras na etiqueta de preço. | Tipo "Customização" aparece e faz sentido |
| 7 | Bug, escalado | Lentidão | Marcos (Distribuidora Norte) diz que o sistema está lento desde a atualização de ontem, todos os usuários, 12 máquinas. Prioridade alta. Você não conseguiu reproduzir na base de teste. | "Reproduzido na base de teste = Não"; escalonamento |
| 8 | Dúvida, resolvida | Acesso | Tatiane (Clínica Sorriso) perdeu a senha de administrador. O telefone que ela passa tem **um dígito a menos** e o CNPJ que ela dita é 12.345.678/0001-00 (inválido). | Alertas de telefone e CNPJ, "Corrigir" e "Seguir mesmo assim" |
| 9 | Bug, resolvido | Backup | Eduardo (Mecânica Rápida) relata que o backup noturno falhou 2 dias seguidos. Era disco cheio no servidor; ele liberou espaço e rodou de novo. Resolvido. | Lista de passos; "dependências externas" |
| 10 | Qualquer | Correção no meio | Comece um atendimento de bug e, na pergunta 8, perceba que errou o nome da empresa na 2. **Use Voltar/Editar** para corrigir sem perder o resto. | Voltar, editar pelo "O que já anotei", nota atualizando |

## Perguntas de fechamento
1. Em que cenário você ficou mais tempo e por quê?
2. Alguma pergunta pareceu desnecessária? Alguma faltou?
3. O texto colado no Zendesk precisaria de ajuste manual? Qual?
4. No celular, a digitação ficou tolerável?
5. Você usaria isto no meio de uma ligação de verdade, ou atrapalharia a conversa?

## Registro

| # | Tempo (min:seg) | Perguntas puladas | Onde travou | Texto ficou bom? (s/n) | Observações |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |
| 9 | | | | | |
| 10 | | | | | |

## Como ler o resultado
- Tempo médio **abaixo de ~2 min** por atendimento e texto bom em 8 de 10: seguir para o teste de uma semana com atendimentos reais.
- Muitas travadas na mesma pergunta: ajustar o roteiro (é só mudar o JSON do perfil) e repetir esses cenários.
- Você sentiu que atrapalha mais do que ajuda: dizer com franqueza. É exatamente o sinal que queremos antes de investir mais.
