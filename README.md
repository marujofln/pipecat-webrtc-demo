# Pipecat WebRTC Demo — agente de voz para WhatsApp

Agente de voz em português que atende chamadas WebRTC (WhatsApp Business Calling API ou navegador),
segue instruções em Markdown, consulta uma base de conhecimento (RAG) e chama APIs externas
(CRM, estacionamento) **somente quando o chamador tem autorização**.

```
WhatsApp ──webhook (SDP offer)──► /whatsapp/webhook ─┐
Navegador ──POST /api/offer─────────────────────────┤
                                                     ▼
              SmallWebRTCTransport → STT → LLM (+tools, RAG) → TTS → áudio de volta
```

## Rodando

```bash
uv sync
cp .env.example .env        # preencha as chaves dos provedores escolhidos
uv run uvicorn mock_apis.server:app --port 8002     # CRM + estacionamento falsos
uv run uvicorn app.main:app --port 7860             # agente
```

Abra http://localhost:7860, escolha o chamador e clique em **Ligar**.

Roteiro de teste:
- "Que horas vocês abrem?" → responde pela base de conhecimento (`search_knowledge`).
- Como `5511999990001` (patient): "Quero marcar uma consulta" → lista horários e marca no CRM.
- Como `5511999990002` (resident): "Abre a cancela, placa ABC1D23" → abre a cancela.
- Como `5500000000000` (guest): pedir para abrir a cancela → o agente recusa.

## Personalizando o atendimento

| O quê | Onde |
|---|---|
| Persona, tom e regras do atendimento | `agent/system.md` |
| Base de conhecimento (RAG) | `agent/knowledge/*.md`, um trecho por título `#`/`##` |
| Quem pode usar cada tool | `agent/policies.yaml` (papel → tools; número → papel) |
| Novas tools / APIs | `app/tools/` + registro em `app/tools/__init__.py` |
| Provedores | `STT_PROVIDER`, `LLM_PROVIDER`, `TTS_PROVIDER` no `.env` |

Provedores suportados: STT `deepgram|openai`, LLM `anthropic|openai|google`, TTS `cartesia|elevenlabs|openai`.
Para adicionar outro, inclua um `case` em `app/providers.py`.

### Autorização
O prompt só informa ao LLM quais tools existem; a barreira real fica no handler de cada tool
(`app/tools/registry.py` → `Policies.can_call`). Mesmo que o LLM chame uma tool não permitida,
a chamada é negada e registrada no log. Tools fora da allowlist do chamador também não são
enviadas no schema para o LLM.

No WhatsApp, o chamador é o número de origem (`from`) do webhook. No cliente web, o chamador
vem do próprio navegador (`request_data.caller`): **isso é só para teste local**. Não exponha
`/api/offer` publicamente sem autenticação.

## WhatsApp Business Calling API

1. Número business na Cloud API com chamadas habilitadas (Phone number settings → Calling).
2. Exponha o servidor: `ngrok http 7860`.
3. No app Meta, em Webhooks, configure `https://<ngrok>/whatsapp/webhook`, use o mesmo
   `WHATSAPP_VERIFY_TOKEN` do `.env` e assine o campo **calls**.
4. Preencha `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_APP_SECRET`
   (este último valida o `X-Hub-Signature-256`).
5. Ligue para o número pelo WhatsApp.

Fluxo: evento `connect` com SDP offer → o servidor gera o SDP answer (aiortc, com os ICE
candidates já incluídos, pois o WhatsApp não faz trickle ICE) → `pre_accept` → `accept` →
o agente fala. Evento `terminate` encerra a sessão; se o agente encerrar primeiro, o servidor
envia `terminate` à Graph API.

Atrás de NAT restritivo, pode ser necessário um servidor TURN para a mídia.

## Testes

```bash
uv run pytest
```

Cobrem autorização, RAG, tools contra o mock (inclusive negação quando o LLM tenta uma tool não
permitida) e o parse/assinatura do webhook do WhatsApp.

## Fora da v1
Persistência, multi-tenant, transferência para humano, transcrições e analytics, RAG vetorial.
