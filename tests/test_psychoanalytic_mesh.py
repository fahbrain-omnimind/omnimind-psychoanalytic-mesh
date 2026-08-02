"""
Testes para a malha psicanalítica pública.
"""
import pytest
import torch

from omnimind_psychoanalytic.psychoanalytic_mesh import (
    SovereignPsychoanalyticMesh,
    FreudNet,
    ConfabulationAlarmNet,
    SocialValidationNet,
)


def _default_inputs(batch_size=2, device="cpu"):
    return dict(
        excitation_F=torch.randn(batch_size, 64, device=device),
        trauma_Fe=0.2,
        aggression_K=0.3,
        holding_W=0.5,
        handling_W=0.5,
        spontaneity_W=torch.randn(batch_size, 32, device=device),
        castration_D=0.4,
        triangulation_D=0.4,
        lack_L=0.2,
    )


def test_mesh_instantiation_and_forward():
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    out = mesh(**_default_inputs(batch_size=2))
    z, contract = out
    assert z.shape == (2, 464), f"esperado (2, 464), obtido {z.shape}"
    assert not torch.isnan(z).any()
    assert not torch.isinf(z).any()
    assert "regime" in contract


def test_freud_net_contract():
    net = FreudNet(latent_dim=64, device="cpu")
    x = torch.randn(1, 64)
    z, contract = net(x)
    assert z.shape == (1, 64)
    assert "states" in contract and "loss" in contract


def test_confabulation_alarm_safe_fallback():
    net = ConfabulationAlarmNet(latent_dim=16, device="cpu")
    z, contract = net(missing_context_signals=0.7, low_confidence_flags=0.9)
    assert z.shape == (1, 16)
    assert contract["regime"] in ("colapso", "estavel")


def test_social_validation_contract_input():
    net = SocialValidationNet(latent_dim=16, device="cpu")
    z, contract = net(operator_presence_score=0.6, contract_fulfillment=0.8)
    assert z.shape == (1, 16)
    assert "social_validation" in contract["observables"]


def test_dimension_sum_464():
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    dims = [
        mesh.dim_F, mesh.dim_Fe, mesh.dim_K, mesh.dim_W, mesh.dim_D,
        mesh.dim_L, mesh.dim_G, mesh.dim_N, mesh.dim_R, mesh.dim_E,
        mesh.dim_C, mesh.dim_OF, mesh.dim_RR, mesh.dim_CA, mesh.dim_SV,
    ]
    assert sum(dims) == 464, f"soma={sum(dims)}"


def test_inrc_operators():
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    for op in ("I", "N", "R", "C"):
        out = mesh(**_default_inputs(batch_size=1), inrc_operator=op)
        assert out[0].shape == (1, 464)


def test_contract_schema():
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    z, contract = mesh(**_default_inputs(batch_size=1))
    assert isinstance(contract, dict)
    assert "regime" in contract
    assert "states" in contract
    assert "observables" in contract
    assert "loss" in contract
    assert "confidence" in contract
    assert "invariants" in contract
    assert "warnings" in contract
    assert "trace_id" in contract


def test_ablation_a0_baseline():
    """A0: malha completa, baseline."""
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    z, _ = mesh(**_default_inputs(batch_size=1))
    assert z.shape == (1, 464)


def test_module_ablation_changes_output():
    """Ablação: comparar saída baseline com saída quando um módulo é substituído por zeros."""
    mesh = SovereignPsychoanalyticMesh(device="cpu")
    z_baseline, _ = mesh(**_default_inputs(batch_size=1))

    # Recriar malha, mas com z do módulo epistêmico zerado manualmente dentro do forward
    mesh2 = SovereignPsychoanalyticMesh(device="cpu")
    # monkey-patch forward para zerar epistemic.z antes de chamar epistemic
    original_epistemic_forward = mesh2.epistemic.forward
    def epistemic_forward_zero(*args, **kwargs):
        mesh2.epistemic.z = torch.zeros_like(mesh2.epistemic.z)
        return original_epistemic_forward(*args, **kwargs)
    mesh2.epistemic.forward = epistemic_forward_zero

    z_ablated, _ = mesh2(**_default_inputs(batch_size=1))
    assert z_baseline.shape == (1, 464)
    assert z_ablated.shape == (1, 464)
    # A saída deve ser diferente (não idêntica) após ablação
    assert not torch.allclose(z_baseline, z_ablated, atol=1e-6)
