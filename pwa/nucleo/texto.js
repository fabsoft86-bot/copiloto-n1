// Gera o texto final do chamado, em texto simples, para colar no Zendesk.
// Função pura: mesma entrada, mesma saída. Só entram as seções que se aplicam ao tipo/situação
// do atendimento; o que se aplica e não foi informado aparece como "NÃO INFORMADO" (assim o
// próximo analista vê a lacuna em vez de supor que o dado não existia).

import { passosAplicaveis } from './roteiro.js';

const NAO_INFORMADO = 'NÃO INFORMADO';

function rotuloDaOpcao(perfil, id, valor) {
  const passo = perfil.roteiro.find((p) => p.id === id);
  return passo?.opcoes?.find((o) => o.valor === valor)?.rotulo ?? valor;
}

function vazio(v) {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '') || (Array.isArray(v) && v.length === 0);
}

function linha(rotulo, valor) {
  return `${rotulo}: ${vazio(valor) ? NAO_INFORMADO : String(valor).trim()}`;
}

function simNao(v) {
  return typeof v === 'boolean' ? (v ? 'Sim' : 'Não') : null;
}

function lista(itens) {
  if (vazio(itens)) return [NAO_INFORMADO];
  return itens.map((x, i) => `${i + 1}. ${String(x).trim()}`);
}

/**
 * @param estado estado do roteiro (usa `estado.chamado` e os passos aplicáveis)
 * @param perfil perfil carregado
 * @returns {string} texto pronto para colar
 */
export function gerarTexto(estado, perfil) {
  const c = estado.chamado;
  const aplica = new Set(passosAplicaveis(estado, perfil).map((p) => p.id));
  const so = (id, rotulo, valor) => (aplica.has(id) ? [linha(rotulo, valor)] : []);

  const telefone = vazio(c.telefone) ? null : `${c.telefone} (${c.telefone_confirmado ? 'confirmado com o cliente' : 'não confirmado'})`;
  const tipo = rotuloDaOpcao(perfil, 'tipo', c.tipo);
  const prioridade = rotuloDaOpcao(perfil, 'prioridade', c.prioridade);
  const status = rotuloDaOpcao(perfil, 'status', c.status);

  const secoes = [];

  secoes.push(['SOLICITANTE', [linha('Nome', c.contato_nome), linha('Empresa', c.empresa), linha('CNPJ', c.cnpj), linha('Telefone', telefone), linha('E-mail', c.email)]]);

  secoes.push([
    'PROBLEMA',
    [
      linha('Título', c.titulo),
      linha('Tipo', tipo),
      linha('Prioridade', prioridade),
      linha('Descrição', c.descricao),
      linha('Módulo/tela', c.modulo),
      ...so('versao', 'Versão', c.versao),
      linha('Quando começou', c.quando_comecou),
      linha('Recorrente', simNao(c.recorrente)),
      linha('Mudança recente', c.mudanca_recente),
      linha('Abrangência', c.escopo),
    ],
  ]);

  if (aplica.has('passos_reproducao')) secoes.push(['PASSOS PARA REPRODUZIR', lista(c.passos_reproducao)]);

  const tecnico = [
    ...so('evidencias', 'Evidências', Array.isArray(c.evidencias) ? c.evidencias.join('; ') : c.evidencias),
    ...so('reproduzido_base_teste', 'Reproduzido na base de teste', simNao(c.reproduzido_base_teste)),
    ...so('dependencias_externas', 'Dependências externas', c.dependencias_externas),
  ];
  if (tecnico.length) secoes.push(['INVESTIGAÇÃO', tecnico]);

  const desfecho = [linha('Situação', status), ...so('causa_raiz', 'Causa identificada', c.causa_raiz), ...so('solucao', 'Solução aplicada', c.solucao), ...so('destino_escalonamento', 'Escalado para', c.destino_escalonamento), ...so('retorno_ao_cliente_feito', 'Cliente informado', simNao(c.retorno_ao_cliente_feito))];
  secoes.push(['SITUAÇÃO', desfecho]);

  return secoes.map(([titulo, linhas]) => `${titulo}\n${linhas.join('\n')}`).join('\n\n') + '\n';
}
