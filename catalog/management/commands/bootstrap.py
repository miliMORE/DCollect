from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from catalog.models import (
    BenchmarkJob,
    BenefitType,
    ComparatorOrganization,
    County,
    DocumentType,
    JobFamily,
    JobGroup,
    OptionItem,
    OptionSet,
    SRCGrade,
    SiteSettings,
    SurveyPeriod,
    ValidationItem,
)
from collection.models import (
    ComparatorPayRow,
    CountyCase,
    IndividualResponse,
    JobPayRow,
)
from collection.services import ensure_case_structure, ensure_staff_link


COUNTIES = [
    ("001", "Mombasa", "Coast"),
    ("002", "Kwale", "Coast"),
    ("003", "Kilifi", "Coast"),
    ("004", "Tana River", "Coast"),
    ("005", "Lamu", "Coast"),
    ("006", "Taita-Taveta", "Coast"),
    ("007", "Garissa", "North Eastern"),
    ("008", "Wajir", "North Eastern"),
    ("009", "Mandera", "North Eastern"),
    ("010", "Marsabit", "Eastern"),
    ("011", "Isiolo", "Eastern"),
    ("012", "Meru", "Eastern"),
    ("013", "Tharaka-Nithi", "Eastern"),
    ("014", "Embu", "Eastern"),
    ("015", "Kitui", "Eastern"),
    ("016", "Machakos", "Eastern"),
    ("017", "Makueni", "Eastern"),
    ("018", "Nyandarua", "Central"),
    ("019", "Nyeri", "Central"),
    ("020", "Kirinyaga", "Central"),
    ("021", "Murang'a", "Central"),
    ("022", "Kiambu", "Central"),
    ("023", "Turkana", "Rift Valley"),
    ("024", "West Pokot", "Rift Valley"),
    ("025", "Samburu", "Rift Valley"),
    ("026", "Trans Nzoia", "Rift Valley"),
    ("027", "Uasin Gishu", "Rift Valley"),
    ("028", "Elgeyo-Marakwet", "Rift Valley"),
    ("029", "Nandi", "Rift Valley"),
    ("030", "Baringo", "Rift Valley"),
    ("031", "Laikipia", "Rift Valley"),
    ("032", "Nakuru", "Rift Valley"),
    ("033", "Narok", "Rift Valley"),
    ("034", "Kajiado", "Rift Valley"),
    ("035", "Kericho", "Rift Valley"),
    ("036", "Bomet", "Rift Valley"),
    ("037", "Kakamega", "Western"),
    ("038", "Vihiga", "Western"),
    ("039", "Bungoma", "Western"),
    ("040", "Busia", "Western"),
    ("041", "Siaya", "Nyanza"),
    ("042", "Kisumu", "Nyanza"),
    ("043", "Homa Bay", "Nyanza"),
    ("044", "Migori", "Nyanza"),
    ("045", "Kisii", "Nyanza"),
    ("046", "Nyamira", "Nyanza"),
    ("047", "Nairobi", "Nairobi"),
]

