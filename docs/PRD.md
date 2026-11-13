# PRD — Copiloto N1

**Status:** rascunho v0.2 · produto redefinido em 2026-11-11: assistente pessoal sem LLM, **PWA primeiro** (ADR-0003). As seções abaixo ainda descrevem a visão anterior (com IA); o backlog em `docs/backlog.md` é a fonte do que será feito agora.
**Dono do produto:** você (decide escopo e prioridade)
**Perfil inicial:** software house / ERP (campos configuráveis para outros perfis)

---

## 1. Problema

Analistas de suporte N1 perdem tempo e qualidade em duas coisas:

1. **Registrar o chamado** de forma completa e rápida. Chamados com título vazio, sem contato confirmado, sem evidência, sem versão ou com tipo errado (dúvida marcada como bug, ou o contrário) geram retrabalho no N2/N3, relatórios distorcidos e clientes que repetem a história.
2. **Saber o que perguntar, para quem escalar e como responder**, sem interromper colegas mais experientes.

Os registros ruins são uma queixa recorrente em equipes de suporte e um motivo comum de atrito entre N1 e N2.

## 2. Objetivo

Um **copiloto para o analista N1** que acompanha o atendimento, preenche o chamado a partir da conversa, aponta o que falta, sugere a próxima pergunta e gera o registro final com um clique. **O analista continua no controle**: a ferramenta sugere e preenche; o humano revisa e confirma.

**Diferencial:** um **validador de qualidade do chamado** (nota + pendências + pergunta sugerida para cada pendência), independente de qual helpdesk a empresa usa.

### Fora do escopo (não-objetivos)

- Não é um helpdesk nem substitui o sistema de chamados da empresa.
- Não substitui o analista; não responde ao cliente sozinho (chatbot é fase posterior).
- Não decide prioridade ou escalonamento sem confirmação humana.

## 3. Papéis (quem usa e quem é afetado)

| Papel | Relação com o produto |
|---|---|
| **Analista N1** (usuário principal) | Atende, vê o painel ao vivo, confirma e salva o chamado |
| **Analista N2/N3** | Recebe escalonamentos; ganha chamados completos e reprodutíveis |
| **Supervisor / QA** | Usa a nota de qualidade e indicadores para treinar a equipe |
| **Administrador do helpdesk** | Configura integração (adaptador) e o perfil de campos |
| **Responsável pela base de conhecimento** | Revisa os rascunhos de artigos gerados |
| **Cliente / usuário final** | Beneficiado (menos repetição, retorno mais rápido); dados dele exigem cuidado |
| **Segurança / LGPD** | Define o que pode ser gravado (áudio, dados sensíveis) |

## 4. Dores e funcionalidades candidatas

| Dor | Funcionalidade |
|---|---|
| Esquece dados básicos | Painel ao vivo com campos preenchidos pela conversa e alerta do que falta |
| Não sabe o que perguntar | Sugestão da próxima pergunta (checklist dinâmico, 5 porquês guiado) |
| Classifica errado | Sugestão de tipo e prioridade com justificativa; o humano confirma |
| Não sabe para quem escalar | Roteador de escalonamento com script pronto (POP) |
| Pergunta a colegas como resolver | Busca em chamados antigos, troubleshooting e artigos |
| Registro ruim e demorado | Chamado completo em um clique + nota de qualidade |
| Cliente esquecido | Lembrete de retorno e rascunho de mensagem de status |
| Conhecimento se perde | Rascunho de artigo KCS (problema, causa, solução) ao fechar |
| SLA e indicadores | Timer visível e resumo pessoal (tempo de resposta, resolução no 1º contato, reabertura) |
| Linguagem técnica com o cliente | Tradução para linguagem simples |
| Dados sensíveis ditos em voz alta | Mascaramento antes de gravar (LGPD) |

## 5. Requisitos funcionais

Prioridade MoSCoW. Cada item deve virar uma tarefa no backlog com critério de aceite.

### Must (protótipo)

- **RF-01** Receber a conversa como **texto** (colada ou arquivo) no formato `Analista:` / `Cliente:`.
- **RF-02** Extrair campos do chamado a partir da conversa (nome, empresa, CNPJ, telefone, e-mail, descrição, tipo, módulo, versão etc.).
- **RF-03** Mostrar um **painel** com os campos preenchidos e o que falta, atualizando a cada trecho.
- **RF-04** **Validar** o chamado contra um perfil configurável e devolver nota (0–100), pendências por severidade (bloqueante, importante, sugestão) e a **pergunta sugerida** para cada uma.
- **RF-05** Gerar o **chamado final** e um **resumo** em texto, editáveis pelo analista antes de salvar.
- **RF-06** O analista pode **editar qualquer campo**; edição humana sempre prevalece sobre a extração automática.

