from app.services import BillCalculator
from app.models import Participant, MonthlyBill, MeterReading, BillComponent, ComponentAdjustment


def P(id, name):
    return Participant(id=id, name=name)


def R(pid, cur, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=cur, reading_previous=prev)


def test_percent_includes_self_and_zeroed_targets_leftover_equal():
    # Three participants, water ninety split evenly -> 30 each base
    # Zero Bob's water; rule targets Bob himself (100%) and Charlie (0%)
    # With self-redistribution allowed, Bob gets his 30 back to himself
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Charlie")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    # Create Water component with zero rule targeting self and zero percent for others
    water = BillComponent(month_id=1, name="Water",
                          amount=90.0, split_method='equal', position=0)
    water.id = 201
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=B.id, zero=True,
                              redis_rule={'mode': 'percent', 'targets': {str(B.id): 100, C.id: 0}})
    c = BillCalculator().compute_contributions_dynamic(
        bill, [water], [], parts, [adj])
    by = {x.participant.id: x for x in c}
    # Bob's 30 redistributes: 100% back to self = 30
    # Alice and Charlie remain at their base 30 each
    assert by[A.id].components["Water"] == 30.0
    assert by[B.id].components["Water"] == 30.0
    assert by[C.id].components["Water"] == 30.0
    assert round(sum(x.components["Water"] for x in c), 2) == bill.water_amount


def test_amount_underflow_leftover_equal():
    # Two participants, internet 100 -> 50 each base
    # Zero Alice; amount rule asks only 10 to Bob -> leftover 40 splits equally among remaining (only Bob) so Bob gets all 50
    A, B = P(1, "Alice"), P(2, "Bob")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=0.0, internet_amount=100.0)
    parts = [A, B]
    internet = BillComponent(month_id=1, name="Internet",
                             amount=100.0, split_method='equal', position=0)
    internet.id = 202
    adj = ComponentAdjustment(month_id=1, component_id=internet.id, participant_id=A.id, zero=True,
                              redis_rule={'mode': 'amount', 'targets': {B.id: 10}})
    c = BillCalculator().compute_contributions_dynamic(
        bill, [internet], [], parts, [adj])
    by = {x.participant.id: x for x in c}
    assert by[A.id].components["Internet"] == 0.0
    assert by[B.id].components["Internet"] == 100.0
    assert round(sum(x.components["Internet"]
                 for x in c), 2) == bill.internet_amount


def test_multiple_zeroed_participants_same_component():
    # Three participants, water 90 -> 30 each base
    # Zero Alice -> 100% to Bob; Zero Charlie -> 100% to Bob
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Charlie")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    water = BillComponent(month_id=1, name="Water",
                          amount=90.0, split_method='equal', position=0)
    water.id = 203
    adjA = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=A.id, zero=True,
                               redis_rule={'mode': 'percent', 'targets': {B.id: 100}})
    adjC = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=C.id, zero=True,
                               redis_rule={'mode': 'percent', 'targets': {B.id: 100}})
    c = BillCalculator().compute_contributions_dynamic(
        bill, [water], [], parts, [adjA, adjC])
    by = {x.participant.id: x for x in c}
    assert by[A.id].components["Water"] == 0.0
    assert by[C.id].components["Water"] == 0.0
    assert by[B.id].components["Water"] == 90.0
    assert round(sum(x.components["Water"] for x in c), 2) == bill.water_amount


def test_empty_targets_treated_as_equal_split():
    # Four participants, water 80 -> 20 each base
    # Zero Dave with empty targets dict -> entire 20 leftover split equally among remaining 3
    A, B, C, D = P(1, "Alice"), P(2, "Bob"), P(3, "Cara"), P(4, "Dave")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=80.0, internet_amount=0.0)
    parts = [A, B, C, D]
    water = BillComponent(month_id=1, name="Water",
                          amount=80.0, split_method='equal', position=0)
    water.id = 204
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=D.id, zero=True,
                              redis_rule={'mode': 'percent', 'targets': {}})
    c = BillCalculator().compute_contributions_dynamic(
        bill, [water], [], parts, [adj])
    by = {x.participant.id: x for x in c}
    # Dave zeroed -> others get +6.666.. each -> after rounding, two will be 26.67 and one 26.66 to preserve total
    vals = sorted([by[A.id].components["Water"],
                  by[B.id].components["Water"], by[C.id].components["Water"]])
    assert vals == [26.66, 26.67, 26.67]
    assert by[D.id].components["Water"] == 0.0
    assert round(sum(x.components["Water"] for x in c), 2) == bill.water_amount