OPTION_SETS = {
    "yes_no": ("Yes / No", [("Yes", "Yes"), ("No", "No")]),
    "medical_insurance": (
        "Medical insurance provided",
        [
            ("Yes", "Yes"),
            ("No", "No"),
            ("Mixed", "Mixed (Partially SHA, Partially Private Insurance)"),
        ],
    ),
    "medical_cover": (
        "How medical cover is arranged",
        [
            ("SHA only", "SHA only"),
            ("Private medical insurance only", "Private medical insurance only"),
            ("Mixed (part SHA, part private insurance)", "Mixed (part SHA, part private insurance)"),
            ("County self-funded / in-house scheme", "County self-funded / in-house scheme"),
            ("Reimbursement of medical bills", "Reimbursement of medical bills"),
            ("Combination of arrangements", "Combination of arrangements"),
            ("Not provided", "Not provided"),
            ("Other", "Other"),
        ],
    ),
    "yes_no_unknown": ("Yes / No / Not known", [("Yes", "Yes"), ("No", "No"), ("Not known", "Not known")]),
    "approved_policy": (
        "Approved remuneration policy",
        [
            ("Yes", "Yes"),
            ("No", "No"),
            ("Under development", "Under development"),
            ("Under review", "Under review"),
        ],
    ),
    "market_position": (
        "Stated market position",
        [
            ("Below market", "Below market"),
            ("Market median / 50th percentile", "Market median / 50th percentile"),
            ("Above market", "Above market"),
            ("Different by job family", "Different by job family"),
            ("Not formally determined", "Not formally determined"),
        ],
    ),
    "progression_factors": (
        "Salary progression factors",
        [
            ("Annual increment", "Annual increment"),
            ("Performance-based", "Performance-based"),
            ("Competency-based", "Competency-based"),
            ("Promotion only", "Promotion only"),
            ("Other", "Other"),
        ],
    ),
    "frequency": (
        "Frequency",
        [
            ("Frequently", "Frequently"),
            ("Sometimes", "Sometimes"),
            ("Rarely", "Rarely"),
            ("Never", "Never"),
        ],
    ),
    "benchmarking_frequency": (
        "External benchmarking frequency",
        [
            ("Regularly", "Regularly"),
            ("Occasionally", "Occasionally"),
            ("Rarely", "Rarely"),
            ("Never", "Never"),
        ],
    ),
    "internal_equity": (
        "Internal equity",
        [
            ("Very equitable", "Very equitable"),
            ("Equitable", "Equitable"),
            ("Moderately equitable", "Moderately equitable"),
            ("Inequitable", "Inequitable"),
            ("Highly inequitable", "Highly inequitable"),
            ("Not Sure", "Not Sure"),
        ],
    ),
    "compression": (
        "Salary compression concern",
        [
            ("Significant", "Significant"),
            ("Moderate", "Moderate"),
            ("Low", "Low"),
            ("None", "None"),
            ("Not known", "Not known"),
        ],
    ),
    "vs_market": (
        "Position versus market",
        [
            ("Significantly below market", "Significantly below market"),
            ("Below market", "Below market"),
            ("Around market median", "Around market median"),
            ("Above market", "Above market"),
            ("Significantly above market", "Significantly above market"),
            ("Not known", "Not known"),
        ],
    ),
    "progression_method": (
        "Annual progression method",
        [
            ("Fixed increment", "Fixed increment"),
            ("Percentage increment", "Percentage increment"),
            ("Performance-based", "Performance-based"),
            ("Not automatic", "Not automatic"),
            ("Other", "Other"),
        ],
    ),
    "affordability": (
        "Ability to fund an increase",
        [
            ("Yes, fully", "Yes, fully"),
            ("Yes, partially", "Yes, partially"),
            ("Only through phased implementation", "Only through phased implementation"),
            ("No", "No"),
            ("Not known", "Not known"),
        ],
    ),
    "implementation_approach": (
        "Implementation approach",
        [
            ("Immediate implementation", "Immediate implementation"),
            ("Phased implementation", "Phased implementation"),
            ("Prioritize lower grades", "Prioritize lower grades"),
            ("Prioritize critical skills", "Prioritize critical skills"),
            ("Across-the-board adjustment", "Across-the-board adjustment"),
            ("Other", "Other"),
        ],
    ),
    "implementation_period": (
        "Implementation period",
        [
            ("1 year", "1 year"),
            ("2 years", "2 years"),
            ("3 years", "3 years"),
            ("4–5 years", "4–5 years"),
            ("Other", "Other"),
        ],
    ),
    "provided": (
        "Provided / received",
        [("Yes", "Yes"), ("No", "No"), ("Partial", "Partial")],
    ),
    "validation_status": (
        "Validation status",
        [
            ("Complete", "Complete"),
            ("Partial", "Partial"),
            ("Outstanding", "Outstanding"),
            ("Not applicable", "Not applicable"),
        ],
    ),
}

