# `motor/`

> Onde o dado confiável vira veredito: julgamento, incerteza e precedência entre
> regras, em Python.

**O que vive aqui**
A camada de métricas lendo das marts, e as regras de detecção:

| | |
|---|---|
| **R0** | dados incompletos — bloqueante, roda primeiro |
| **R1, R2, R4, R5** | econômicas (CAC, CPL, margem, payback) |
| **R3, R6, R7** | operacionais (SLA, pipeline parado, follow-up) |
| **R8, R10** | rastreabilidade de receita e mudança de mix |
| **R99** | amostra insuficiente — silencia as regras econômicas |

Mais a hierarquia que decide qual regra tem precedência sobre qual.

**O que não vive aqui**
SQL de detecção, e nenhuma tela. Também não vive aqui o gabarito: o motor não
pode enxergar a resposta que ele está tentando adivinhar.

**Lê de** as marts do DuckDB · **Escreve** achados, consumidos por `app/` e
medidos por `avaliacao/`

**O que distingue este motor de um relatório:** ele decide *qual* é o problema,
com quanta confiança — e **se recusa a responder** quando a amostra não permite
afirmar. R4 e R10 são as regras mais valiosas justamente porque impedem uma ação
errada: um detector ingênuo mata a campanha mais lucrativa da conta porque olhou
só o CAC.
