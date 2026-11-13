// Tela do roteiro guiado. Toda a lógica está em ../nucleo (testada sem navegador); este arquivo só
// desenha o estado e encaminha os cliques e as teclas. Nada sai do dispositivo.

import {
  novoAtendimento,
  proximoPasso,
  progresso,
  responder,
  pular,
  reabrir,
  passoAnterior,
  retomarPuladas,
  passoPorId,
} from '../nucleo/roteiro.js';
import { validar, checarCampo } from '../nucleo/validador.js';
import { gerarTexto } from '../nucleo/texto.js';

const raiz = document.getElementById('app');

let perfil;
let estado;
let alerta = null; // { id, mensagem, valor }: validação que espera decisão do analista
let atalhos = {}; // tecla -> ação, só para a pergunta que está na tela

// --- utilidades de DOM (sem innerHTML: o que o analista digita nunca vira HTML) ------------------

function h(tag, atributos = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [nome, valor] of Object.entries(atributos)) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (nome.startsWith('on')) el.addEventListener(nome.slice(2), valor);
    else if (nome === 'class') el.className = valor;
    else el.setAttribute(nome, valor === true ? '' : valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined || filho === false) continue;
    el.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return el;
}

// --- formatação -----------------------------------------------------------------------------------

function textoDoValor(passo, chamado) {
  const v = chamado[passo.id];
  if (passo.id === 'telefone') return `${v} (${chamado.telefone_confirmado ? 'confirmado' : 'não confirmado'})`;
  if (Array.isArray(v)) return v.map((x, i) => `${i + 1}. ${x}`).join('\n');
  if (typeof v === 'boolean') return v ? 'Sim' : 'Não';
  if (passo.opcoes) return passo.opcoes.find((o) => o.valor === v)?.rotulo ?? String(v);
  return v === null || v === undefined ? '' : String(v);
}

function classeDaNota(nota) {
  if (nota >= 80) return 'bom';
  if (nota >= 50) return 'atencao';
  return 'ruim';
}

// --- ações ------------------------------------------------------------------------------------------

function atualizar(novoEstado) {
  estado = novoEstado;
  alerta = null;
  render();
}

function enviar(passo, valor) {
  const novo = responder(estado, perfil, passo.id, valor);
  const digitada = ['texto', 'texto_longo', 'telefone'].includes(passo.entrada);
  if (digitada && passo.campo && novo.respondidos.includes(passo.id)) {
    const problema = checarCampo(passo.campo, novo.chamado, perfil);
    if (problema) {
      alerta = { id: passo.id, mensagem: problema, valor };
      render();
      return;
    }
  }
  atualizar(novo);
}

function novoAtendimentoComConfirmacao() {
  if (estado.respondidos.length > 0 && !window.confirm('Descartar este atendimento e começar outro?')) return;
  atualizar(novoAtendimento(perfil));
}

// --- peças da tela --------------------------------------------------------------------------------------

function topo() {
  const { nota } = validar(estado.chamado, perfil);
  return h(
    'header',
    { class: 'topo' },
    h('h1', {}, 'Copiloto N1'),
    h('span', { class: `nota ${classeDaNota(nota)}`, title: 'Nota de qualidade do chamado até agora' }, `Nota ${nota}`),
    h('button', { class: 'discreto', type: 'button', onclick: novoAtendimentoComConfirmacao }, 'Novo'),
  );
}

function valorInicial(passo) {
  if (alerta && alerta.id === passo.id) return alerta.valor;
  const v = estado.chamado[passo.id];
  if (passo.entrada === 'telefone') return { telefone: v ?? '', confirmado: estado.chamado.telefone_confirmado === true };
  if (Array.isArray(v)) return v.join('\n');
  return v ?? '';
}