FAMILIES = [
    ("governance", "Governance"),
    ("finance", "Finance"),
    ("audit", "Audit"),
    ("hr", "Human Resource"),
    ("legal", "Legal"),
    ("ict", "ICT"),
    ("planning", "Economic Planning"),
    ("health", "Health"),
    ("infrastructure", "Infrastructure"),
    ("agriculture", "Agriculture"),
    ("admin", "Administration"),
    ("support", "Support"),
]

JOB_GROUPS = list("ABCDEFGHJKLMNPQRSTU")

JOBS = [
    (10, "county-secretary", "County Secretary / Head of Public Service", "governance", "S", "SRC-S"),
    (20, "co-finance", "Chief Officer, Finance", "finance", "R", "SRC-R"),
    (30, "co-health", "Chief Officer, Health", "health", "R", "SRC-R"),
    (40, "director-hr", "Director, Human Resource Management", "hr", "P", "SRC-P"),
    (50, "director-finance", "Director, Finance / County Accountant", "finance", "P", "SRC-P"),
    (60, "director-audit", "Director, Internal Audit", "audit", "P", "SRC-P"),
    (70, "county-attorney", "County Attorney", "legal", "P", "SRC-P"),
    (80, "director-planning", "Director, Economic Planning", "planning", "P", "SRC-P"),
    (90, "medical-superintendent", "Medical Superintendent / Medical Officer", "health", "P", "SRC-P"),
    (100, "director-ict", "Director, ICT", "ict", "N", "SRC-N"),
    (110, "county-nursing-officer", "County Nursing Officer", "health", "N", "SRC-N"),
    (120, "principal-hr", "Principal Human Resource Officer", "hr", "N", "SRC-N"),
    (130, "principal-accountant", "Principal Accountant", "finance", "N", "SRC-N"),
    (140, "county-engineer", "County Civil Engineer", "infrastructure", "N", "SRC-N"),
    (150, "economist", "Economist", "planning", "L", "SRC-L"),
    (160, "agricultural-officer", "Agricultural Officer", "agriculture", "L", "SRC-L"),
    (170, "ict-officer", "ICT Officer", "ict", "K", "SRC-K"),
    (180, "accountant-i", "Accountant I", "finance", "K", "SRC-K"),
    (190, "hr-officer-i", "Human Resource Officer I", "hr", "J", "SRC-J"),
    (200, "admin-officer", "Administrative Officer", "admin", "H", "SRC-H"),
    (210, "clerical-officer", "Clerical Officer", "admin", "F", "SRC-F"),
    (220, "driver", "Driver", "support", "D", "SRC-D"),
    (230, "support-staff", "Support Staff / Cleaner", "support", "B", "SRC-B"),
]

BENEFITS = [
    (10, "medical-insurance", "Medical Insurance", False),
    (20, "pension", "Pension", False),
    (30, "group-life", "Group Life Insurance", False),
    (40, "personal-accident", "Personal Accident", False),
    (50, "housing", "Housing", False),
    (60, "transport", "Transport", False),
    (70, "training", "Training/Development", False),
    (80, "staff-welfare", "Staff Welfare", False),
    (90, "annual-leave", "Annual Leave", False),
    (100, "sick-leave", "Sick Leave", False),
    (110, "maternity-leave", "Maternity Leave", False),
    (120, "paternity-leave", "Paternity Leave", False),
    (130, "car-loan", "Car loan", True),
    (140, "house-mortgage", "House mortgage", True),
    (150, "official-car", "Official car", False),
    (160, "domestic-staff", "Domestic staff Allowance", False),
    (170, "entertainment", "Entertainment Allowance", False),
    (180, "extraneous", "Extraneous Allowance", False),
    (190, "meal", "Meal Allowance", False),
    (200, "others", "Others", False),
]

