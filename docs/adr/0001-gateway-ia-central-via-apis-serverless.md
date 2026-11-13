---
status: accepted
---

# 0001 — Gateway de IA Central via APIs Serverless (LiteLLM + OpenRouter/AI Studio)

Decidimos centralizar o acesso aos modelos **Gemma 4 (31B e 26B MoE)** usando o **LiteLLM Proxy** na VPS Central consumindo APIs serverless (OpenRouter e Google AI Studio), em vez de executar modelos localmente nos notebooks dos desenvolvedores ou alugar GPUs dedicadas em nuvem por hora.

## Considered Options

- **Execucao local nos PCs dos desenvolvedores:** Nao atende equipes com notebooks de 16 GB de RAM unificada/disco limitado (onde o Gemma 4 31B e inviavel e o 26B MoE satura a memoria), alem de impedir governanca centralizada de uso.
- **Aluguel de GPU dedicada em nuvem (RunPod/Vast.ai):** Gera custo fixo elevado por tempo de ociosidade (~90% do tempo em que o desenvolvedor esta lendo ou testando codigo) e exige gerenciamento manual de liga/desliga.
- **LiteLLM Proxy + APIs Serverless (escolhida):** Paga apenas pelos tokens gerados, entrega o modelo Gemma 4 31B na velocidade maxima em qualquer notebook e concentra chaves externas e limites mensais (Virtual Keys) em uma unica conta da empresa.

## Consequences

- O codigo enviado nos prompts transita por provedores de API externos; projetos com restricao estrita de compliance/air-gap exigirao adicionar um endpoint interno (vLLM/Ollama em GPU propria) no `litellm_config.yaml` no futuro — mudanca transparente para os desenvolvedores, que continuam apontando para o mesmo Gateway.
