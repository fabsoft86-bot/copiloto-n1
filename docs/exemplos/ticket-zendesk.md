# Exemplo de texto final para o Zendesk (fictício)

Gerado pelo Copiloto N1 a partir de um atendimento inventado (bug de NFC-e escalado ao N2).
Nenhum dado é real. O mesmo texto é verificado byte a byte em `pwa/tests/texto.test.js`.

```text
SOLICITANTE
Nome: Marina Souza
Empresa: Calçados Exemplo Ltda
CNPJ: 11.222.333/0001-81
Telefone: (11) 91234-5678 (confirmado com o cliente)
E-mail: marina.souza@exemplo.com.br

PROBLEMA
Título: Erro de assinatura ao emitir NFC-e no PDV após atualização
Tipo: Erro do sistema (bug)
Prioridade: Alta: sistema parado
Descrição: Ao finalizar a venda o PDV mostra erro de assinatura e não emite a NFC-e
Módulo/tela: PDV - emissão de NFC-e
Versão: 5.2.1
Quando começou: Hoje cedo, após a atualização de ontem
Recorrente: Sim
Mudança recente: Atualização para a 5.2.1 ontem à noite
Abrangência: Todos os caixas da loja

PASSOS PARA REPRODUZIR
1. Abrir o PDV e lançar um item
2. Finalizar a venda em dinheiro
3. O erro aparece ao emitir

INVESTIGAÇÃO
Evidências: print-erro-nfce.png
Reproduzido na base de teste: Sim
Dependências externas: Internet ok; SEFAZ operando

SITUAÇÃO
Situação: Escalado
Escalado para: N2 (desenvolvimento fiscal)
Cliente informado: Sim
```
