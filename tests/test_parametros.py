"""Testes de `dados_sinteticos.parametros`.

Estes testes existem porque o `ruff` passou três vezes seguidas num arquivo que
tinha cinco defeitos reais: ticket de R$ 3,50, baseline errado, tupla que era
lista, dicionário mutável dentro de um frozen, e multiplicador com sinal
trocado. Linter verifica forma; estes testes verificam significado.
"""

from dataclasses import FrozenInstanceError, fields
from typing import get_type_hints

import pytest

from dados_sinteticos.parametros import (
    COMPLETUDE_BASE,
    CONTAS_PADRAO,
    DISTRIBUICAO_LAG,
    FUNIL_BASE,
    JANELA_PADRAO,
    RUIDO,
    SEMENTE_PADRAO,
    SLA_POR_ESTAGIO,
    SLA_PRIMEIRO_CONTATO,
    Conta,
    Estagio,
)

TICKET_MINIMO = 3_000
TICKET_MAXIMO = 15_000


# --------------------------------------------------------------------------
# Tipos declarados x valores reais
# --------------------------------------------------------------------------
def test_tipos_das_contas_batem_com_a_anotacao():
    """`@dataclass` NÃO valida tipo em runtime — a anotação é só documentação.

    Foi assim que `ticket_base=3.500` passou: Python leu como float 3.5, o
    dataclass aceitou e o ruff não olhou. Este teste é a validação que falta.
    """
    anotacoes = get_type_hints(Conta)
    for conta in CONTAS_PADRAO:
        for campo in fields(conta):
            valor = getattr(conta, campo.name)
            esperado = anotacoes[campo.name]
            if esperado is int:
                # `type(...) is int` e não isinstance: float NÃO pode passar
                assert type(valor) is int, (
                    f"{conta.id}.{campo.name} = {valor!r} é {type(valor).__name__}, deveria ser int"
                )
            else:
                assert isinstance(valor, esperado), (
                    f"{conta.id}.{campo.name} = {valor!r} não é {esperado}"
                )


def test_ticket_dentro_da_faixa_do_projeto():
    """CLAUDE.md seção 2: ticket de R$ 3 a 15 mil. Fora disso, é erro de dígito."""
    for conta in CONTAS_PADRAO:
        assert TICKET_MINIMO <= conta.ticket_base <= TICKET_MAXIMO, (
            f"{conta.id}: ticket {conta.ticket_base}"
        )


# --------------------------------------------------------------------------
# Imutabilidade — sem ela, gerar("normal", 42) para de ser reprodutível
# --------------------------------------------------------------------------
def test_contas_sao_tupla_e_nao_lista():
    """Lista aceitaria `.append()` e a coleção mudaria em runtime."""
    assert isinstance(CONTAS_PADRAO, tuple)


def test_conta_nao_aceita_mutacao():
    with pytest.raises(FrozenInstanceError):
        CONTAS_PADRAO[0].cpl_base = 999  # type: ignore[misc]


def test_sla_por_estagio_e_somente_leitura():
    """`dict` comum furaria a garantia do frozen: o objeto interno é mutável."""
    with pytest.raises(TypeError):
        SLA_POR_ESTAGIO[Estagio.NOVO] = 99  # type: ignore[index]


# --------------------------------------------------------------------------
# Coerência do conjunto de contas
# --------------------------------------------------------------------------
def test_doze_contas_com_id_unico():
    assert len(CONTAS_PADRAO) == 12
    ids = [c.id for c in CONTAS_PADRAO]
    assert len(set(ids)) == len(ids)


def test_dispersao_entre_contas_e_real():
    """Contas parecidas fariam um limiar único funcionar — e o projeto não
    provaria nada. A estratégia promete ticket variando ~4x."""
    tickets = [c.ticket_base for c in CONTAS_PADRAO]
    assert max(tickets) / min(tickets) >= 3.0


