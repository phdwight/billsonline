from pathlib import Path
import sys

# Ensure project root is on sys.path for 'app' imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant, BillComponent


def make_p(id, name, include=True):
    # include flag kept for signature compatibility; not used.
    return Participant(id=id, name=name)


def make_r(pid, current, prev):
    r = MeterReading(participant_id=pid, month_id=1, reading_current=current, reading_previous=prev)
    return r


def test_calculation_basic_distribution():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "Alice"), make_p(2, "Bob"), make_p(3, "Cara", include=False)]
    readings = [make_r(1, 200, 100), make_r(2, 150, 100), make_r(3, 100, 100)]
    # dynamic components equivalent to legacy amounts
    c1 = BillComponent(month_id=1, name="Electricity", amount=300.0, split_method='usage', position=0)
    c2 = BillComponent(month_id=1, name="Water", amount=100.0, split_method='equal', position=1)
    c3 = BillComponent(month_id=1, name="Internet", amount=80.0, split_method='equal', position=2)
    c1.id, c2.id, c3.id = 1, 2, 3
    res = BillCalculator().compute_contributions_dynamic(bill, [c1, c2, c3], readings, participants, [])
    by_name = {x.participant.name: x for x in res}
    # Electricity usage: Alice 100, Bob 50, Cara 0 -> total 150
    # Shares: Alice 200, Bob 100, Cara 0
    assert by_name["Alice"].components["Electricity"] == 200.0
    assert by_name["Bob"].components["Electricity"] == 100.0
    assert by_name["Cara"].components["Electricity"] == 0.0
    # Water equal among 3 -> totals preserved with rounding: two 33.33 and one 33.34
    water_vals = sorted([
        by_name["Alice"].components["Water"],
        by_name["Bob"].components["Water"],
        by_name["Cara"].components["Water"],
    ])
    assert water_vals == [33.33, 33.33, 33.34]
    # Internet equal among 3 -> totals preserved with rounding: one 26.66 and two 26.67
    inet_vals = sorted([
        by_name["Alice"].components["Internet"],
        by_name["Bob"].components["Internet"],
        by_name["Cara"].components["Internet"],
    ])
    assert inet_vals == [26.66, 26.67, 26.67]


def test_zero_total_usage_electricity():
    bill = MonthlyBill(year=2025, month=10)
    participants = [make_p(1, "A"), make_p(2, "B")]
    readings = [make_r(1, 100, 100), make_r(2, 200, 200)]  # all zero usage
    c1 = BillComponent(month_id=1, name="Electricity", amount=300.0, split_method='usage', position=0)
    c2 = BillComponent(month_id=1, name="Water", amount=90.0, split_method='equal', position=1)
    c3 = BillComponent(month_id=1, name="Internet", amount=60.0, split_method='equal', position=2)
    c1.id, c2.id, c3.id = 11, 12, 13
    res = BillCalculator().compute_contributions_dynamic(bill, [c1, c2, c3], readings, participants, [])
    for x in res:
        assert x.components["Electricity"] == 0.0
        assert x.components["Water"] == 45.0
        assert x.components["Internet"] == 30.0