DOCUMENTS = [
    (10, "salary-structure", "Current approved salary structure", False),
    (30, "staff-establishment", "Staff establishment", False),
    (40, "job-grades-families", "Job grades and job families", False),
    (50, "positions-list", "List of positions/designations (The staff establishment)", False),
    (60, "allowance-schedule", "Allowance schedule", False),
    (70, "benefits-schedule", "Employee benefits schedule", False),
    (90, "cba", "Relevant CBA (where applicable)", False),
    (100, "previous-survey", "Previous salary survey/report (if available)", False),
    (110, "pension-arrangements", "Pension arrangements", False),
    (120, "medical-arrangements", "Medical insurance arrangements", False),
    (130, "other-docs", "Other relevant remuneration documents", False),
]

VALIDATIONS = [
    (10, "salary-structure-received", "Salary structure received"),
    (20, "payroll-received", "Payroll data received"),
    (30, "allowances-verified", "Allowances verified"),
    (40, "benefits-verified", "Benefits verified"),
    (50, "job-grades-verified", "Job grades verified"),
    (60, "job-families-verified", "Job families verified"),
    (70, "headcount-reconciled", "Employee numbers reconciled"),
    (80, "basic-reconciled", "Basic salary reconciled with payroll"),
    (90, "allowances-reconciled", "Allowances reconciled with payroll"),
    (100, "outliers", "Outliers identified"),
    (110, "missing-data", "Missing data identified"),
    (120, "clarifications", "Clarifications requested"),
    (130, "validated-by-institution", "Data validated by institution"),
]

COMPARATORS = [
    (10, "src-public-service", "National Public Service / SRC structure", "National government"),
    (20, "state-corporation", "Typical State Corporation", "State corporation"),
    (30, "peer-county", "Peer County Government", "County government"),
]


