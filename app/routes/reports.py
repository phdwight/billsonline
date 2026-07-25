"""Reports routes - single responsibility: report generation and display."""
from __future__ import annotations

from flask import Blueprint, render_template, request, jsonify

from ..repositories import (
    MonthlyBillRepository,
    ParticipantRepository,
    MeterReadingRepository,
    BillComponentRepository,
    ComponentAdjustmentRepository,
    MonthParticipantRepository,
)
from ..services.bill_calculator import BillCalculator

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _get_bill_repo() -> MonthlyBillRepository:
    return MonthlyBillRepository()


def _get_participants_repo() -> ParticipantRepository:
    return ParticipantRepository()


def _get_reading_repo() -> MeterReadingRepository:
    return MeterReadingRepository()


def _get_component_repo() -> BillComponentRepository:
    return BillComponentRepository()


def _get_comp_adjust_repo() -> ComponentAdjustmentRepository:
    return ComponentAdjustmentRepository()


def _get_month_part_repo() -> MonthParticipantRepository:
    return MonthParticipantRepository()


@bp.get("/")
def index():
    """GET /reports - Reports page with month range selector."""
    bill_repo = _get_bill_repo()
    
    # Get all available months (including archived) for the dropdown
    all_bills = bill_repo.list_all_including_archived()
    
    # Create list of available months as (year, month, display_name)
    available_months = []
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    for bill in all_bills:
        display = f"{month_names[bill.month - 1]} {bill.year}"
        available_months.append({
            'year': bill.year,
            'month': bill.month,
            'display': display,
            'value': f"{bill.year}-{bill.month:02d}"
        })
    
    return render_template("reports.html", available_months=available_months)


@bp.get("/data")
def get_report_data():
    """GET /reports/data - API endpoint for report data.
    
    Query params:
        from_year, from_month: Start of range
        to_year, to_month: End of range
    """
    bill_repo = _get_bill_repo()
    participants_repo = _get_participants_repo()
    reading_repo = _get_reading_repo()
    component_repo = _get_component_repo()
    comp_adjust_repo = _get_comp_adjust_repo()
    month_part_repo = _get_month_part_repo()
    calculator = BillCalculator()
    
    # Parse query parameters
    try:
        from_year = int(request.args.get('from_year', 0))
        from_month = int(request.args.get('from_month', 0))
        to_year = int(request.args.get('to_year', 0))
        to_month = int(request.args.get('to_month', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid parameters'}), 400
    
    if not all([from_year, from_month, to_year, to_month]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    # Get all participants
    all_participants = participants_repo.list_all()
    participant_names = {p.id: p.name for p in all_participants}
    
    # Get all bills (including archived) in range
    all_bills = bill_repo.list_all_including_archived()
    
    # Filter bills within the date range
    bills_in_range = []
    for bill in all_bills:
        bill_date = (bill.year, bill.month)
        start_date = (from_year, from_month)
        end_date = (to_year, to_month)
        
        if start_date <= bill_date <= end_date:
            bills_in_range.append(bill)
    
    # Sort by date ascending
    bills_in_range.sort(key=lambda b: (b.year, b.month))
    
    # Build response data
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    labels = []  # Month labels for x-axis
    datasets = {}  # {participant_name: [totals per month]}
    usage_datasets = {}  # {participant_name: [usage per month]}
    
    for bill in bills_in_range:
        label = f"{month_names[bill.month - 1]} {bill.year}"
        labels.append(label)
        
        # Get components and readings for this bill
        components = component_repo.list_for_month(bill.id)
        readings = reading_repo.list_for_month(bill.id)
        comp_adjs = comp_adjust_repo.list_for_month(bill.id)
        
        # Get month members
        month_members = month_part_repo.list_for_month(bill.id)
        member_ids = {m.participant_id for m in month_members}
        
        # If no members set, use all participants (legacy behavior)
        if not member_ids:
            member_ids = {p.id for p in all_participants}
        
        member_participants = [p for p in all_participants if p.id in member_ids]
        
        # Compute contributions
        if components:
            contributions = calculator.compute_contributions_dynamic(
                bill=bill,
                components=components,
                readings=readings,
                participants=member_participants,
                component_adjustments=comp_adjs,
            )
        else:
            # Legacy bill without components - create synthetic
            contributions = []
        
        # Create a map of participant_id -> total for this month
        totals_this_month = {p.id: 0.0 for p in all_participants}
        for contrib in contributions:
            totals_this_month[contrib.participant.id] = contrib.total
        
        # Create a map of participant_id -> usage for this month
        usage_this_month = {p.id: 0.0 for p in all_participants}
        for reading in readings:
            usage_this_month[reading.participant_id] = reading.usage()
        
        # Add to datasets
        for p in all_participants:
            name = p.name
            if name not in datasets:
                datasets[name] = []
            datasets[name].append(round(totals_this_month[p.id], 2))
            
            if name not in usage_datasets:
                usage_datasets[name] = []
            usage_datasets[name].append(round(usage_this_month[p.id], 2))
    
    # Convert datasets to Chart.js format
    chart_datasets = []
    usage_chart_datasets = []
    # Validated categorical palette (colorblind-safe on the #f2f2f3 surface).
    # Colors are assigned per participant in stable id order — never cycled —
    # so a person keeps their color across ranges and charts; participants
    # beyond the palette fold to neutral gray.
    colors = [
        '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
        '#e87ba4', '#008300', '#4a3aa7', '#e34948',
    ]
    neutral = '#7a7a7d'
    color_by_name = {
        p.name: (colors[i] if i < len(colors) else neutral)
        for i, p in enumerate(sorted(all_participants, key=lambda p: p.id))
    }

    for name, data in sorted(datasets.items()):
        color = color_by_name.get(name, neutral)
        chart_datasets.append({
            'label': name,
            'data': data,
            'backgroundColor': color,
            'borderColor': color,
            'borderWidth': 2,
            'fill': False,
            'tension': 0.1
        })
    
    for name, data in sorted(usage_datasets.items()):
        color = color_by_name.get(name, neutral)
        usage_chart_datasets.append({
            'label': name,
            'data': data,
            'backgroundColor': color,
            'borderColor': color,
            'borderWidth': 1,
        })
    
    return jsonify({
        'labels': labels,
        'datasets': chart_datasets,
        'usage_datasets': usage_chart_datasets
    })
