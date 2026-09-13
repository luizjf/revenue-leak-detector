# `docs/`

> Guarda as duas coisas que o código não consegue contar sozinho: **o que foi
> combinado** e **por que foi decidido assim**.

**O que vive aqui**

| Arquivo | Natureza | Etapa |
|---|---|---|
| `contrato-de-dados.md` | **especificação** — campos, tipo na origem, obrigatoriedade, chave, limites de aceitação | 1.3 |
| `adr/0001` … `adr/0004` | **decisão** — Contexto / Decisão / Consequências | 1.4 |
| `parametros-e-cenarios.md` | **estratégia** — estrutura de negócio, faixas do funil, os 10 cenários e as 7 armadilhas | 1.5 |
| `amostras/` | recorte curto de cada arquivo de `raw/`, escrito pelo próprio exportador | 1.7 |

A distinção entre as duas primeiras linhas é o motivo desta pasta existir:
o contrato diz **o quê** (`spend` chega como string, `campaign_source` pode ser
nulo); a ADR diz **por quê** (CAC por coorte, porque sem isso o período tinha 1
fechamento maduro contra 95 do baseline). Especificação sem justificativa vira
regra arbitrária; justificativa sem especificação não é verificável.

**Sobre `campaign_source`**
Ele **pode** ser nulo, e isso não viola o contrato — é o fenômeno que a regra R8
mede. O contrato precisa deixar essa diferença explícita, senão a camada de
staging trata como erro algo que é o sinal.

**Sobre as ADRs**
As quatro primeiras não se reabrem sem argumento novo. Cada uma nasceu de uma
medição, não de uma preferência — e é a medição que fica registrada.
