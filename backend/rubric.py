"""Versioned scoring rules. Models supply evidence; the server decides totals and eligibility."""
from decimal import Decimal, ROUND_HALF_UP

VERSION='science-weighted-evaluation-v2'
WEIGHTS={'originality':30,'inquiry':30,'feasibility':15,'utility':15,'interest':10}
CONDITIONS=('level','place','equipment','budget','time','observation','safety')
STATUSES=('가능','검토 필요','불가')

def calculate(entry):
    numerator=sum(entry[axis]['score']*weight for axis,weight in WEIGHTS.items())
    raw=Decimal(numerator)/100
    display=float(raw.quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))
    checks=entry['execution_checks']
    if set(checks)!=set(CONDITIONS):raise ValueError('execution conditions')
    for check in checks.values():
        if not isinstance(check,dict) or check.get('status') not in STATUSES or not isinstance(check.get('reason'),str) or not check['reason'].strip():raise ValueError('execution evidence')
    status=max((c['status'] for c in checks.values()),key=STATUSES.index)
    return float(raw),display,numerator>=8000,status
