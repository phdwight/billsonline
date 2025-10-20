from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant, BillComponent, ComponentAdjustment


def P(id, name, include=True):
    # include flag no longer used; keep signature for compatibility
    return Participant(id=id, name=name)


def R(pid, current, prev):
    return MeterReading(participant_id=pid, month_id=1, reading_current=current, reading_previous=prev)


def test_zero_electricity_redistributes_to_rest():
    bill = MonthlyBill(year=2025, month=10)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = [R(1, 200, 100), R(2, 150, 100), R(3, 100, 100)]  # usage: 100,50,0 -> shares: 200,100,0
    parts = [A, B, C]
    elec = BillComponent(month_id=1, name="Electricity", amount=300.0, split_method='usage', position=0)
    water = BillComponent(month_id=1, name="Water", amount=90.0, split_method='equal', position=1)
    inet = BillComponent(month_id=1, name="Internet", amount=60.0, split_method='equal', position=2)
    elec.id, water.id, inet.id = 1, 2, 3
    # Zero A on Electricity with no explicit rule -> leftover equal among remaining
    adj = ComponentAdjustment(month_id=1, component_id=elec.id, participant_id=A.id, zero=True, redis_rule=None)
    c = BillCalculator().compute_contributions_dynamic(bill, [elec, water, inet], readings, parts, [adj])
    by = {x.participant.id: x for x in c}
    assert by[1].components["Electricity"] == 0.0
    assert by[2].components["Electricity"] == 300.0
    assert by[3].components["Electricity"] == 0.0


def test_zero_water_even_split_then_redistribute():
    bill = MonthlyBill(year=2025, month=10)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = []
    parts = [A, B, C]
    water = BillComponent(month_id=1, name="Water", amount=90.0, split_method='equal', position=0)
    water.id = 10
    # Zero B's Water
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=B.id, zero=True, redis_rule=None)
    c = BillCalculator().compute_contributions_dynamic(bill, [water], readings, parts, [adj])
    by = {x.participant.id: x for x in c}
    assert by[1].components["Water"] == 45.0
    assert by[2].components["Water"] == 0.0
    assert by[3].components["Water"] == 45.0
    assert round(sum(x.components["Water"] for x in c), 2) == 90.0


def test_zero_internet_equal_among_all():
    bill = MonthlyBill(year=2025, month=10)
    A, B, C = P(1, "A"), P(2, "B"), P(3, "C")
    readings = []
    parts = [A, B, C]
    inet = BillComponent(month_id=1, name="Internet", amount=90.0, split_method='equal', position=0)
    inet.id = 20
    adj = ComponentAdjustment(month_id=1, component_id=inet.id, participant_id=A.id, zero=True, redis_rule=None)
    c = BillCalculator().compute_contributions_dynamic(bill, [inet], readings, parts, [adj])
    by = {x.participant.id: x for x in c}
    assert by[1].components["Internet"] == 0.0
    assert by[2].components["Internet"] == 45.0
    assert by[3].components["Internet"] == 45.0