def test_zero_usage_electricity_with_zero_flag_no_effect():
    # Electricity amount present but all usage zero -> all base shares 0.
    # Zeroing anyone should have zeroed_total 0 and no changes.
    A, B = P(1, "Alice"), P(2, "Bob")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=50.0,
                       water_amount=0.0, internet_amount=0.0)
    readings = [R(A.id, 100, 100), R(B.id, 200, 200)]  # zero usage
    parts = [A, B]
    electricity = BillComponent(
        month_id=1, name="Electricity", amount=50.0, split_method='usage', position=0)
    electricity.id = 205
    adj = ComponentAdjustment(
        month_id=1, component_id=electricity.id, participant_id=A.id, zero=True)
    c = BillCalculator().compute_contributions_dynamic(
        bill, [electricity], readings, parts, [adj])
    assert all(x.components["Electricity"] == 0.0 for x in c)
    assert round(sum(x.components["Electricity"] for x in c), 2) == 0.0


def test_nonnumeric_percent_ignored_leftover_equal():
    # Non-numeric percent entries should be ignored; leftover goes equal
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Cara")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    water = BillComponent(month_id=1, name="Water",
                          amount=90.0, split_method='equal', position=0)
    water.id = 206
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=A.id, zero=True,
                              redis_rule={'mode': 'percent', 'targets': {B.id: 'xx', C.id: 10}})
    c = BillCalculator().compute_contributions_dynamic(
        bill, [water], [], parts, [adj])
    by = {x.participant.id: x for x in c}
    # Base 30 each; A zeroed -> to_distribute=30. Only Cara has numeric 10 but total_pct fails (TypeError handled -> 0), so no allocation -> leftover equal to B & C => 15 each
    assert by[B.id].components["Water"] == 45.0
    assert by[C.id].components["Water"] == 45.0
    assert by[A.id].components["Water"] == 0.0
    assert round(sum(x.components["Water"] for x in c), 2) == bill.water_amount


def test_zeroed_participant_receives_from_another_zeroed():
    """
    Scenario: Multiple zeroed participants can redistribute to each other.
    - A redistributes to B/C/D (0% to self)
    - B redistributes to A/B/C/D (amounts including A)
    A should receive from B's redistribution even though A is also zeroed.
    """
    A, B, C, D = P(1, "A"), P(2, "B"), P(3, "C"), P(4, "D")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=0.0, internet_amount=0.0)
    parts = [A, B, C, D]
    # Water: 650 split by usage 300/100/200/50 => A=300/650*650=300, etc
    # Let's simplify: total=650, A gets ~300.00, B gets ~100.00, C~200.00, D~50.00
    water = BillComponent(month_id=1, name="Water",
                          amount=650.0, split_method='equal', position=0)
    water.id = 207
    # Equal split: 650/4 = 162.50 each base

    # A zeroed: 0% to self, ~34%/33%/33% to B/C/D
    adjA = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=A.id, zero=True,
                               redis_rule={'mode': 'percent', 'targets': {str(A.id): 0, str(B.id): 34, str(C.id): 33, str(D.id): 33}})
    # B zeroed: amounts totaling more than base -> normalized. 400 to A, 100 to B, 100 to C, 50 to D
    adjB = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=B.id, zero=True,
                               redis_rule={'mode': 'amount', 'targets': {str(A.id): 400, str(B.id): 100, str(C.id): 100, str(D.id): 50}})

    c = BillCalculator().compute_contributions_dynamic(
        bill, [water], [], parts, [adjA, adjB])
    by = {x.participant.id: x for x in c}

    # Base: 162.50 each
    # A zeroed -> 162.50 to distribute: 0% to A, 34% to B (~55.25), 33% to C (~53.625), 33% to D (~53.625)
    # B zeroed -> 162.50 to distribute: amounts 400+100+100+50=650, normalized to 162.50
    #   A gets 400/650 * 162.50 = 100, B gets 100/650 * 162.50 = 25, C gets 100/650 * 162.50 = 25, D gets 50/650 * 162.50 = 12.5

    # Final:
    # A: 0 + (from B's redistribution) = 100
    # B: 162.50 + (from A) 55.25 + (from B to self) 25 = ~242.75
    # C: 162.50 + (from A) 53.625 + (from B) 25 = ~241.125
    # D: 162.50 + (from A) 53.625 + (from B) 12.5 = ~228.625

    # Key assertion: A should NOT be zero! A should receive from B's redistribution
    assert by[A.id].components["Water"] > 0, "A should receive from B's redistribution"
    assert round(sum(x.components["Water"] for x in c), 2) == 650.0
