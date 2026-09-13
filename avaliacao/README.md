# `avaliacao/`

> O adversário do motor: guarda o gabarito e mede se o veredito está certo.

**O que vive aqui**
`gabarito_contas.json` (qual cenário foi plantado em cada conta), a matriz de
confusão, o conjunto cego com as armadilhas, e o **detector trivial** — três
linhas do tipo *"alerte se o CAC subiu mais de 25%"*, que roda em todo commit
como concorrente. Se o motor não ganhar dele com folga, a complexidade não se
paga.

**Por que é separada de `tests/`**
As duas testam, mas fazem perguntas diferentes:

| | Pergunta |
|---|---|
| `tests/` | *o código faz o que eu escrevi?* |
| `avaliacao/` | *o que eu escrevi acerta a realidade?* |

Um teste unitário verde não diz nada sobre precisão. Um motor pode passar em
todos os testes e ainda assim errar 80% dos diagnósticos.

**Por que o gabarito não fica em `raw/`**
Não é sigilo — todo dado aqui é sintético. É que o gabarito é a resposta da
prova. Se ele estiver dentro de `raw/`, o pipeline pode chegar nele, e a medição
de precisão deixa de significar qualquer coisa.

**Números de referência a bater** (protótipo): precisão ≥ 0,95 em toda regra no
conjunto cego; alarme falso em armadilhas de **1,4%**, contra **41,4%** do
detector trivial.

**Se o prazo apertar, corte interface e narrativa. Nunca corte esta pasta** — é
ela que transforma o projeto de demonstração em evidência.
