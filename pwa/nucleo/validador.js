// Validador de qualidade do chamado: nota, pendências e a pergunta sugerida para cada uma.
//
// Porta de src/copiloto_n1/validador.py (especificação de referência). Mesmas regras, mesmos
// resultados: tests/validador.test.js confere os dois contra tests/casos/validador.json, gerado
// pelo Python. Sem DOM, sem dependências.

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const ORDEM_SEVERIDADE = { bloqueante: 0, importante: 1, sugestao: 2 };

export function textoVazio(valor) {
  return valor === null || valor === undefined || (typeof valor === 'string' && valor.trim() === '');
}

/** Avalia 'sempre' ou 'campo=valor1|valor2' contra o chamado. */
export function condicaoAtendida(quando, chamado) {
  const q = quando.trim();
  if (q === 'sempre') return true;
  const i = q.indexOf('=');
  if (i === -1) throw new Error(`Condição inválida no perfil: '${q}'.`);
  const campo = q.slice(0, i).trim();
  const valores = q.slice(i + 1).split('|').map((v) => v.trim());
  let atual = chamado[campo];
  if (campo === 'status') atual = atual ?? 'aberto'; // atendimento novo ainda é "aberto"
  return valores.includes(String(atual));
}

export function cnpjValido(cnpj) {
  const digitos = cnpj.replace(/\D/g, '');
  if (digitos.length !== 14 || new Set(digitos).size === 1) return false;
  const digito = (base, pesos) => {
    const soma = [...base].reduce((total, d, i) => total + Number(d) * pesos[i], 0);
    const resto = soma % 11;
    return resto < 2 ? '0' : String(11 - resto);
  };
  const d1 = digito(digitos.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const d2 = digito(digitos.slice(0, 12) + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  return digitos.slice(12) === d1 + d2;
}

function checarTitulo(titulo, perfil) {
  if (textoVazio(titulo)) return 'título ausente';
  const t = titulo.trim();
  if (!/[A-Za-zÀ-ÿ]/.test(t)) return 'o título não tem texto (só símbolos ou números)';
  const normalizado = t.toLowerCase().replace(/^[ .:-]+|[ .:-]+$/g, '');
  if (perfil.titulo.genericos.includes(normalizado)) {
    return `título genérico ('${t}'): não permite achar o chamado depois`;
  }
  const palavras = t.split(/\s+/).filter(Boolean);
  if ([...t].length < perfil.titulo.min_caracteres || palavras.length < perfil.titulo.min_palavras) {
    return (
      `título curto demais (mínimo ${perfil.titulo.min_caracteres} caracteres e ` +
      `${perfil.titulo.min_palavras} palavras)`
    );
  }
  return null;
}

/** Devolve a descrição do problema, ou null se o campo está ok. */
export function checarCampo(regra, chamado, perfil) {
  const valor = chamado[regra.id];
  switch (regra.validador) {
    case 'presenca':
      return textoVazio(valor) ? 'não informado' : null;
    case 'lista':
      return !valor || valor.length === 0 ? 'nenhum item informado' : null;
    case 'booleano_definido':
      return valor === null || valor === undefined ? 'não informado' : null;
    case 'verdadeiro':
      return valor !== true ? 'ainda não feito/confirmado' : null;
    case 'cnpj':
      if (textoVazio(valor)) return 'não informado';
      return cnpjValido(valor) ? null : 'CNPJ inválido (confira os dígitos)';
    case 'telefone': {
      if (textoVazio(valor)) return 'não informado';
      let digitos = valor.replace(/\D/g, '');
      if (digitos.startsWith('55') && digitos.length > 11) digitos = digitos.slice(2);
      if (digitos.length !== 10 && digitos.length !== 11) {
        return 'telefone com número de dígitos inválido (use DDD + número)';
      }
      if (chamado.telefone_confirmado !== true) return 'telefone ainda não confirmado com o cliente';
      return null;
    }
    case 'titulo':
      return checarTitulo(valor, perfil);
    case 'email':
      if (textoVazio(valor)) return 'não informado';
      return EMAIL.test(valor.trim()) ? null : 'e-mail em formato inválido';
    default:
      throw new Error(`Validador desconhecido: ${regra.validador}`);
  }
}

function avisos(chamado, perfil) {
  const lista = [];
  const texto = `${chamado.titulo ?? ''} ${chamado.descricao ?? ''}`.toLowerCase();
  if (chamado.tipo === 'duvida' && perfil.palavras_de_erro.some((p) => texto.includes(p))) {
    lista.push(
      'Marcado como dúvida, mas o texto menciona erro/falha. Confirme se não é um bug ' +
        '(classificação errada distorce relatórios e atrasa o N2).',
    );
  }
  if (chamado.tipo === 'bug' && chamado.reproduzido_base_teste === false && (chamado.evidencias ?? []).length === 0) {
    lista.push('Bug não reproduzido na base de teste e sem evidência: o N2 terá dificuldade em investigar.');
  }
  return lista;
}

// Python arredonda "metade para o par" (round); Math.round arredonda metade para cima.
function arredondar(x) {
  const piso = Math.floor(x);
  const resto = x - piso;
  if (resto > 0.5) return piso + 1;
  if (resto < 0.5) return piso;
  return piso % 2 === 0 ? piso : piso + 1;
}

/** Valida o chamado. A nota é proporcional ao peso dos campos que se aplicam a ele. */
export function validar(chamado, perfil) {
  let aplicavel = 0;
  let ganho = 0;
  const pendencias = [];

  for (const regra of perfil.campos) {
    if (!condicaoAtendida(regra.quando, chamado)) continue;
    aplicavel += regra.peso;
    const problema = checarCampo(regra, chamado, perfil);
    if (problema === null) {
      ganho += regra.peso;
    } else {
      pendencias.push({
        campo: regra.id,
        rotulo: regra.rotulo,
        severidade: regra.severidade,
        problema,
        pergunta: regra.pergunta,
      });
    }
  }

  const nota = aplicavel ? arredondar((100 * ganho) / aplicavel) : 100;
  pendencias.sort((a, b) => ORDEM_SEVERIDADE[a.severidade] - ORDEM_SEVERIDADE[b.severidade]);
  const slaHoras = chamado.prioridade ? (perfil.sla_horas[chamado.prioridade] ?? null) : null;
  const bloqueantes = pendencias.filter((p) => p.severidade === 'bloqueante');

  return { nota, pendencias, bloqueantes, aprovado: bloqueantes.length === 0, avisos: avisos(chamado, perfil), slaHoras };
}

/** A pergunta da pendência mais grave (ou null se não há pendências). */
export function proximaPergunta(resultado) {
  return resultado.pendencias.length ? resultado.pendencias[0].pergunta : null;
}
