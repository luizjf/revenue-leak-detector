# `tests/`

> Prova que o código Python faz o que ele diz que faz — e só isso.

**O que vive aqui**
Testes de `pytest` sobre o código Python: gerador, exportador, camada de
métricas e as regras do motor.

**O que não vive aqui** — e esta é a parte que importa

Neste projeto existem **três** coisas que testam. Cada uma tem seu lugar:

| Onde | O que verifica | Quem roda |
|---|---|---|
| `tests/` | o código Python faz o que foi escrito | `pytest` |
| `transform/` | o dado obedece ao contrato | `dbt build` |
| `avaliacao/` | o diagnóstico acerta a realidade | a matriz de confusão |

Teste de SQL não vem para cá: ele vive junto do modelo que testa, e quem o
executa é o dbt. Medição de precisão também não: um motor pode passar em 100%
dos testes unitários e ainda errar o diagnóstico.

**Marcadores**
`lento` — rodada longa do conjunto cego (300 execuções por cenário, etapa 3.6).
Pular com `-m "not lento"`. O `--strict-markers` do `pyproject.toml` faz um
marcador com typo virar erro, em vez de silenciosamente rodar tudo.

**Roda com** `pytest`, a partir da raiz do repositório.