/** Monta a entrada da pergunta. Devolve os elementos e uma função que lê o valor digitado. */
function entradaDoPasso(passo) {
  const inicial = valorInicial(passo);
  switch (passo.entrada) {
    case 'texto':
      return { nos: [h('input', { type: 'text', id: 'resposta', autocomplete: 'off', value: inicial, 'data-foco': true })], ler: () => document.getElementById('resposta').value };
    case 'texto_longo':
      return { nos: [h('textarea', { id: 'resposta', 'data-foco': true }, inicial), h('p', { class: 'dica' }, 'Ctrl+Enter para responder')], ler: () => document.getElementById('resposta').value };
    case 'lista':
      return { nos: [h('textarea', { id: 'resposta', 'data-foco': true }, inicial), h('p', { class: 'dica' }, 'Um item por linha. Ctrl+Enter para responder')], ler: () => document.getElementById('resposta').value };
    case 'telefone':
      return {
        nos: [
          h('input', { type: 'tel', id: 'resposta', autocomplete: 'off', inputmode: 'tel', value: inicial.telefone, 'data-foco': true }),
          h('label', { class: 'confirma' }, h('input', { type: 'checkbox', id: 'confirmado', checked: inicial.confirmado }), 'Repeti o número e o cliente confirmou'),
        ],
        ler: () => ({ telefone: document.getElementById('resposta').value, confirmado: document.getElementById('confirmado').checked }),
      };
    default:
      return null;
  }
}

function botoesDeEscolha(passo) {
  atalhos = {};
  const botoes = passo.opcoes.map((opcao, i) => {
    const acao = () => enviar(passo, opcao.valor);
    atalhos[String(i + 1)] = acao;
    return h('button', { type: 'button', onclick: acao, 'data-foco': i === 0 }, h('span', { class: 'tecla' }, String(i + 1)), opcao.rotulo);
  });
  return h('div', { class: 'opcoes' }, botoes);
}

function botoesSimNao(passo) {
  atalhos = { s: () => enviar(passo, true), n: () => enviar(passo, false) };
  return h(
    'div',
    { class: 'opcoes duas' },
    h('button', { type: 'button', onclick: atalhos.s, 'data-foco': true }, h('span', { class: 'tecla' }, 'S'), 'Sim'),
    h('button', { type: 'button', onclick: atalhos.n }, h('span', { class: 'tecla' }, 'N'), 'Não'),
  );
}

function caixaDeAlerta(passo) {
  if (!alerta || alerta.id !== passo.id) return null;
  return h(
    'div',
    { class: 'alerta', role: 'alert' },
    h('p', {}, `Atenção: ${alerta.mensagem}.`),
    h(
      'div',
      { class: 'acoes' },
      h('button', { type: 'button', onclick: () => document.getElementById('resposta')?.focus() }, 'Corrigir'),
      h('button', { type: 'button', onclick: () => atualizar(responder(estado, perfil, passo.id, alerta.valor)) }, 'Seguir mesmo assim'),
    ),
  );
}

function jaAnotado() {
  if (estado.historico.length === 0) return null;
  const itens = estado.historico.flatMap((id) => {
    const passo = passoPorId(id, perfil);
    const pulado = estado.puladas.includes(id);
    return [
      h('dt', {}, passo.rotulo),
      h(
        'dd',
        {},
        pulado ? h('span', { class: 'pulado' }, 'pulada') : textoDoValor(passo, estado.chamado),
        ' ',
        h('button', { type: 'button', class: 'discreto', onclick: () => atualizar(reabrir(estado, id)) }, 'editar'),
      ),
    ];
  });
  return h('details', { class: 'cartao anotado' }, h('summary', {}, `O que já anotei (${estado.historico.length})`), h('dl', {}, itens));
}

function telaDaPergunta(passo) {
  const { feitos, total } = progresso(estado, perfil);
  const entrada = entradaDoPasso(passo);
  atalhos = {};

  let corpo;
  if (passo.entrada === 'escolha') corpo = botoesDeEscolha(passo);
  else if (passo.entrada === 'simnao') corpo = botoesSimNao(passo);
  else {
    corpo = h('form', {
      onsubmit: (e) => {
        e.preventDefault();
        enviar(passo, entrada.ler());
      },
      onkeydown: (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          e.currentTarget.requestSubmit();
        }
      },
    }, entrada.nos, caixaDeAlerta(passo), h('div', { class: 'acoes' }, h('button', { type: 'submit', class: 'principal' }, 'Responder')));
  }

  const anterior = passoAnterior(estado);
  return [
    h('p', { class: 'sr-only', role: 'status' }, `Pergunta ${feitos + 1} de ${total}: ${passo.pergunta}`),
    h(
      'section',
      { class: 'cartao' },
      h('p', { class: 'progresso-texto' }, `Pergunta ${Math.min(feitos + 1, total)} de ${total}`),
      h('progress', { max: total, value: feitos, 'aria-label': 'Progresso do roteiro' }),
      h('p', { class: 'rotulo' }, passo.rotulo),
      h('h2', {}, passo.entrada === 'escolha' || passo.entrada === 'simnao' ? passo.pergunta : h('label', { for: 'resposta' }, passo.pergunta)),
      corpo,
      h(
        'div',
        { class: 'acoes' },
        anterior ? h('button', { type: 'button', class: 'discreto', onclick: () => atualizar(reabrir(estado, anterior)) }, 'Voltar') : null,
        h('button', { type: 'button', class: 'discreto', onclick: () => atualizar(pular(estado, perfil, passo.id)) }, 'Pular'),
      ),
    ),
    jaAnotado(),
  ];
}

