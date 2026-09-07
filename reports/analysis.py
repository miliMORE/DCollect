from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

from catalog.models import JobGroup
from collection.models import ComparatorPayRow, IndividualResponse


def _as_decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _row_value(row, measure):
    if row is None or row.not_applicable:
        return None
    if measure == "total":
        return row.total_cash()
    return row.midpoint_basic()


def comparator_value(org, period, job, measure="basic"):
    row = ComparatorPayRow.objects.filter(
        organization=org, survey_period=period, job=job
    ).first()
    return _row_value(row, measure)


def _sorted_amounts(values):
    nums = []
    for value in values:
        amount = _as_decimal(value)
        if amount is not None:
            nums.append(amount)
    nums.sort()
    return nums


def _interpolated(nums, p):
    """Inclusive percentile (Excel PERCENTILE.INC). nums must be sorted and n >= 2."""
    rank = (Decimal(str(p)) / Decimal("100")) * Decimal(len(nums) - 1)
    lower = int(rank.to_integral_value(rounding=ROUND_DOWN))
    upper = min(lower + 1, len(nums) - 1)
    weight = rank - Decimal(lower)
    return (nums[lower] * (Decimal("1") - weight) + nums[upper] * weight).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def percentile(values, p):
    """Linear interpolation. p is 0–100. A single observation is returned for any p."""
    nums = _sorted_amounts(values)
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    return _interpolated(nums, p)


def distribution(values):
    """P25 / P50 / P75. Quartiles are blank when there is only one observation."""
    nums = _sorted_amounts(values)
    n = len(nums)
    if n == 0:
        return {"n": 0, "p25": None, "p50": None, "p75": None}
    if n == 1:
        return {"n": 1, "p25": None, "p50": nums[0], "p75": None}
    return {
        "n": n,
        "p25": _interpolated(nums, 25),
        "p50": _interpolated(nums, 50),
        "p75": _interpolated(nums, 75),
    }


def market_scale_label(county, p25, p50, p75):
    if county is None or p50 is None:
        return "", ""
    if p25 is not None and county < p25:
        return "Below P25 (lag)", "pos-below"
    if p75 is not None and county > p75:
        return "Above P75 (lead)", "pos-above"
    _ratio, _label, css = position_meta(county, p50)
    if css == "pos-below":
        return "Below market median", css
    if css == "pos-above":
        return "Above market median", css
    return "At market median", css


def position_meta(county, market):
    if county is None or market in (None, 0):
        return None, "", ""
    ratio = (county / market).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if ratio < Decimal("0.90"):
        return ratio, "Below market", "pos-below"
    if ratio > Decimal("1.10"):
        return ratio, "Above market", "pos-above"
    return ratio, "Around market", "pos-around"


def money(value):
    value = _as_decimal(value)
    if value is None:
        return ""
    return f"{value:,.0f}"


