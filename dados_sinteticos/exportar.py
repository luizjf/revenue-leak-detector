"""Exportação para raw/: transforma os dados limpos no que as fontes entregariam.

ESTA É A ÚNICA CAMADA QUE PIORA O DADO, e de propósito. Se raw/ nascer limpo,
a Fase 2 não tem o que tratar e os 30 testes da 2.5 não têm o que reprovar.

TRÊS CAMADAS, nesta ordem:
    renderizar  DadosConta -> registros no formato da fonte (ainda limpos)
    sujar       registros -> registros (funções PURAS, testáveis uma a uma)
    gravar      registros -> arquivo (único lugar com pathlib/csv/json)

O GABARITO VAI PARA avaliacao/. Nunca para raw/.

PANDAS NÃO ENTRA AQUI: `csv` da stdlib dá controle exato sobre separador,
decimal e aspas. O DataFrame faria coerção silenciosa de tipo — que é
exatamente a classe de bug que este projeto passa o tempo todo combatendo.
"""

import base64
import csv
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Final

import numpy as np

from dados_sinteticos.gerador import DadosConta, Resultado
from dados_sinteticos.parametros import COMPLETUDE_BASE, Conta

# A IMPORTAR quando a orquestracao for escrita — o ruff apaga import nao usado:
#   gerar, CONTAS_PADRAO, SEMENTE_PADRAO  ->  main() e exportar()

# ── constantes ─────────────────────────────────────────────────────────────

# Semente PRÓPRIA da sujeira, e não SeedSequence.spawn(2).
# Medido: spawn(2)[1] é o mesmo fluxo de spawn(12)[1], que o gerador usa na
# conta nº 2. A sujeira sairia sincronizada com os dados daquela conta.
SEMENTE_SUJEIRA_PADRAO: Final[int] = 20_260_914

# 25 linhas por página força ~15 páginas por conta: o suficiente para que ler
# só a primeira seja um erro visível, e não um detalhe.
LINHAS_POR_PAGINA: Final[int] = 25

# As cinco caixas que convivem no mesmo arquivo. Normalizar isto e trabalho de
# staging (tipagem), nao regra de negocio.
#
# SO VARIACOES DE CAIXA DO MESMO VALOR. Nao entram variantes de "google ads":
# o CLAUDE.md secao 2 fixa UM canal de midia por conta (Meta), e trocar a
# origem de um lead nao e sujeira de apresentacao — e dado errado. Isso
# quebraria o limite entre fontes do contrato (secao 6, "toda campaign_source
# do CRM existe nos insights") e inventaria um segundo canal que nao existe.
CAIXAS_UTM: Final[tuple[str, ...]] = (
    "facebook_ads",
    "FaceBook_Ads",
    "FACEBOOK ADS",
    "Facebook-Ads",
    " facebook_ads ",
)

FRACAO_DUPLICATAS: Final[float] = COMPLETUDE_BASE.contato_duplicado
LINHAS_NA_AMOSTRA: Final[int] = 20
NOME_GABARITO: Final[str] = "gabarito_contas.json"

# (separador, decimal) por arquivo. O financeiro e o UNICO com ponto e virgula
# e decimal em virgula (contrato, 5.5) — e o arquivo mais perigoso do projeto:
# "3.450,00" lido por parser de ponto decimal vira 3.450, mil vezes menor,
# sem excecao e sem log.
CONVENCAO_CSV: Final[Mapping[str, tuple[str, str]]] = {
    "financeiro_margens.csv": (";", ","),
}
CONVENCAO_CSV_PADRAO: Final[tuple[str, str]] = (",", ".")

# Terminador de linha FIXO, nunca o default do modulo csv (CRLF).
# O CI roda em Linux e a maquina de desenvolvimento e Windows: com
# terminador dependente de plataforma, o mesmo comando produziria raw/
# diferente nos dois, e o criterio da etapa 1.7 -- gerar 12 contas do zero
# em maquina limpa -- perderia o sentido.
FIM_DE_LINHA: Final[str] = chr(10)  # LF explicito, sem escape ambiguo


