# `transform/`

> Transforma o cru em confiável, em SQL: tipa, deduplica, define grão e recusa
> dado fora do contrato.

**O que vive aqui**
O projeto dbt sobre DuckDB, em quatro camadas:

| Camada | Trabalho |
|---|---|
| `sources` | aponta para os arquivos de `raw/` |
| `staging` | tipagem e renomeação. **Zero regra de negócio** |
| `intermediate` | deduplicação por hash, coorte de lead, custo por campanha e dia, negócios atribuídos |
| `marts` | tabela pronta para consumo: `fct_coorte_semanal`, `fct_funil_diario`, `mart_metricas_periodo`, `dim_campanha`, `dim_estagio` |

Mais os testes em SQL — chaves, relacionamentos, valores aceitos, e os testes
singulares (fechamento anterior ao lead, maturidade de coorte).

**O que não vive aqui**
Regra de detecção. O `CLAUDE.md` seção 6 é explícito: *"dbt não roda a
detecção"*. Intervalo de confiança, teste de proporção e hierarquia condicional
são Python, em `motor/`. Regra de detecção escrita em SQL vira código impossível
de testar unitariamente.

**Lê de** `raw/` · **Escreve em** o arquivo DuckDB (não versionado)

**A capacidade que importa aqui não é modelar — é recusar.** Um `dbt build` que
nunca falha é um pipeline que não está olhando. `target/`, `logs/` e
`dbt_packages/` são gerados e ficam fora do Git.
