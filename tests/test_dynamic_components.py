from pathlib import Path
import sys

# Ensure project root is on sys.path for 'app' imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant, BillComponent, ComponentAdjustment


def make_p(id, name):
    return Participant(id=id, name=name)


def make_r(pid, current, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=current, reading_previous=prev)


def test_dynamic_basic_usage_and_equal():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara")]
    readings = [make_r(1, 200, 100), make_r(2, 150, 100), make_r(3, 100, 100)]
    # Components: Electricity by usage (300), Water equal (90)
    c1 = BillComponent(month_id=1, name="Electricity", amount=300.0, split_method='usage', position=1)
    c2 = BillComponent(month_id=1, name="Water", amount=90.0, split_method='equal', position=2)
    # assign ids for deterministic sort in dynamic code
    c1.id = 1
    c2.id = 2
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [c1, c2], readings, participants, [])
    by_name = {x.participant.name: x for x in res}
    # Electricity usage: Alice 100, Bob 50, Cara 0 -> total 150
    # Shares: Alice 200, Bob 100, Cara 0
    assert by_name["Alice"].components["Electricity"] == 200.0
    assert by_name["Bob"].components["Electricity"] == 100.0
    assert by_name["Cara"].components["Electricity"] == 0.0
    # Water equal among 3 -> 30 each
    assert by_name["Alice"].components["Water"] == 30.0
    assert by_name["Bob"].components["Water"] == 30.0
    assert by_name["Cara"].components["Water"] == 30.0


def test_dynamic_zero_and_redistribution_percent():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara")]
    readings = []  # not used for equal split
    water = BillComponent(month_id=1, name="Water", amount=90.0, split_method='equal', position=1)
    water.id = 10
    # Zero Cara's water and redistribute 100% to Alice
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=3, zero=True,
                              redis_rule={"mode": "percent", "targets": {1: 100}})
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [water], readings, participants, [adj])
    by_name = {x.participant.name: x for x in res}
    # Base is 30 each; Cara zeroed, her 30 goes 100% to Alice -> Alice 60, Bob 30, Cara 0
    assert by_name["Alice"].components["Water"] == 60.0
    assert by_name["Bob"].components["Water"] == 30.0
    assert by_name["Cara"].components["Water"] == 0.0


def test_dynamic_percentage_distribution_component():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara")]
    readings = []
    comp = BillComponent(month_id=1, name="Gas", amount=200.0, split_method='percentage', position=1)
    # distribution in percentages
    comp.distribution = {1: 50, 2: 30, 3: 20}
    comp.id = 20
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], readings, participants, [])
    by = {x.participant.id: x for x in res}
    assert by[1].components["Gas"] == 100.0
    assert by[2].components["Gas"] == 60.0
    assert by[3].components["Gas"] == 40.0


def test_dynamic_amount_distribution_component():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara")]
    readings = []
    comp = BillComponent(month_id=1, name="Trash", amount=90.0, split_method='amount', position=1)
    # absolute amounts
    comp.distribution = {1: 20, 2: 30, 3: 40}
    comp.id = 21
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], readings, participants, [])
    by = {x.participant.id: x for x in res}
    assert by[1].components["Trash"] == 20.0
    assert by[2].components["Trash"] == 30.0
    assert by[3].components["Trash"] == 40.0


def test_dynamic_percentage_with_zero_and_redistribute_amount_mode():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara")]
    readings = []
    comp = BillComponent(month_id=1, name="Fuel", amount=100.0, split_method='percentage', position=1)
    comp.distribution = {1: 70, 2: 20, 3: 10}
    comp.id = 22
    # Zero Cara and redistribute her base (10) amounts equally to Alice and Bob via explicit amount rule
    # Here we set targets 5 and 5; since sum equals base, full allocation goes as-is
    adj = ComponentAdjustment(month_id=1, component_id=comp.id, participant_id=3, zero=True,
                              redis_rule={"mode": "amount", "targets": {1: 5, 2: 5}})
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], readings, participants, [adj])
    by = {x.participant.id: x for x in res}
    # Base: A 70, B 20, C 10 -> after zero C: distribute 10 as 5/5
    assert by[1].components["Fuel"] == 75.0
    assert by[2].components["Fuel"] == 25.0
    assert by[3].components["Fuel"] == 0.0
