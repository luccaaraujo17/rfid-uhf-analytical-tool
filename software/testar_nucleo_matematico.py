# -*- coding: utf-8 -*-
"""Autoteste mínimo do núcleo físico-matemático."""
import math
from rfid_physics_core import (
    AntennaProfile, LinkBudgetInput, compute_link_budget,
    wavelength_m, fraunhofer_distance_m, fspl_db,
    mismatch_loss_from_vswr_db, angular_gain_dbi,
)

def close(a, b, tol):
    assert abs(a-b) <= tol, f"Esperado {b}, obtido {a}"

ant = AntennaProfile()
assert ant.model == "PAL90209H"
assert ant.polarization == "LHCP"
close(ant.hpbw_azimuth_deg, 70.0, 1e-12)
close(ant.largest_dimension_m, 0.2591, 1e-12)
close(wavelength_m(915e6), 0.3276420306, 1e-9)
close(fraunhofer_distance_m(915e6, 0.2591), 0.4097936390, 1e-9)
close(mismatch_loss_from_vswr_db(1.3), 0.0745232840, 1e-9)
close(angular_gain_dbi(9.0, 35.0, 70.0, 20.0), 6.0, 1e-12)
close(fspl_db(1.0, 915e6), 31.674, 0.01)

r05 = compute_link_budget(LinkBudgetInput(distance_m=0.5, conducted_power_dbm=20.0))
r10 = compute_link_budget(LinkBudgetInput(distance_m=1.0, conducted_power_dbm=20.0))
r20 = compute_link_budget(LinkBudgetInput(distance_m=2.0, conducted_power_dbm=20.0))
assert r05.p_tag_dbm > r10.p_tag_dbm > r20.p_tag_dbm
assert r05.p_rx_dbm > r10.p_rx_dbm > r20.p_rx_dbm
assert r10.in_far_field
print("AUTOTESTE CONCLUÍDO COM SUCESSO")
print("R_FF =", r10.fraunhofer_m, "m")
print("P_tag 1 m =", r10.p_tag_dbm, "dBm")
print("P_rx 1 m =", r10.p_rx_dbm, "dBm")
