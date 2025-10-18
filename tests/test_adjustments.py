from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant


def P(id, name, include=True):
    # include flag no longer used; keep signature for compatibility
    return Participant(id=id, name=name)


def R(pid, current, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=current, reading_previous=prev)


def test_zero_electricity_redistributes_to_rest():
    bill = MonthlyBill(year=2025, month=10, electricity_amount=300.0, water_amount=90.0, internet_amount=60.0)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = [R(1, 200, 100), R(2, 150, 100), R(3, 100, 100)]  # usage: 100,50,0 -> shares: 200,100,0
    parts = [A, B, C]
    adjustments = {1: {"electricity": True, "water": False, "internet": False}}
    c = BillCalculator().compute_contributions(bill, readings, parts, adjustments)
    by = {x.participant.id: x for x in c}
    # A's electricity zeroed -> 200 redistributes to B (100 of remaining 100) fully
    assert by[1].electricity == 0.0
    assert by[2].electricity == 300.0
    assert by[3].electricity == 0.0


def test_zero_water_even_split_then_redistribute():
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=90.0, internet_amount=0.0)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = []
    parts = [A, B, C]
    adjustments = {2: {"electricity": False, "water": True, "internet": False}}
    c = BillCalculator().compute_contributions(bill, readings, parts, adjustments)
    by = {x.participant.id: x for x in c}
    # Base water 30 each -> B zeroed; remaining total 90 is split across A and C equally => 45 each
    assert by[1].water == 45.0
    assert by[2].water == 0.0
    assert by[3].water == 45.0
    assert round(by[1].water + by[2].water + by[3].water, 2) == 90.0


def test_zero_internet_equal_among_all():
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=0.0, internet_amount=90.0)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = []
    parts = [A, B, C]
    adjustments = {1: {"electricity": False, "water": False, "internet": True}}
    c = BillCalculator().compute_contributions(bill, readings, parts, adjustments)
    by = {x.participant.id: x for x in c}
    # Base internet: 30 each. A zeroed -> 30 redistributes equally to B and C => 45 each.
    assert by[1].internet == 0.0
    assert by[2].internet == 45.0
    assert by[3].internet == 45.0
