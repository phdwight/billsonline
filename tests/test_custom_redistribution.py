from app.services import BillCalculator, Contribution
from app.models import Participant, MonthlyBill, MeterReading


def make_participants(names):
    return [Participant(id=i+1, name=n) for i, n in enumerate(names)]


def test_percent_redistribution_single_zero():
    # Setup: 3 participants, water even; zero Bob's water, redistribute 70/30 to Alice/Charlie
    p = make_participants(["Alice", "Bob", "Charlie"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=120.0, internet_amount=0.0)
    readings = []
    adjustments = {
        p[1].id: {
            'water': True,
            'redis_water': {
                'mode': 'percent',
                'targets': {p[0].id: 70, p[2].id: 30},
            }
        }
    }
    calc = BillCalculator()
    contribs = calc.compute_contributions(bill, readings, p, adjustments)

    # Base water share is 40 each; Bob's 40 is redistributed 70/30 => +28 to Alice, +12 to Charlie
    amounts = {c.participant.name: c.water for c in contribs}
    assert round(amounts['Alice'], 2) == 68.0
    assert round(amounts['Bob'], 2) == 0.0
    assert round(amounts['Charlie'], 2) == 52.0
    # Totals preserved
    assert sum(a.water for a in contribs) == bill.water_amount


def test_amount_redistribution_overflow_normalized():
    # Setup: 2 participants, internet even; zero Alice's internet 50, targets ask 60 -> normalized to 50
    p = make_participants(["Alice", "Bob"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=0.0, water_amount=0.0, internet_amount=100.0)
    readings = []
    adjustments = {
        p[0].id: {
            'internet': True,
            'redis_internet': {
                'mode': 'amount',
                'targets': {p[1].id: 60},
            }
        }
    }
    calc = BillCalculator()
    contribs = calc.compute_contributions(bill, readings, p, adjustments)

    # Base internet share is 50 each; Alice's 50 moves to Bob
    amounts = {c.participant.name: c.internet for c in contribs}
    assert round(amounts['Alice'], 2) == 0.0
    assert round(amounts['Bob'], 2) == 100.0
    assert sum(a.internet for a in contribs) == bill.internet_amount


def test_mixed_missing_targets_leftover_equal():
    # Electricity by usage; zero Charlie's electricity, provide only one target (Alice)
    # Leftover should be split equally among remaining eligible (Alice & Bob)
    p = make_participants(["Alice", "Bob", "Charlie"])
    bill = MonthlyBill(year=2025, month=10, electricity_amount=90.0, water_amount=0.0, internet_amount=0.0)
    # Usage: Alice 1, Bob 2, Charlie 3 -> shares: 15, 30, 45
    readings = [
        MeterReading(participant_id=p[0].id, month_id=1, reading_current=1.0, reading_previous=0.0),
        MeterReading(participant_id=p[1].id, month_id=1, reading_current=2.0, reading_previous=0.0),
        MeterReading(participant_id=p[2].id, month_id=1, reading_current=3.0, reading_previous=0.0),
    ]
    adjustments = {
        p[2].id: {
            'electricity': True,
            'redis_electricity': {
                'mode': 'percent',
                # Only Alice targeted with 100%; Bob gets leftover via equal split since both are eligible
                'targets': {p[0].id: 100},
            }
        }
    }
    calc = BillCalculator()
    contribs = calc.compute_contributions(bill, readings, p, adjustments)

    # Before zeroing: [15, 30, 45]; Charlie's 45 redistributed: 100% to Alice per rule -> +45 to Alice
    # But we also treat leftover (zero due to full allocation) equally; nothing left to split. Final: [60, 30, 0]
    amounts = {c.participant.name: c.electricity for c in contribs}
    assert round(amounts['Alice'], 2) == 60.0
    assert round(amounts['Bob'], 2) == 30.0
    assert round(amounts['Charlie'], 2) == 0.0
    assert sum(a.electricity for a in contribs) == bill.electricity_amount
