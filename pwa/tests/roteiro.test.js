import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  novoAtendimento,
  proximoPasso,
  progresso,
  responder,
  pular,
  reabrir,
  passoAnterior,
  retomarPuladas,
  passosAplicaveis,
} from '../nucleo/roteiro.js';
import { validar } from '../nucleo/validador.js';

const perfil = JSON.parse(readFileSync(new URL('../perfis/software_house.json', import.meta.url), 'utf-8'));

const CLIENTE = {
  contato_nome: 'Marina Souza',
  empresa: 'Calçados Exemplo Ltda',
  cnpj: '11.222.333/0001-81',
  telefone: { telefone: '(11) 91234-5678', confirmado: true },
  email: 'marina.souza@exemplo.com.br',
};

/** Simula um atendimento: responde cada pergunta com o script; o que não está no script é pulado. */
function atender(script) {
  let estado = novoAtendimento(perfil);
  const perguntadas = [];
  for (let guarda = 0; guarda < 100; guarda++) {
    const passo = proximoPasso(estado, perfil);
    if (!passo) return { estado, perguntadas };
    perguntadas.push(passo.id);
    estado = passo.id in script ? responder(estado, perfil, passo.id, script[passo.id]) : pular(estado, perfil, passo.id);
  }
  throw new Error('o roteiro não terminou: laço infinito');
}

// --- Aceite da Etapa 1: três atendimentos fictícios do início ao fim ----------------------------

test('atendimento 1, dúvida resolvida: não pergunta nada de erro e fecha com nota 100', () => {
  const { estado, perguntadas } = atender({
    ...CLIENTE,
    tipo: 'duvida',
    descricao: 'Como emitir o relatório mensal de vendas por vendedor',
    modulo: 'Relatórios',
    quando_comecou: 'Primeira vez que precisa',
    recorrente: false,
    mudanca_recente: 'nenhuma',
    escopo: 'Só ela',
    prioridade: 'baixa',
    titulo: 'Dúvida sobre relatório mensal de vendas por vendedor',
    status: 'resolvido',
    causa_raiz: 'Filtro de vendedor estava escondido em Opções avançadas',
    solucao: 'Orientada a usar Relatórios > Vendas > Opções avançadas > Vendedor',
    retorno_ao_cliente_feito: true,
  });
  for (const so_de_erro of ['versao', 'evidencias', 'passos_reproducao', 'reproduzido_base_teste', 'dependencias_externas', 'destino_escalonamento']) {
    assert.ok(!perguntadas.includes(so_de_erro), `dúvida não deveria perguntar '${so_de_erro}'`);
  }
  const r = validar(estado.chamado, perfil);
  assert.equal(r.nota, 100);
  assert.equal(r.pendencias.length, 0);
  assert.equal(proximoPasso(estado, perfil), null);
});

test('atendimento 2, erro escalado: pergunta o que é de bug e o destino, mas não a causa/solução', () => {
  const { estado, perguntadas } = atender({
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
  });
  for (const de_bug of ['versao', 'evidencias', 'passos_reproducao', 'reproduzido_base_teste']) {
    assert.ok(perguntadas.includes(de_bug), `bug deveria perguntar '${de_bug}'`);
  }
  assert.ok(perguntadas.includes('destino_escalonamento'));
  assert.ok(!perguntadas.includes('solucao'));
  assert.ok(!perguntadas.includes('causa_raiz'));
  assert.deepEqual(estado.chamado.passos_reproducao.length, 3);
  assert.equal(validar(estado.chamado, perfil).nota, 100);
});

test('atendimento 3, melhoria em aberto: só o essencial e nada de desfecho', () => {
  const { estado, perguntadas } = atender({
    ...CLIENTE,
    tipo: 'melhoria',
    descricao: 'Gostaria de filtrar o relatório de estoque por fornecedor',
    modulo: 'Estoque',
    quando_comecou: 'Pedido novo',
    recorrente: false,
    mudanca_recente: 'nenhuma',
    escopo: 'Toda a empresa',
    prioridade: 'baixa',
    titulo: 'Melhoria: filtro por fornecedor no relatório de estoque',
    status: 'aberto',
  });
  for (const id of ['versao', 'solucao', 'causa_raiz', 'destino_escalonamento', 'retorno_ao_cliente_feito']) {
    assert.ok(!perguntadas.includes(id), `melhoria aberta não deveria perguntar '${id}'`);
  }
  assert.equal(validar(estado.chamado, perfil).nota, 100);
});