# ===========================================================================
# 1. RENDERIZAR — DadosConta -> registros no formato de cada fonte
#    Sem sujeira nenhuma. Dá para conferir campo a campo contra o contrato.
# ===========================================================================
def _identidade(contact_id: str) -> dict[str, str]:
    """Deriva e-mail, nome e telefone do id, de forma determinística.

    Estes três campos NÃO vêm do gerador de propósito: nenhuma regra do motor
    os usa. O único consumidor deles é a duplicata de contato — e campo cujo
    único uso é a sujeira pertence à camada da sujeira.
    """


def _registros_insights(dados: DadosConta, conta: Conta, indice: int) -> list[dict]:
    """Um registro por campanha por dia, no formato /insights da Graph API.

    `date_start` e `date_stop` saem IGUAIS: é o que declara que o grão é
    diário. Se um dia divergirem, o pipeline soma semanas achando que são
    dias — sem erro nenhum aparecer.
    """


def _registros_contatos(dados: DadosConta) -> list[dict]:
    """Um registro por lead, no formato do export do CRM.

    `data_criacao` sai com `-03:00` porque o datetime já nasceu com tzinfo lá
    no gerador: `.isoformat()` produz o fuso sozinho. Timestamp ingênuo aqui
    obrigaria a colar o offset como string, e ninguém testaria isso.
    """


def _registros_negocios(dados: DadosConta) -> list[dict]:
    """Um registro por negócio.

    `campaign_source` vazio quando o gerador produziu None — é o fenômeno da
    R8, não sujeira nossa. `data_fechamento` vazio quando aberto.
    `margem` NÃO entra aqui: pertence ao financeiro. Um objeto de origem pode
    alimentar dois arquivos de destino.
    """


def _registros_atividades(dados: DadosConta) -> list[dict]:
    """Um registro por toque. `direcao` e `resultado` são obrigatórios: sem os
    dois, a R7 não distingue "não ligou" de "ligou e o lead sumiu"."""


def _registros_margens(dados: DadosConta) -> list[dict]:
    """Um registro por negócio GANHO, por mês de competência.

    Os valores saem como float e só viram texto no escritor — é lá que mora a
    convenção de vírgula decimal.
    """


# ===========================================================================
# 2. SUJAR — funções puras. Nenhuma toca em disco, nenhuma muda a entrada.
#    [EU DIGITO] — cinco funções, uma de cada vez.
# ===========================================================================
def sujar_numeros_como_texto(registros: list[dict], campos: Sequence[str]) -> list[dict]:
    """Converte os campos indicados para string. Sem alterar mais nada."""


def sujar_caixa_utm(
    registros: list[dict], campos: Sequence[str], rng: np.random.Generator
) -> list[dict]:
    """Sorteia uma das CAIXAS_UTM para cada registro. Sujeira de APRESENTAÇÃO:
    depois de normalizar, tem que sobrar o valor de origem."""


def duplicar_contatos(
    registros: list[dict], fracao: float, rng: np.random.Generator
) -> tuple[list[dict], int]:
    """Repete ~`fracao` dos contatos com MESMO e-mail e `contact_id` NOVO.
    Devolve (registros, quantidade duplicada) — a contagem vai para o gabarito."""


def reentregar_um_dia(registros: list[dict], rng: np.random.Generator) -> tuple[list[dict], str]:
    """Duplica EXATAMENTE uma linha (campanha, dia) dos insights, cópia
    idêntica. Devolve (registros, chave duplicada)."""


def orfanizar_uma_campanha(
    negocios: list[dict], rng: np.random.Generator
) -> tuple[list[dict], str]:
    """Reescreve `campaign_source` de alguns negócios para uma campanha que não
    existe nos insights. Devolve (registros, id órfão)."""


