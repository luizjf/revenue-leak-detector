"""Testes de `dados_sinteticos.cenarios`.

Especificação executável do módulo: se estes passam, o registro está coerente
com docs/parametros-e-cenarios.md, seções 5 a 7.
"""

from dataclasses import FrozenInstanceError

import pytest

from dados_sinteticos.cenarios import (
    ARMADILHAS,
    CENARIOS,
    CONDICOES_TRANSVERSAIS,
    Faixa,
    NomeCenario,
    NomeCondicao,
    Perturbacao,
)

REGRAS_VALIDAS = {"R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R10", "R99"}


# --------------------------------------------------------------------------
# Faixa
# --------------------------------------------------------------------------
def test_faixa_recusa_intervalo_invertido():
    """Faixa invertida sortearia de intervalo vazio: cenário sem perturbação."""
    with pytest.raises(ValueError):
        Faixa(minimo=1.7, maximo=1.3)


def test_faixa_e_imutavel():
    with pytest.raises(FrozenInstanceError):
        Faixa(minimo=1.0, maximo=2.0).minimo = 9.0  # type: ignore[misc]


# --------------------------------------------------------------------------
# Registro de cenários
# --------------------------------------------------------------------------
def test_todo_nome_tem_entrada_no_registro():
    assert set(CENARIOS) == set(NomeCenario)


def test_chave_bate_com_o_nome_interno():
    """Divergência faz o gabarito gravar um cenário e a matriz procurar outro —
    a precisão daquela regra vira zero sem explicação."""
    for chave, cenario in CENARIOS.items():
        assert cenario.nome == chave


def test_onze_cenarios():
    """Dez perturbações mais o controle `normal`."""
    assert len(CENARIOS) == 11


def test_registro_e_somente_leitura():
    with pytest.raises(TypeError):
        CENARIOS[NomeCenario.NORMAL] = None  # type: ignore[index]


def test_normal_nao_perturba_nada():
    """Controle: qualquer achado do motor aqui é falso positivo."""
    normal = CENARIOS[NomeCenario.NORMAL]
    assert normal.perturbacao == Perturbacao()
    assert normal.regras_esperadas == ()


def test_demais_cenarios_perturbam_e_esperam_regra():
    for nome, cenario in CENARIOS.items():
        if nome is NomeCenario.NORMAL:
            continue
        assert cenario.perturbacao != Perturbacao(), f"{nome} não perturba nada"
        assert cenario.regras_esperadas, f"{nome} não espera regra nenhuma"


def test_regras_esperadas_existem():
    for nome, cenario in CENARIOS.items():
        for regra in cenario.regras_esperadas:
            assert regra in REGRAS_VALIDAS, f"{nome}: regra desconhecida {regra}"


def test_todo_cenario_tem_descricao():
    for nome, cenario in CENARIOS.items():
        assert cenario.descricao.strip(), f"{nome} sem descrição"


# --------------------------------------------------------------------------
# Semântica dos sufixos: _mult x _delta_pp x _frac
# --------------------------------------------------------------------------
def _faixas_por_sufixo(sufixo: str) -> list[tuple[str, str, Faixa]]:
    """Varre toda perturbação declarada: cenários, condições e armadilhas."""
    fontes = [*CENARIOS.items(), *CONDICOES_TRANSVERSAIS.items(), *ARMADILHAS.items()]
    return [
        (str(nome), campo, valor)
        for nome, item in fontes
        for campo, valor in vars(item.perturbacao).items()
        if valor is not None and campo.endswith(sufixo)
    ]


def test_multiplicadores_sao_positivos():
    """`*_mult` multiplica a base. Zero ou negativo denuncia delta no lugar."""
    for nome, campo, faixa in _faixas_por_sufixo("_mult"):
        assert faixa.minimo > 0, f"{nome}.{campo}: mínimo {faixa.minimo}"


def test_multiplicadores_de_queda_nao_exageram():
    """ "-25%" como multiplicador é 0.75, não 0.25. Mínimo abaixo de 0,15 quase
    sempre é a redução escrita no lugar do que resta dela."""
    for nome, campo, faixa in _faixas_por_sufixo("_mult"):
        assert faixa.minimo >= 0.15, f"{nome}.{campo}: mínimo {faixa.minimo}"