### Should

- **RF-07** Sugerir a **próxima pergunta** com base nas pendências e no tipo do chamado.
- **RF-08** Sugerir **tipo** e **prioridade** com justificativa curta (aviso quando a descrição parece bug mas está como dúvida).
- **RF-09** Buscar **chamados e artigos parecidos** em uma base local.
- **RF-10** Salvar o chamado por um **adaptador** (primeiro em arquivo; depois GLPI).

### Could

- **RF-11** Rascunho de **artigo KCS** (problema, causa, solução) ao resolver.
- **RF-12** **Indicadores pessoais** (tempo médio de resposta, FCR, reabertura).
- **RF-13** **Mascaramento** de dados sensíveis (senhas, CPF, cartões) antes de persistir.
- **RF-14** **Tradução** da resposta técnica para linguagem simples.

### Depois

- Áudio em tempo real (captura, transcrição em streaming, identificação de quem fala).
- Integração com helpdesk (GLPI primeiro; Zammad, Zendesk, Freshdesk depois).
- Chatbot de autoatendimento reaproveitando a base e a extração.

## 6. Requisitos não funcionais

- **RNF-01 Humano no controle:** nenhuma ação externa (salvar, escalar, responder) sem confirmação.
- **RNF-02 Latência:** sugestões em poucos segundos; caso contrário atrapalham o atendimento.
- **RNF-03 Privacidade/LGPD:** por padrão **não guardar áudio**, só texto, com mascaramento de dados sensíveis; decidir cedo se o processamento é local ou em nuvem.
- **RNF-04 Neutralidade de helpdesk:** o núcleo não conhece nenhum helpdesk; integração só por adaptadores.
- **RNF-05 Configurável:** campos, pesos, SLA e perguntas vivem em um **perfil** (YAML), não no código.
- **RNF-06 Testável offline:** validador e extrator por regras rodam sem internet e sem chave de API.
- **RNF-07 Explicável:** toda nota e pendência diz o motivo, e toda sugestão automática indica a origem.

## 7. Critérios de aceite do MVP

1. Dado um chamado ruim (título vazio, sem contato, sem evidência), o validador reprova, lista as pendências e sugere uma pergunta para cada uma.
2. Dado um chamado completo, o validador aprova com nota 100.
3. Um CNPJ inválido, um telefone não confirmado e um título genérico são detectados.
4. Chamado do tipo **bug** exige versão, evidência, passos e teste na base; do tipo **dúvida** não exige.
5. Chamado **resolvido** exige solução; **escalado** exige destino.
6. A extração por regras encontra CNPJ, telefone e e-mail em uma conversa de exemplo sem internet.
7. Trocar o perfil (outro YAML) muda as regras sem alterar o código.
8. Toda a suíte de testes passa localmente.

## 8. Métricas de sucesso (para o portfólio e uso próprio)

- Nota média de qualidade dos chamados gerados com o copiloto vs. preenchidos à mão.
- Tempo para fechar o registro após o atendimento.
- Número de pendências bloqueantes por chamado.

## 9. Riscos e decisões em aberto

| Risco / dúvida | Mitigação |
|---|---|
| Qualidade da transcrição em português com ruído de telefone | Começar por texto (ADR-0002); avaliar serviços de voz só na fase 2 |
| Extração por LLM errar e o analista confiar demais | Humano confirma; marcar a origem de cada campo; testes com conversas reais fictícias |
| LGPD (voz e dados pessoais) | Sem áudio persistido; mascaramento; decisão local vs. nuvem antes da fase 2 |
| SLA dos exemplos varia (2h, 4h) | SLA é configuração do perfil, não regra fixa |
| Dependência de material de terceiros | Usar o curso só como inspiração; checklist próprio; não copiar textos |
| Escopo crescer demais | Seguir MoSCoW; uma fatia vertical por vez |

**Em aberto:** serviço de transcrição (local ou nuvem), provedor de IA, orçamento, licença do projeto (sugestão: MIT).

## 10. Roadmap por fatias verticais

- **Fatia 1 — Validador (este esqueleto):** schemas, perfil YAML, validador, CLI, testes.
- **Fatia 2 — Extração por regras + painel:** conversa em texto → campos → painel simples (hoje: PWA, ver ADR-0003).
- **Fatia 3 — Extração por LLM:** saída estruturada validada com pydantic; sugestão da próxima pergunta.
- **Fatia 4 — Geração do registro final e adaptador de arquivo.**
- **Fatia 5 — Base de conhecimento:** busca de casos parecidos e rascunho KCS.
- **Fatia 6 — Áudio em tempo real** e **adaptador GLPI**.
- **Fatia 7 — Chatbot** de autoatendimento.
