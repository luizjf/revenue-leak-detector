# ADR 0004 — Guardas de amostra são relativas, nunca absolutas

- **Status:** aceita
- **Data:** 2026-09-12
- **Motivada por:** ADR 0003

## Contexto

Para evitar diagnóstico em cima de pouco dado, o protótipo usava uma guarda
absoluta: **"só avalie se houver ao menos 20 negócios"**. É o tipo de regra que
parece prudência e passa em qualquer revisão de código.

**A medição:** essa guarda silenciou a regra **R8** em **88% dos casos com dois
problemas simultâneos**.

O motivo é perverso, e é o que torna esta ADR importante: **uma conta com
problema tem menos negócios justamente porque está com problema.** Vazamento de
receita reduz o denominador. A guarda absoluta, portanto, cala o motor
preferencialmente nas contas mais doentes — as únicas em que ele tinha algo a
dizer. Quanto pior a conta, mais silencioso o produto.

A ADR 0003 agravou isso: avaliar por campanha divide a amostra, e um piso fixo
de 20 aplicado a cada campanha praticamente desliga o motor.

## Decisão

A guarda deixa de perguntar **"tenho dado suficiente?"** e passa a perguntar
**"a diferença que observei é distinguível de ruído com o dado que tenho?"**.

1. Comparações de proporção (taxa de conversão, taxa de contato no SLA,
   cobertura de origem) usam **teste de proporção**.
2. Comparações de valor (CAC, CPL, ticket) reportam **intervalo de confiança**;
   o achado só emite se o intervalo não cruzar o valor do baseline.
3. A **R99** emite quando o teste não consegue distinguir — e o texto que ela
   gera diz isso, não inventa um número.
4. Nenhum limiar absoluto de contagem sobrevive no motor. Se aparecer um
   `if n < 20`, é bug.

## Consequências

**O que ganhamos**

- O motor volta a falar nas contas com problemas múltiplos — que são, por
  definição, as que mais precisam.
- A R99 ganha significado: "não é distinguível de ruído" é uma afirmação
  estatística verificável, enquanto "menos de 20 negócios" era numerologia.
- Coerência com a identidade do produto: *recusar-se a responder quando os dados
  não permitem afirmar* passa a ser uma decisão calculada, não um piso arbitrado.

**O que pagamos**

- **Isto não é implementável em SQL de forma testável.** Teste de proporção e
  intervalo de confiança vão para Python, em `motor/`. Esta ADR é uma das razões
  concretas da regra "dbt não roda a detecção" (`CLAUDE.md` seção 6).
- **A explicação para o cliente fica mais difícil.** "Menos de 20 negócios" cabe
  numa frase. "O intervalo de confiança da diferença cruza zero" não cabe — e a
  etapa 4.1 (narrativa determinística) tem que traduzir isso para português sem
  mentir. Custo real de comunicação.
- Mais um lugar onde comparações múltiplas mordem: mais testes, mais chance de
  um resultado significativo por acaso. Somado à ADR 0003, é a falha aberta mais
  séria do red team.

## Trade-off em uma frase

Trocamos **um limiar explicável em cinco palavras** por **uma decisão correta que
exige um parágrafo**.

## O que reabriria esta decisão

Evidência de que o teste de proporção, no tamanho de amostra típico destas
contas, tem poder tão baixo que a R99 domina a saída — caso em que o problema
não seria a guarda, e sim a janela de análise ser curta demais.