def test_fracoes_estao_entre_zero_e_um():
    """`*_frac` é fração de casos: nunca passa de 1,0."""
    for nome, campo, faixa in _faixas_por_sufixo("_frac"):
        assert 0.0 <= faixa.minimo <= faixa.maximo <= 1.0, f"{nome}.{campo}"


def test_deltas_em_pontos_percentuais_sao_pequenos():
    """`*_delta_pp` soma pontos: 0.05 = +5 p.p. Acima de 1,0 é multiplicador
    disfarçado."""
    for nome, campo, faixa in _faixas_por_sufixo("_delta_pp"):
        assert max(abs(faixa.minimo), abs(faixa.maximo)) <= 1.0, f"{nome}.{campo}"


# --------------------------------------------------------------------------
# Cenários cuja resposta correta NÃO é alarme
# --------------------------------------------------------------------------
def test_caro_porem_saudavel_sobe_cpl_e_sobe_margem():
    """R4 exige as duas coisas juntas. Sem a margem subindo, vira cpl_alto."""
    p = CENARIOS[NomeCenario.CARO_POREM_SAUDAVEL].perturbacao
    assert p.cpl_mult is not None and p.cpl_mult.minimo > 1.0
    assert p.margem_delta_pp is not None and p.margem_delta_pp.minimo > 0


def test_barato_porem_destrutivo_baixa_cpl_e_baixa_margem():
    """Espelho do anterior: CPL cai e margem cai. Margem positiva aqui tornaria
    a R5 indistinguível da R4."""
    p = CENARIOS[NomeCenario.BARATO_POREM_DESTRUTIVO].perturbacao
    assert p.cpl_mult is not None and p.cpl_mult.maximo < 1.0
    assert p.margem_delta_pp is not None and p.margem_delta_pp.maximo < 0


def test_mudanca_de_mix_nao_piora_campanha_nenhuma():
    """R10: o agregado sobe por migração de verba. Se uma campanha piorasse,
    deixaria de ser Simpson e viraria R1 legítima (ADR 0003)."""
    p = CENARIOS[NomeCenario.MUDANCA_DE_MIX].perturbacao
    assert p.migracao_verba_delta_pp is not None
    assert p.cpl_mult is None, "mix não altera o CPL de campanha nenhuma"


# --------------------------------------------------------------------------
# Condições transversais
# --------------------------------------------------------------------------
def test_condicoes_transversais_declaradas():
    assert set(CONDICOES_TRANSVERSAIS) == set(NomeCondicao)


def test_condicoes_apontam_para_as_regras_que_calam():
    """R0 bloqueia por completude; R99 silencia por amostra. Trocar as duas
    faria a avaliação cobrar a regra errada."""
    condicoes = CONDICOES_TRANSVERSAIS
    assert condicoes[NomeCondicao.DADOS_INCOMPLETOS].regras_esperadas == ("R0",)
    assert condicoes[NomeCondicao.AMOSTRA_PEQUENA].regras_esperadas == ("R99",)


# --------------------------------------------------------------------------
# Armadilhas
# --------------------------------------------------------------------------
def test_sete_armadilhas():
    """Critério de saída da fase 3: alarme falso < 5% com sete armadilhas."""
    assert len(ARMADILHAS) == 7


def test_armadilha_nao_espera_regra_nenhuma():
    """Armadilha PARECE problema. A resposta certa é silêncio."""
    for nome, armadilha in ARMADILHAS.items():
        assert armadilha.regras_esperadas == (), f"{nome} espera alarme"


def test_armadilha_perturba_ou_declara_mecanismo():
    """Sem um dos dois, a armadilha gera dado igual ao normal e não arma nada."""
    for nome, armadilha in ARMADILHAS.items():
        tem_perturbacao = armadilha.perturbacao != Perturbacao()
        assert tem_perturbacao or armadilha.mecanismo.strip(), f"{nome} não arma nada"
