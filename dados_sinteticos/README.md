# `dados_sinteticos/`

> Simula o mundo: produz o dado como ele nasceria nas fontes, com a sujeira que
> elas têm — e não sabe **como o motor procura**, embora saiba **o que plantou**.

**O que vive aqui**
`parametros.py` (faixas base do funil), `cenarios.py` (as perturbações dos 10
cenários), `gerador.py` (a simulação) e `exportar.py` (a gravação no formato das
APIs, com a sujeira injetada).

**O que não vive aqui**
Nenhuma regra de detecção e nenhum limiar do motor. Esta é a fronteira que
sustenta a medição de precisão: o gerador registra no gabarito **qual** problema
plantou, mas não pode conhecer o limiar com que o motor o procura. No dia em que
ele plantar "CPL 26% acima" porque o motor dispara em 25%, o alvo passa a ser
desenhado para o motor acertar, e o número de precisão vira ficção.

**Escreve em**
`raw/` (os dados, sujos) e `avaliacao/gabarito_contas.json` (a resposta).
Nunca os dois no mesmo lugar — ver `avaliacao/README.md`.

**Lê de**
Nada. É a origem do projeto.