class Command(BaseCommand):
    help = "Load catalogues, activate the survey period, and create starter accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-data",
            action="store_true",
            help="Add sample Nairobi figures for automated tests.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = settings.BOOTSTRAP_PASSWORD
        self._counties()
        self._options()
        from catalog.question_seed import seed_questions

        seed_questions()
        families, groups, grades = self._jobs()
        self._benefits()
        self._documents()
        self._validations()
        self._comparators()
        period = self._period()
        settings_obj = SiteSettings.load()
        settings_obj.active_survey_period = period
        settings_obj.save()
        users = self._users(password, include_county=options["demo_data"])
        if options["demo_data"]:
            cases = self._cases(period, users["consultant"])
            self._demo_data(cases["nairobi"], period)
        self.stdout.write(self.style.SUCCESS("Bootstrap complete."))
        self.stdout.write("")
        self.stdout.write("Starter accounts:")
        self.stdout.write(f"  admin            / {password}")
        self.stdout.write(f"  admin2           / {password}")
        self.stdout.write(f"  consultant       / {password}")
        self.stdout.write(f"  analyst          / {password}")
        if options["demo_data"]:
            self.stdout.write(f"  county.nairobi   / {password}")
            self.stdout.write(f"  county.mombasa   / {password}")
        self.stdout.write("")
        self.stdout.write("Change these passwords after first sign-in.")

    def _counties(self):
        for i, (code, name, region) in enumerate(COUNTIES, 1):
            County.objects.update_or_create(
                code=code,
                defaults={"name": name, "region": region, "sort_order": i, "is_active": True},
            )

    def _options(self):
        for code, (name, items) in OPTION_SETS.items():
            option_set, _ = OptionSet.objects.update_or_create(code=code, defaults={"name": name})
            keep = []
            for i, (value, label) in enumerate(items, 1):
                OptionItem.objects.update_or_create(
                    option_set=option_set,
                    value=value,
                    defaults={"label": label, "sort_order": i, "is_active": True},
                )
                keep.append(value)
            OptionItem.objects.filter(option_set=option_set).exclude(value__in=keep).update(is_active=False)

    def _jobs(self):
        families = {}
        for i, (code, name) in enumerate(FAMILIES, 1):
            families[code], _ = JobFamily.objects.update_or_create(
                code=code, defaults={"name": name, "sort_order": i, "is_active": True}
            )
        groups = {}
        for i, code in enumerate(JOB_GROUPS, 1):
            groups[code], _ = JobGroup.objects.update_or_create(
                code=code, defaults={"name": f"Job Group {code}", "sort_order": i, "is_active": True}
            )
        grades = {}
        for i, code in enumerate(JOB_GROUPS, 1):
            grades[f"SRC-{code}"], _ = SRCGrade.objects.update_or_create(
                code=f"SRC-{code}",
                defaults={"name": f"SRC Grade {code}", "sort_order": i, "is_active": True},
            )
        for code in ("EX1", "EX2", "EX3", "EX4", "EX5"):
            SRCGrade.objects.update_or_create(
                code=code,
                defaults={"name": f"SRC equivalent {code}", "sort_order": 0, "is_active": True},
            )
        for sort, code, title, family, group, grade in JOBS:
            BenchmarkJob.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "job_family": families[family],
                    "job_group": groups[group],
                    "src_grade": grades[grade],
                    "is_required": True,
                    "is_active": True,
                    "sort_order": sort,
                },
            )
        return families, groups, grades

    def _benefits(self):
        for sort, code, name, interest in BENEFITS:
            BenefitType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "collects_interest": interest,
                    "is_active": True,
                    "sort_order": sort,
                },
            )

    def _documents(self):
        for sort, code, name, required in DOCUMENTS:
            DocumentType.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_required": required, "is_active": True, "sort_order": sort},
            )

    def _validations(self):
        for sort, code, name in VALIDATIONS:
            ValidationItem.objects.update_or_create(
                code=code, defaults={"name": name, "is_active": True, "sort_order": sort}
            )

    def _comparators(self):
        for sort, code, name, sector in COMPARATORS:
            ComparatorOrganization.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "sector": sector,
                    "is_active": True,
                    "include_in_market_median": True,
                    "sort_order": sort,
                },
            )

    def _period(self):
        period, _ = SurveyPeriod.objects.update_or_create(
            code="2026-review",
            defaults={
                "name": "2026 County Salary & Remuneration Review",
                "start_date": date(2026, 8, 1),
                "end_date": date(2026, 12, 31),
                "is_active": True,
                "notes": "Active field collection period for the CPSB-NCF review.",
            },
        )
        return period

    def _users(self, password, include_county=False):
        specs = [
            ("admin", User.Role.ADMIN, None, "Platform", "Administrator", True),
            ("admin2", User.Role.COLLECTION_ADMIN, None, "Collection", "Administrator", False),
            ("consultant", User.Role.CONSULTANT, None, "Field", "Consultant", False),
            ("analyst", User.Role.ANALYST, None, "Survey", "Analyst", False),
        ]
        if include_county:
            nairobi = County.objects.get(name="Nairobi")
            mombasa = County.objects.get(name="Mombasa")
            specs += [
                ("county.nairobi", User.Role.COUNTY, nairobi, "Nairobi", "Respondent", False),
                ("county.mombasa", User.Role.COUNTY, mombasa, "Mombasa", "Respondent", False),
            ]
        users = {}
        for username, role, county, first, last, staff in specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "county": county,
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@dcollect.local",
                    "is_staff": staff,
                    "is_superuser": staff,
                    "must_change_password": False,
                },
            )
            user.role = role
            user.county = county
            user.is_staff = staff or user.is_staff
            user.is_superuser = staff or user.is_superuser
            user.is_active = True
            if created or not user.has_usable_password():
                user.set_password(password)
            user.save()
            users[username] = user
        return users

    def _cases(self, period, consultant):
        created = {}
        for name in ("Nairobi", "Mombasa"):
            county = County.objects.get(name=name)
            case, _ = CountyCase.objects.get_or_create(
                county=county,
                survey_period=period,
                defaults={"assigned_consultant": consultant},
            )
            if not case.assigned_consultant_id:
                case.assigned_consultant = consultant
                case.save(update_fields=["assigned_consultant"])
            ensure_case_structure(case)
            created[name.lower()] = case
        return created

    def _demo_data(self, case, period):
        q = case.questionnaire
        q.department = "County Public Service Board / HRM"
        q.respondent_name = "Jane Wanjiku"
        q.respondent_designation = "Director, Human Resource"
        q.respondent_telephone = "0712 000 000"
        q.respondent_email = "hr@nairobi.go.ke"
        q.permanent_pensionable = 8200
        q.contract_employees = 1400
        q.temporary_casual = 600
        q.other_employees = 80
        q.approved_policy = "Under review"
        q.philosophy_defined = "Yes"
        q.market_position = "Below market"
        q.last_review_year = "2019"
        q.review_triggers = "Inflation, retention of health staff, SRC circulars"
        q.number_of_grades = 18
        q.progression_factors = "Annual increment"
        q.paid_above_maximum = "No"
        q.main_allowances = "House, commuter, leave, extraneous, risk (health)"
        q.remunerative_allowances = "House, commuter, leave, extraneous, risk (health)"
        q.non_remunerative_allowances = "Leave travelling, acting, special duty"
        q.annual_allowance_expenditure = Decimal("2400000000")
        q.medical_insurance = "Yes"
        q.medical_cost_per_employee = Decimal("48000")
        q.pension_employer_pct = Decimal("15.00")
        q.pension_employee_pct = Decimal("7.50")
        q.gratuity_pct = Decimal("31.00")
        q.recruitment_challenges = "Scarce clinical and engineering skills; lengthy clearance; below-market pay."
        q.job_families_recruitment = "Health, Engineering, ICT"
        q.job_families_retention = "Health, Finance"
        q.challenge_reasons = "Below-market pay in scarce skills; slow recruitment cycle"
        q.retention_challenge_reasons = "Better offers in national government and private sector; slow progression"
        q.benchmarking_frequency = "Rarely"
        q.usual_comparators = "SRC, other metro counties, selected state corporations"
        q.internal_equity = "Moderately equitable"
        q.pay_differences = "Yes"
        q.pay_difference_causes = "Historical allowances; some contract conversions"
        q.compression_concern = "Moderate"
        q.compression_grades = "J, K, L"
        q.basic_vs_market = "Below market"
        q.benefits_vs_market = "Around market median"
        q.categories_below_market = "Medical officers, engineers, ICT"
        q.categories_above_market = "Some support cadres in selected units"
        q.basic_pct = Decimal("62.00")
        q.allowances_pct = Decimal("30.00")
        q.other_cash_pct = Decimal("8.00")
        q.progression_method = "Fixed increment"
        q.avg_years_in_grade = Decimal("4.0")
        q.placement_factors = "Entry qualification, years of service, SRC grade"
        q.personnel_pct_budget = Decimal("48.00")
        q.can_accommodate_increase = "Only through phased implementation"
        q.implementation_approach = "Phased implementation"
        q.implementation_period = "3 years"
        q.priority_categories = "Lower grades and scarce health skills, because turnover and attraction gaps are largest there."
        q.salary_structure_attached = "Yes"
        q.payroll_extract_attached = "Yes"
        q.allowance_schedule_attached = "Yes"
        q.benefits_schedule_attached = "Yes"
        q.hr_policy_attached = "Yes"
        q.previous_survey_attached = "No"
        q.three_challenges = "Compression in mid grades; scarce skills; allowance dependence"
        q.three_recommendations = "Rebuild structure; target scarce skills; phase over 3 years"
        q.save()

        samples = {
            "county-secretary": (180000, 250000, 60000, 20000, 8000, 15000),
            "co-finance": (144000, 196000, 50000, 16000, 6000, 10000),
            "director-hr": (98000, 134000, 35000, 12000, 4000, 6000),
            "director-finance": (98000, 134000, 35000, 12000, 4000, 6000),
            "medical-superintendent": (120000, 172000, 40000, 14000, 4000, 12000),
            "principal-accountant": (58000, 82000, 20000, 8000, 2000, 3000),
            "economist": (42000, 62000, 16000, 6000, 1500, 2000),
            "ict-officer": (36000, 52000, 12000, 5000, 1500, 1500),
            "admin-officer": (28000, 40000, 10000, 4000, 0, 1000),
            "clerical-officer": (18000, 26000, 6500, 3000, 0, 500),
            "driver": (14000, 20000, 5000, 3000, 0, 0),
        }
        group_samples = {
            "S": (180000, 240000, 50000, 16000, 6000, 10000),
            "R": (144000, 196000, 50000, 16000, 6000, 10000),
            "P": (98000, 134000, 35000, 12000, 4000, 6000),
            "N": (58000, 82000, 20000, 8000, 2000, 3000),
            "L": (42000, 62000, 16000, 6000, 1500, 2000),
        }
        for row in case.job_rows.select_related("job_group"):
            payload = group_samples.get(row.job_group.code)
            if not payload:
                continue
            row.min_basic, row.max_basic, row.house_allowance, row.commuter_allowance, row.airtime, row.other_allowances = [
                Decimal(v) for v in payload
            ]
            row.src_equivalent = f"EX-{row.job_group.code}"
            row.median_basic = (row.min_basic + row.max_basic) / Decimal("2")
            row.save()

        for row in case.benefit_rows.select_related("benefit"):
            if row.benefit.code in {"medical-insurance", "pension", "annual-leave", "sick-leave", "maternity-leave", "paternity-leave"}:
                row.provided = "Yes"
            elif row.benefit.code in {"car-loan", "house-mortgage"}:
                row.provided = "Partial"
                row.interest_charged = "Preferential"
            else:
                row.provided = "No"
            row.save()

        org = ComparatorOrganization.objects.get(code="src-public-service")
        for job in BenchmarkJob.objects.filter(is_active=True):
            ComparatorPayRow.objects.update_or_create(
                organization=org,
                survey_period=period,
                job=job,
                defaults={
                    "min_basic": Decimal("90000"),
                    "max_basic": Decimal("120000"),
                    "median_basic": Decimal("105000"),
                },
            )
        org2 = ComparatorOrganization.objects.get(code="state-corporation")
        for job in BenchmarkJob.objects.filter(is_active=True):
            ComparatorPayRow.objects.update_or_create(
                organization=org2,
                survey_period=period,
                job=job,
                defaults={
                    "min_basic": Decimal("100000"),
                    "max_basic": Decimal("140000"),
                    "median_basic": Decimal("120000"),
                },
            )
        link = ensure_staff_link(case.county, period)
        jobs_by_code = {job.code: job for job in BenchmarkJob.objects.filter(is_active=True)}
        staff_samples = [
            ("county-secretary", Decimal("205000"), Decimal("60000"), Decimal("20000")),
            ("county-secretary", Decimal("218000"), Decimal("60000"), Decimal("20000")),
            ("director-hr", Decimal("110000"), Decimal("35000"), Decimal("12000")),
            ("director-hr", Decimal("118000"), Decimal("35000"), Decimal("12000")),
            ("ict-officer", Decimal("41000"), Decimal("12000"), Decimal("5000")),
            ("ict-officer", Decimal("47000"), Decimal("12000"), Decimal("5000")),
            ("ict-officer", Decimal("39000"), Decimal("12000"), Decimal("5000")),
        ]
        for code, basic, house, commuter in staff_samples:
            job = jobs_by_code.get(code)
            if not job:
                continue
            IndividualResponse.objects.create(
                link=link,
                county=case.county,
                survey_period=period,
                job=job,
                job_title=job.title,
                department="County Public Service",
                employment_type=IndividualResponse.EmploymentType.PERMANENT,
                current_basic=basic,
                house_allowance=house,
                commuter_allowance=commuter,
            )
        self.stdout.write("Sample Nairobi and comparator figures loaded.")
