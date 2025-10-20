from pathlib import Path
import sys

# Ensure project root is on sys.path for 'app' imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant, BillComponent, ComponentAdjustment


def P(id, name):
    return Participant(id=id, name=name)


def R(pid, cur, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=cur, reading_previous=prev)


def test_percentage_distribution_normalizes_when_not_100():
    bill = MonthlyBill(year=2025, month=10)
    parts = [P(1, 'A'), P(2, 'B'), P(3, 'C')]
    comp = BillComponent(month_id=1, name='Percenty', amount=100.0, split_method='percentage', position=1)
    # Sums to 110 -> should normalize to 100 preserving ratios
    comp.distribution = {1: 50, 2: 40, 3: 20}
    comp.id = 101
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], [], parts, [])
    by = {x.participant.id: x for x in res}
    # Ratios 50:40:20 -> normalized to sum=100, preserving ratios
    # Expected base (before rounding correction): 45.45, 36.36, 18.18 (sum=100)
    # Implementation may nudge by 0.01 to preserve total after rounding, so allow 0.01 tolerance.
    a = by[1].components['Percenty']
    b = by[2].components['Percenty']
    c = by[3].components['Percenty']
    assert round(a + b + c, 2) == 100.0
    assert abs(a - 45.45) <= 0.01
    assert abs(b - 36.36) <= 0.01
    assert abs(c - 18.18) <= 0.01


def test_rounding_correction_preserves_total_equal_split():
    bill = MonthlyBill(year=2025, month=10)
    # 3 participants, 100 split equal -> 33.33, 33.33, 33.34 after correction
    parts = [P(1,'A'), P(2,'B'), P(3,'C')]
    comp = BillComponent(month_id=1, name='Equal100', amount=100.0, split_method='equal', position=1)
    comp.id = 102
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], [], parts, [])
    vals = sorted([c.components['Equal100'] for c in res])
    assert vals == [33.33, 33.33, 33.34]
    assert round(sum(c.components['Equal100'] for c in res), 2) == 100.0


def test_rounding_correction_preserves_total_usage_split():
    bill = MonthlyBill(year=2025, month=10)
    # Usage shares: 1,1,1 -> amount 100 -> same as equal rounding
    parts = [P(1,'A'), P(2,'B'), P(3,'C')]
    readings = [R(1, 101, 100), R(2, 201, 200), R(3, 301, 300)]  # each usage 1
    comp = BillComponent(month_id=1, name='Usage100', amount=100.0, split_method='usage', position=1)
    comp.id = 103
    calc = BillCalculator()
    res = calc.compute_contributions_dynamic(bill, [comp], readings, parts, [])
    vals = sorted([c.components['Usage100'] for c in res])
    assert vals == [33.33, 33.33, 33.34]
    assert round(sum(c.components['Usage100'] for c in res), 2) == 100.0
