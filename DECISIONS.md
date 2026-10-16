# Modeling Decisions

> Practice model – not the real game. All numbers are estimates.

## 1. Demand model

**Decision**: Lognormal noise with CV=0.47 (calibrated from R2 forecast error range 44–65%).
**Reason**: The lognormal distribution is always positive (no negative demand), skews right like real consumer demand, and CV=0.47 sits in the middle of the observed range.
**Assumption**: `demand_noise_cv` in assumptions.yaml. Status: calibrated.

## 2. Contract index — additive deltas

**Decision**: Contract index = R2_base + sum of deltas for each lever (payment term, trade unit, promo pressure, horizon, deadline, VMI, shelf life).
**Reason**: The game manual describes each lever as independently affecting the index. An additive model is the simplest approximation that preserves direction of effects.
**Limitation**: Real game uses a multiplicative or tabular model; interactions are not captured.
**Assumptions**: All `idx_*` magnitudes in assumptions.yaml. Most are UNVERIFIED.

## 3. Material cost — volume index scaling

**Decision**: `material_cost = R2_purchase_value × volume_index × supplier_index × preform_fraction`
where `volume_index = current_liters / R2_liters`.
**Reason**: No explicit bill-of-materials recipe available. Scaling from R2 actuals × relative volume captures proportional changes without fabricating ingredient quantities.
**Limitation**: Does not capture non-linear yield effects or minimum order quantities.

## 4. Working capital / Investment calibration

**Decision**: Compute WC from AR−AP+inventory formula, then scale by `wc_scale = r2_implied_wc / wc_investment` (clamped 0.5–2.0) so that R2 baseline investment = €3,517,221.
**Reason**: Equipment investment ≈ €802K; actual game investment = €3,517,221; the gap (≈€2,715K) is working capital. The AR/AP formula gives a different number than the real game, likely because inventory calculation differs from the game's method. Scaling anchors the model to the R2 calibration point.
**Limitation**: WC sensitivity to term changes is proportionally scaled, not absolutely correct.

## 5. Inflate PET — depreciation

**Decision**: Two sub-scenarios for the assumption `inflate_depreciation_per_round`: 0 (no depreciation charge visible in P&L in-round) and 70K (approximate straight-line over 10 rounds).
**Reason**: The €700K investment is capitalized; the annual charge depends on accounting method and game round length. Real value is UNVERIFIED.

## 6. Inflate PET — transport saving

**Decision**: Separate assumption `inflate_pet_transport_saving_pct` (default 0, range 0–0.90) applied to PET transport line.
**Reason**: Preforms arrive from a different supplier; transport cost may drop significantly. Without confirmation from the real game, this is UNVERIFIED.

## 7. Obsoletes / Scrap model

**Decision**: `scrap = 52800 × (avg_ss_weeks / r2_avg_ss) × volume_index`. Risk = scrap (same amount in R2 actuals).
**Reason**: R2 scrap = R2 risk = €52,800. Scrap scales with safety stock level (more SS = more aged inventory exposed to expiry) and with total volume. No explicit shelf-life curve available.

## 8. PIT calibration

**Decision**: PIT formula: `(production_h + changeover_h_after_SMED) / available_h`.
With R2 settings (SMED 30% reduction, 10-day interval, 6 SKUs, 80h/week available) → PIT ≈ 77%.
**Calibration**: Target 77%; model produces ~77% with seed averaging.
**Source**: Roles PDF states "SMED reduces changeover times by 30%" — confirmed, not estimated.
**Assumption**: `smed_changeover_reduction = 0.30` (calibrated from Roles document).

## 9. Service bonus/penalty

**Decision**: Simple proportional penalty/bonus: if actual service < promise, apply penalty per unit shortfall scaled from R2 (€12,095 bonus). Bonus when service > promise by small margin.
**Calibration**: Scaled to reproduce R2 total €12,095.

## 10. Customer VMI

**Decision**: VMI forces trade_unit = pallet and deadline = 14:00. Contract index shift = `idx_customer_vmi_delta_fg` (calibrated assumption).
**Reason**: VMI service level commitment changes the contract; the index shift is calibrated to be small but positive (VMI improves service reliability → slight index increase for customer).

## 11. RM warehouse overflow

**Decision**: Peak RM pallets = Σ (SS + lot/2) × weekly_consumption / pallet_units.
Inflate PET multiplies PET pallets by `inflate_pet_storage_fraction` (default 0.10 = 10% of original).
**Calibration**: R2 actual RM usage ≈ 635 pallets → model targets < 700 (700 locations available).

## 12. Monte Carlo sampling

**Decision**: UNVERIFIED assumptions sampled uniformly from [min, max]. Each run uses a unique seed (base_seed + run_index). Results summarized as mean, P10, P90.
**Reason**: Uniform distribution is the least-informative prior when only range is known. 500 runs gives stable percentiles.

## 14. PET pallet size calibration

**Decision**: `pieces_per_pallet` for PET bottles = 5293 (back-calculated from R2 distribution cost).
**Calibration**: R2 distribution cost €198,000 ÷ €31/pallet = 6,387 pallets dispatched. Carton products account for (70,100+11,900+44,000)×26÷600 = 5,460 pallets. PET remainder = 927 pallets for 4,906,200 pieces → 5,293 pieces/pallet.
**Limitation**: The game's actual TI (transport instruction) pallet configuration is not confirmed; 5293 is inferred from the R2 cost figure.

## 13. Scenarios not implemented

**Decision**: `outsource_fg: mcc` (scenario 13) and bottling line variants (scenarios 14–15) are not fully modeled — the engine applies a placeholder cost delta from assumptions.yaml (`mcc_outsourcing_cost_per_round`, `topspeed_extra_investment`, etc.).
**Reason**: The real game costs for outsourcing and line upgrades are UNVERIFIED.
