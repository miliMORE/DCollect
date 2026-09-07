"""Questionnaire section titles and field labels."""

SECTION_TITLES = {
    "a": "SECTION A: INSTITUTION & RESPONDENT INFORMATION",
    "b": "SECTION B: WORKFORCE PROFILE",
    "c": "SECTION C: REMUNERATION POLICY & PHILOSOPHY",
    "d": "SECTION D: SALARY STRUCTURE",
    "e": "SECTION E: ALLOWANCES & BENEFITS",
    "f": "SECTION F: RECRUITMENT, RETENTION & MARKET COMPETITIVENESS",
    "g": "SECTION G: INTERNAL & EXTERNAL EQUITY",
    "h": "SECTION H: PAY MIX & PROGRESSION",
    "i": "SECTION I: AFFORDABILITY & IMPLEMENTATION",
    "j": "SECTION J: DOCUMENTS & KEY OBSERVATIONS",
}

INTRO = "Complete one questionnaire per County Government."

LABELS = {
    "department": "Department / Directorate / Unit",
    "respondent_name": "Respondent Name (Confidential For Consultant's Use only)",
    "respondent_designation": "Designation (Confidential For Consultant's Use only)",
    "respondent_telephone": "Telephone (For Consultant's use only)",
    "respondent_email": "Email (For Consultant's use only)",
    "permanent_pensionable": "No Permanent & Pensionable Employees",
    "contract_employees": "No of Contract Employees",
    "temporary_casual": "No of Temporary/Casual Employees",
    "other_employees": "Other Employees",
    "approved_policy": "Do you have an Approved Remuneration/Compensation Policy?",
    "philosophy_defined": "Is your Compensation philosophy formally defined?",
    "market_position": "What is your market position?",
    "last_review_year": "Which Year was remuneration structure last reviewed",
    "review_triggers": "What were the main triggers for salary review eg Inflation",
    "number_of_grades": "Number of salary grades in your organization",
    "progression_factors": "Factors contributing to Salary progression eg Annual Increment",
    "progression_factors_notes": "If Other, specify the factors contributing to salary progression",
    "paid_above_maximum": "Are there situations when Employees are paid above maximum?",
    "paid_above_maximum_why": "If Yes, why?",
    "main_allowances": "Main allowances provided",
    "remunerative_allowances": "Remunerative Allowances (Paid monthly)",
    "non_remunerative_allowances": "Non-Remunerative allowances",
    "annual_allowance_expenditure": "Approx. annual allowance expenditure (KES)",
    "medical_insurance": "Medical insurance provided?",
    "medical_cover_how": "How is medical cover arranged for employees?",
    "medical_cover_notes": (
        "Explain how medical insurance is handled (who is covered, SHA vs private, "
        "in-patient/out-patient, contributions, and any exceptions)"
    ),
    "medical_cost_per_employee": "Annual employer medical cost per employee (KES)",
    "pension_employer_pct": "Pension employer contribution (%)",
    "pension_employee_pct": "Pension employee contribution (%)",
    "gratuity_pct": "Gratuity (%):",
    "other_significant_benefits": "Other significant benefits",
    "recruitment_challenges": "Challenges affecting Recruitment",
    "job_families_recruitment": "Job families with greatest recruitment challenges (Difficult to get the right candidates)",
    "job_families_retention": "Job families with greatest retention challenges",
    "challenge_reasons": "Main reasons for recruitment challenges",
    "retention_challenge_reasons": "Main reasons for retention challenges",
    "benchmarking_frequency": "External salary benchmarking frequency ie After how long do you do external salary benchmarking?",
    "usual_comparators": "Usual comparator organizations",
    "internal_equity": "Overall internal equity assessment (Equal pay for work of equal value)",
    "pay_differences": "Are there Significant pay differences for similar work?",
    "pay_difference_causes": (
        "Main causes of pay differences (If Yes in the above, what are the causes of pay differentials?)"
    ),
    "compression_concern": (
        "Level of salary compression concern ie employees with different levels of experience, "
        "responsibility, or seniority have salaries that are too close together. "
        "(The Concern: No concern (1)  Low concern (2)  Moderate concern (3)  "
        "High concern (4)  Very high concern (5)"
    ),
    "compression_grades": "Grades with greatest compression eg Grades 4, 5 and 6.",
    "basic_vs_market": (
        "Basic salary position vs similar public sector organizations "
        "(Much lower; Lower; About the same; Higher; Much higher; Don’t know)"
    ),
    "benefits_vs_market": "Benefits position vs similar organizations",
    "categories_below_market": "Job categories likely below market",
    "categories_above_market": "Job categories likely above market",
    "basic_pct": "Basic salary as % of cash remuneration ((Basic Salary ÷ Total Cash Remuneration) × 100)",
    "allowances_pct": "Allowances as % of cash remuneration",
    "other_cash_pct": "Other cash payments as % ((Other Cash Payments ÷ Total Cash Payments) x100)",
    "progression_method": "Annual salary progression method",
    "avg_years_in_grade": "Average years in a salary grade",
    "placement_factors": "What Factors do determining salary placement?",
    "personnel_pct_budget": "Personnel/remuneration expenditure as % of budget",
    "can_accommodate_increase": "Can County accommodate general remuneration increase of about 15%?",
    "implementation_approach": "Most sustainable implementation approach",
    "implementation_period": "Preferred implementation period",
    "priority_categories": (
        "Given budget constraints, which category of employees would you prioritize for salary increase? and why?"
    ),
    "salary_structure_attached": "Current salary structure attached?",
    "payroll_extract_attached": "Payroll extract attached?",
    "allowance_schedule_attached": "Allowance schedule attached?",
    "benefits_schedule_attached": "Benefits schedule attached?",
    "hr_policy_attached": "HR/Remuneration policy attached?",
    "previous_survey_attached": "Previous salary survey attached?",
    "three_challenges": "Three key remuneration challenges",
    "three_recommendations": "Three recommended changes",
    "other_comments": "Other issues/comments",
}