// --- Comportamento do motor ---------------------------------------------------------------------

test('o roteiro começa pela identificação e a ordem do perfil é respeitada', () => {
  let estado = novoAtendimento(perfil);
  assert.equal(proximoPasso(estado, perfil).id, 'contato_nome');
  estado = responder(estado, perfil, 'contato_nome', 'Marina');
  assert.equal(proximoPasso(estado, perfil).id, 'empresa');
});

test('pular não repete a pergunta, mas o campo segue como pendência na revisão', () => {
  let estado = novoAtendimento(perfil);
  estado = pular(estado, perfil, 'contato_nome');
  assert.notEqual(proximoPasso(estado, perfil).id, 'contato_nome');
  const r = validar(estado.chamado, perfil);
  assert.ok(r.pendencias.some((p) => p.campo === 'contato_nome'));
});

test('resposta em branco equivale a pular', () => {
  let estado = novoAtendimento(perfil);
  estado = responder(estado, perfil, 'contato_nome', '   ');
  assert.ok(estado.puladas.includes('contato_nome'));
  assert.equal(estado.chamado.contato_nome, null);
});

test('telefone não confirmado não trava o roteiro: segue e vira pendência', () => {
  let estado = novoAtendimento(perfil);
  estado = responder(estado, perfil, 'telefone', { telefone: '(11) 91234-5678', confirmado: false });
  assert.notEqual(proximoPasso(estado, perfil).id, 'telefone');
  const r = validar(estado.chamado, perfil);
  assert.ok(r.pendencias.some((p) => p.campo === 'telefone' && p.problema.includes('não confirmado')));
});

test('mudar o tipo para bug passa a exigir as perguntas de erro', () => {
  let estado = novoAtendimento(perfil);
  assert.ok(!passosAplicaveis(estado, perfil).some((p) => p.id === 'versao'));
  estado = responder(estado, perfil, 'tipo', 'bug');
  assert.ok(passosAplicaveis(estado, perfil).some((p) => p.id === 'versao'));
});

test('voltar: reabrir um passo devolve a pergunta e permite corrigir a resposta', () => {
  let estado = novoAtendimento(perfil);
  estado = responder(estado, perfil, 'contato_nome', 'Marna');
  estado = responder(estado, perfil, 'empresa', 'Exemplo Ltda');
  assert.equal(passoAnterior(estado), 'empresa');
  estado = reabrir(estado, 'empresa');
  assert.equal(proximoPasso(estado, perfil).id, 'empresa');
  estado = responder(estado, perfil, 'empresa', 'Exemplo Comércio Ltda');
  assert.equal(estado.chamado.empresa, 'Exemplo Comércio Ltda');
});

test('retomar puladas faz a pergunta voltar', () => {
  let estado = novoAtendimento(perfil);
  estado = pular(estado, perfil, 'contato_nome');
  estado = retomarPuladas(estado);
  assert.equal(proximoPasso(estado, perfil).id, 'contato_nome');
});

test('progresso conta só os passos que se aplicam e cresce quando o tipo é bug', () => {
  let estado = novoAtendimento(perfil);
  const antes = progresso(estado, perfil).total;
  estado = responder(estado, perfil, 'tipo', 'bug');
  const depois = progresso(estado, perfil);
  assert.ok(depois.total > antes);
  assert.equal(depois.feitos, 1);
});

test('as funções não alteram o estado recebido', () => {
  const estado = novoAtendimento(perfil);
  const copia = structuredClone(estado);
  responder(estado, perfil, 'contato_nome', 'Marina');
  pular(estado, perfil, 'empresa');
  assert.deepEqual(estado, copia);
});

test('todo passo do roteiro existe no perfil e tem pergunta e tipo de entrada', () => {
  for (const passo of perfil.roteiro) {
    const def = passosAplicaveis({ chamado: { tipo: 'bug', status: 'resolvido' } }, perfil).find((p) => p.id === passo.id);
    // status=resolvido e tipo=bug juntos aplicam todos menos destino_escalonamento
    if (passo.id === 'destino_escalonamento') continue;
    assert.ok(def, `passo '${passo.id}' deveria aplicar-se a bug resolvido`);
    assert.ok(def.pergunta && def.rotulo && def.entrada, `passo '${passo.id}' incompleto`);
  }
});
