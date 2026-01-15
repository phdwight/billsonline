from app.services import BillCalculator
from app.models import Participant, MonthlyBill, MeterReading, BillComponent, ComponentAdjustment


def make_participants(names):
    return [Participant(id=i + 1, name=n) for i, n in enumerate(names)]


def test_percent_redistribution_single_zero():
    # Setup: 3 participants, water even; zero Bob's water, redistribute 70/30 to Alice/Charlie
    p = make_participants(["Alice", "Bob", "Charlie"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=120.0, internet_amount=0.0)
    readings = []
    # Dynamic component for Water
    water = BillComponent(month_id=1, name="Water",
                          amount=120.0, split_method='equal', position=1)
    water.id = 100
    # Zero Bob's water and redistribute 70/30 to Alice/Charlie
    adj = ComponentAdjustment(month_id=1, component_id=water.id, participant_id=p[1].id, zero=True,
                              redis_rule={
                                  'mode': 'percent',
                                  'targets': {p[0].id: 70, p[2].id: 30},
    })
    calc = BillCalculator()
    contribs = calc.compute_contributions_dynamic(
        bill, [water], readings, p, [adj])

    # Base water share is 40 each; Bob's 40 is redistributed 70/30 => +28 to Alice, +12 to Charlie
    amounts = {c.participant.name: c.components["Water"] for c in contribs}
    assert round(amounts['Alice'], 2) == 68.0
    assert round(amounts['Bob'], 2) == 0.0
    assert round(amounts['Charlie'], 2) == 52.0
    # Totals preserved
    assert sum(a.components["Water"] for a in contribs) == bill.water_amount


def test_amount_redistribution_overflow_normalized():
    # Setup: 2 participants, internet even; zero Alice's internet 50, targets ask 60 -> normalized to 50
    p = make_participants(["Alice", "Bob"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=0.0, internet_amount=100.0)
    readings = []
    internet = BillComponent(month_id=1, name="Internet",
                             amount=100.0, split_method='equal', position=1)
    internet.id = 101
    adj = ComponentAdjustment(month_id=1, component_id=internet.id, participant_id=p[0].id, zero=True,
                              redis_rule={
                                  'mode': 'amount',
                                  'targets': {p[1].id: 60},
    })
    calc = BillCalculator()
    contribs = calc.compute_contributions_dynamic(
        bill, [internet], readings, p, [adj])

    # Base internet share is 50 each; Alice's 50 moves to Bob
    amounts = {c.participant.name: c.components["Internet"] for c in contribs}
    assert round(amounts['Alice'], 2) == 0.0
    assert round(amounts['Bob'], 2) == 100.0
    assert sum(a.components["Internet"]
               for a in contribs) == bill.internet_amount


def test_mixed_missing_targets_leftover_equal():
    # Electricity by usage; zero Charlie's electricity, provide only one target (Alice)
    # Leftover should be split equally among remaining eligible (Alice & Bob)
    p = make_participants(["Alice", "Bob", "Charlie"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=90.0,
                       water_amount=0.0, internet_amount=0.0)
    # Usage: Alice 1, Bob 2, Charlie 3 -> shares: 15, 30, 45
    readings = [
        MeterReading(participant_id=p[0].id, month_id=1,
                     reading_current=1.0, reading_previous=0.0),
        MeterReading(participant_id=p[1].id, month_id=1,
                     reading_current=2.0, reading_previous=0.0),
        MeterReading(participant_id=p[2].id, month_id=1,
                     reading_current=3.0, reading_previous=0.0),
    ]
    electricity = BillComponent(
        month_id=1, name="Electricity", amount=90.0, split_method='usage', position=1)
    electricity.id = 102
    adj = ComponentAdjustment(month_id=1, component_id=electricity.id, participant_id=p[2].id, zero=True,
                              redis_rule={
                                  'mode': 'percent',
                                  # Only Alice targeted with 100%; Bob gets leftover via equal split
                                  'targets': {p[0].id: 100},
    })
    calc = BillCalculator()
    contribs = calc.compute_contributions_dynamic(
        bill, [electricity], readings, p, [adj])

    # Before zeroing: [15, 30, 45]; Charlie's 45 redistributed: 100% to Alice per rule -> +45 to Alice
    # But we also treat leftover (zero due to full allocation) equally; nothing left to split. Final: [60, 30, 0]
    amounts = {
        c.participant.name: c.components["Electricity"] for c in contribs}
    assert round(amounts['Alice'], 2) == 60.0
    assert round(amounts['Bob'], 2) == 30.0
    assert round(amounts['Charlie'], 2) == 0.0
    assert sum(a.components["Electricity"]
               for a in contribs) == bill.electricity_amount


def test_self_redistribution_percent():
    """Test that a participant can redistribute part of their share back to themselves."""
    p = make_participants(["Alice", "Bob", "Charlie"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=0.0, internet_amount=90.0)
    readings = []
    # Internet split equally: base 30 each
    internet = BillComponent(month_id=1, name="Internet",
                             amount=90.0, split_method='equal', position=1)
    internet.id = 103
    # Alice redistributes her 30: 50% to self (15), 30% to Bob (9), 20% to Charlie (6)
    adj = ComponentAdjustment(
        month_id=1, component_id=internet.id, participant_id=p[0].id, zero=True,
        redis_rule={
            'mode': 'percent',
            'targets': {p[0].id: 50, p[1].id: 30, p[2].id: 20},  # Includes self
        }
    )
    calc = BillCalculator()
    contribs = calc.compute_contributions_dynamic(
        bill, [internet], readings, p, [adj])

    # Base: [30, 30, 30]
    # Alice's 30 redistributed: 50% to self (15), 30% to Bob (9), 20% to Charlie (6)
    # Final: Alice: 0 + 15 = 15, Bob: 30 + 9 = 39, Charlie: 30 + 6 = 36
    amounts = {c.participant.name: c.components["Internet"] for c in contribs}
    assert round(amounts['Alice'], 2) == 15.0
    assert round(amounts['Bob'], 2) == 39.0
    assert round(amounts['Charlie'], 2) == 36.0
    # Totals preserved
    assert sum(a.components["Internet"] for a in contribs) == bill.internet_amount


def test_self_redistribution_amount():
    """Test that a participant can redistribute specific amounts including to themselves."""
    p = make_participants(["Alice", "Bob"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0,
                       water_amount=100.0, internet_amount=0.0)
    readings = []
    # Water split equally: base 50 each
    water = BillComponent(month_id=1, name="Water",
                          amount=100.0, split_method='equal', position=1)
    water.id = 104
    # Alice redistributes her 50: 20 to self, 30 to Bob
    adj = ComponentAdjustment(
        month_id=1, component_id=water.id, participant_id=p[0].id, zero=True,
        redis_rule={
            'mode': 'amount',
            'targets': {p[0].id: 20, p[1].id: 30},  # Includes self
        }
    )
    calc = BillCalculator()
    contribs = calc.compute_contributions_dynamic(
        bill, [water], readings, p, [adj])

    # Base: [50, 50]
    # Alice's 50 redistributed: 20 to self, 30 to Bob
    # Final: Alice: 0 + 20 = 20, Bob: 50 + 30 = 80
    amounts = {c.participant.name: c.components["Water"] for c in contribs}
    assert round(amounts['Alice'], 2) == 20.0
    assert round(amounts['Bob'], 2) == 80.0
    # Totals preserved
    assert sum(a.components["Water"] for a in contribs) == bill.water_amount