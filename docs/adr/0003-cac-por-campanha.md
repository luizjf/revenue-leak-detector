# ADR 0003 — CAC avaliado por campanha, não só no agregado

- **Status:** aceita
- **Data:** 2026-09-12
- **Depende de:** ADR 0001 · **Motiva:** ADR 0004

## Contexto

O motor avaliava o CAC no nível da conta. Parecia razoável: é o número que o
cliente pergunta.

**A medição:** **80 dos 86 falsos positivos** do protótipo vinham de um único
fenômeno — **paradoxo de Simpson**.

O mecanismo, em concreto. Uma conta com duas campanhas:

| | Campanha A | Campanha B | Conta |
|---|---|---|---|
| **Antes** — CAC | R$ 400 | R$ 900 | — |
| **Antes** — verba | 80% | 20% | CAC agregado ≈ **R$ 500** |
| **Depois** — CAC | R$ 380 | R$ 850 | — |
| **Depois** — verba | 30% | 70% | CAC agregado ≈ **R$ 709** |

O CAC agregado subiu 42%. **As duas campanhas melhoraram.** Nenhuma piorou.
O que mudou foi a distribuição da verba — e migração de verba costuma ser
decisão deliberada do gestor, não vazamento.

Um alerta aqui não é apenas inútil: ele pede para reverter uma decisão que pode
estar certa. É o caso em que a ferramenta ativamente piora o resultado do
cliente.

## Decisão

1. A **R1 avalia CAC por campanha**. O alerta nasce no nível em que a ação
   existe — ninguém "pausa uma conta", pausa-se uma campanha.
2. O CAC agregado continua sendo reportado, mas **sempre decomposto**: quanto da
   variação veio de mudança dentro das campanhas e quanto veio de mudança de
   peso entre elas.
3. Quando o agregado sobe e **nenhuma campanha individual piorou**, o motor emite
   **R10 — mudança de mix**, de classe *informativa*. Não é alerta; é explicação.

## Consequências

**O que ganhamos**

- 80 de 86 falsos positivos eliminados.
- Nasce a **R10**, que junto com a R4 forma o par mais valioso do produto: as
  duas regras cujo trabalho é **impedir uma ação errada**. Um detector ingênuo
  mata a campanha mais lucrativa da conta porque olhou só o agregado.
- O achado passa a ter endereço. "CAC alto" não tem dono; "CAC alto na campanha
  X" tem.

**O que pagamos**

- **Amostra por campanha é menor que amostra por conta.** Dividir para dez
  campanhas divide o poder estatístico por dez, e muitos casos passam a cair na
  R99 (amostra insuficiente). Foi essa consequência que forçou a **ADR 0004** —
  uma guarda de amostra absoluta, neste desenho, calaria o motor quase sempre.
- **Comparações múltiplas.** Avaliar dez campanhas é fazer dez testes; a chance
  de pelo menos um falso positivo por acaso cresce com o número de campanhas.
  Isso está registrado como **falha aberta** do red team (etapa 4.3), não como
  resolvido.
- Custo de leitura: o relatório tem mais linhas, e a interface precisa ordenar
  por dinheiro em risco para não afogar o usuário.

## Trade-off em uma frase

Trocamos **um número simples que engana** por **muitos números corretos que
exigem ordenação**.

## O que reabriria esta decisão

Contas com uma única campanha ativa, onde a decomposição é vazia e o custo de
leitura não se paga — nesse caso, o nível de avaliação pode colapsar no
agregado sem perda. É configuração, não revogação.
