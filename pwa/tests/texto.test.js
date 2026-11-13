import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { novoAtendimento, proximoPasso, responder, pular } from '../nucleo/roteiro.js';
import { gerarTexto } from '../nucleo/texto.js';

const perfil = JSON.parse(readFileSync(new URL('../perfis/software_house.json', import.meta.url), 'utf-8'));

function atender(script) {
  let estado = novoAtendimento(perfil);
  for (let i = 0; i < 100; i++) {
    const passo = proximoPasso(estado, perfil);
    if (!passo) return estado;
    estado = passo.id in script ? responder(estado, perfil, passo.id, script[passo.id]) : pular(estado, perfil, passo.id);
  }
  throw new Error('laço infinito');
}

const CLIENTE = {
  contato_nome: 'Marina Souza',
  empresa: 'Calçados Exemplo Ltda',
  cnpj: '11.222.333/0001-81',
  telefone: { telefone: '(11) 91234-5678', confirmado: true },
  email: 'marina.souza@exemplo.com.br',
};

const BUG_ESCALADO = {
  ...CLIENTE,
  tipo: 'bug',
  descricao: 'Ao finalizar a venda o PDV mostra erro de assinatura e não emite a NFC-e',
  modulo: 'PDV - emissão de NFC-e',
  versao: '5.2.1',
  quando_comecou: 'Hoje cedo, após a atualização de ontem',
  recorrente: true,
  mudanca_recente: 'Atualização para a 5.2.1 ontem à noite',
  escopo: 'Todos os caixas da loja',
  prioridade: 'alta',
  passos_reproducao: 'Abrir o PDV e lançar um item\nFinalizar a venda em dinheiro\nO erro aparece ao emitir',
  evidencias: 'print-erro-nfce.png',
  reproduzido_base_teste: true,
  dependencias_externas: 'Internet ok; SEFAZ operando',
  titulo: 'Erro de assinatura ao emitir NFC-e no PDV após atualização',
  status: 'escalado',
  destino_escalonamento: 'N2 (desenvolvimento fiscal)',
  retorno_ao_cliente_feito: true,
};

test('bug escalado: texto completo, com passos numerados e destino, sem causa/solução', () => {
  const texto = gerarTexto(atender(BUG_ESCALADO), perfil);
  assert.equal(
    texto,
    readFileSync(new URL('./casos/texto_bug_escalado.txt', import.meta.url), 'utf-8'),
  );
});

test('dúvida resolvida: mostra causa e solução, não mostra seções de bug', () => {
  const texto = gerarTexto(
    atender({
      ...CLIENTE,
      tipo: 'duvida',
      descricao: 'Como emitir o relatório mensal por vendedor',
      modulo: 'Relatórios',
      quando_comecou: 'Primeira vez',
      recorrente: false,
      mudanca_recente: 'nenhuma',
      escopo: 'Só ela',
      prioridade: 'baixa',
      titulo: 'Dúvida sobre relatório mensal por vendedor',
      status: 'resolvido',
      causa_raiz: 'Filtro escondido em Opções avançadas',
      solucao: 'Orientada a usar Relatórios > Vendas > Opções avançadas',
      retorno_ao_cliente_feito: true,
    }),
    perfil,
  );
  assert.match(texto, /Solução aplicada: Orientada/);
  assert.match(texto, /Causa identificada: Filtro escondido/);
  assert.doesNotMatch(texto, /PASSOS PARA REPRODUZIR|INVESTIGAÇÃO|Versão|Escalado para/);
});

test('o que se aplica e foi pulado aparece como NÃO INFORMADO; o que não se aplica some', () => {
  const texto = gerarTexto(atender({ ...BUG_ESCALADO, versao: undefined, evidencias: undefined }), perfil);
  assert.match(texto, /Versão: NÃO INFORMADO/);
  assert.match(texto, /Evidências: NÃO INFORMADO/);
  assert.doesNotMatch(texto, /Solução aplicada/);
});

test('telefone não confirmado é dito no texto', () => {
  const texto = gerarTexto(atender({ ...BUG_ESCALADO, telefone: { telefone: '(11) 91234-5678', confirmado: false } }), perfil);
  assert.match(texto, /Telefone: \(11\) 91234-5678 \(não confirmado\)/);
});

test('atendimento recém-aberto não quebra: tudo NÃO INFORMADO', () => {
  const texto = gerarTexto(novoAtendimento(perfil), perfil);
  assert.match(texto, /Nome: NÃO INFORMADO/);
  assert.match(texto, /Situação: NÃO INFORMADO/);
});

test('o texto não usa Markdown nem caracteres que o Zendesk poderia reinterpretar', () => {
  const texto = gerarTexto(atender(BUG_ESCALADO), perfil);
  assert.doesNotMatch(texto, /[*_`#>|]|\[.*\]\(.*\)/);
});
