# MaineMed — roadmap rumo ao prontuário eletrônico (SBIS/NGS2)

O app atual é a fase 1: gravar → transcrever local → gerar prontuário →
revisar → exportar. Ele **não** guarda banco de dados de pacientes. As
decisões abaixo vieram da conversa de arquitetura sobre a fase 2 (prontuário
eletrônico completo) — são baratas de acomodar cedo e caríssimas depois.

## Já implementado na fase 1

- **Proveniência IA vs. humano** (`provenancia.py`): a saída bruta do Whisper
  (`transcricao-original.txt`) e a bruta do modelo de linguagem
  (`prontuario-gerado.txt`) nunca são sobrescritas; o que a médica revisa e
  aprova fica em `transcricao-revisada.txt` / `prontuario-final.txt`, com
  modelos e timestamps de cada etapa em `consulta.json`. O que se assina no
  futuro é sempre a versão final aprovada, nunca a saída bruta.
- **Sem resíduos temporários**: o WAV não passa por diretório temporário —
  vai direto para a pasta da consulta em Application Support.

## Fase 2 — decisões de fundação (antes de existir banco)

1. **Serialização canônica congelada.** Assinatura digital assina bytes: o
   registro precisa ser reproduzível byte a byte anos depois (JSON com
   chaves ordenadas, encoding fixo, timestamp em formato único, schema
   versionado). Consertar depois = reassinar tudo, muitas vezes impossível.
2. **Trilha de auditoria append-only, incluindo leitura.** Visualizar
   prontuário é evento auditável. Filtros mínimos: data, evento, id
   permanente do usuário, id do registro. Hash encadeado entre entradas dá
   integridade quase de graça.
3. **Nada de DELETE físico.** Registro médico se retifica, não se apaga — a
   versão anterior fica recuperável, com autor e motivo. O SQLite já deve
   nascer assim.
4. **Tela de assinatura isolada.** Exibir somente o que será assinado, sem
   elementos de telas adjacentes — o renderizador de documento precisa de um
   modo "só conteúdo" desde o design.
5. **Fila de pendências de assinatura.** Se não assinar no ato (esqueceu o
   token), o registro entra em estado "pendente de assinatura" e notifica.
   Modelar como estado do registro desde o início.
6. **Limpeza de temporários.** Cache de PDFs visualizados e intermediários
   excluídos após a operação.

### Fotos

Arquivo no disco cifrado, **caminho** no banco (não BLOB); **remover EXIF na
ingestão** (foto de celular carrega GPS); thumbnail de ~200 px para a tela.

### SBIS/NGS2 — contexto

- NGS2 exige certificado **ICP-Brasil** para assinatura e autenticação; só
  sistemas em conformidade podem ser 100% digitais, sem imprimir prontuário.
  É opcional — e é exatamente o que justifica o MaineMed existir.
- São 34 requisitos (55 sub-requisitos). O certificado vale para a **versão
  auditada**: versões novas exigem extensão e mudanças relevantes disparam
  nova auditoria — certificação é custo recorrente que amarra o ciclo de
  release. Planejar o roadmap com isso antes de prometer prazo a clínica.
