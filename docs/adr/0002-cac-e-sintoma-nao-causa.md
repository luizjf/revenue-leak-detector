# ADR 0002 — CAC elevado é sintoma; causas-raiz operacionais têm precedência

- **Status:** aceita
- **Data:** 2026-09-12
- **Depende de:** ADR 0001

## Contexto

A primeira versão do motor tratava "CAC subiu" como achado. Toda vez que o CAC
da conta passava do limiar, a regra R1 emitia.

**A medição:** precisão da R1 de **0,194**. Quatro em cada cinco alertas estavam
errados — no sentido que importa, que é o alerta apontar para uma causa que não
era a causa.

O motivo é conceitual, não de implementação: **CAC alto quase nunca é a doença.**
Ele é o resultado visível de outra coisa. Nos dados do protótipo, um CAC elevado
apareceu como consequência de:

- lead de alto fit não contatado dentro do SLA (**R3**) — o dinheiro foi gasto,
  o lead chegou, ninguém ligou;
- follow-up insuficiente (**R7**) — perdidos com menos de três toques;
- pipeline parado além do SLA do estágio (**R6**);
- mudança de mix entre campanhas (**R10**) — ver ADR 0003.

Dizer "seu CAC subiu 40%" para um gestor cuja equipe não está ligando para os
leads é dar um diagnóstico **verdadeiro e inútil**. Ele já sabia que o CAC subiu;
é por isso que contratou o relatório. O que ele não sabe é por quê.

## Decisão

O motor avalia por **hierarquia condicional**, não por lista de verificações
independentes:

1. **R0** roda primeiro e é bloqueante. Sem dado íntegro, nada é afirmado.
2. As regras **operacionais** (R3, R6, R7) e a de **mix** (R10) são avaliadas
   antes das econômicas.
3. Se uma delas explica a variação observada do CAC, a **R1 não emite como
   achado**. O CAC aparece como *consequência quantificada* da causa encontrada,
   não como problema próprio.
4. A R1 só emite sozinha quando o CAC subiu e **nenhuma** causa operacional ou de
   mix explica a subida.

**Resultado medido:** precisão da R1 de **0,194 → 0,979**.

## Consequências

**O que ganhamos**

- Precisão cinco vezes maior na regra mais visível do produto.
- O achado passa a ser acionável: ele nomeia um dono e uma ação, em vez de
  nomear um número.

**O que pagamos**

- **Recall cai, e isso é uma perda real.** Casos em que o CAC subiu *e* havia
  também um problema operacional deixam de gerar alerta de CAC. Se as duas
  coisas eram independentes, o problema econômico fica silenciado.
  A magnitude dessa perda **não está medida** — medi-la é trabalho da fase 3, e
  ela precisa aparecer na matriz de confusão do conjunto cego. Não se declara
  ganho de precisão sem declarar o recall que o pagou.
- O motor fica mais difícil de testar: **a ordem passa a importar**, e ordem é
  coisa que se quebra em refatoração sem ninguém perceber. Exige teste próprio.

## Trade-off em uma frase

Trocamos **cobertura** por **credibilidade**.

## Por que essa troca está certa para este destinatário — e errada para outro

O destinatário é uma **agência apresentando resultado ao cliente**. Nesse
contexto, um falso positivo é uma recomendação errada dada numa reunião: pausar
a campanha que estava funcionando, cobrar o time pelo problema errado. O custo é
credibilidade, e credibilidade perdida não volta com um alerta correto na semana
seguinte — que é exatamente o mecanismo de churn descrito na seção 2 do
`CLAUDE.md`: 28% dos cancelamentos são problema de comprovação.

Um falso negativo, no mesmo contexto, custa uma oportunidade adiada em um ciclo.

**Para outro destinatário a troca seria errada.** Num sistema de monitoramento
interno, onde um analista faz triagem de tudo que o motor emite, perder um caso
custa mais do que investigar um alarme falso — investigar é barato quando é o
seu próprio time, e o caso perdido nunca mais aparece. Ali, o correto seria
emitir a R1 sempre e ranquear por confiança, deixando o humano decidir.

A decisão não é "precisão é melhor que recall". É **quem paga pelo erro**.

## O que reabriria esta decisão

Um destinatário diferente (uso interno com triagem humana), ou evidência de que
a perda de recall concentra-se em casos de alto valor financeiro — situação em
que valeria emitir a R1 rebaixada em vez de suprimi-la.