# ===========================================================================
# 3. GRAVAR — único lugar do módulo com I/O
# ===========================================================================
def _formatar(valor: object, decimal: str = ".") -> str:
    """Converte um valor Python para o texto que vai para a célula do CSV.

    É aqui que a convenção decimal de cada fonte se materializa. Repare que a
    escolha NÃO é de estilo: o contrato fixa dois formatos incompatíveis, e o
    parser da Fase 2 é escrito contra eles.

        decimal="."  ->  3450.00     CRM, contrato 5.2: ^\\d+(\\.\\d{1,2})?$
                                     sem separador de milhar
        decimal=","  ->  3.450,00    financeiro, contrato 5.5:
                                     ^\\d{1,3}(\\.\\d{3})*,\\d{2}$

    `None` vira campo vazio, nunca a string "None". Isso importa: o contrato
    permite nulo em `campaign_source`, `data_fechamento` e `motivo_perda` — a
    ausência é sinal (R8, negócio aberto), e escrever "None" transformaria o
    sinal num valor literal que o staging trataria como texto válido.
    """
    if valor is None:
        return ""
    # bool antes de int: em Python, bool É int, e True viraria "1".
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float):
        if decimal == ",":
            # f"{v:,.2f}" produz o padrão en-US (3,450.00). A troca em duas
            # etapas usa um marcador intermediário porque substituir "," por
            # "." e depois "." por "," desfaria a primeira troca.
            texto = f"{valor:,.2f}"
            return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        # Sem separador de milhar: o contrato do CRM não o permite.
        return f"{valor:.2f}"
    if isinstance(valor, datetime | date):
        # `.isoformat()` já emite o offset -03:00 porque o gerador criou o
        # datetime com tzinfo. Se ele fosse ingênuo, o offset teria que ser
        # colado como string aqui — e nenhum teste pegaria o erro.
        return valor.isoformat()
    return str(valor)


def _cursor(indice_pagina: int) -> str:
    """Cursor de paginação, opaco e determinístico.

    A Graph API devolve algo como "MjQZD" — base64 sem significado para quem
    consome. Opaco é o ponto: a ingestão tem que SEGUIR o cursor em vez de
    calcular a próxima página, que é o erro clássico de quem assume
    `?page=N+1`. Determinístico é exigência do critério de saída: duas
    execuções com a mesma entrada produzem arquivos byte a byte iguais.
    """
    bruto = f"cursor:{indice_pagina:04d}".encode()
    return base64.urlsafe_b64encode(bruto).decode("ascii").rstrip("=")


def _escrever_csv(
    registros: list[dict],
    caminho: Path,
    sep: str = ",",
    decimal: str = ".",
    citar: bool = False,
) -> None:
    """Escreve um CSV. Um escritor, duas convenções — parametrizado.

    Três detalhes que parecem burocracia e são bug se faltarem:

    `newline=""`      sem isso o csv.writer escreve CR CR LF no Windows, e todo
                      leitor vê uma linha em branco entre cada registro. Não
                      aparece no editor; aparece no `wc -l` e no parser.
    `encoding="utf-8"` o default no Windows é a codepage ANSI. "Saúde" viraria
                      mojibake, e o contrato (seção 4) exige UTF-8.
    `lineterminator`  fixo em LF, senão o mesmo comando gera arquivos
                      diferentes no Windows e no CI Linux.

    `citar=True` força aspas em todos os campos — o export do CRM as tem
    (contrato 5.2). O financeiro não (5.5), por isso é parâmetro e não default.

    O cabeçalho sai das chaves do PRIMEIRO registro: os renderizadores montam
    todos os dicionários com as mesmas chaves na mesma ordem, e um registro
    fora do padrão é bug de renderizador, não algo a tolerar aqui.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not registros:
        # Arquivo vazio em vez de arquivo ausente: a Fase 2 lê a fonte e
        # encontra zero linhas, em vez de estourar em "arquivo não existe".
        caminho.write_text("", encoding="utf-8")
        return

    colunas = list(registros[0].keys())
    aspas = csv.QUOTE_ALL if citar else csv.QUOTE_MINIMAL
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=sep, quoting=aspas, lineterminator=FIM_DE_LINHA)
        escritor.writerow(colunas)
        for registro in registros:
            escritor.writerow([_formatar(registro.get(c), decimal) for c in colunas])


def _escrever_json_paginado(
    registros: list[dict],
    pasta: Path,
    prefixo: str,
    por_pagina: int = LINHAS_POR_PAGINA,
) -> list[Path]:
    """Quebra os registros em páginas no formato /insights e grava cada uma.

    Formato de cada página, igual ao da Graph API:

        {"data": [...], "paging": {"cursors": {"before":…, "after":…},
                                   "next": "https://…?after=…"}}

    A ÚLTIMA página não tem `next`. É a ausência dele que diz à ingestão onde
    parar — quem parar antes perde custo, e custo perdido derruba o CAC sem
    erro nenhum aparecer.

    Nome com zero à esquerda (`_pagina_01`) porque são ~15 páginas por conta:
    sem o zero, a ordem alfabética seria 1, 10, 11, 2, e quem concatenar na
    ordem do diretório monta o arquivo embaralhado.

    Devolve os caminhos na ordem, para os testes conferirem a concatenação.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    total = max(1, math.ceil(len(registros) / por_pagina))
    caminhos: list[Path] = []

    for indice in range(total):
        fatia = registros[indice * por_pagina : (indice + 1) * por_pagina]
        e_ultima = indice == total - 1
        depois = _cursor(indice + 1)
        pagina = {
            "data": fatia,
            "paging": {
                "cursors": {"before": _cursor(indice), "after": depois},
                # None e não chave ausente: a API devolve o campo, e é o valor
                # nulo que sinaliza o fim. Ausência da chave também funcionaria,
                # mas obrigaria a ingestão a distinguir "sem next" de "chave
                # que eu esqueci de ler".
                "next": None if e_ultima else f"{prefixo}?after={depois}",
            },
        }
        caminho = pasta / f"{prefixo}_pagina_{indice + 1:02d}.json"
        caminho.write_text(
            # ensure_ascii=False preserva "PROSPECÇÃO" legível no arquivo;
            # indent=2 é desvio deliberado (a API real devolve compacto) porque
            # raw/ é lido por humano em toda depuração e o parser não se importa.
            json.dumps(pagina, ensure_ascii=False, indent=2, default=_formatar) + FIM_DE_LINHA,
            encoding="utf-8",
            newline="",
        )
        caminhos.append(caminho)
    return caminhos