async function copiarTexto(texto, botao) {
  let ok = false;
  try {
    await navigator.clipboard.writeText(texto);
    ok = true;
  } catch {
    const area = document.getElementById('texto-final');
    area.focus();
    area.select();
    try { ok = document.execCommand('copy'); } catch { ok = false; }
  }
  botao.textContent = ok ? 'Copiado!' : 'Não consegui copiar: selecione o texto e use Ctrl+C';
  setTimeout(() => { botao.textContent = 'Copiar texto'; }, 2500);
}

function blocoDoTexto() {
  const texto = gerarTexto(estado, perfil);
  const botao = h('button', { type: 'button', class: 'principal', 'data-foco': true, onclick: () => copiarTexto(texto, botao) }, 'Copiar texto');
  return h(
    'section',
    { class: 'cartao' },
    h('p', { class: 'rotulo' }, 'Texto para colar no Zendesk'),
    h('textarea', { id: 'texto-final', class: 'texto-final', readonly: true, rows: 14, 'aria-label': 'Texto final do chamado' }, texto),
    h('div', { class: 'acoes' }, botao),
  );
}

function telaDaRevisao() {
  const r = validar(estado.chamado, perfil);
  const pendencias = r.pendencias.map((p) =>
    h(
      'div',
      { class: 'pendencia' },
      h('h3', {}, h('span', { class: `sev ${p.severidade}` }, p.severidade), p.rotulo),
      h('p', { class: 'problema' }, p.problema),
      h('p', {}, p.pergunta),
      h('button', { type: 'button', onclick: () => atualizar(reabrir(estado, p.campo)) }, 'Perguntar agora'),
    ),
  );
  return [
    h(
      'section',
      { class: 'cartao' },
      h('p', { class: 'rotulo' }, 'Revisão do atendimento'),
      h('p', { class: `revisao-nota ${classeDaNota(r.nota)}` }, `${r.nota}`),
      h('p', { class: 'revisao-estado' }, r.aprovado ? (r.pendencias.length ? 'Sem bloqueios, mas há itens a melhorar.' : 'Chamado completo.') : `Faltam ${r.bloqueantes.length} item(ns) bloqueante(s).`),
      r.slaHoras ? h('p', { class: 'dica' }, `SLA da prioridade: ${r.slaHoras} h`) : null,
      r.avisos.length ? h('ul', { class: 'aviso-lista' }, r.avisos.map((a) => h('li', {}, a))) : null,
      pendencias,
      h(
        'div',
        { class: 'acoes' },
        estado.puladas.length ? h('button', { type: 'button', onclick: () => atualizar(retomarPuladas(estado)) }, `Retomar ${estado.puladas.length} puladas`) : null,
      ),
    ),
    blocoDoTexto(),
    h('div', { class: 'acoes' }, h('button', { type: 'button', onclick: novoAtendimentoComConfirmacao }, 'Novo atendimento')),
    jaAnotado(),
  ];
}

// --- laço de desenho ---------------------------------------------------------------------------------------

function render() {
  const passo = proximoPasso(estado, perfil);
  atalhos = {};
  raiz.replaceChildren(topo(), ...(passo ? telaDaPergunta(passo) : telaDaRevisao()));
  const foco = raiz.querySelector('[data-foco]');
  if (foco) foco.focus();
}

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const alvo = e.target;
  if (alvo instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(alvo.tagName)) return;
  const acao = atalhos[e.key.toLowerCase()];
  if (acao) {
    e.preventDefault();
    acao();
  }
});

async function iniciar() {
  try {
    const resposta = await fetch('./perfis/software_house.json');
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    perfil = await resposta.json();
  } catch (erro) {
    raiz.replaceChildren(h('p', { role: 'alert' }, `Não consegui carregar o roteiro (${erro.message}). Abra o app por um servidor (npm start), não direto do arquivo.`));
    return;
  }
  estado = novoAtendimento(perfil);
  render();
}

iniciar();
