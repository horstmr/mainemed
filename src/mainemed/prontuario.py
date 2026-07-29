"""Geração do prontuário a partir da transcrição, via API da Anthropic."""

from __future__ import annotations

import anthropic

DEFAULT_MODEL = "claude-opus-5"

SYSTEM = """Você redige prontuários médicos em português do Brasil a partir da transcrição automática de uma consulta.

Regras:
- Use exclusivamente informações presentes na transcrição. Nunca invente dados, valores de exames, doses, nomes de medicamentos ou diagnósticos.
- Quando uma informação esperada não aparecer na transcrição, escreva [não registrado].
- A transcrição é automática e pode conter erros de reconhecimento de fala; interprete termos claramente distorcidos pelo contexto clínico e, quando a dúvida for relevante, registre a forma ouvida entre aspas seguida de (?).
- Linguagem técnica, objetiva, em terceira pessoa.
- Não inclua nome do paciente nem data — o aplicativo adiciona o cabeçalho.
- Responda em texto simples, sem markdown, com os títulos de seção em maiúsculas, nesta ordem:

QUEIXA PRINCIPAL
HISTÓRIA DA DOENÇA ATUAL
ANTECEDENTES PESSOAIS E FAMILIARES
MEDICAMENTOS EM USO
ALERGIAS
EXAME FÍSICO
HIPÓTESES DIAGNÓSTICAS
CONDUTA E PRESCRIÇÃO
ORIENTAÇÕES E RETORNO"""


class ProntuarioError(RuntimeError):
    pass


def gerar(api_key: str, transcricao: str, modelo: str = DEFAULT_MODEL) -> str:
    if not api_key:
        raise ProntuarioError(
            "Nenhuma chave configurada. Abra Configurações e cole a chave recebida."
        )
    if not transcricao.strip():
        raise ProntuarioError("A transcrição está vazia. Grave uma consulta primeiro.")

    client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=240.0)
    kwargs = dict(
        model=modelo,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": "Transcrição da consulta:\n\n" + transcricao}],
    )
    try:
        try:
            # Fallback automático do lado do servidor caso o modelo recuse;
            # se a conta não tiver o beta, repete a chamada sem ele.
            resposta = client.messages.create(
                extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
                extra_body={"fallbacks": "default"},
                **kwargs,
            )
        except anthropic.BadRequestError:
            resposta = client.messages.create(**kwargs)
    except anthropic.AuthenticationError as exc:
        raise ProntuarioError(
            "Chave inválida ou revogada. Confira a chave em Configurações."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise ProntuarioError(
            "Muitas solicitações neste momento. Aguarde um minuto e tente de novo."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise ProntuarioError(
            "Sem conexão com o serviço. Verifique a internet e tente de novo."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise ProntuarioError(
            f"Erro do serviço ({exc.status_code}). Tente novamente em instantes."
        ) from exc

    if resposta.stop_reason == "refusal":
        raise ProntuarioError(
            "O serviço recusou gerar este texto. Revise a transcrição e tente novamente."
        )

    texto = "".join(
        bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text"
    ).strip()
    if not texto:
        raise ProntuarioError("O serviço retornou uma resposta vazia. Tente novamente.")
    if resposta.stop_reason == "max_tokens":
        texto += "\n\n[Atenção: o texto atingiu o limite de tamanho e pode ter sido cortado.]"
    return texto