HELP = {
    "respondent_name": "Confidential. For the consultant’s use only.",
    "respondent_designation": "Confidential. For the consultant’s use only.",
    "respondent_telephone": "Confidential. For the consultant’s use only.",
    "respondent_email": "Use a valid email address. Confidential — consultant use only.",
    "permanent_pensionable": "Whole number. Zero if none.",
    "contract_employees": "Whole number. Zero if none.",
    "temporary_casual": "Whole number. Zero if none.",
    "other_employees": "Whole number. Zero if none.",
    "last_review_year": "Four-digit year, for example 2019.",
    "annual_allowance_expenditure": "Kenya Shillings. Do not use commas.",
    "medical_cost_per_employee": "Kenya Shillings per employee per year.",
    "medical_cover_how": "Counties handle medical cover differently. Pick the arrangement that best matches this county.",
    "medical_cover_notes": "Use this if cover is mixed, combined, or Other, or to describe who is included.",
    "pension_employer_pct": "Number from 0 to 100.",
    "pension_employee_pct": "Number from 0 to 100.",
    "gratuity_pct": "Number from 0 to 100.",
    "remunerative_allowances": "Allowances paid monthly as part of remuneration.",
    "non_remunerative_allowances": "Allowances that are not paid monthly as part of regular remuneration.",
    "recruitment_challenges": "Describe the challenges that affect recruitment.",
    "basic_pct": "Number from 0 to 100. Together with allowances and other cash this should add to 100.",
    "allowances_pct": "Number from 0 to 100.",
    "other_cash_pct": "Number from 0 to 100.",
    "personnel_pct_budget": "Number from 0 to 100.",
    "avg_years_in_grade": "For example 4 or 4.5.",
    "number_of_grades": "Whole number of salary grades.",
    "salary_structure_attached": "Also upload the file on the Documents tab.",
    "payroll_extract_attached": "Also upload the file on the Documents tab.",
    "allowance_schedule_attached": "Also upload the file on the Documents tab.",
    "benefits_schedule_attached": "Also upload the file on the Documents tab.",
    "hr_policy_attached": "Also upload the file on the Documents tab.",
    "previous_survey_attached": "Also upload the file on the Documents tab if Yes.",
}