def mean(values):
    nums = []
    for value in values:
        amount = _as_decimal(value)
        if amount is not None:
            nums.append(amount)
    if not nums:
        return None
    return (sum(nums) / Decimal(len(nums))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def orgs_with_pay(orgs, period):
    usable = []
    for org in orgs:
        has_pay = ComparatorPayRow.objects.filter(
            organization=org, survey_period=period, not_applicable=False
        ).exclude(min_basic=None, max_basic=None, median_basic=None).exists()
        if has_pay:
            usable.append(org)
    return usable


def staff_pay_values(county, period, job_group, measure="basic"):
    qs = IndividualResponse.objects.filter(
        county=county, survey_period=period, job__job_group=job_group
    )
    values = []
    for row in qs:
        values.append(row.total_cash() if measure == "total" else row.current_basic)
    return [v for v in values if v is not None]


def comparator_group_value(org, period, job_group, measure="basic"):
    rows = ComparatorPayRow.objects.filter(
        organization=org,
        survey_period=period,
        job__job_group=job_group,
        not_applicable=False,
    )
    values = [_row_value(row, measure) for row in rows]
    present = [v for v in values if v is not None]
    return percentile(present, 50)


def _staff_by_group(county, period, measure):
    grouped = defaultdict(list)
    qs = IndividualResponse.objects.filter(county=county, survey_period=period).select_related(
        "job", "job__job_group"
    )
    for row in qs:
        if not row.job_id or not row.job.job_group_id:
            continue
        amount = row.total_cash() if measure == "total" else row.current_basic
        if amount is not None:
            grouped[row.job.job_group_id].append(amount)
    return grouped


def _comparator_by_org_group(orgs, period, measure):
    grouped = defaultdict(list)
    if not orgs or not period:
        return grouped
    rows = ComparatorPayRow.objects.filter(
        organization__in=orgs,
        survey_period=period,
        not_applicable=False,
    ).select_related("job", "job__job_group")
    for row in rows:
        group_id = getattr(row.job, "job_group_id", None)
        amount = _row_value(row, measure)
        if group_id and amount is not None:
            grouped[(row.organization_id, group_id)].append(amount)
    return grouped


def unmatched_staff_count(case, period):
    if not case or not period:
        return 0
    qs = IndividualResponse.objects.filter(county=case.county, survey_period=period)
    matched = qs.filter(job__job_group__code__in=JobGroup.PAY_CODES)
    return qs.count() - matched.count()


def build_analysis_rows(case, orgs, period, measure="basic"):
    orgs = list(orgs)
    rows = []
    if not case:
        return rows
    staff_map = _staff_by_group(case.county, period, measure)
    comp_map = _comparator_by_org_group(orgs, period, measure)
    job_rows = case.job_rows.select_related("job_group", "case__county").filter(
        job_group__code__in=JobGroup.PAY_CODES
    )
    for job_row in job_rows:
        group_id = job_row.job_group_id
        comps = [
            percentile(comp_map.get((org.id, group_id), []), 50) for org in orgs
        ]
        present = [c for c in comps if c is not None]
        market_dist = distribution(present)
        official = _row_value(job_row, measure)
        staff = staff_map.get(group_id, [])
        sample = []
        if official is not None:
            sample.append(official)
        sample.extend(staff)
        county_dist = distribution(sample)
        county = county_dist["p50"]
        market = market_dist["p50"]
        ratio, label, css = position_meta(county, market)
        scale_label, scale_css = market_scale_label(
            county, market_dist["p25"], market, market_dist["p75"]
        )
        rows.append(
            {
                "job": job_row.job_group,
                "job_group": job_row.job_group.code if job_row.job_group_id else "",
                "src_equivalent": job_row.src_equivalent_code(),
                "official": official,
                "county": county,
                "county_p25": county_dist["p25"],
                "county_p75": county_dist["p75"],
                "county_sample": sample,
                "comparators": comps,
                "market": market,
                "market_p25": market_dist["p25"],
                "market_p75": market_dist["p75"],
                "market_n": market_dist["n"],
                "position": ratio,
                "position_label": label,
                "position_class": css,
                "scale_label": scale_label,
                "scale_class": scale_css,
                "staff_n": len(staff),
                "sample_n": county_dist["n"],
                "not_applicable": job_row.not_applicable,
                "has_county": bool(sample),
                "total_cash": job_row.total_cash(),
            }
        )
    return rows


def rollup_rows(rows, key):
    """Group job-level analysis rows by county job group or SRC equivalent."""
    buckets = {}
    order = []
    for row in rows:
        if row.get("not_applicable"):
            continue
        label = (row.get(key) or "").strip()
        if not label:
            continue
        if label not in buckets:
            buckets[label] = []
            order.append(label)
        buckets[label].append(row)

    grouped = []
    for label in order:
        items = buckets[label]
        county_sample = []
        for row in items:
            extra = row.get("county_sample")
            if extra:
                county_sample.extend(extra)
            elif row.get("county") is not None:
                county_sample.append(row["county"])
        county_dist = distribution(county_sample)
        county_vals = [r["county"] for r in items if r.get("county") is not None]
        comps_lists = [list(r.get("comparators") or []) for r in items]
        n_orgs = max((len(cols) for cols in comps_lists), default=0)
        if n_orgs:
            org_medians = []
            for index in range(n_orgs):
                vals = [
                    cols[index]
                    for cols in comps_lists
                    if index < len(cols) and cols[index] is not None
                ]
                if vals:
                    org_medians.append(percentile(vals, 50))
            market_dist = distribution(org_medians)
        else:
            market_dist = distribution(
                [r["market"] for r in items if r.get("market") is not None]
            )
        county = county_dist["p50"]
        market = market_dist["p50"]
        ratio, pos_label, css = position_meta(county, market)
        scale_label, scale_css = market_scale_label(
            county, market_dist["p25"], market, market_dist["p75"]
        )
        grouped.append(
            {
                "label": label,
                "n": len(items),
                "jobs_with_pay": len(county_vals),
                "average": mean(county_vals),
                "county_p25": county_dist["p25"],
                "county": county,
                "county_p75": county_dist["p75"],
                "market_n": market_dist["n"],
                "market_p25": market_dist["p25"],
                "market": market,
                "market_p75": market_dist["p75"],
                "position": ratio,
                "position_label": pos_label,
                "position_class": css,
                "scale_label": scale_label,
                "scale_class": scale_css,
            }
        )
    grouped.sort(key=lambda item: item["label"])
    return grouped


def summarise_rows(rows):
    scored = [r for r in rows if r["position"] is not None]
    scaled = [r for r in rows if r.get("scale_label")]
    return {
        "jobs": len(rows),
        "compared": len(scored),
        "below": sum(1 for r in scored if r["position_class"] == "pos-below"),
        "around": sum(1 for r in scored if r["position_class"] == "pos-around"),
        "above": sum(1 for r in scored if r["position_class"] == "pos-above"),
        "missing": sum(1 for r in rows if not r["has_county"] and not r["not_applicable"]),
        "lag": sum(1 for r in scaled if r.get("scale_class") == "pos-below" and "P25" in r.get("scale_label", "")),
        "lead": sum(1 for r in scaled if r.get("scale_class") == "pos-above" and "P75" in r.get("scale_label", "")),
        "staff_jobs": sum(1 for r in rows if r.get("staff_n")),
        "staff_n": sum(r.get("staff_n") or 0 for r in rows),
        "sample_n": sum(r.get("sample_n") or 0 for r in rows),
    }
