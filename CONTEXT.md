# onecoder

Plataforma interna de engenharia para centralizar o uso de IA operacional e automatizar deploys multi-VPS com governanca entre ambientes de teste e producao.

## Language

**Control Plane (VPS Central)**:
Servidor unico da empresa que hospeda o orquestrador de deploy e o proxy de IA, concentrando credenciais e politicas de acesso.
_Avoid_: Servidor principal, master, host geral

**VPS de Cliente**:
Servidor isolado que executa os sistemas de um cliente especifico em containers e aceita comandos apenas a partir da rede privada do Control Plane.
_Avoid_: Maquina do cliente, node, worker

**Gateway de IA**:
Ponto unico de acesso aos modelos de linguagem da empresa, responsavel por roteamento, contabilizacao de uso e controle de orcamento por desenvolvedor.
_Avoid_: API da IA, servidor de modelo, backend LLM

**Virtual Key**:
Credencial individual emitida pelo Gateway de IA para cada desenvolvedor com teto mensal de gastos e lista restrita de modelos permitidos.
_Avoid_: Chave OpenRouter, token mestre, senha de IA

**Catalogo da Empresa**:
Registro estruturado que descreve clientes, sistemas, dominios, regras de engenharia e topologia conhecida pela IA operacional.
_Avoid_: Inventario, planilha, base de clientes

**Agente Operacional (MCP)**:
Interface padronizada que permite ao editor ou CLI do desenvolvedor consultar o Catalogo da Empresa, inspecionar servicos e acionar deploys sem acesso direto as maquinas.
_Avoid_: Plugin, bot de chat, script de IA

**Ambiente de Teste (Preview)**:
Instancia temporaria e isolada de uma branch publicada em subdominio de homologacao para validacao antes do merge na branch principal.
_Avoid_: Staging compartilhado, QA manual, branch server

**Perfil Dev**:
Nivel de permissao padrao de desenvolvedor, autorizado a consultar diagnosticos, criar sistemas iniciais e publicar livremente em Ambiente de Teste (Preview).
_Avoid_: Usuario comum, colaborador

**Perfil Admin**:
Nivel de permissao elevado autorizado a aprovar merges em producao e acionar deploys diretos na branch principal de clientes.
_Avoid_: Root, superuser, dono
