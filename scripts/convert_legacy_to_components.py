#!/usr/bin/env python3
"""
Convert all months that still have only raw amounts (and no dynamic components) into
predefined dynamic components in one go.

Creates components per month:
- Electricity: split by usage
- Water: split equally
- Internet: split equally

Idempotent: skips months that already have at least one component.
Prints a summary at the end.

Usage:
    python scripts/convert_legacy_to_components.py

Requires the same environment variables/config as the Flask app.
"""
from __future__ import annotations

from typing import Tuple

from app import create_app
from app.extensions import db
from app.models import MonthlyBill
from app.repositories import BillComponentRepository


def convert_month(bill: MonthlyBill, comp_repo: BillComponentRepository) -> Tuple[int, int]:
    """Convert one bill to components if none exist. Returns (created_count, skipped_flag)."""
    existing = comp_repo.list_for_month(bill.id)
    if existing:
        return 0, 1  # skipped
    created = 0
    position = 0
    # Electricity by usage
    if bill.electricity_amount and float(bill.electricity_amount) > 0:
        comp_repo.add(bill.id, name="Electricity", amount=float(bill.electricity_amount), split_method="usage", position=position)
        position += 1
        created += 1
    # Water equal
    if bill.water_amount and float(bill.water_amount) > 0:
        comp_repo.add(bill.id, name="Water", amount=float(bill.water_amount), split_method="equal", position=position)
        position += 1
        created += 1
    # Internet equal
    if bill.internet_amount and float(bill.internet_amount) > 0:
        comp_repo.add(bill.id, name="Internet", amount=float(bill.internet_amount), split_method="equal", position=position)
        position += 1
        created += 1
    return created, 0


def main() -> None:
    app = create_app()
    comp_repo = BillComponentRepository()
    with app.app_context():
        # Ensure DB ready
        db.create_all()
        total = 0
        skipped = 0
        months = MonthlyBill.query.order_by(MonthlyBill.year.asc(), MonthlyBill.month.asc()).all()
        for bill in months:
            created, was_skipped = convert_month(bill, comp_repo)
            total += created
            skipped += was_skipped
            if created:
                print(f"Converted {bill.year}-{bill.month:02d}: created {created} components")
            else:
                print(f"Skipped {bill.year}-{bill.month:02d}: already has components")
        print("\nDone.")
        print(f"Months processed: {len(months)}  |  Skipped (already had components): {skipped}  |  Components created: {total}")


if __name__ == "__main__":
    main()
