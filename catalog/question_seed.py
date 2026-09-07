"""Seed built-in questionnaire questions from the survey spec. Safe to run again."""


OPTION_SET_SPECS = {
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
}


def input_type_for(code):
    from collection.questionnaire_spec import (
        CHOICE_SETS,
        INTEGER_FIELDS,
        MONEY_FIELDS,
        PERCENT_FIELDS,
        TEXTAREA_FIELDS,
    )

    if code in INTEGER_FIELDS:
        return "integer"
    if code in MONEY_FIELDS:
        return "money"
    if code in PERCENT_FIELDS:
        return "percent"
    if code in CHOICE_SETS:
        return "choice"
    if code in TEXTAREA_FIELDS:
        return "textarea"
    if code == "last_review_year":
        return "year"
    if code == "respondent_email":
        return "email"
    if code == "respondent_telephone":
        return "tel"
    if code == "avg_years_in_grade":
        return "decimal"
    return "text"


def seed_option_sets():
    from .models import OptionItem, OptionSet

    specs = {}
    try:
        from catalog.management.commands.bootstrap import OPTION_SETS

        specs.update(OPTION_SETS)
    except Exception:
        pass
    specs.update(OPTION_SET_SPECS)
    for code, (name, items) in specs.items():
        option_set, _ = OptionSet.objects.update_or_create(code=code, defaults={"name": name})
        keep = []
        for index, (value, label) in enumerate(items, 1):
            OptionItem.objects.update_or_create(
                option_set=option_set,
                value=value,
                defaults={"label": label, "sort_order": index, "is_active": True},
            )
            keep.append(value)
        # Do not deactivate custom extras the administrator added to a list.
        OptionItem.objects.filter(option_set=option_set, value__in=keep).update(is_active=True)


def seed_questions():
    from collection.questionnaire_spec import (
        CHOICE_SETS,
        HELP,
        LABELS,
        RETIRED_CODES,
        SECTION_FIELDS,
        SECTION_TITLES,
    )

    from .models import OptionSet, QuestionItem

    seed_option_sets()
    option_sets = {item.code: item for item in OptionSet.objects.all()}
    created = 0
    for section, codes in SECTION_FIELDS.items():
        for index, code in enumerate(codes, 1):
            defaults = {
                "section": section,
                "label": LABELS.get(code, code.replace("_", " ").title()),
                "help_text": HELP.get(code, ""),
                "input_type": input_type_for(code),
                "option_set": option_sets.get(CHOICE_SETS.get(code, "")),
                "is_required": False,
                "is_active": True,
                "is_builtin": True,
                "sort_order": index * 10,
            }
            obj, was_created = QuestionItem.objects.get_or_create(code=code, defaults=defaults)
            if was_created:
                created += 1
            elif obj.is_builtin and not obj.option_set_id and defaults.get("option_set"):
                obj.option_set = defaults["option_set"]
                obj.save(update_fields=["option_set"])
    if RETIRED_CODES:
        QuestionItem.objects.filter(code__in=RETIRED_CODES, is_builtin=True).update(is_active=False)
    return created, SECTION_TITLES


def apply_questionnaire_copy():
    """One-off wording, order and option-set updates for the current survey form."""
    from collection.questionnaire_spec import (
        CHOICE_SETS,
        HELP,
        LABELS,
        RETIRED_CODES,
        SECTION_FIELDS,
    )

    from .models import OptionSet, QuestionItem

    seed_questions()
    option_sets = {item.code: item for item in OptionSet.objects.all()}
    for section, codes in SECTION_FIELDS.items():
        for index, code in enumerate(codes, 1):
            QuestionItem.objects.filter(code=code, is_builtin=True).update(
                section=section,
                label=LABELS.get(code, code.replace("_", " ").title()),
                help_text=HELP.get(code, ""),
                input_type=input_type_for(code),
                option_set=option_sets.get(CHOICE_SETS.get(code, "")),
                sort_order=index * 10,
                is_active=True,
            )
    if RETIRED_CODES:
        QuestionItem.objects.filter(code__in=RETIRED_CODES, is_builtin=True).update(is_active=False)
