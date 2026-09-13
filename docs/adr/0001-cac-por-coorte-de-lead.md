# ADR 0001 — CAC por coorte de lead, com 30 dias de maturação

- **Status:** aceita
- **Data:** 2026-09-12
- **Substitui:** o cálculo convencional de CAC (gasto do período ÷ vendas do período)

> **Nota de autoria:** a etapa 1.4 previa esta ADR escrita por Luiz. A pedido
> explícito dele, foi redigida por Claude. Ver `docs/contrato-de-dados.md` para o
> registro da mesma divergência na etapa 1.3.

## Contexto

O CAC como o mercado calcula é `gasto do mês ÷ vendas do mês`. Isso pressupõe
que o lead que gerou a venda de março entrou em março.

Não entra. O lead fecha com atraso, e o atraso não é pequeno nem constante: num
funil B2B com ticket de R$ 3 a 15 mil, a mediana fica na casa das três semanas e
a cauda passa de dois meses. As vendas de março vêm, em boa parte, do dinheiro
gasto em janeiro e fevereiro.

Dividir um numerador de um período por um denominador de outro produz um número
que **parece** uma métrica e não mede nada. Pior: ele se move quando nada mudou —
basta o atraso variar.

**A medição que fechou a discussão:** no protótipo, com o cálculo convencional,
o período analisado (30 dias) tinha **1 fechamento maduro** contra **95 do
baseline** (60 dias). O motor estava comparando 1 observação contra 95 e
chamando a diferença de "piora do CAC". Não era piora — era o período recente
ainda não ter acontecido.

## Decisão

O custo é atribuído à **coorte do lead**, não ao mês do caixa:

1. Todo lead pertence à coorte do dia (e da semana) em que entrou.
2. O custo de mídia daquele dia é atribuído àquela coorte.
3. As vendas contam para a coorte **do lead que as originou**, não para o mês em
   que o contrato foi assinado.
4. Uma coorte só é considerada **madura** após **30 dias** do último lead que a
   compõe. Coorte imatura não entra em comparação de CAC.

O CAC de uma coorte é, portanto, `custo da coorte ÷ vendas maduras da coorte`.

## Consequências

**O que ganhamos**

- Comparação entre períodos passa a ser entre iguais. O baseline e o período
  analisado carregam o mesmo grau de maturação.
- A flag de maturidade da camada `intermediate` (etapa 2.3) e a regra **R99**
  passam a ter base: "não sei ainda" vira um estado explícito, não um número
  ruim disfarçado de resposta.
- A decomposição da R1 em efeito-CPL e efeito-conversão só é possível com
  coorte, porque os dois efeitos precisam se referir ao mesmo grupo de leads.

**O que pagamos**

- **O período mais recente é permanentemente indiagnosticável.** Não se
  responde sobre os últimos 30 dias. Para uma agência acostumada a relatório
  semanal, isso é uma frustração real e precisa estar declarada no README, não
  escondida.
- A geração de dados passa a exigir **30 dias simulados além do último lead**
  (etapa 1.6). Sem isso, a coorte final nunca amadurece e o período analisado
  fica vazio — que é exatamente o bug que esta ADR corrige.
- A camada `intermediate` fica mais cara: é preciso ligar venda a lead, e não
  apenas somar por mês.

## Trade-off em uma frase

Abrimos mão de responder sobre **ontem** para poder responder com verdade sobre
**há quarenta e cinco dias**.

## O que reabriria esta decisão

Uma medição mostrando que a distribuição do lag de fechamento é suficientemente
concentrada (por exemplo, 90% dos fechamentos dentro de 7 dias) a ponto de o
erro do cálculo convencional ficar abaixo do ruído. Nesse funil, seria o caso de
reduzir a janela de maturação — não de abandonar a coorte.