def test_lag_cabe_dentro_do_corte_da_distribuicao():
    """p90 ≈ 2,2 x mediana; se o p90 estourar o corte, a cauda é amputada."""
    for conta in CONTAS_PADRAO:
        p90 = conta.lag_mediano_dias * DISTRIBUICAO_LAG.razao_p90_mediana
        assert p90 < DISTRIBUICAO_LAG.corte_dias, f"{conta.id}: p90 {p90:.0f}d"


# --------------------------------------------------------------------------
# Faixas de probabilidade — tudo que é taxa tem que estar em [0, 1]
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "valor",
    [
        FUNIL_BASE.taxa_lead_qualificado,
        FUNIL_BASE.taxa_qualificado_proposta,
        FUNIL_BASE.taxa_proposta_ganho,
        COMPLETUDE_BASE.utm_valida,
        COMPLETUDE_BASE.campaign_source_nulo,
        COMPLETUDE_BASE.contato_duplicado,
        RUIDO.variacao_diaria_amplitude,
    ],
)
def test_taxas_entre_zero_e_um(valor: float):
    assert 0.0 <= valor <= 1.0


def test_margens_entre_zero_e_um():
    for conta in CONTAS_PADRAO:
        assert 0.0 < conta.margem_base < 1.0, conta.id


def test_fim_de_semana_e_multiplicador_e_nao_desconto():
    """0.55 = "resta 55% do volume". Um valor negativo denuncia que alguém
    guardou o delta (-0.45) num campo que o gerador vai multiplicar."""
    assert 0.0 < RUIDO.fim_de_semana_mult <= 1.0


# --------------------------------------------------------------------------
# Faixas de score_fit
# --------------------------------------------------------------------------
def test_proporcoes_de_fit_somam_um():
    """Se não somarem 1,0, parte dos leads não recebe faixa — e a R3 avalia
    SLA contra um denominador que não existe."""
    total = sum(f.proporcao_leads for f in SLA_PRIMEIRO_CONTATO)
    assert total == pytest.approx(1.0)


def test_faixas_de_fit_sao_descendentes_e_cobrem_do_zero():
    cortes = [f.score_min for f in SLA_PRIMEIRO_CONTATO]
    assert cortes == sorted(cortes, reverse=True), "faixas fora de ordem"
    assert cortes[-1] == 0, "a faixa mais baixa tem que começar em 0"


def test_sla_mais_curto_para_o_fit_mais_alto():
    """Lead melhor, resposta mais rápida. O inverso inverteria a R3."""
    slas = [f.sla_minutos for f in SLA_PRIMEIRO_CONTATO]
    assert slas == sorted(slas), "SLA deveria crescer conforme o fit cai"


# --------------------------------------------------------------------------
# SLA por estágio
# --------------------------------------------------------------------------
def test_estagios_terminais_nao_tem_sla():
    """GANHO e PERDIDO são estados finais: não dá para ficar "parado" neles."""
    assert Estagio.GANHO not in SLA_POR_ESTAGIO
    assert Estagio.PERDIDO not in SLA_POR_ESTAGIO


def test_todo_estagio_nao_terminal_tem_sla():
    terminais = {Estagio.GANHO, Estagio.PERDIDO}
    for estagio in Estagio:
        if estagio not in terminais:
            assert estagio in SLA_POR_ESTAGIO, estagio


# --------------------------------------------------------------------------
# Janela e semente
# --------------------------------------------------------------------------
def test_baseline_maior_que_periodo_analisado():
    """ADR 0001: o baseline precisa de mais massa que o período comparado."""
    assert JANELA_PADRAO.baseline > JANELA_PADRAO.analisado


def test_maturacao_de_trinta_dias():
    """ADR 0001. Mudar isto invalida a comparação entre coortes."""
    assert JANELA_PADRAO.maturacao == 30


def test_semente_e_inteiro():
    assert isinstance(SEMENTE_PADRAO, int)
