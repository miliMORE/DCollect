const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, TableOfContents,
  LevelFormat,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "docs", "DCollect-User-Manual.docx");
const DESKTOP = path.join(require("os").homedir(), "Desktop", "DCollect User Manual.docx");
const LOGO = path.join(ROOT, "static", "brand", "logo.png");

const NAVY = "1B2A4A";
const GOLD = "C6A15B";
const INK = "161410";
const MUTED = "6B6256";
const HEAD_BG = "1B2A4A";
const ROW_BG = "F4EFE6";
const WHITE = "FFFFFF";
const PAGE_W = 11906;
const PAGE_H = 16838;
const MARGIN = 1134;
const CONTENT_W = PAGE_W - MARGIN * 2; // 9638
const thin = { style: BorderStyle.SINGLE, size: 4, color: "C5BBA8" };
const borders = { top: thin, bottom: thin, left: thin, right: thin };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function run(text, opts = {}) {
  return new TextRun({
    text,
    font: "Calibri",
    size: opts.size || 22,
    bold: !!opts.bold,
    italics: !!opts.italics,
    color: opts.color || INK,
    underline: opts.underline ? {} : undefined,
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 160, before: opts.before ?? 0, line: 276 },
    alignment: opts.align || AlignmentType.JUSTIFIED,
    children: Array.isArray(text) ? text : [run(text, opts)],
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    pageBreakBefore: true,
    spacing: { before: 0, after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GOLD, space: 4 } },
    children: [new TextRun({ text, font: "Calibri", size: 32, bold: true, color: NAVY })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, font: "Calibri", size: 26, bold: true, color: NAVY })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, font: "Calibri", size: 24, bold: true, color: NAVY })],
  });
}

function bullet(text, ref = "bullets") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80, line: 276 },
    children: [run(text)],
  });
}

function numItem(text, ref) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80, line: 276 },
    children: [run(text)],
  });
}

function cell(text, width, opts = {}) {
  const fill = opts.header ? HEAD_BG : opts.alt ? ROW_BG : WHITE;
  const color = opts.header ? WHITE : INK;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      new Paragraph({
        children: [
          run(text, { bold: !!opts.header || !!opts.bold, color, size: opts.header ? 20 : 20 }),
        ],
      }),
    ],
  });
}

function table(headers, rows, widths) {
  const head = new TableRow({
    children: headers.map((h, i) => cell(h, widths[i], { header: true })),
  });
  const body = rows.map((row, r) =>
    new TableRow({
      children: row.map((value, i) => cell(String(value), widths[i], { alt: r % 2 === 1 })),
    })
  );
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [head, ...body],
  });
}

function spacer(after = 120) {
  return new Paragraph({ spacing: { after }, children: [] });
}

function caption(text) {
  return new Paragraph({
    spacing: { after: 200, before: 40 },
    children: [run(text, { italics: true, size: 18, color: MUTED })],
  });
}

const numbering = {
  config: [
    {
      reference: "bullets",
      levels: [
        {
          level: 0,
          format: LevelFormat.BULLET,
          text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 360, hanging: 180 } } },
        },
      ],
    },
    ...["nCounty", "nCert", "nConsult", "nPrep", "nLinux", "nWin", "nClarify", "nStaff"].map((reference) => ({
      reference,
      levels: [
        {
          level: 0,
          format: LevelFormat.DECIMAL,
          text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420, hanging: 240 } } },
        },
      ],
    })),
  ],
};

const logoData = fs.readFileSync(LOGO);

const children = [];

