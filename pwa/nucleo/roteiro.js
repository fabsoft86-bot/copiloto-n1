// Motor do roteiro: decide qual é a próxima pergunta do atendimento.
//
// Funções puras sobre um "estado" imutável. Sem DOM, sem armazenamento: a tela só chama estas
// funções e desenha o resultado. Estado:
//   { chamado, respondidos: [id], puladas: [id], historico: [id], reabertas: [id] }

import { checarCampo, condicaoAtendida, textoVazio } from './validador.js';

/** Chamado novo: todo campo do perfil começa vazio. */
export function chamadoVazio(perfil) {
  const chamado = { telefone_confirmado: null, status: null };
  for (const campo of perfil.campos) {
    chamado[campo.id] = campo.validador === 'lista' ? [] : null;
  }
  return chamado;
}

export function novoAtendimento(perfil) {
  return { chamado: chamadoVazio(perfil), respondidos: [], puladas: [], historico: [], reabertas: [] };
}

/** Junta o passo do roteiro com as regras do campo (rótulo, pergunta e condição vêm do perfil). */
export function definicaoDoPasso(passo, perfil) {
  const campo = perfil.campos.find((c) => c.id === passo.id);
  return {
    id: passo.id,
    entrada: passo.entrada,
    opcoes: passo.opcoes ?? null,
    rotulo: passo.rotulo ?? campo?.rotulo ?? passo.id,
    pergunta: passo.pergunta ?? campo?.pergunta ?? passo.id,
    quando: passo.quando ?? campo?.quando ?? 'sempre',
    campo: campo ?? null,
  };
}

function passoPorId(id, perfil) {
  const passo = perfil.roteiro.find((p) => p.id === id);
  if (!passo) throw new Error(`Passo desconhecido no roteiro: '${id}'.`);
  return definicaoDoPasso(passo, perfil);
}

/** Passos que se aplicam a este atendimento (a condição `quando` depende de tipo e status). */
export function passosAplicaveis(estado, perfil) {
  return perfil.roteiro
    .map((p) => definicaoDoPasso(p, perfil))
    .filter((p) => condicaoAtendida(p.quando, estado.chamado));
}

function concluido(passo, estado, perfil) {
  if (estado.reabertas.includes(passo.id)) return false; // o analista voltou para corrigir
  if (estado.respondidos.includes(passo.id) || estado.puladas.includes(passo.id)) return true;
  // Dado que já veio preenchido por outra fonte e está correto não precisa ser perguntado de novo.
  if (passo.id === 'status') return false;
  return passo.campo ? checarCampo(passo.campo, estado.chamado, perfil) === null : false;
}

/** A próxima pergunta, ou null quando não resta nenhuma. */
export function proximoPasso(estado, perfil) {
  const aplicaveis = passosAplicaveis(estado, perfil);
  const reaberto = estado.reabertas.at(-1);
  if (reaberto) {
    const passo = aplicaveis.find((p) => p.id === reaberto);
    if (passo) return passo;
  }
  return aplicaveis.find((p) => !concluido(p, estado, perfil)) ?? null;
}

/** { feitos, total }: quantos passos aplicáveis já foram atendidos (respondidos ou pulados). */
export function progresso(estado, perfil) {
  const passos = passosAplicaveis(estado, perfil);
  const feitos = passos.filter((p) => concluido(p, estado, perfil)).length;
  return { feitos, total: passos.length };
}

function converter(passo, valor) {
  switch (passo.entrada) {
    case 'lista':
      return String(valor ?? '')
        .split('\n')
        .map((linha) => linha.trim())
        .filter(Boolean);
    case 'simnao':
      return valor === true || valor === 'sim';
    case 'texto':
    case 'texto_longo':
      return String(valor ?? '').trim();
    default:
      return valor;
  }
}

function semDuplicata(lista, id) {
  return lista.filter((x) => x !== id);
}

/**
 * Registra a resposta de um passo. Resposta vazia (texto em branco, lista sem itens) conta como pular.
 * Para `telefone`, `valor` é { telefone, confirmado }.
 */
export function responder(estado, perfil, id, valor) {
  const passo = passoPorId(id, perfil);
  const chamado = { ...estado.chamado };

  if (passo.entrada === 'telefone') {
    const telefone = String(valor?.telefone ?? '').trim();
    if (telefone === '') return pular(estado, perfil, id);
    chamado.telefone = telefone;
    chamado.telefone_confirmado = valor?.confirmado === true;
  } else {
    const convertido = converter(passo, valor);
    const vazio = Array.isArray(convertido) ? convertido.length === 0 : textoVazio(convertido);
    if (vazio) return pular(estado, perfil, id);
    chamado[id] = convertido;
  }

  return {
    chamado,
    respondidos: [...semDuplicata(estado.respondidos, id), id],
    puladas: semDuplicata(estado.puladas, id),
    historico: [...semDuplicata(estado.historico, id), id],
    reabertas: semDuplicata(estado.reabertas, id),
  };
}

/** Deixa a pergunta para depois: não será feita de novo, mas continua como pendência na revisão. */
export function pular(estado, perfil, id) {
  passoPorId(id, perfil); // valida o id
  return {
    ...estado,
    respondidos: semDuplicata(estado.respondidos, id),
    puladas: [...semDuplicata(estado.puladas, id), id],
    historico: [...semDuplicata(estado.historico, id), id],
    reabertas: semDuplicata(estado.reabertas, id),
  };
}

/** Reabre um passo já feito para o analista corrigir a resposta. */
export function reabrir(estado, id) {
  return {
    ...estado,
    respondidos: semDuplicata(estado.respondidos, id),
    puladas: semDuplicata(estado.puladas, id),
    historico: semDuplicata(estado.historico, id),
    reabertas: [...semDuplicata(estado.reabertas, id), id],
  };
}

/** Id do passo anterior (o último atendido), ou null se não houver. */
export function passoAnterior(estado) {
  return estado.historico.length ? estado.historico[estado.historico.length - 1] : null;
}

/** Volta às perguntas puladas, para o analista tentar de novo. */
export function retomarPuladas(estado) {
  return { ...estado, puladas: [] };
}

export { passoPorId };
