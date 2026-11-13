// Servidor estático mínimo para desenvolver o PWA: `npm start` e abra http://localhost:8080
// (módulos ES e service worker não funcionam em file://). Só serve arquivos desta pasta.

import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = resolve(fileURLToPath(new URL('.', import.meta.url)));
const PORTA = Number(process.env.PORT ?? 8080);
const TIPOS = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json',
};

createServer(async (req, res) => {
  try {
    let caminho = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (caminho.endsWith('/')) caminho += 'index.html';
    const arquivo = resolve(join(RAIZ, normalize(caminho)));
    if (arquivo !== RAIZ && !arquivo.startsWith(RAIZ + sep)) {
      res.writeHead(403).end('Proibido');
      return;
    }
    if (!(await stat(arquivo)).isFile()) throw new Error('não é arquivo');
    const corpo = await readFile(arquivo);
    res.writeHead(200, { 'Content-Type': TIPOS[extname(arquivo)] ?? 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(corpo);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Não encontrado');
  }
}).listen(PORTA, '127.0.0.1', () => console.log(`Copiloto N1 em http://localhost:${PORTA}`));