// Cover
children.push(
  new Paragraph({ spacing: { before: 400, after: 200 }, alignment: AlignmentType.CENTER, children: [] }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [
      new ImageRun({
        type: "png",
        data: logoData,
        transformation: { width: 72, height: 72 },
        altText: { name: "DCollect logo", description: "DCollect square mark", title: "DCollect" },
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
    children: [run("DCollect", { size: 56, bold: true, color: NAVY })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 280 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 16, color: GOLD, space: 8 } },
    children: [run("USER MANUAL", { size: 32, bold: true, color: GOLD })],
  }),
  para("County Public Service Salary and Remuneration Survey Platform", {
    align: AlignmentType.CENTER,
    size: 26,
    after: 80,
  }),
  para("County Public Service Board National Consultative Forum (CPSB-NCF)", {
    align: AlignmentType.CENTER,
    after: 40,
    color: MUTED,
  }),
  para("Implemented by BINSTOPEJ Management Solutions Ltd", {
    align: AlignmentType.CENTER,
    after: 360,
    color: MUTED,
  }),
  spacer(200),
  table(
    ["Field", "Detail"],
    [
      ["Document title", "DCollect User Manual"],
      ["Audience", "Authorised administrators, collection staff, consultants, analysts and county respondents"],
      ["Version", "1.0"],
      ["Date", "August 2026"],
      ["Classification", "Confidential — for authorised survey users only"],
      ["Applies to", "DCollect web application as deployed for the 2026 review"],
    ],
    [2800, CONTENT_W - 2800]
  ),
  spacer(280),
  para(
    "This manual describes how to deploy, configure, complete, review and analyse the County Public Service salary and remuneration survey in DCollect. Menu names match the live application. Where a page is absent from the left menu, it is not part of that user’s role.",
    { after: 80 }
  ),
  para(
    "Information entered in DCollect is treated as confidential and is used solely for the Salary and Remuneration Review. Institution-level data that is commercially or administratively sensitive may be reported in aggregated form.",
    { after: 200 }
  )
);

children.push(
  h1("Contents"),
  new Paragraph({
    spacing: { after: 200 },
    children: [run("Right-click the table of contents in Microsoft Word and choose Update Field to refresh page numbers after opening.", { italics: true, size: 20, color: MUTED })],
  }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" })
);

// 1 Purpose
children.push(
  h1("1. Purpose of DCollect"),
  para(
    "DCollect is the field collection and analysis application for the County Public Service Salary and Remuneration Review commissioned by the County Public Service Board National Consultative Forum (CPSB-NCF) and undertaken by BINSTOPEJ Management Solutions Ltd. It captures one institutional file per County Government, supporting documents, optional individual staff responses, and comparator organisation pay, then produces market position analysis."
  ),
  para(
    "Each County Government completes one questionnaire and one jobs, benefits and documents file for the active survey period. Counties cannot see other counties’ answers. Market comparison is available to analysts (and to a county only if an administrator expressly allows it)."
  ),
  h2("1.1 What the platform does"),
  bullet("Opens a county file for the active survey period."),
  bullet("Collects the institutional questionnaire (sections A–J), job-group pay, benefits and uploads."),
  bullet("Locks a file after submit, and reopens only the modules named in a clarification."),
  bullet("Records consultant validation and an activity history on each file."),
  bullet("Collects comparator organisation pay on the same job catalogue."),
  bullet("Accepts staff survey forms through a unique link, tagged to a county."),
  bullet("Calculates county and market percentiles and issues Excel workbooks."),
  h2("1.2 Confidentiality"),
  para(
    "Respondent name, designation, telephone and email on the institutional questionnaire are marked for the consultant’s use only. Staff survey name and email are optional. Uploaded files are not public: they are downloaded from the county file after sign-in. Do not circulate passwords, staff survey links beyond the intended audience, or county packs outside the review team."
  )
);

// 2 Roles
children.push(
  h1("2. Roles and what each person can do"),
  para(
    "Sign in with the account issued to you. The left-hand menu shows only the work for that role. Collection administrators do not see the in-application “What I need to do” page; this manual is the reference for that role."
  ),
  table(
    ["Role", "Starter login (fresh install)", "Principal work"],
    [
      ["Administrator", "admin", "Owns the site name, help text, audit trail and data reset. Can do everything else as well."],
      ["Collection administrator", "admin2", "Survey periods, catalogues, forms, users and county files. Cannot change site identity, open the audit trail, or reset all data."],
      ["Field consultant", "consultant", "Reviews assigned (or all unassigned) files, validation, clarifications, comparators. Cannot change catalogues."],
      ["Analyst", "analyst", "Analysis and Reports. Does not fill or certify county files."],
      ["County respondent", "created under Users", "Completes one county’s file. Cannot open another county."],
    ],
    [2200, 2800, CONTENT_W - 5000]
  ),
  caption("Table 1. Roles. Change starter passwords at first sign-in. Default password on a fresh install is ChangeMe!2026 unless BOOTSTRAP_PASSWORD is set."),
  para(
    "A county login must be linked to exactly one county. Administrators, collection administrators, consultants and analysts are not linked to a county. Only a platform administrator can create or edit another administrator account."
  )
);

// 3 Navigation
children.push(
  h1("3. Signing in and finding your way"),
  h2("3.1 Sign-in"),
  bullet("Open the survey address in a browser (for a local test, http://127.0.0.1:8000/)."),
  bullet("Enter the username and password issued to you."),
  bullet("If the account is set to require a new password, DCollect opens Change password before any other page. The new password must be at least 10 characters."),
  bullet("Use Change password at any later time from the bottom of the left menu."),
  bullet("Sign out from the left menu when you finish. The session also expires after eight hours of idle time."),
  h2("3.2 Screen layout"),
  para("Every signed-in page has the same frame:"),
  bullet("Left menu — role-specific links. On a small screen, use Menu."),
  bullet("Top bar — breadcrumb, page title, and the active survey period."),
  bullet("Main area — the work for that page."),
  bullet("Gold buttons — the primary action (Save, Submit, Download). Ghost buttons — secondary actions."),
  h2("3.3 Left menu by role"),
  table(
    ["Menu item", "Who sees it", "Opens"],
    [
      ["Dashboard", "Everyone", "Counts, next step, and shortcuts."],
      ["My county file / Clarifications", "County respondent", "That county’s file only."],
      ["County files / Questionnaires", "Admin, collection admin, consultant, analyst", "All files in the active period (consultants: assigned files, or all if none are assigned)."],
      ["Staff survey links", "Admin, collection admin", "Public and per-county staff form URLs."],
      ["Comparators / Analysis / Reports", "Admin, collection admin, consultant, analyst", "Market input and outputs. Analysis also appears for a county if that option is switched on."],
      ["Variables & settings, Forms & questions, Users", "Admin, collection admin", "Setup. Site name and confidentiality text: administrator only."],
      ["Audit trail / Data administration", "Administrator only", "Who did what, and destructive data tools."],
      ["Django admin", "Administrator", "Low-level database forms. Prefer the DCollect screens."],
      ["What I need to do", "Everyone except collection administrator", "Short in-app checklist for the role."],
      ["Change password / Sign out", "Everyone", "Account security."],
    ],
    [2400, 2800, CONTENT_W - 5200]
  ),
  caption("Table 2. Navigation. Missing items are intentional, not an error."),
  h2("3.4 Inside a county file"),
  para("Open a file from Dashboard, County files, or My county file. A horizontal file menu is always available:"),
  table(
    ["Tab", "Purpose"],
    [
      ["Overview", "Status, progress percentages, assignment, certify/submit/validate/return, activity."],
      ["Questionnaire", "Institutional form, sections A–J. Save each section."],
      ["Jobs", "Pay by job group A–U (excluding I and O)."],
      ["Benefits", "Whether each listed benefit is provided, interest, eligibility, comments."],
      ["Documents", "Uploads. Optional items may be marked Not available."],
      ["Certify", "Name, designation, initials. Date is stored automatically."],
      ["Clarifications", "Reviewer questions and county answers."],
      ["Individual responses", "Staff who used the county survey link."],
      ["Validation", "Consultant quality checklist (reviewers only)."],
    ],
    [2400, CONTENT_W - 2400]
  ),
  caption("Table 3. County file tabs.")
);

// 4 Deploy
children.push(
  h1("4. Installing DCollect (fresh machine or fresh server)"),
  para(
    "A fresh deployment means the server or computer has no existing DCollect database. Unzipping DCollect.zip and running the start script for the first time is a fresh deployment, including a Linux server where you run ./run.sh and choose Production."
  ),
  h2("4.1 Requirements"),
  bullet("Python 3.11 or later on the PATH (python3 on Linux)."),
  bullet("Network access to install packages on first run."),
  bullet("Port 8000 free, unless you set PORT."),
  h2("4.2 Windows (local test or Windows server)"),
  numItem("Unzip DCollect.zip to a folder such as C:\\DCollect.", "nWin"),
  numItem("Double-click run.bat, or run run.bat local or run.bat production.", "nWin"),
  numItem("Choose 1 for local test (http://127.0.0.1:8000/) or 2 for production (listens on all interfaces, port 8000).", "nWin"),
  numItem("Wait while the virtual environment, packages, .env, database and starter accounts are created.", "nWin"),
  h2("4.3 Linux or macOS server (including choosing Production)"),
  numItem("Copy and unzip DCollect.zip on the server. Example: unzip DCollect.zip && cd DCollect", "nLinux"),
  numItem("Make the script executable: chmod +x run.sh", "nLinux"),
  numItem("Start: ./run.sh   then choose 2 for production. Or run ./run.sh production", "nLinux"),
  numItem("The same first-run work happens: virtual environment, packages, .env, migrate, bootstrap, then collectstatic and gunicorn on 0.0.0.0:8000 (or $PORT).", "nLinux"),
  numItem("Keep the process running (systemd, tmux or a process manager). Stopping the terminal stops the site unless you have configured a service.", "nLinux"),
  para(
    "That is a complete first-time production start. You do not run migrate or bootstrap separately unless you are updating an existing site."
  ),
  h2("4.4 After the first production start"),
  para("Edit the generated .env file (do not replace it on later updates):"),
  bullet("DEBUG=false"),
  bullet("ALLOWED_HOSTS=your public hostname or IP, for example collect.internetcongress.org"),
  bullet("CSRF_TRUSTED_ORIGINS=https://your-hostname  (required for sign-in on HTTPS)"),
  bullet("Change BOOTSTRAP_PASSWORD if you still need it for new county logins, then change every starter password in the application."),
  para("Restart ./run.sh production after saving .env. For PostgreSQL, set DATABASE_URL in .env before the first migrate (or migrate again after switching)."),
  h2("4.5 Updating an existing live site"),
  para(
    "Copy the new application files over the current folder. Do not replace db.sqlite3, .env, .venv or the media folder. Then run migrate and collectstatic with the existing virtual environment, and restart. Existing passwords and collected answers stay."
  ),
  h2("4.6 Starter accounts (fresh install only)"),
  para("Password: ChangeMe!2026 unless BOOTSTRAP_PASSWORD was set. Accounts: admin, admin2, consultant, analyst. Create county respondents under Users. These accounts are not created again if they already exist."),
  h2("4.7 Hosted platforms (Render and similar)"),
  para(
    "Use the start command in Procfile / render.yaml: install requirements, collectstatic, migrate, bootstrap, gunicorn. Set SECRET_KEY, DEBUG=false, ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS in the host’s environment, including https://collect.internetcongress.org if that is the public URL."
  )
);

// 5 Prepare survey
children.push(
  h1("5. Preparing the survey (administrator and collection administrator)"),
  para("Counties cannot start until an active period exists, files are opened, and county logins exist."),
  h2("5.1 Recommended order"),
  numItem("Variables & settings — confirm survey title, support email, confidentiality text, maximum upload size (megabytes), active period, whether certification is required before submit, and whether county users may open live Analysis.", "nPrep"),
  numItem("Survey periods — one period is active at a time. Dashboards and reports use the active period.", "nPrep"),
  numItem("Catalogues — counties, job families, job groups, SRC grades, benchmark jobs, benefit types, document types, validation items, comparator organisations. Inactive items are hidden from new work. New jobs, benefits and documents appear on a file the next time it is opened.", "nPrep"),
  numItem("Forms & questions — mark required questionnaire items, jobs, benefits and documents. Add extra questions to a section if needed. Use Place after to sit a new question between two existing ones. Built-in questions can be reworded and have their input type changed; they cannot be deleted. Retired items (for example payroll extract on the questionnaire) stay hidden.", "nPrep"),
  numItem("Dropdown lists (under Catalogues) — Yes/No, medical insurance (Yes, No, Mixed — partially SHA, partially private), internal equity, affordability, and the rest. Analysis and forms read these lists.", "nPrep"),
  numItem("Users — one county respondent per county (or Create missing county logins). Add consultants and analysts. Collection administrators cannot create administrator accounts.", "nPrep"),
  numItem("Open county files — on Variables & settings, select counties (Ctrl or Cmd for several) or open a file for every county. Safe to repeat: existing files are not overwritten.", "nPrep"),
  numItem("Assign a consultant on a file’s Overview if you want that person to own the review.", "nPrep"),
  numItem("Staff survey links — copy the county-specific URL and send it to staff who do not have a county login. There is also one open (unscoped) link if you need it; prefer the county link so answers are tagged correctly.", "nPrep"),
  h2("5.2 Form rules that affect submit"),
  bullet("Require certification before submit — county must complete Certify first (default on)."),
  bullet("Require complete to submit — county cannot submit while required questionnaire items, jobs, benefits or documents are incomplete."),
  bullet("Jobs require SRC equivalent — each applicable job-group row must have SRC text (for example EX4)."),
  h2("5.3 Catalogues counties should not invent"),
  para(
    "Benchmark jobs are a locked list shared with comparators so medians line up. Do not ask counties to type their own job titles on the jobs table. Individual staff may pick the closest benchmark job or type a title on the public staff form."
  )
);

// 6 County
children.push(
  h1("6. County respondent — completing a file"),
  para("You work only on your county. Keep the approved salary structure and allowance and benefits schedules beside you. Amounts are Kenya shillings, monthly, without thousands separators in number fields."),
  h2("6.1 Order of work"),
  numItem("Dashboard — open My county file. If Next step is showing, start there.", "nCounty"),
  numItem("Questionnaire — sections A to J. Save a section before leaving it (Save this section, or Save and continue).", "nCounty"),
  numItem("Jobs — one row per job group A–U excluding I and O. Mark N/A if the county does not use that group. Enter SRC equivalent as free text, min basic, max basic, house, commuter, airtime, and Total of Other Allowances. Analysis uses the midpoint of min and max.", "nCounty"),
  numItem("Benefits — Provided? Yes / No / Partial; Interest charged? where relevant; eligibility; explanatory comments.", "nCounty"),
  numItem("Documents — upload the file for each requested type. A required item needs a file. Optional items may be ticked Not available if you do not have them. Allowed types include PDF, Excel, Word, CSV, PNG and JPEG, within the size limit set by the administrator.", "nCounty"),
  numItem("Certify — name, designation, initials.", "nCounty"),
  numItem("Overview — Submit for review. After submit you cannot edit until a reviewer returns the file.", "nCounty"),
  numItem("If Clarifications appear, answer each one, correct only the unlocked section(s), certify if needed, and submit again.", "nCounty"),
  h2("6.2 Progress on Overview"),
  para(
    "Percentages are Questionnaire, Jobs, Benefits, Documents, plus whether the file is certified. Jobs count a row as done when it is N/A or when a basic figure exists (min, max, or both). Required documents must have a file, not only a “received” tick."
  ),
  h2("6.3 After submit"),
  para(
    "The file is locked. You can still read it and download a county pack of your own answers (Overview or Reports if offered). That pack is not the market comparison. You may download your uploaded files from Documents."
  )
);

// 7 Questionnaire
children.push(
  h1("7. Questionnaire (sections A–J)"),
  para(
    "Complete one questionnaire per County Government. County name and survey period are filled from the file and cannot be edited on the form. Extra questions added by the administrator appear in the section they were placed in."
  ),
  h2("7.1 Section A — Institution and respondent"),
  para("Department / directorate / unit. Respondent name, designation, telephone and email — confidential, for the consultant’s use only."),
  h2("7.2 Section B — Workforce profile"),
  para("Counts of permanent and pensionable, contract, temporary/casual, and other employees. Total employees is calculated automatically. Use zero if none."),
  h2("7.3 Section C — Remuneration policy and philosophy"),
  para("Approved remuneration/compensation policy; whether the compensation philosophy is formally defined; stated market position; year the structure was last reviewed (four digits); main triggers for review."),
  h2("7.4 Section D — Salary structure"),
  para("Number of salary grades; factors contributing to progression (if Other, specify); whether employees are ever paid above maximum, and why if Yes."),
  h2("7.5 Section E — Allowances and benefits"),
  bullet("Main allowances has two parts: Remunerative Allowances (paid monthly) and Non-Remunerative allowances."),
  bullet("Approximate annual allowance expenditure (KES)."),
  bullet("Medical insurance provided? Yes, No, or Mixed (partially SHA, partially private insurance). If Yes or Mixed, enter annual employer medical cost per employee."),
  bullet("Pension employer and employee contribution (percent)."),
  bullet("Gratuity (percent), then other significant benefits."),
  h2("7.6 Section F — Recruitment, retention and market competitiveness"),
  bullet("Challenges affecting recruitment — free text, not a list."),
  bullet("Job families with greatest recruitment challenges (difficult to get the right candidates)."),
  bullet("Job families with greatest retention challenges."),
  bullet("Main reasons for recruitment challenges, and separately main reasons for retention challenges."),
  bullet("How often external salary benchmarking is done, and usual comparator organisations."),
  h2("7.7 Section G — Internal and external equity"),
  bullet("Overall internal equity assessment (equal pay for work of equal value): Very equitable; Equitable; Moderately equitable; Inequitable; Highly inequitable; Not Sure."),
  bullet("Whether there are significant pay differences for similar work, and if Yes, the causes."),
  h2("7.8 Section H — Pay mix and progression"),
  bullet("Basic salary as a percentage of cash remuneration ((Basic Salary ÷ Total Cash Remuneration) × 100)."),
  bullet("Allowances as a percentage of cash remuneration."),
  bullet("Other cash payments as a percentage ((Other Cash Payments ÷ Total Cash Payments) × 100). These three should add to 100."),
  bullet("Annual salary progression method; average years in a salary grade; factors that determine salary placement."),
  h2("7.9 Section I — Affordability and implementation"),
  bullet("Personnel/remuneration expenditure as a percentage of budget."),
  bullet("Can the County accommodate a general remuneration increase of about 15%?"),
  bullet("Most sustainable implementation approach and preferred period."),
  bullet("Given budget constraints, which category of employees would you prioritize for salary increase, and why?"),
  h2("7.10 Section J — Documents and key observations"),
  para("Whether listed supporting schedules are attached (use the Documents tab to upload the files), three key remuneration challenges, three recommended changes, and other comments. Payroll extract and HR policy questions are not on this form; those document types are not requested as uploads.")
);

// 8 Jobs benefits docs
children.push(
  h1("8. Jobs, benefits and documents in detail"),
  h2("8.1 Jobs (benchmark positions)"),
  para(
    "Rows are county job groups A–U excluding I and O. SRC equivalent is free text (for example Job Group S may be EX4). Do not enter a median or headcount on this table; those are not collected here. Total of Other Allowances is the last cash column."
  ),
  para(
    "If a group is not used, tick N/A. Saving the table keeps notes that are not shown on screen. If min and max are both entered, analysis uses their midpoint. If only one bound is entered, that bound is used."
  ),
  h2("8.2 Benefits matrix"),
  para(
    "Every active benefit type appears as a row: Provided? (Yes / No / Partial), Interest charged? (Yes / No) where the type collects interest (for example car loan and house mortgage), employer contribution, employee contribution, eligibility criteria, explanatory comments."
  ),
  h2("8.3 Documents"),
  para("Typical request list (the administrator can add, hide or mark required):"),
  bullet("Current approved salary structure"),
  bullet("Staff establishment"),
  bullet("Job grades and job families"),
  bullet("List of positions/designations (the staff establishment)"),
  bullet("Allowance schedule"),
  bullet("Employee benefits schedule"),
  bullet("Relevant CBA (where applicable)"),
  bullet("Previous salary survey/report (if available)"),
  bullet("Pension arrangements"),
  bullet("Medical insurance arrangements"),
  bullet("Other relevant remuneration documents"),
  para(
    "Save each document card after you attach a file. Use Download all uploaded files for a zip of everything on the file. Reviewers use the same links. Direct /media/ addresses are not public."
  )
);

// 9 Clarifications
children.push(
  h1("9. File status, submit, clarification and validation"),
  table(
    ["Status", "Meaning"],
    [
      ["Draft", "County (or reviewer) can edit all modules."],
      ["Submitted", "Locked for the county. Waiting for review."],
      ["Clarification requested", "County can edit only modules named on open clarifications (or all modules if the clarification is general, or if every clarification has been answered)."],
      ["Validated", "Accepted for analysis. County remains locked."],
      ["In analysis / Closed", "Available on the Overview assignment form for administrators when a file should be marked further along."],
    ],
    [2800, CONTENT_W - 2800]
  ),
  caption("Table 4. County file status."),
  h2("9.1 Consultant review"),
  numItem("Dashboard → Needs attention, or County files filtered to Submitted or Clarification.", "nConsult"),
  numItem("Read questionnaire, jobs, benefits and documents. Download files from Documents or Download uploaded files.", "nConsult"),
  numItem("Complete Validation. Status and comments are stored per checklist item.", "nConsult"),
  numItem("If something must be corrected, Clarifications → name the module (questionnaire, jobs, benefits, documents, or general) and write the request. That sets status to Clarification requested.", "nConsult"),
  numItem("When the file is in order, Mark validated on Overview.", "nConsult"),
  h2("9.2 County response to a clarification"),
  numItem("Open Clarifications, write the response, and save. That marks the item answered.", "nClarify"),
  numItem("Edit only the unlocked section(s). After every clarification is answered, the whole file can be finished again.", "nClarify"),
  numItem("Certify if required, then Submit for review.", "nClarify"),
  para("Overview also shows Activity for that file (saves, submit, validation). The administrator Audit trail is the system-wide log and is not shown to counties.")
);

// 10 Comparators
children.push(
  h1("10. Comparators"),
  para(
    "Comparators are market organisations on the same benchmark job list as counties. Only organisations that are active and marked include in market median enter Analysis."
  ),
  bullet("Comparators in the left menu — add an organisation (reviewers) or open an existing one."),
  bullet("Details — name, sector, whether it is in the market median. A platform administrator can delete an organisation from this page; that removes its pay and benefits rows, not county files. Type the organisation name to confirm."),
  bullet("Pay table — min, max, median (used when known), house, commuter, airtime, other. Tick N/A if the organisation does not have the job."),
  bullet("Benefits — same matrix as counties."),
  para("Enter comparator pay before relying on Analysis. If no comparator pay exists for the period, market columns stay blank.")
);

// 11 Staff
children.push(
  h1("11. Staff survey (individual responses)"),
  para(
    "People who do not have a county login can submit one form through a link. Each form is one observation. On Analysis, those observations are combined with the official jobs-table figure for the same job group."
  ),
  h2("11.1 Issuing a link"),
  numItem("Staff survey links (setup menu). Prefer the row for the county, not the open link, so the answer is tagged to that county.", "nStaff"),
  numItem("Copy the URL and send it to the intended staff. The link stays valid while it is active.", "nStaff"),
  h2("11.2 Completing the public form"),
  para("No login. Choose the closest benchmark position or enter a job title. Enter monthly basic salary (required) and allowances. Name and email are optional. County is locked when the link belongs to one county."),
  h2("11.3 Viewing results"),
  para(
    "On the county file, Individual responses lists the forms and shows county-wide basic P25, P50 and P75 across all jobs (quartiles need two or more responses). Unmatched forms (no benchmark job, or a job outside groups A–U excluding I and O) are listed here and counted on Analysis as unmatched."
  )
);

// 12 Analysis
children.push(
  h1("12. Analysis"),
  para("Open Analysis. Choose a county and Basic or Total cash. Draft or clarification files show as a preview, not a validated result."),
  h2("12.1 How to read the main table"),
  table(
    ["Column", "Meaning"],
    [
      ["Job group / SRC equivalent", "County job group and the SRC text the county entered."],
      ["Official", "Midpoint of min and max basic (or total cash). A stored payroll median is used only if min and max are both blank."],
      ["Staff n", "Number of individual staff forms matched to that group."],
      ["County P25 / P50 / P75", "Percentiles of the official figure plus those staff forms. Quartiles are shown only when there are at least two observations; with one figure only P50 appears."],
      ["Market n", "Number of comparator organisations with a figure for that group."],
      ["Market P25 / P50 / P75", "Percentiles of one median per comparator organisation (each employer counts once). Quartiles need two or more organisations."],
      ["Ratio", "County P50 ÷ market P50. Below 0.90 is below market; 0.90–1.10 around market; above 1.10 above market."],
      ["Position / Scale", "Position follows the ratio bands. Scale uses market P25/P75 when they exist (below P25 lag, above P75 lead)."],
    ],
    [2800, CONTENT_W - 2800]
  ),
  caption("Table 5. Analysis columns. Amounts are Kenya shillings."),
  h2("12.2 Other blocks on the page"),
  bullet("Comparator medians — each organisation’s median for jobs that sit in that county job group."),
  bullet("By SRC equivalent — groups this county mapped to the same SRC code (for example EX4). County percentiles pool official and staff figures across those groups. Market n is organisations with a figure in any of those groups."),
  h2("12.3 County access"),
  para(
    "By default counties do not see Analysis. If Variables & settings has “Let county users open live analysis” switched on, a county sees only their own file against the market. They cannot download the all-county workbook or open Reports."
  )
);

// 13 Reports
children.push(
  h1("13. Reports"),
  para("Reports lists Excel downloads for the active period. Open a workbook in spreadsheet software. County packs can also be taken from a file Overview."),
  table(
    ["Report", "Contents"],
    [
      ["Collection progress", "Status and completion of every county file."],
      ["Questionnaire extract", "One row per county; institutional answers including the current A–J items."],
      ["Individual responses", "Every staff survey form, tagged to a county."],
      ["Market position", "Every county × job group: official, staff n, county and market percentiles, ratio, position, scale, plus SRC roll-up."],
      ["Job group pay", "Min, max, midpoint, SRC equivalent and allowances by group (A–U excluding I and O)."],
      ["Benefits matrix", "Every county’s benefits answers."],
      ["Document register", "What was requested, received, marked not available, and the file name. Download the files from the county file, not from this register."],
      ["County pack", "One county: instructions, questionnaire, jobs, comparators, benefits, documents, validation and analysis summary."],
    ],
    [2800, CONTENT_W - 2800]
  ),
  caption("Table 6. Report workbooks.")
);

// 14 Users audit data
children.push(
  h1("14. Users, audit trail and data administration"),
  h2("14.1 Users"),
  para("Create, edit, deactivate or (administrator only) delete a login. Deleting a login does not delete collected answers or audit rows. Type the username to confirm deletion. You cannot delete or deactivate your own account. Keep at least one active administrator."),
  para("Create missing county logins makes one respondent per active county that does not already have an active county login. Initial password is the bootstrap password; they must change it at first sign-in."),
  h2("14.2 Audit trail (administrator only)"),
  para(
    "Every signed-in action is recorded with time, account, role, county file where relevant, summary, and network address. Password values are not stored. Filter and download CSV. Collection administrators cannot open this page. The Activity list on a county file is only that file’s working history."
  ),
  h2("14.3 Data administration (administrator only)"),
  bullet("Delete collected data for one county — questionnaire, jobs, benefits, uploads, validation, clarifications and staff responses. The login and audit trail remain."),
  bullet("Delete data collected by one user — if they are a county respondent, that county file is cleared; files they uploaded are removed. The login remains."),
  bullet("Reset all collected survey data — no county files, answers, uploads, staff forms or comparator pay. Users, passwords, catalogues and the audit trail remain. Type RESET ALL COLLECTED DATA to confirm. Open county files again when you are ready to collect."),
  para("These tools are for test data you do not want in the live survey. They cannot be undone.")
);

// 15 Troubleshooting
children.push(
  h1("15. If something will not work"),
  table(
    ["What you see", "What to do"],
    [
      ["Sign-in returns Forbidden (403) on the live hostname", "The hostname must be in ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS (https://…). Restart after editing .env."],
      ["Asked to change password in a loop", "Complete Change password; the new password must be 10+ characters."],
      ["Cannot edit after submit", "Expected. Wait for a clarification, or ask a reviewer to return the file."],
      ["Can only edit one section after a clarification", "Edit that module, answer the clarification, then submit again."],
      ["Cannot submit", "Complete required items and certify if that rule is on. Read the message on Overview."],
      ["Market columns are blank", "Enter comparator pay for organisations included in the market median."],
      ["P25 and P75 are dashes", "Only one observation: P50 is shown. Quartiles need two or more figures or organisations."],
      ["Upload rejected", "Use an allowed file type and stay within the megabyte limit."],
      ["New job or document not on the file", "Open the file once more; structure is created on open."],
      ["Page missing from the menu", "It is not part of this role."],
      ["Cannot sign in", "Ask the person who issued the account. Confirm the account is active."],
    ],
    [3600, CONTENT_W - 3600]
  ),
  caption("Table 7. Common issues."),
  h2("15.1 Support"),
  para(
    "Use the support email set under Variables & settings. Do not send passwords. For deployment issues, confirm Python 3.11+, that migrate has been run on updates, and that .env was not overwritten when copying a new zip onto a live site."
  )
);

// 16 Appendix
children.push(
  h1("16. Appendix — job groups used for pay"),
  para(
    "County pay is collected for groups A, B, C, D, E, F, G, H, J, K, L, M, N, P, Q, R, S, T and U. Groups I and O are not used. SRC equivalent on each row is whatever denotation the county uses (for example EX4)."
  ),
  h2("16.1 Percentile method"),
  para(
    "DCollect uses inclusive linear interpolation (the same family as Excel PERCENTILE.INC). P50 is the median. With a single value, P25 and P75 are not displayed. Market percentiles are computed on organisation-level medians so that an employer with many jobs in a group is not counted many times."
  ),
  h2("16.2 Document control"),
  para(
    "This version describes DCollect as configured for the 2026 County Salary and Remuneration Review, including the questionnaire wording in sections E–J, job-group collection, document list without payroll extract or HR policy as upload types, analysis percentiles, and role-based navigation. Update this manual if the administrator adds questions or changes catalogues in a way that staff must follow."
  )
);

const doc = new Document({
  creator: "BINSTOPEJ Management Solutions Ltd",
  title: "DCollect User Manual",
  description: "Official user manual for the DCollect salary and remuneration survey platform.",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Calibri", color: NAVY },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 26, bold: true, font: "Calibri", color: NAVY },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1 },
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 24, bold: true, font: "Calibri", color: NAVY },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
      },
    ],
  },
  numbering,
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: 1280, right: MARGIN, bottom: 1280, left: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: GOLD, space: 6 } },
              spacing: { after: 120 },
              children: [
                run("DCollect User Manual", { size: 18, bold: true, color: NAVY }),
                run("    Confidential — authorised users only", { size: 18, color: MUTED }),
              ],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              border: { top: { style: BorderStyle.SINGLE, size: 6, color: "C5BBA8", space: 8 } },
              spacing: { before: 80 },
              children: [
                run("CPSB-NCF  ·  BINSTOPEJ Management Solutions Ltd  ·  Page ", { size: 16, color: MUTED }),
                new TextRun({ children: [PageNumber.CURRENT], font: "Calibri", size: 16, color: MUTED }),
              ],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT, buffer);
  fs.copyFileSync(OUT, DESKTOP);
  console.log("wrote", OUT);
  console.log("copied", DESKTOP);
  console.log("bytes", buffer.length);
});
