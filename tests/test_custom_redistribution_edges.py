from app.services import BillCalculator
from app.models import Participant, MonthlyBill, MeterReading


def P(id, name):
    return Participant(id=id, name=name)


def R(pid, cur, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=cur, reading_previous=prev)


def test_percent_includes_self_and_zeroed_targets_leftover_equal():
    # Three participants, water  ninety split evenly -> 30 each base
    # Zero Bob's water; rule targets Bob himself and Charlie (self should be ignored), leftover goes equally to Alice/Charlie
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Charlie")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    adjustments = {
        B.id: {
            'water': True,
            'redis_water': {
                'mode': 'percent',
                'targets': {str(B.id): 100, C.id: 0}  # self ignored; 0 for Charlie means no directed allocation
            }
        }
    }
    c = BillCalculator().compute_contributions(bill, [], parts, adjustments)
    by = {x.participant.id: x for x in c}
    # Bob's 30 redistributes equally to remaining eligible (Alice & Charlie) => +15 each
    assert by[A.id].water == 45.0
    assert by[B.id].water == 0.0
    assert by[C.id].water == 45.0
    assert round(sum(x.water for x in c), 2) == bill.water_amount


def test_amount_underflow_leftover_equal():
    # Two participants, internet 100 -> 50 each base
    # Zero Alice; amount rule asks only 10 to Bob -> leftover 40 splits equally among remaining (only Bob) so Bob gets all 50
    A, B = P(1, "Alice"), P(2, "Bob")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=0.0, internet_amount=100.0)
    parts = [A, B]
    adjustments = {
        A.id: {
            'internet': True,
            'redis_internet': {
                'mode': 'amount',
                'targets': {B.id: 10}
            }
        }
    }
    c = BillCalculator().compute_contributions(bill, [], parts, adjustments)
    by = {x.participant.id: x for x in c}
    assert by[A.id].internet == 0.0
    assert by[B.id].internet == 100.0
    assert round(sum(x.internet for x in c), 2) == bill.internet_amount


def test_multiple_zeroed_participants_same_component():
    # Three participants, water 90 -> 30 each base
    # Zero Alice -> 100% to Bob; Zero Charlie -> 100% to Bob
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Charlie")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    adjustments = {
        A.id: {'water': True, 'redis_water': {'mode': 'percent', 'targets': {B.id: 100}}},
        C.id: {'water': True, 'redis_water': {'mode': 'percent', 'targets': {B.id: 100}}},
    }
    c = BillCalculator().compute_contributions(bill, [], parts, adjustments)
    by = {x.participant.id: x for x in c}
    assert by[A.id].water == 0.0
    assert by[C.id].water == 0.0
    assert by[B.id].water == 90.0
    assert round(sum(x.water for x in c), 2) == bill.water_amount


def test_empty_targets_treated_as_equal_split():
    # Four participants, water 80 -> 20 each base
    # Zero Dave with empty targets dict -> entire 20 leftover split equally among remaining 3
    A, B, C, D = P(1, "Alice"), P(2, "Bob"), P(3, "Cara"), P(4, "Dave")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=80.0, internet_amount=0.0)
    parts = [A, B, C, D]
    adjustments = {
        D.id: {'water': True, 'redis_water': {'mode': 'percent', 'targets': {}}}
    }
    c = BillCalculator().compute_contributions(bill, [], parts, adjustments)
    by = {x.participant.id: x for x in c}
    # Dave zeroed -> others get +6.666.. each -> after rounding, two will be 26.67 and one 26.66 to preserve total
    vals = sorted([by[A.id].water, by[B.id].water, by[C.id].water])
    assert vals == [26.66, 26.67, 26.67]
    assert by[D.id].water == 0.0
    assert round(sum(x.water for x in c), 2) == bill.water_amount


def test_zero_usage_electricity_with_zero_flag_no_effect():
    # Electricity amount present but all usage zero -> all base shares 0.
    # Zeroing anyone should have zeroed_total 0 and no changes.
    A, B = P(1, "Alice"), P(2, "Bob")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=50.0, water_amount=0.0, internet_amount=0.0)
    readings = [R(A.id, 100, 100), R(B.id, 200, 200)]  # zero usage
    parts = [A, B]
    adjustments = {A.id: {'electricity': True}}
    c = BillCalculator().compute_contributions(bill, readings, parts, adjustments)
    assert all(x.electricity == 0.0 for x in c)
    assert round(sum(x.electricity for x in c), 2) == 0.0


def test_nonnumeric_percent_ignored_leftover_equal():
    # Non-numeric percent entries should be ignored; leftover goes equal
    A, B, C = P(1, "Alice"), P(2, "Bob"), P(3, "Cara")
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=90.0, internet_amount=0.0)
    parts = [A, B, C]
    adjustments = {
        A.id: { 'water': True, 'redis_water': { 'mode': 'percent', 'targets': { B.id: 'xx', C.id: 10 } } }
    }
    c = BillCalculator().compute_contributions(bill, [], parts, adjustments)
    by = {x.participant.id: x for x in c}
    # Base 30 each; A zeroed -> to_distribute=30. Only Cara has numeric 10 but total_pct fails (TypeError handled -> 0), so no allocation -> leftover equal to B & C => 15 each
    assert by[B.id].water == 45.0
    assert by[C.id].water == 45.0
    assert by[A.id].water == 0.0
    assert round(sum(x.water for x in c), 2) == bill.water_amount
