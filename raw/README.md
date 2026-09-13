# `raw/`

> O que as fontes entregaram, intocado: ninguém edita nada aqui à mão, e nada
> daqui vai para o Git.

**Esta pasta não é versionada.** Este README é a única exceção — ele existe para
que quem abrir o repositório saiba que a pasta existe, o que cai nela e como
recriá-la.

**O que cai aqui**

```
raw/
├── conta_001/
│   ├── meta_ads_insights_pagina_1.json   resposta paginada da Graph API
│   ├── meta_ads_insights_pagina_2.json
│   ├── crm_negocios.csv                  export do CRM
│   ├── crm_contatos.csv
│   ├── crm_atividades.csv
│   └── financeiro_margens.csv            planilha do financeiro
├── conta_002/  …  └── conta_012/
```

Doze contas, cerca de 29 MB. O conteúdo é sujo de propósito: número gravado como
string, timestamp ISO com fuso `-03:00`, UTM em caixas inconsistentes, contatos
duplicados, `campaign_source` nulo, paginação com cursor, CSV com ponto e vírgula
e decimal com vírgula. Se o dado nascesse limpo, a camada de transformação não
teria o que fazer.

**Por que não é versionada**
Porque é regenerável, e porque o histórico do Git é imutável: 29 MB que entram
num commit ficam em todo clone para sempre, mesmo depois de apagados.

**Como recriar** *(a partir da etapa 1.7)*

```
python -m dados_sinteticos.gerador
```

**Como ver o formato sem rodar nada** *(a partir da etapa 1.7)*
`docs/amostras/` guarda um recorte curto de cada arquivo, versionado e escrito
pelo próprio exportador — se o formato mudar, a amostra muda junto.

**O que nunca entra aqui**
O gabarito de qual cenário foi plantado em cada conta. Ele vive em `avaliacao/`.
O pipeline não pode enxergar a resposta.
