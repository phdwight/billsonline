from pathlib import Path
import sys

# Ensure project root is on sys.path for 'app' imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant


def make_p(id, name, include=True):
    p = Participant(id=id, name=name, include_in_internet=include)
    return p


def make_r(pid, current, prev):
    r = MeterReading(participant_id=pid, month_id=1, reading_current=current, reading_previous=prev)
    return r


def test_calculation_basic_distribution():
    bill = MonthlyBill(year=2025, month=10, electricity_amount=300.0, water_amount=100.0, internet_amount=80.0)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara", include=False)]
    readings = [make_r(1, 200, 100), make_r(2, 150, 100), make_r(3, 100, 100)]
    c = BillCalculator().compute_contributions(bill, readings, participants)
    # Electricity usage: Alice 100, Bob 50, Cara 0 -> total 150
    # Shares: Alice 200, Bob 100, Cara 0
    by_name = {x.participant.name: x for x in c}
    assert by_name["Alice"].electricity == 200.0
    assert by_name["Bob"].electricity == 100.0
    assert by_name["Cara"].electricity == 0.0
    # Water equal among 3 -> 33.33 each (rounded 2)
    assert by_name["Alice"].water == 33.33
    assert by_name["Bob"].water == 33.33
    assert by_name["Cara"].water == 33.33
    # Internet among included (Alice, Bob) -> 40 each
    assert by_name["Alice"].internet == 40.0
    assert by_name["Bob"].internet == 40.0
    assert by_name["Cara"].internet == 0.0


def test_zero_total_usage_electricity():
    bill = MonthlyBill(year=2025, month=10, electricity_amount=300.0, water_amount=90.0, internet_amount=60.0)
    participants = [make_p(1, "A"), make_p(2, "B")]
    readings = [make_r(1, 100, 100), make_r(2, 200, 200)]  # all zero usage
    c = BillCalculator().compute_contributions(bill, readings, participants)
    for x in c:
        assert x.electricity == 0.0
        assert x.water == 45.0
        assert x.internet == 30.0
