"""Build the official DCollect user manual PDF."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "DCollect-User-Manual.pdf"
DESKTOP = Path.home() / "Desktop" / "DCollect User Manual.pdf"
LOGO = ROOT / "static" / "brand" / "logo.png"
SHOTS = ROOT / "docs" / "manual-screens"

NAVY = colors.HexColor("#1B2A4A")
GOLD = colors.HexColor("#C6A15B")
INK = colors.HexColor("#161410")
MUTED = colors.HexColor("#6B6256")
PAPER = colors.HexColor("#F4EFE6")
LINE = colors.HexColor("#C5BBA8")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"], fontName="Times-Bold",
            fontSize=11, textColor=GOLD, alignment=TA_CENTER, spaceAfter=4,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Times-Bold",
            fontSize=28, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6, leading=32,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontName="Times-Roman",
            fontSize=13, textColor=INK, alignment=TA_CENTER, spaceAfter=4, leading=18,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta", parent=base["Normal"], fontName="Times-Italic",
            fontSize=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=3, leading=14,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Times-Bold",
            fontSize=16, textColor=NAVY, spaceBefore=4, spaceAfter=10, leading=20,
            borderPadding=3,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Times-Bold",
            fontSize=13, textColor=NAVY, spaceBefore=12, spaceAfter=6, leading=16,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"], fontName="Times-Bold",
            fontSize=11.5, textColor=NAVY, spaceBefore=8, spaceAfter=4, leading=14,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, textColor=INK, alignment=TA_JUSTIFY, leading=14,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"], fontName="Times-Italic",
            fontSize=8.5, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3,
            spaceAfter=12, leading=11,
        ),
        "toc": ParagraphStyle(
            "toc", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10.5, textColor=INK, leading=16, spaceAfter=2,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontName="Times-Bold",
            fontSize=8.5, textColor=WHITE, leading=11,
        ),
        "td": ParagraphStyle(
            "td", parent=base["Normal"], fontName="Times-Roman",
            fontSize=8.5, textColor=INK, leading=11,
        ),
        "step": ParagraphStyle(
            "step", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, textColor=INK, leading=14, leftIndent=4, spaceAfter=3,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Times-Roman",
            fontSize=8, textColor=MUTED, alignment=TA_CENTER,
        ),
        "warn": ParagraphStyle(
            "warn", parent=base["Normal"], fontName="Times-Roman",
            fontSize=10, textColor=INK, leading=14, spaceAfter=8,
            leftIndent=6, rightIndent=6, backColor=PAPER, borderPadding=6,
        ),
    }
    return s


S = styles()


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items):
    flow = []
    for item in items:
        flow.append(
            ListItem(P(item, "step"), leftIndent=12, bulletColor=NAVY, value="bullet")
        )
    return ListFlowable(flow, bulletType="bullet", start="•", leftIndent=16, spaceAfter=8)


def steps(items):
    flow = []
    for i, item in enumerate(items, 1):
        flow.append(ListItem(P(item, "step"), leftIndent=14, value=str(i)))
    return ListFlowable(flow, bulletType="1", leftIndent=18, spaceAfter=8)


def grid(headers, rows, widths):
    th = [P(h, "th") for h in headers]
    data = [th]
    for row in rows:
        data.append([P(c, "td") for c in row])
    t = Table(data, colWidths=widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), PAPER))
    t.setStyle(TableStyle(style_cmds))
    return t


def shot(filename, caption, width=160 * mm):
    path = SHOTS / filename
    if not path.exists():
        return []
    img = Image(str(path))
    iw, ih = img.imageWidth, img.imageHeight
    img.drawWidth = width
    img.drawHeight = width * ih / iw
    img.hAlign = "CENTER"
    return [Spacer(1, 4), img, P(caption, "caption")]


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, PAGE_H - 12.8 * mm, PAGE_W, 1.6 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Times-Bold", 9)
    canvas.drawString(MARGIN, PAGE_H - 8 * mm, "DCollect user manual")
    canvas.setFont("Times-Roman", 8)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 8 * mm, "Confidential — authorised survey users")
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.rect(0, 12 * mm, PAGE_W, 1.2 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(MARGIN, 5 * mm, "County Public Service Salary & Remuneration Review")
    canvas.drawRightString(PAGE_W - MARGIN, 5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def cover_page():
    story = [Spacer(1, 18 * mm)]
    if LOGO.exists():
        logo = Image(str(LOGO), width=22 * mm, height=22 * mm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 8 * mm))
    story += [
        P("COUNTY PUBLIC SERVICE BOARD NATIONAL CONSULTATIVE FORUM", "cover_kicker"),
        P("DCollect", "cover_title"),
        P("USER MANUAL", "cover_kicker"),
        Spacer(1, 6 * mm),
        P("County Public Service Salary and Remuneration Survey Platform", "cover_sub"),
        P("Implemented by BINSTOPEJ Management Solutions Ltd", "cover_meta"),
        P("Version 2.0  ·  August 2026  ·  Confidential", "cover_meta"),
        Spacer(1, 10 * mm),
        grid(
            ["Field", "Detail"],
            [
                ["Document title", "DCollect User Manual (PDF)"],
                ["Audience", "Administrators, collection staff, consultants, analysts and county respondents"],
                ["Classification", "Confidential — for authorised survey users only"],
                ["Applies to", "DCollect web application for the 2026 CPSB-NCF review"],
                ["How to obtain", "Platform administrator: left menu → User manual (PDF)"],
            ],
            [45 * mm, 120 * mm],
        ),
        Spacer(1, 8 * mm),
        P(
            "This manual describes how to sign in, configure the survey, complete a county file, "
            "review submissions, download collected data and analyse market position. Menu names "
            "match the live application. Figures illustrate typical screens; wording on a live "
            "site may differ slightly by role and period.",
        ),
        P(
            "Information entered in DCollect is confidential and is used solely for the Salary "
            "and Remuneration Review. Institution-level data that is commercially or "
            "administratively sensitive may be reported in aggregated form.",
        ),
    ]
    return story


def build_story():
    usable = PAGE_W - 2 * MARGIN
    story = []
    story += cover_page()
    story.append(PageBreak())

    story += [
        P("1. Contents", "h1"),
        P("1. Purpose of DCollect", "toc"),
        P("2. Roles and left-hand menu", "toc"),
        P("3. Signing in and moving around", "toc"),
        P("4. County respondent — completing a file", "toc"),
        P("5. Questionnaire sections A–J", "toc"),
        P("6. Jobs, benefits and documents", "toc"),
        P("7. Submit, clarification and validation", "toc"),
        P("8. Consultants, comparators and staff links", "toc"),
        P("9. Analysis and reports", "toc"),
        P("10. Administrator setup, users, audit and data", "toc"),
        P("11. Installing or updating DCollect", "toc"),
        P("12. If something will not work", "toc"),
        PageBreak(),
    ]

    story += [
        P("1. Purpose of DCollect", "h1"),
        P(
            "DCollect is the field collection and analysis application for the County Public "
            "Service Salary and Remuneration Review commissioned by the County Public Service "
            "Board National Consultative Forum (CPSB-NCF) and undertaken by BINSTOPEJ Management "
            "Solutions Ltd. It captures <b>one institutional file per County Government</b> for "
            "the active survey period, together with supporting documents, optional individual "
            "staff responses, and comparator organisation pay. It then produces market position "
            "tables and Excel extracts."
        ),
        P("1.1 What the platform does", "h2"),
        bullets([
            "Opens a county file for the active survey period.",
            "Collects the institutional questionnaire (sections A–J), job-group pay, the benefits matrix and uploads.",
            "Locks a file after submit, and reopens only the modules named in a clarification.",
            "Records consultant validation and an activity history on each file.",
            "Collects comparator organisation pay on the same job catalogue.",
            "Accepts staff survey forms through a unique link, tagged to a county.",
            "Calculates county and market percentiles (P25 / P50 / P75) and issues workbooks and a complete county zip.",
        ]),
        P("1.2 Confidentiality", "h2"),
        P(
            "Respondent name, designation, telephone and email on the institutional questionnaire "
            "are for the consultant’s use only. Staff survey name and email are optional. Uploaded "
            "files are not public: they are downloaded from the county file after sign-in. Do not "
            "circulate passwords, staff survey links beyond the intended audience, or county packs "
            "outside the review team."
        ),
        PageBreak(),
    ]

    story += [
        P("2. Roles and left-hand menu", "h1"),
        P(
            "Sign in with the account issued to you. The left-hand menu shows only the work for "
            "that role. If a page is missing, it is not part of your role."
        ),
        grid(
            ["Role", "Fresh-install login", "Principal work"],
            [
                ["Administrator", "admin", "Owns site identity, audit trail and data reset. Can do everything else as well."],
                ["Collection administrator", "admin2", "Periods, catalogues, forms, users and county files. Cannot open the audit trail or reset all data."],
                ["Field consultant", "consultant", "Reviews files, validation, clarifications and comparators."],
                ["Analyst", "analyst", "Analysis and Reports. Does not fill or certify county files."],
                ["County respondent", "created under Users", "Completes one county’s file. Cannot open another county."],
            ],
            [42 * mm, 42 * mm, 81 * mm],
        ),
        P("Table 1. Roles. Change starter passwords at first sign-in. Default password on a fresh install is ChangeMe!2026 unless BOOTSTRAP_PASSWORD is set.", "caption"),
        P("2.1 What each person sees in the left menu", "h2"),
        grid(
            ["Menu item", "Who sees it", "Opens"],
            [
                ["Dashboard", "Everyone", "Greeting, next step, counts and shortcuts."],
                ["My county file / Clarifications", "County respondent", "That county’s file only."],
                ["County files / Questionnaires", "Admin, collection admin, consultant, analyst", "Files in the active period."],
                ["Staff survey links", "Admin, collection admin", "Public and per-county staff form URLs."],
                ["Comparators / Analysis / Reports", "Admin, collection admin, consultant, analyst", "Market input and outputs."],
                ["Variables &amp; settings, Forms &amp; questions, Users", "Admin, collection admin", "Setup."],
                ["Audit trail / Data administration / User manual (PDF)", "Platform administrator only", "Who did what, destructive tools, this manual."],
                ["What I need to do", "Everyone except collection administrator", "Short in-app checklist."],
                ["Change password / Sign out", "Everyone", "Account security."],
            ],
            [52 * mm, 55 * mm, 58 * mm],
        ),
        P("Table 2. Navigation. Collection administrators do not see Audit trail, Data administration or the PDF manual.", "caption"),
        *shot("02-dashboard.jpg", "Figure 1. Administrator dashboard and left-hand menu (illustrative layout)."),
        PageBreak(),
    ]

    story += [
        P("3. Signing in and moving around", "h1"),
        P("3.1 Sign in", "h2"),
        steps([
            "Open the survey address in a browser (local test: http://127.0.0.1:8000/).",
            "Enter the username and password issued to you, then choose <b>Enter workspace</b>.",
            "If the account must change password, DCollect opens Change password first. The new password must be at least 10 characters.",
            "Use <b>Change password</b> at any later time from the bottom of the left menu.",
            "Choose <b>Sign out</b> when you finish. The session also ends after <b>10 minutes without activity</b>. You will see a notice on the sign-in page. Idle sign-out is written to the audit trail.",
        ]),
        *shot("01-sign-in.jpg", "Figure 2. Sign-in screen. After idle sign-out the same page explains that you must sign in again."),
        P("3.2 Screen layout", "h2"),
        bullets([
            "<b>Left menu</b> — role-specific links. On a small screen, use Menu.",
            "<b>Top bar</b> — breadcrumb, page title, and the active survey period.",
            "<b>Main area</b> — the work for that page.",
            "<b>Gold buttons</b> — the primary action (Save, Submit, Download complete file). Ghost buttons are secondary.",
        ]),
        P("3.3 Inside a county file", "h2"),
        P(
            "Open a file from Dashboard, County files, or My county file. A horizontal file menu "
            "is always available at the top of the file:"
        ),
        grid(
            ["Tab", "Purpose"],
            [
                ["Overview", "Status, progress, assignment, certify / submit / validate / return, activity."],
                ["Questionnaire", "Institutional form, sections A–J. Save each section."],
                ["Jobs", "Pay by job group A–U (excluding I and O)."],
                ["Benefits", "Provided? Interest charged? Eligibility and comments."],
                ["Documents", "Uploads. Several files per heading. Optional items may be Not available."],
                ["Certify", "Name, designation, initials. Date is stored automatically."],
                ["Clarifications", "Reviewer questions and county answers."],
                ["Individual responses", "Staff who used the county survey link."],
                ["Validation", "Consultant quality checklist (reviewers only)."],
            ],
            [42 * mm, 123 * mm],
        ),
        P("Table 3. County file tabs.", "caption"),
        *shot("03-county-overview.jpg", "Figure 3. County file Overview: progress cards, file tabs, and Download complete file."),
        PageBreak(),
    ]

    story += [
        P("4. County respondent — completing a file", "h1"),
        P(
            "You work only on your county. Keep the approved salary structure and the allowance "
            "and benefits schedules beside you. Amounts are Kenya shillings, monthly, without "
            "thousands separators in number fields."
        ),
        P("4.1 Order of work", "h2"),
        steps([
            "<b>Dashboard</b> → <b>Open file</b> (or <b>My county file</b>). If a Next step box is showing, start there.",
            "<b>Questionnaire</b> — sections A to J. Save a section before leaving it (<b>Save this section</b> or <b>Save and continue</b>).",
            "<b>Jobs</b> — one row per job group A–U excluding I and O. Mark N/A if the county does not use that group. Enter SRC equivalent as free text (for example EX4), then min basic, max basic, house, commuter, airtime and Total of Other Allowances.",
            "<b>Benefits</b> — Provided? Yes / No / Partial; Interest charged? Yes / No on every row (leave blank if interest does not apply); eligibility; comments.",
            "<b>Documents</b> — upload the file or files for each heading. A required heading needs at least one file. Optional headings may be ticked Not available. Several files are allowed under one heading (for example more than one salary structure).",
            "<b>Certify</b> — name, designation, initials.",
            "<b>Overview</b> → <b>Submit for review</b>. After submit you cannot edit until a reviewer returns the file.",
            "If <b>Clarifications</b> appear, answer each one, correct only the unlocked section(s), certify if needed, and submit again.",
        ]),
        P("4.2 Progress percentages", "h2"),
        P(
            "Overview percentages measure <b>what has actually been filled or uploaded</b>. An empty "
            "file shows 0%, not 100%. Questionnaire counts answered questions. Jobs count a row "
            "when it is N/A or when both min and max basic are entered. Benefits count a row when "
            "Provided? is answered (and Interest charged? when the benefit is a loan-type item "
            "marked Yes or Partial). Documents count a heading when a file is present, or when an "
            "optional heading is marked Not available. Items marked Required still control whether "
            "you can submit; optional blanks do not inflate the percentage."
        ),
        P("4.3 After submit", "h2"),
        P(
            "The file is locked. You can still read it. On Overview use <b>Download complete file</b> "
            "for one zip that contains the county workbook and every uploaded document in folders. "
            "<b>Workbook only</b> is the Excel pack. <b>Documents only</b> is the attachments zip. "
            "These copies of your own file are not the market comparison."
        ),
        PageBreak(),
    ]

    story += [
        P("5. Questionnaire sections A–J", "h1"),
        P(
            "Complete <b>one questionnaire per County Government</b>. County name and survey period "
            "are filled from the file and cannot be edited on the form. Extra questions added by "
            "the administrator appear in the section they were placed in."
        ),
        *shot("04-questionnaire.jpg", "Figure 4. Questionnaire — section pills A–J and Section E (allowances and medical cover)."),
        P("5.1 Navigation", "h2"),
        steps([
            "Open the county file → <b>Questionnaire</b>.",
            "Use the section pills A–J at the top. A green outline means that section is fully answered.",
            "Complete the fields. Dropdowns include a blank “Select” until you choose.",
            "Choose <b>Save this section</b> to stay, or <b>Save and continue</b> to move to the next section.",
        ]),
        P("5.2 What each section asks", "h2"),
        grid(
            ["Section", "Content"],
            [
                ["A Institution", "Department; respondent name, designation, telephone, email (consultant use only)."],
                ["B Workforce", "Permanent &amp; pensionable, contract, casual, other. Total is calculated. Use 0 if none."],
                ["C Policy", "Approved policy; philosophy defined; market position; last review year; triggers."],
                ["D Structure", "Number of grades; progression factors (If Other, specify); paid above maximum and why."],
                ["E Allowances", "Remunerative and non-remunerative allowances; expenditure; medical insurance and how cover is arranged (SHA, private, mixed, self-funded, reimbursement, combination, other); medical cost; pension %; gratuity %; other benefits."],
                ["F Recruitment", "Recruitment challenges (free text); hard-to-recruit and hard-to-retain families; reasons; benchmarking frequency; usual comparators."],
                ["G Equity", "Internal equity (equal pay for work of equal value); significant pay differences and causes if Yes."],
                ["H Pay mix", "Basic %, allowances %, other cash % (should add to 100); progression method; years in grade; placement factors."],
                ["I Affordability", "Personnel % of budget; can the county accommodate about 15%; implementation approach and period; priority categories and why."],
                ["J Observations", "Whether listed schedules are attached (upload on Documents); three challenges; three recommendations; other comments."],
            ],
            [38 * mm, 127 * mm],
        ),
        P("Table 4. Questionnaire map.", "caption"),
        PageBreak(),
    ]

    story += [
        P("6. Jobs, benefits and documents", "h1"),
        P("6.1 Jobs (benchmark positions)", "h2"),
        steps([
            "County file → <b>Jobs</b>.",
            "For each job group A–U excluding I and O: either tick <b>N/A</b>, or enter SRC equivalent, min basic, max basic, house, commuter, airtime and Total of Other Allowances.",
            "SRC equivalent is free text (for example Job Group S may be EX4). There is no median or headcount column.",
            "Choose <b>Save positions</b>.",
        ]),
        P(
            "Analysis uses the midpoint of min and max. A leftover payroll median is used only if both min and max are blank. A row counts as complete for progress only when it is N/A or when both min and max are filled."
        ),
        *shot("05-jobs.jpg", "Figure 5. Jobs table — SRC equivalent, min/max basic and allowances. N/A marks unused groups."),
        P("6.2 Benefits matrix", "h2"),
        steps([
            "County file → <b>Benefits</b>.",
            "For each listed benefit set <b>Provided?</b> to Yes, No or Partial.",
            "Set <b>Interest charged?</b> Yes or No where it applies (always visible). For car loan and house mortgage, if Provided is Yes or Partial you must also answer Interest charged.",
            "Add employer/employee contribution, eligibility and comments as known.",
            "Choose <b>Save benefits</b>.",
        ]),
        P("6.3 Documents", "h2"),
        steps([
            "County file → <b>Documents</b>.",
            "Open a heading (for example Current approved salary structure).",
            "Choose files (several at once if needed) and <b>Save this section</b>. Existing files are kept.",
            "Download any single file, or <b>Download complete file</b> for the workbook plus all attachments.",
            "Optional headings may be marked <b>Not available</b> if you do not have the document. A required heading needs at least one file. Marking Received without a file is not accepted.",
        ]),
        P(
            "Typical headings (the administrator can add, hide or mark required): current approved salary structure; staff establishment; job grades and job families; list of positions/designations; allowance schedule; employee benefits schedule; relevant CBA; previous salary survey; pension arrangements; medical insurance arrangements; other relevant remuneration documents."
        ),
        *shot("06-documents.jpg", "Figure 6. Documents — several files under one heading, Download on each row, Not available on optional items."),
        PageBreak(),
    ]

    story += [
        P("7. Submit, clarification and validation", "h1"),
        grid(
            ["Status", "Meaning"],
            [
                ["Draft", "County (or reviewer) can edit all modules."],
                ["Submitted", "Locked for the county. Waiting for review."],
                ["Clarification requested", "County can edit only the modules named in open clarifications (and Certify)."],
                ["Validated", "Accepted for analysis. County remains locked."],
            ],
            [50 * mm, 115 * mm],
        ),
        P("Table 5. File status.", "caption"),
        P("7.1 County submit", "h2"),
        steps([
            "Complete the modules. Overview percentages should reflect real answers and files.",
            "Certify if the survey requires it (default on).",
            "Overview → <b>Submit for review</b>. Confirm the completion percentage shown in the prompt.",
        ]),
        P("7.2 Consultant return and validate", "h2"),
        steps([
            "Dashboard → <b>Needs attention</b>, or County files filtered to Submitted / Clarification.",
            "Read questionnaire, jobs, benefits and documents. Open each uploaded file as needed.",
            "Validation tab — set a status on <b>every</b> item. An empty checklist cannot be used to mark the file validated.",
            "If something must change: Clarifications → name the module → send. That returns the file to the county.",
            "When the file is in order: Overview → <b>Mark validated</b>.",
        ]),
        P(
            "If every open clarification is answered, the county can edit the whole file again until they re-submit."
        ),
        PageBreak(),
    ]

    story += [
        P("8. Consultants, comparators and staff links", "h1"),
        P("8.1 Comparators", "h2"),
        steps([
            "Left menu → <b>Comparators</b>.",
            "Open an organisation → <b>Pay table</b> and enter min / max / median and allowances for the same benchmark jobs the counties use. Tick N/A where the organisation has no equivalent.",
            "Open <b>Benefits</b> for that organisation.",
            "Only organisations marked <b>include in market median</b> enter Analysis.",
            "A platform administrator can delete a comparator from its Details page. That removes stored pay and benefits; county files are not touched.",
        ]),
        P("8.2 Staff survey links", "h2"),
        steps([
            "Left menu → <b>Staff survey links</b> (administrators and collection administrators).",
            "Copy the <b>county-specific</b> URL and send it to people who work in that county but do not have a DCollect login.",
            "Each completed form is stored on that county’s <b>Individual responses</b> tab.",
            "There is also one open (unscoped) link; prefer the county link so answers are tagged correctly.",
        ]),
        P(
            "Staff enter job title or the closest benchmark job, terms, years in role, and monthly basic plus allowances. Name and email are optional."
        ),
        PageBreak(),
    ]

    story += [
        P("9. Analysis and reports", "h1"),
        P("9.1 Live analysis", "h2"),
        steps([
            "Left menu → <b>Analysis</b>.",
            "Pick a county. Switch <b>Basic</b> or <b>Total cash</b> (basic plus house, commuter, airtime and other).",
            "Read Official (midpoint of min/max), Staff n, County P25/P50/P75, Market n, Market P25/P50/P75, Ratio, Position and Scale.",
            "Use <b>By SRC equivalent</b> to see groups mapped to the same SRC denotation (for example EX4).",
            "Download the market workbook, or <b>Download complete file</b> for that county.",
        ]),
        P(
            "County P25/P50/P75 combine the official figure with staff forms for that job group. Quartiles need at least two observations; with one figure only P50 is shown. Market percentiles are taken from comparator organisation medians (each organisation counts once). Ratio is county P50 ÷ market P50 (1.00 = at market). Scale uses market P25/P75 when two or more organisations have a figure."
        ),
        P("9.2 Reports centre", "h2"),
        steps([
            "Left menu → <b>Reports</b>.",
            "Download a cross-county workbook (progress, questionnaire extract, individual responses, market position, job group pay, benefits, document register).",
            "In the County packs table choose <b>Complete file</b> for one zip per county.",
        ]),
        *shot("07-reports.jpg", "Figure 7. Reports centre — cross-county extracts and per-county Complete file / Workbook / Documents."),
        P("9.3 Complete county file (zip)", "h2"),
        P(
            "From Overview, Documents, Reports or County files, <b>Download complete file</b> produces one zip you can unzip and review as a folder:"
        ),
        bullets([
            "<b>README.txt</b> — county, period, status, headings marked not available or still empty.",
            "<b>1-County-submission.xlsx</b> — questionnaire, jobs, staff responses, benefits, document checklist, validation; reviewers also receive comparator and market sheets.",
            "<b>2-Supporting-documents/</b> — one sub-folder per document heading, with every uploaded file.",
        ]),
        P(
            "Workbook only is the Excel pack. Documents only is the attachments. The market workbook is all counties at once. County respondents who download a pack of their own file do not receive comparator or market sheets unless Analysis is switched on for counties."
        ),
        PageBreak(),
    ]

    story += [
        P("10. Administrator setup, users, audit and data", "h1"),
        P(
            "Counties cannot start until an active period exists, files are opened, and county logins exist. Platform administrators also download this PDF from the left menu: <b>User manual (PDF)</b>."
        ),
        P("10.1 Recommended setup order", "h2"),
        steps([
            "<b>Variables &amp; settings</b> — survey title, support email, confidentiality text, maximum upload size, active period, whether certification is required before submit, whether county users may open live Analysis.",
            "<b>Survey periods</b> — one period is active at a time. Dashboards and reports use the active period.",
            "<b>Catalogues</b> — counties, job families, job groups, SRC grades, benchmark jobs, benefit types, document types, validation items, comparator organisations. Inactive items are hidden from new work.",
            "<b>Forms &amp; questions</b> — mark required questionnaire items, jobs, benefits and documents. Add extra questions. Use Place after to sit a new question between two existing ones. Built-in questions can be reworded; they cannot be deleted.",
            "<b>Dropdown lists</b> (Catalogues) — Yes/No, medical insurance, medical cover arrangement, internal equity, affordability, and the rest.",
            "<b>Users</b> — one county respondent per county, or <b>Create missing county logins</b>. Add consultants and analysts. Only a platform administrator can create another administrator.",
            "<b>Open county files</b> — Variables &amp; settings or County files: select counties or open every county. Safe to repeat; existing files are not overwritten.",
            "Assign a consultant on a file’s Overview if that person should own the review.",
            "<b>Staff survey links</b> — copy county URLs.",
        ]),
        P("10.2 Form rules that affect submit", "h2"),
        bullets([
            "Require certification before submit — county must complete Certify first (default on).",
            "Require complete to submit — county cannot submit while items marked Required are incomplete. Overview percentages still count every active question, job group, benefit and document.",
            "Jobs require SRC equivalent — each applicable job-group row must have SRC text.",
        ]),
        P("10.3 Users", "h2"),
        P(
            "A county login must be linked to exactly one county. Deleting a login under Users does "
            "not remove answers they already entered; audit rows stay under the username."
        ),
        P("10.4 Audit trail (platform administrator only)", "h2"),
        P(
            "Left menu → <b>Audit trail</b>. Filter by search, role, area, county, outcome and dates. "
            "Download CSV. Events include sign-in, failed sign-in, sign-out, idle timeout, user "
            "administration, catalogue changes, county file saves, downloads (including complete "
            "file and this manual), and data purge. Passwords are never stored."
        ),
        P("10.5 Data administration (platform administrator only)", "h2"),
        P(
            "Delete collected data for one county or one user, or reset all collected answers. "
            "Catalogues and logins stay unless you delete a login under Users. Type the confirmation "
            "name exactly. This cannot be undone."
        ),
        PageBreak(),
    ]

    story += [
        P("11. Installing or updating DCollect", "h1"),
        P("11.1 Fresh machine (no existing database)", "h2"),
        P("Windows: unzip, double-click run.bat, choose 1 (local test) or 2 (production)."),
        P("Linux / macOS: unzip, then <b>chmod +x run.sh</b> and <b>./run.sh</b> (choose 2 for production) or <b>./run.sh production</b>."),
        P(
            "First run creates .venv, .env, applies migrations, loads catalogues and starter accounts. "
            "After production start, edit .env: DEBUG=false, ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS "
            "(include https://collect.internetcongress.org if that is the public URL). Restart. "
            "Change every starter password at first sign-in."
        ),
        P("11.2 Updating the live site", "h2"),
        P(
            "Copy new application files over the current project. <b>Do not replace</b> db.sqlite3, "
            ".env, .venv or media. Then run migrate and collectstatic with the existing virtual "
            "environment, and restart. Do not run run.sh, run.bat or bootstrap on the live server. "
            "See DEPLOY.txt in the share pack."
        ),
        PageBreak(),
    ]

    story += [
        P("12. If something will not work", "h1"),
        bullets([
            "After submit, the county file is locked. The county can edit again only in sections where a clarification was requested (or the whole file if all clarifications are answered).",
            "A county login cannot open another county’s file.",
            "Jobs, benefits or document types added in settings appear the next time that file is opened.",
            "If you cannot sign in, contact the person who issued the account.",
            "You are signed out after 10 minutes without activity. Sign in again. After timeout you are returned to the page you were on when possible.",
            "If a dropdown has no options, an administrator should attach a list under Setup → Catalogues → Dropdowns.",
            "If a download fails, try again or use Documents to take files one by one. Uploaded files are not available as raw public /media/ links.",
            "Overview at 100% on an empty file means an old version; this release counts actual answers and uploads.",
        ]),
        P("12.1 Support", "h2"),
        P(
            "In-application: left menu → <b>What I need to do</b> (not shown to collection administrators). "
            "Platform administrators: left menu → <b>User manual (PDF)</b> for this document. "
            "Use the support email set under Variables &amp; settings."
        ),
        Spacer(1, 10 * mm),
        P("— End of manual —", "cover_meta"),
    ]
    return story


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="DCollect User Manual",
        author="BINSTOPEJ Management Solutions Ltd",
        subject="County Public Service Salary and Remuneration Survey — DCollect",
    )
    doc.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    DESKTOP.write_bytes(OUT.read_bytes())
    print("wrote", OUT, OUT.stat().st_size)
    print("wrote", DESKTOP, DESKTOP.stat().st_size)


if __name__ == "__main__":
    main()
