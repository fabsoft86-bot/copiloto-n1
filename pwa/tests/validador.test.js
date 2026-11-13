import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { validar, proximaPergunta, cnpjValido } from '../nucleo/validador.js';

const ler = (caminho) => JSON.parse(readFileSync(new URL(caminho, import.meta.url), 'utf-8'));
const perfil = ler('../perfis/software_house.json');
const casos = ler('./casos/validador.json');

test('o validador em JS dá o mesmo resultado que o Python em todos os casos dourados', () => {
  assert.ok(casos.length >= 300, 'esperava a suíte dourada completa');
  for (const [i, { chamado, esperado }] of casos.entries()) {
    const r = validar(chamado, perfil);
    const contexto = `caso #${i}: ${JSON.stringify(chamado)}`;
    assert.equal(r.nota, esperado.nota, `nota; ${contexto}`);
    assert.equal(r.aprovado, esperado.aprovado, `aprovado; ${contexto}`);
    assert.equal(r.slaHoras, esperado.sla_horas, `sla; ${contexto}`);
    assert.deepEqual(r.avisos, esperado.avisos, `avisos; ${contexto}`);
    assert.deepEqual(
      r.pendencias.map(({ campo, severidade, problema }) => ({ campo, severidade, problema })),
      esperado.pendencias,
      `pendências; ${contexto}`,
    );
    assert.equal(proximaPergunta(r), esperado.proxima_pergunta, `próxima pergunta; ${contexto}`);
  }
});

test('CNPJ: aceita válido, recusa dígito errado e sequência repetida', () => {
  assert.equal(cnpjValido('11.222.333/0001-81'), true);
  assert.equal(cnpjValido('11222333000181'), true);
  assert.equal(cnpjValido('11.222.333/0001-82'), false);
  assert.equal(cnpjValido('11111111111111'), false);
  assert.equal(cnpjValido('123'), false);
});

test('chamado bom aprova com nota 100 e sem pendências', () => {
  const bom = casos.find((c) => c.esperado.nota === 100 && c.chamado.tipo === 'bug');
  assert.ok(bom, 'esperava um caso bug nota 100 na suíte');
  const r = validar(bom.chamado, perfil);
  assert.equal(r.nota, 100);
  assert.equal(r.pendencias.length, 0);
  assert.equal(proximaPergunta(r), null);
});