def _escrever_amostras(por_fonte: dict[str, list[dict]], pasta: Path) -> None:
    """Grava um recorte curto de cada fonte em `docs/amostras/`.

    A chave de `por_fonte` é o NOME DO ARQUIVO (`crm_contatos.csv`,
    `meta_ads_insights.json`) — é dele que sai a convenção de separador e
    decimal, via CONVENCAO_CSV. Passar o nome em vez de um enum evita uma
    tabela de tradução a mais entre esta função e a orquestração.

    Por que existir: quem avalia o projeto abre o GitHub por dois minutos e não
    vai clonar nada. Precisa VER a sujeira — o número como string, o fuso, o
    ponto e vírgula. E a amostra é escrita pelo mesmo código que escreve raw/,
    no mesmo passo: vitrine copiada à mão apodrece na primeira mudança de
    formato, vitrine gerada não.

    Estes arquivos SÃO versionados (ao contrário de raw/): são kilobytes.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, registros in por_fonte.items():
        recorte = registros[:LINHAS_NA_AMOSTRA]
        if nome.endswith(".json"):
            _escrever_json_paginado(recorte, pasta, nome.removesuffix(".json"), LINHAS_NA_AMOSTRA)
        else:
            sep, decimal = CONVENCAO_CSV.get(nome, CONVENCAO_CSV_PADRAO)
            _escrever_csv(recorte, pasta / nome, sep=sep, decimal=decimal)


# ===========================================================================
# 4. ORQUESTRAÇÃO
# ===========================================================================
def _exportar_conta(
    dados: DadosConta,
    conta: Conta,
    indice: int,
    raiz: Path,
    rng: np.random.Generator,
) -> dict:
    """Renderiza, suja e grava uma conta. Devolve as contagens de sujeira."""


def exportar(
    resultado: Resultado,
    raiz: Path,
    semente_sujeira: int = SEMENTE_SUJEIRA_PADRAO,
) -> dict:
    """Grava tudo sob `raiz`: raw/, avaliacao/ e docs/amostras/.

    Recebe o `Resultado` pronto em vez de chamar `gerar()`: separar as duas
    coisas é o que permite testar a exportação sem esperar 5 s de simulação, e
    exportar o mesmo dado com sujeiras diferentes.

    `raiz` é argumento, e não `Path("raw")` fixo, para os testes escreverem em
    tmp_path. Exportador que assume o diretório do projeto não é testável.
    """


def main() -> None:
    """Ponto de entrada: python -m dados_sinteticos.exportar

    O critério de saída da etapa é `make dados`, mas `make` não existe nesta
    máquina. O Makefile da 1.8 é um invólucro de três linhas em volta disto —
    quem faz o trabalho é o módulo, e atalho que não roda no Windows não pode
    ser o único caminho.
    """
