import os
import warnings

import pytest

os.environ["LNG_STRICT"] = "1"      # unexpected exceptions inside cycle bodies must fail tests, not be logged as FLASH_FAIL
warnings.filterwarnings("ignore")

from lng_robust.config import load_basis
from lng_robust.cycles.pretreat import pretreat

A1_RAW = {"C1": 92.51, "C2": 2.78, "C3": 1.66, "iC4": 0.39, "nC4": 0.39, "iC5": 0.15, "nC5": 0.15, "N2": 0.22, "CO2": 0.11}


@pytest.fixture(scope="session")
def basis():
    return load_basis()


@pytest.fixture(scope="session")
def fast_basis():
    return load_basis().override(mshe_N=40, mshe_n_table=24)


@pytest.fixture(scope="session")
def feed():
    return pretreat(A1_RAW).treated


# A hand-set N2 dual design used only to exercise the code (it is not an optimum and not a result).
X_DUAL = dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_warm_C=-30, T_exp_in_cold_C=-100, split=0.5, T_lng_C=-150)
X_SINGLE = dict(P_high_bar=60, P_low_bar=10, flow_ratio=8, T_exp_in_C=-95, T_lng_C=-150)
X_SMR = dict(ref={"N2": 0.08, "C1": 0.28, "C2": 0.35, "C3": 0.12, "nC4": 0.15, "iC5": 0.02}, P_high_bar=25, P_low_bar=3.5,
             flow_ratio=2.5, T_lng_C=-150)