CHOICE_SETS = {
    "approved_policy": "approved_policy",
    "philosophy_defined": "yes_no",
    "market_position": "market_position",
    "progression_factors": "progression_factors",
    "paid_above_maximum": "yes_no",
    "medical_insurance": "medical_insurance",
    "medical_cover_how": "medical_cover",
    "benchmarking_frequency": "benchmarking_frequency",
    "internal_equity": "internal_equity",
    "pay_differences": "yes_no_unknown",
    "basic_vs_market": "vs_market",
    "benefits_vs_market": "vs_market",
    "progression_method": "progression_method",
    "can_accommodate_increase": "affordability",
    "implementation_approach": "implementation_approach",
    "implementation_period": "implementation_period",
    "salary_structure_attached": "yes_no",
    "payroll_extract_attached": "yes_no",
    "allowance_schedule_attached": "yes_no",
    "benefits_schedule_attached": "yes_no",
    "hr_policy_attached": "yes_no",
    "previous_survey_attached": "yes_no",
}

INTEGER_FIELDS = {
    "permanent_pensionable",
    "contract_employees",
    "temporary_casual",
    "other_employees",
    "number_of_grades",
}

MONEY_FIELDS = {
    "annual_allowance_expenditure",
    "medical_cost_per_employee",
}

TEXTAREA_FIELDS = {
    "review_triggers",
    "progression_factors_notes",
    "paid_above_maximum_why",
    "main_allowances",
    "remunerative_allowances",
    "non_remunerative_allowances",
    "medical_cover_notes",
    "other_significant_benefits",
    "recruitment_challenges",
    "job_families_recruitment",
    "job_families_retention",
    "challenge_reasons",
    "retention_challenge_reasons",
    "usual_comparators",
    "pay_difference_causes",
    "categories_below_market",
    "categories_above_market",
    "placement_factors",
    "priority_categories",
    "three_challenges",
    "three_recommendations",
    "other_comments",
}

PERCENT_FIELDS = {
    "pension_employer_pct",
    "pension_employee_pct",
    "gratuity_pct",
    "basic_pct",
    "allowances_pct",
    "other_cash_pct",
    "personnel_pct_budget",
}

SECTION_FIELDS = {
    "a": [
        "department",
        "respondent_name",
        "respondent_designation",
        "respondent_telephone",
        "respondent_email",
    ],
    "b": [
        "permanent_pensionable",
        "contract_employees",
        "temporary_casual",
        "other_employees",
    ],
    "c": [
        "approved_policy",
        "philosophy_defined",
        "market_position",
        "last_review_year",
        "review_triggers",
    ],
    "d": [
        "number_of_grades",
        "progression_factors",
        "progression_factors_notes",
        "paid_above_maximum",
        "paid_above_maximum_why",
    ],
    "e": [
        "remunerative_allowances",
        "non_remunerative_allowances",
        "annual_allowance_expenditure",
        "medical_insurance",
        "medical_cover_how",
        "medical_cover_notes",
        "medical_cost_per_employee",
        "pension_employer_pct",
        "pension_employee_pct",
        "gratuity_pct",
        "other_significant_benefits",
    ],
    "f": [
        "recruitment_challenges",
        "job_families_recruitment",
        "job_families_retention",
        "challenge_reasons",
        "retention_challenge_reasons",
        "benchmarking_frequency",
        "usual_comparators",
    ],
    "g": [
        "internal_equity",
        "pay_differences",
        "pay_difference_causes",
    ],
    "h": [
        "basic_pct",
        "allowances_pct",
        "other_cash_pct",
        "progression_method",
        "avg_years_in_grade",
        "placement_factors",
    ],
    "i": [
        "personnel_pct_budget",
        "can_accommodate_increase",
        "implementation_approach",
        "implementation_period",
        "priority_categories",
    ],
    "j": [
        "salary_structure_attached",
        "allowance_schedule_attached",
        "benefits_schedule_attached",
        "previous_survey_attached",
        "three_challenges",
        "three_recommendations",
        "other_comments",
    ],
}

RETIRED_CODES = {
    "main_allowances",
    "compression_concern",
    "compression_grades",
    "basic_vs_market",
    "benefits_vs_market",
    "categories_below_market",
    "categories_above_market",
    "payroll_extract_attached",
    "hr_policy_attached",
}

GROUP_HEADINGS = {
    "remunerative_allowances": "Main allowances",
}
