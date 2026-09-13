# `app/`

> A última camada e a mais barata: apresenta o que o motor já concluiu, sem
> concluir nada.

**O que vive aqui**
O Streamlit: seletor de conta, CAC com faixa de controle, achados ordenados por
dinheiro em risco, painel de cobertura de atribuição.

**O que não vive aqui**
Cálculo. Nenhum. Se um número precisar ser computado nesta pasta, isso é sinal de
que ele está faltando no `motor/` — a correção é lá, não aqui.

**Lê de** os achados do motor · **Escreve** nada

**Por que "a mais barata"**
É a camada descartável por decisão: se o prazo apertar, corta-se interface e
narrativa antes de qualquer outra coisa. Um projeto sem tela ainda prova o que
promete; um projeto sem avaliação, não.

**O critério de sucesso desta pasta não é estética.** É que duas pessoas que não
conhecem o projeto olhem a tela e digam o que fariam, sem ninguém explicar nada.
