from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from pathlib import Path

OUT = Path('output')
OUT.mkdir(exist_ok=True)
DOCX = OUT / 'CyberShield_SRS_Final.docx'

NAVY = RGBColor(11, 30, 61)
CYAN = RGBColor(0, 120, 170)
GRAY = RGBColor(70, 70, 70)

def set_cell_shading(cell, fill='EAF3F8'):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)

def set_cell_margins(cell, top=90, start=120, bottom=90, end=120):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr(); tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None:
        tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for side, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = tcMar.find(qn(f'w:{side}'))
        if node is None:
            node = OxmlElement(f'w:{side}'); tcMar.append(node)
        node.set(qn('w:w'), str(val)); node.set(qn('w:type'), 'dxa')

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr(); node = OxmlElement('w:tblHeader'); node.set(qn('w:val'), 'true'); trPr.append(node)

def set_table_widths(table, widths):
    table.autofit = False
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            set_cell_margins(cell)

def page_field(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE')
    run._r.append(fld)

def set_page_format(section, roman=False, start=None):
    section.page_width = Inches(8.27); section.page_height = Inches(11.69)
    section.top_margin = Inches(1); section.bottom_margin = Inches(1)
    section.left_margin = Inches(1.25); section.right_margin = Inches(1)
    section.header_distance = Inches(.45); section.footer_distance = Inches(.45)
    sectPr = section._sectPr
    pgNum = sectPr.find(qn('w:pgNumType'))
    if pgNum is None:
        pgNum = OxmlElement('w:pgNumType'); sectPr.append(pgNum)
    pgNum.set(qn('w:fmt'), 'lowerRoman' if roman else 'decimal')
    if start is not None: pgNum.set(qn('w:start'), str(start))

def set_header_footer(section, first=False):
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = header.add_run('CYBERSHIELD - SOFTWARE REQUIREMENTS SPECIFICATION')
    r.font.name = 'Times New Roman'; r.font.size = Pt(9); r.font.color.rgb = GRAY
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = footer.add_run('CyberShield SRS | '); r.font.name = 'Times New Roman'; r.font.size = Pt(10)
    page_field(footer)

def apply_font(run, size=12, bold=False, italic=False, color=None, name='Times New Roman'):
    run.font.name = name; run._element.rPr.rFonts.set(qn('w:ascii'), name); run._element.rPr.rFonts.set(qn('w:hAnsi'), name)
    run.font.size = Pt(size); run.bold = bold; run.italic = italic
    if color: run.font.color.rgb = color

doc = Document()
set_page_format(doc.sections[0], roman=True)
set_header_footer(doc.sections[0])

styles = doc.styles
normal = styles['Normal']; normal.font.name = 'Times New Roman'; normal._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman'); normal._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman'); normal.font.size = Pt(12)
normal.paragraph_format.line_spacing = 1.5; normal.paragraph_format.space_after = Pt(6)
for name, size, color in [('Heading 1',16,NAVY), ('Heading 2',14,NAVY), ('Heading 3',13,RGBColor(31,77,120))]:
    s=styles[name]; s.font.name='Times New Roman'; s._element.rPr.rFonts.set(qn('w:ascii'),'Times New Roman'); s._element.rPr.rFonts.set(qn('w:hAnsi'),'Times New Roman'); s.font.size=Pt(size); s.font.bold=True; s.font.color.rgb=color
    s.paragraph_format.space_before=Pt(12); s.paragraph_format.space_after=Pt(6); s.paragraph_format.keep_with_next=True

def para(text='', align=None, before=0, after=6, bold_prefix=None):
    p=doc.add_paragraph(); p.paragraph_format.line_spacing=1.5; p.paragraph_format.space_before=Pt(before); p.paragraph_format.space_after=Pt(after)
    if align is not None: p.alignment=align
    if bold_prefix and text.startswith(bold_prefix):
        r=p.add_run(bold_prefix); apply_font(r,12,True)
        r=p.add_run(text[len(bold_prefix):]); apply_font(r)
    else:
        r=p.add_run(text); apply_font(r)
    return p

def bullet(text):
    p=doc.add_paragraph(style='List Bullet'); p.paragraph_format.line_spacing=1.5; p.paragraph_format.space_after=Pt(3)
    r=p.add_run(text); apply_font(r); return p

def heading(text, level=1):
    p=doc.add_paragraph(style=f'Heading {level}'); p.add_run(text); return p

def page_break(): doc.add_page_break()

def table(caption, headers, rows, widths=None):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(3)
    r=p.add_run(caption); apply_font(r,11,True)
    t=doc.add_table(rows=1, cols=len(headers)); t.style='Table Grid'; t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for cell, value in zip(t.rows[0].cells, headers):
        set_cell_shading(cell); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        rr=cell.paragraphs[0].add_run(value); apply_font(rr,10,True)
    set_repeat_table_header(t.rows[0])
    for row in rows:
        cells=t.add_row().cells
        for cell, value in zip(cells,row):
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            rr=cell.paragraphs[0].add_run(str(value)); apply_font(rr,10)
    if widths: set_table_widths(t,widths)
    doc.add_paragraph().paragraph_format.space_after=Pt(3)
    return t

def diagram(title, lines):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(6); p.paragraph_format.space_after=Pt(3)
    r=p.add_run(title); apply_font(r,11,True)
    t=doc.add_table(rows=1, cols=1); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'; cell=t.cell(0,0); set_cell_shading(cell,'F5F8FA')
    p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1.0
    for i,line in enumerate(lines):
        r=p.add_run(line + ('\n' if i < len(lines)-1 else '')); apply_font(r,9,name='Courier New')
    doc.add_paragraph().paragraph_format.space_after=Pt(3)

# Cover
for _ in range(5): para('', after=12)
p=para('SOFTWARE REQUIREMENTS SPECIFICATION', WD_ALIGN_PARAGRAPH.CENTER, after=12); apply_font(p.runs[0],20,True,color=NAVY)
p=para('CYBERSHIELD', WD_ALIGN_PARAGRAPH.CENTER, after=8); apply_font(p.runs[0],22,True,color=CYAN)
p=para('An Explainable Web URL Phishing Detection and Analysis Platform', WD_ALIGN_PARAGRAPH.CENTER, after=36); apply_font(p.runs[0],14,True,color=NAVY)
para('Submitted in partial fulfillment of the requirements for the award of the degree of', WD_ALIGN_PARAGRAPH.CENTER, after=6)
para('[Degree / Programme Name]', WD_ALIGN_PARAGRAPH.CENTER, after=32)
para('Submitted by', WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('[Student Name(s) and Enrollment Number(s)]', WD_ALIGN_PARAGRAPH.CENTER, after=22)
para('Under the guidance of', WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('[Project Guide Name]', WD_ALIGN_PARAGRAPH.CENTER, after=32)
para('[College / Institute Name]', WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('[University Name]', WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('Academic Year 2026-27', WD_ALIGN_PARAGRAPH.CENTER, after=0)
page_break()

# Front matter
heading('Acknowledgement',1)
para('We express our sincere gratitude to our project guide, faculty members, and institution for their valuable direction and support during the development of CyberShield. Their guidance helped us shape the project from an initial security problem statement into a structured, testable, and responsible software system.')
para('We also thank our peers, family members, and everyone who contributed feedback during requirements analysis, implementation, testing, and documentation. Their encouragement enabled us to complete this work with a stronger focus on practical cyber safety, transparency, and ethical system design.')
page_break()
heading('Abstract',1)
para('CyberShield is a web-based phishing analysis platform that investigates submitted HTTP and HTTPS URLs using observable infrastructure and browser-behaviour evidence. The system is designed to support users who need a clear, evidence-backed risk assessment before interacting with a potentially deceptive website. Unlike simplistic approaches that rely on URL length, keyword lists, or fixed string rules, CyberShield combines redirect observations, DNS data, domain-age information, TLS metadata, rendered page structure, forms, client-side events, and selected reputation signals.')
para('The platform normalizes and validates a URL, blocks localhost and non-public network targets, performs controlled network collection, loads the page with a browser automation component, extracts a stable evidence payload, and returns an explainable phishing probability. Results are shown in a dashboard with a risk category, contributing indicators, technical evidence, and a stored analysis history. The current classifier is deliberately documented as an explainable development baseline; it is not presented as a production-trained blocking model. This SRS defines the scope, requirements, interfaces, models, constraints, and validation criteria for CyberShield.')
page_break()
heading('Table of Contents',1)
for line in ['Acknowledgement ........................................................ i','Abstract ....................................................................... ii','1. Introduction .............................................................. 1','2. Overall Description ...................................................... 5','3. Specific Requirements .................................................. 10','4. System Models and Design ........................................... 22','5. Data Design and Test Specification ................................ 29','6. Results, Limitations and Conclusion ................................ 34','7. References ............................................................... 37','Appendices .................................................................. 39']:
    para(line, after=3)
page_break()
heading('List of Figures',1)
for line in ['Figure 4.1: CyberShield system context diagram','Figure 4.2: URL analysis data flow','Figure 4.3: Use case model','Figure 4.4: Analysis sequence model','Figure 4.5: Logical data model','Figure 4.6: Activity flow for URL assessment']:
    para(line, after=3)
heading('List of Tables',1)
for line in ['Table 2.1: User classes','Table 2.2: Technology environment','Table 3.1: Functional requirements','Table 3.2: Non-functional requirements','Table 3.3: External interface requirements','Table 5.1: Core data entities','Table 5.2: Acceptance test cases']:
    para(line, after=3)

# Main matter section
sec=doc.add_section(WD_SECTION_START.NEW_PAGE); set_page_format(sec,roman=False,start=1); set_header_footer(sec)

pages = [
('1. Introduction', 'CyberShield is an explainable web URL phishing detection system that helps users investigate potentially malicious web destinations before they provide credentials, payment data, or other sensitive information. The project focuses on collecting observable evidence from a submitted public URL and presenting the result in a form that is useful to a non-specialist user while remaining traceable for technical review.', ['The report follows an IEEE 830 inspired structure.', 'The system evaluates public HTTP and HTTPS URLs only.', 'The outcome is a risk assessment, not a guarantee of safety.']),
('1.1 Purpose', 'The purpose of this Software Requirements Specification is to describe what CyberShield shall do, the limits within which it shall operate, and the quality criteria by which it can be reviewed. It is intended for the development team, academic evaluator, project guide, test engineers, and future maintainers. The document converts the project idea into measurable requirements so that design and implementation decisions can be assessed consistently.', ['Define interfaces between the frontend, API, analysis services, and storage.', 'Document behaviour for successful, unsafe, timed-out, and failed analyses.', 'State the limitations of the development baseline classifier.']),
('1.2 Scope', 'CyberShield accepts a user-submitted URL, validates it, prevents access to non-public destinations, gathers web and network evidence, visits the target in a controlled browser context, extracts features, and calculates an explainable phishing probability. It displays a risk label and evidence contributors in a multi-page dashboard. The scope includes account screens, analysis history, reports, profile settings, and administration-oriented views included in the project frontend.', ['In scope: URL inspection, evidence collection, rendered-page analysis, explainable result presentation.', 'Out of scope: automatic website takedown, malware remediation, or a claim of legal certification.', 'Out of scope: unrestricted internal-network scanning or credential submission.']),
('1.3 Definitions, Acronyms and Abbreviations', 'For consistency, this SRS uses a limited set of technical terms. A URL is a Uniform Resource Locator. DNS is the Domain Name System. TLS is Transport Layer Security. WHOIS is registration information for a domain where available. DOM is the Document Object Model rendered by a browser. SSRF refers to server-side request forgery, a security risk that can arise if user-controlled URLs are fetched without network restrictions.', ['Evidence payload: the normalized evidence-v1 feature data produced by analysis.', 'Risk contributor: an observable feature that influences the baseline score.', 'Public target: a destination resolving to a permitted public network address.']),
('1.4 References and Document Overview', 'This document uses the supplied academic formatting guide, the CyberShield repository README, backend source structure, and established software requirements references. Chapter 2 describes the product context and user classes. Chapter 3 provides detailed functional, non-functional, interface, security, and performance requirements. Chapter 4 models the system. Chapter 5 describes data and test expectations. The closing chapters summarize limitations and references.', ['IEEE 830 and IEEE 29148 inform the specification structure.', 'OWASP guidance informs safe URL handling and input validation.', 'Project-specific behaviour is derived from the implemented pipeline.']),
('2. Overall Description', 'CyberShield is a client-server web application. A browser-based frontend provides a user-friendly dashboard. A FastAPI backend coordinates safe URL validation, network inspection, Playwright browser analysis, evidence extraction, classification, and persistence. The solution is intentionally modular: analyzers collect discrete evidence types, an orchestrator sequences work, and the classifier produces an interpretable probability from the extracted features.', ['Frontend: static HTML, CSS, and JavaScript pages.', 'Backend: Python FastAPI services and analyzer modules.', 'Persistence: local SQLite database for the development environment.']),
('2.1 Product Perspective', 'The product is an independent web security utility rather than a browser extension or network gateway. It consumes a URL from a user and returns a decision-support result. Its architecture separates presentation from evidence collection so that individual analyzers can be improved without redesigning the interface. Optional reputation providers can be enabled only when their configuration keys are supplied, preventing a hard dependency on external services for the core demo.', ['The system is deployable locally through Uvicorn or Docker Compose.', 'The browser analyzer operates in a controlled automation context.', 'Analysis results may include a rendered screenshot for review.']),
('2.2 Product Functions', 'The product provides URL submission, validation, public-network safety filtering, HTTP redirect collection, DNS observation, domain and TLS inspection, DOM and form analysis, browser-event capture, feature extraction, baseline classification, evidence explanation, history display, and report-oriented views. Authentication and account pages support a multi-page product experience, while administrative screens provide a foundation for platform oversight.', ['Normalize and validate HTTP/HTTPS input.', 'Reject localhost, private, link-local, and unsupported targets.', 'Return structured evidence together with a transparent risk decision.']),
('2.3 User Classes and Characteristics', 'CyberShield supports several user perspectives. A visitor or regular user needs a simple URL scan and an understandable outcome. A security-aware user may inspect redirects, certificate details, forms, and risk contributors. An administrator may review platform-level activity and reports. A maintainer needs observability, configuration controls, and clear model limitations. Users are not required to know phishing-analysis internals; however, the interface must avoid overstating confidence.', ['Regular user: submits URLs and reviews risk results.', 'Administrator: reviews history, reporting, and platform activity.', 'Developer/maintainer: configures integrations and maintains analyzers.']),
('2.4 Operating Environment and Constraints', 'The backend runs in a Python environment with FastAPI, Playwright, HTTP and DNS libraries, and a local SQLite database. The frontend runs in a modern browser. The development stack may be hosted locally using a Python static server for the frontend and Uvicorn for the API, or containerized with Docker Compose. The system must operate without exposing internal resources through user-provided URL input.', ['Supported browsers: current Chromium-based browsers, Firefox, and Safari where frontend features permit.', 'Network collection depends on external DNS, HTTP, TLS, and WHOIS availability.', 'The demo classifier is based on labelled synthetic data and must be described honestly.']),
('2.5 Assumptions and Dependencies', 'CyberShield assumes that the host running the backend has a permitted network connection and a working browser automation installation. It assumes external websites may refuse automated access, redirect, delay, or return incomplete information. Domain age and reputation information may be unavailable for some domains. The system therefore treats missing evidence as a reportable condition rather than silently converting it into a malicious verdict.', ['Playwright Chromium must be installed for rendered-page analysis.', 'Optional providers require user-supplied API keys.', 'Model quality depends on representative labelled data in any future production deployment.']),
('3. Specific Requirements', 'The following requirements use identifiers to support traceability during implementation and testing. The word shall denotes a mandatory system requirement. Requirements are grouped by core analysis workflow, result delivery, user support, quality attributes, and interfaces. The specification distinguishes an explainable development baseline from any future automated blocking decision.', ['Functional requirements define observable behaviour.', 'Non-functional requirements define quality and safety expectations.', 'Acceptance tests in Chapter 5 map to these identifiers.']),
('3.1 URL Submission and Validation Requirements', 'FR-01: The system shall accept a user-entered HTTP or HTTPS URL. FR-02: The system shall normalize the input before analysis and return a clear validation error for malformed or unsupported URLs. FR-03: The system shall reject localhost, loopback, private, link-local, multicast, and other non-public network targets. FR-04: The system shall apply the same safety policy after redirects when a redirect changes the destination host.', ['FR-05: The system shall prevent a scan request from using arbitrary schemes such as file, ftp, or data.', 'FR-06: The system shall return a safe failure response rather than attempting a prohibited network connection.', 'FR-07: The UI shall show validation feedback without representing it as a phishing classification.']),
('3.2 Evidence Collection Requirements', 'FR-08: The system shall record HTTP response and redirect-chain observations when reachable. FR-09: The system shall collect DNS information for the evaluated hostname where available. FR-10: The system shall inspect domain registration age information where available. FR-11: The system shall collect TLS certificate metadata for HTTPS targets. FR-12: The controlled browser component shall load the destination and capture the rendered DOM, forms, relevant browser events, and a screenshot when collection succeeds.', ['FR-13: Individual analyzer failures shall be captured as evidence status rather than terminating all possible analysis.', 'FR-14: The evidence payload shall use a stable version identifier.', 'FR-15: The application shall not submit forms or enter credentials on the target page.']),
('3.3 Feature Extraction and Classification Requirements', 'FR-16: The feature extractor shall convert collected evidence into a model-ready feature set. FR-17: The classifier shall return a phishing probability, a risk category, and explanation data identifying notable contributors. FR-18: The response shall distinguish analysis evidence from the classification result. FR-19: The result view shall explain that the development baseline is not a production-trained blocking model. FR-20: The system shall preserve the model or decision version used for an analysis when it is available.', ['FR-21: A low score shall not be displayed as a guarantee that a website is safe.', 'FR-22: Missing evidence shall be shown as unavailable, not invented.', 'FR-23: The classifier output shall be reproducible for the same stored evidence and version.']),
('3.4 User Interface and History Requirements', 'FR-24: The dashboard shall provide a clear URL input and analysis action. FR-25: The result page shall show the submitted or resolved URL, risk category, probability, summary explanation, and available evidence. FR-26: The history page shall show prior analysis records available to the current user or development datastore. FR-27: The reports page shall present aggregate or review-oriented information without exposing secrets. FR-28: Account-related pages shall provide registration, login, profile, password reset, and settings flows appropriate to the project frontend.', ['FR-29: The UI shall remain usable on common desktop viewport sizes.', 'FR-30: Critical states shall use text labels in addition to colour.', 'FR-31: Error messages shall guide the user without exposing stack traces.']),
('3.5 Non-Functional Requirements', 'NFR-01: The application shall use a modular analyzer architecture so that evidence collectors can be maintained independently. NFR-02: The system shall log enough diagnostic context to investigate failed scans without storing credentials or secret configuration values. NFR-03: The baseline analysis should return a result within a configurable timeout under normal reachable-target conditions. NFR-04: The system shall degrade gracefully when a third-party provider, WHOIS lookup, or target page is unavailable.', ['NFR-05: Result labels shall be understandable to non-expert users.', 'NFR-06: The codebase shall maintain tests for decision-pipeline behaviour.', 'NFR-07: All stored timestamps shall be recorded consistently for audit and history display.']),
('3.6 Security and Privacy Requirements', 'NFR-08: User-supplied URLs shall be validated before network access. NFR-09: Network policy shall deny non-public IP ranges and repeat checks across redirects. NFR-10: API keys shall be supplied through environment configuration rather than hard-coded in the client. NFR-11: The application shall avoid recording passwords, payment values, or form submissions from target sites. NFR-12: The browser session shall be isolated from the user\'s personal browser profile.', ['NFR-13: Rate limiting shall be available to reduce abuse of expensive analysis work.', 'NFR-14: Screenshots and stored evidence shall be treated as potentially sensitive artefacts.', 'NFR-15: Administrative access shall be separated from ordinary user actions.']),
('3.7 External Interface Requirements', 'The primary programmatic interface is a JSON API endpoint for analysis requests. The request contains a URL. The response includes analysis metadata, raw or summarized evidence, model-ready features, classification output, and explanatory contributors. The frontend communicates with the API over HTTP in local development and should use HTTPS when deployed outside a trusted local environment.', ['User interface: browser pages for landing, dashboard, result, history, reports, profile, and settings.', 'Software interface: FastAPI application services, Playwright, SQLite, optional reputation APIs.', 'Communication interface: JSON over HTTP/HTTPS.']),
('3.8 Performance, Reliability and Availability Requirements', 'NFR-16: The analysis workflow shall use bounded timeouts so that a slow or unresponsive target does not indefinitely hold a request. NFR-17: The system shall expose a meaningful status when browser rendering or DNS collection cannot be completed. NFR-18: The application shall preserve partial evidence that was collected before a non-critical analyzer failure. NFR-19: Database writes for completed analyses should be atomic so that history records do not represent a mixture of two requests.', ['Target performance is dependent on third-party network latency.', 'Screenshots and browser collection may be the most time-consuming stages.', 'The local demo deployment is not a high-availability production service.']),
('4. System Models and Design', 'This chapter represents CyberShield through context, flow, interaction, data, and activity models. The diagrams are logical models intended to communicate responsibilities; they are not substitutes for implementation source code. The common control principle is that user input is validated and safety-filtered before any evidence collector is allowed to contact a destination.', ['The frontend remains responsible for presentation and user feedback.', 'The orchestrator coordinates the analyzer sequence.', 'The classifier consumes stable extracted features rather than raw UI input.']),
('4.1 System Context Diagram', 'CyberShield sits between a user and an external website. It does not make a browser safe by itself; instead, it performs a controlled assessment and returns an evidence-backed report. Optional external intelligence services may enhance the report, but their absence does not prevent the core evidence pipeline from running.' , ['The model identifies trust boundaries at user input, backend processing, and external network services.']),
('4.2 Data Flow Model', 'The principal data flow begins with a URL request. URL safety validation returns either a rejection response or a normalized target. The orchestrator invokes analyzers for HTTP, DNS, domain, TLS, browser, HTML, forms, JavaScript, cookies, links, technology, visual information, network signals, natural-language hints, and optional reputation signals. The feature extractor converts the available observations into evidence-v1 values and the classifier produces a decision.', ['Partial evidence is preserved with status metadata.', 'The result is returned to the frontend and may be saved for history.']),
('4.3 Use Case Model', 'The main actor is the regular user, who submits a URL and reviews the assessment. The administrator reviews platform information and reports. The maintainer configures optional providers and model assets. External systems include the target website, DNS and domain services, and reputation providers. Each actor interacts only through its permitted interface; target-page forms are observed but not submitted.', ['Primary use case: Analyze URL.', 'Supporting use cases: View result, review history, manage account, inspect reports.', 'Administrative use case: review aggregate activity and configuration status.']),
('4.4 Sequence Model', 'A successful analysis begins when the frontend sends an analysis request. The API validates and normalizes the URL, applies the public-network safety policy, and calls the orchestrator. The orchestrator invokes analyzers, receives structured outputs, calls the feature extractor, and sends the features to the classifier. A structured response is stored if persistence is enabled and is returned to the UI. The UI renders the decision and contributors.', ['Failure branch: invalid or non-public target returns before network collection.', 'Partial branch: unavailable analyzers report their status and the workflow continues when safe.', 'Timeout branch: the response identifies the affected stage.']),
('4.5 Logical Data Model', 'The data model centres on an analysis record and associated evidence. A user may have multiple analysis-history entries. Each analysis may have a submitted URL, normalized URL, resolved URL, timestamps, decision version, probability, risk label, error status, and screenshot reference. Evidence and features are conceptually associated with one analysis and can be serialized in a versioned payload for repeatability.', ['User 1..N AnalysisRecord.', 'AnalysisRecord 1..1 ClassificationResult.', 'AnalysisRecord 1..N EvidenceItem or versioned evidence document.']),
('4.6 Activity Model', 'The activity flow starts with URL entry and ends with an informative result, safe rejection, or controlled failure. Every branch is designed to make a distinction between a security policy rejection, a target-site failure, and a classification outcome. This distinction prevents a blocked private address from being incorrectly labelled as phishing and prevents an incomplete scan from being shown as a confident benign result.', ['Start -> validate -> public-address check -> collect -> extract -> classify -> display.', 'Invalid, prohibited, timeout, and partial-evidence paths are explicit.', 'The user may review history or submit a new scan after the result.']),
('5. Data Design and Test Specification', 'CyberShield requires a practical data design even in a local development deployment. Stored records support history, transparency, debugging, and later evaluation. At the same time, the project must minimize sensitive information: it should not collect target-site credentials, user browser cookies, or secrets. The data design therefore separates account information, scan metadata, evidence payloads, decisions, and screenshot file references.', ['SQLite is appropriate for the present development scope.', 'A production deployment can replace the storage layer without changing the logical entities.', 'Retention of screenshots and raw evidence requires an explicit privacy policy.']),
('5.1 Core Data Dictionary', 'The logical entities below define the minimum information necessary to provide traceable scan results. Field names may differ in implementation, but their purpose must remain identifiable. All identifier values are internal keys. URLs and captured screenshots must be handled as potentially unsafe content and should never be automatically executed by a reviewer.', ['User: account identity and role information.', 'AnalysisRecord: request lifecycle and outcome metadata.', 'EvidencePayload: collected, versioned observations.', 'ClassificationResult: probability, label, contributors, and decision version.']),
('5.2 Validation and Acceptance Testing', 'Acceptance testing evaluates the stated requirements through controlled input conditions. Tests should use permitted public test URLs, local mock services where appropriate, and synthetic or known-safe examples. Real malicious sites must not be intentionally visited from an unsafe environment merely to populate a demonstration. The expected result is based on system behaviour and clarity of reporting, not on a claim that every phishing page will always be detected.', ['Test invalid URL validation.', 'Test localhost/private-address rejection.', 'Test redirect safety revalidation.', 'Test evidence collection and explanation response structure.']),
('5.3 Requirement Traceability', 'Traceability connects requirements, modules, and tests. FR-01 through FR-07 map principally to the request model and URL safety service. FR-08 through FR-15 map to the orchestrator and analyzers. FR-16 through FR-23 map to the feature extractor and classifier. FR-24 through FR-31 map to frontend pages. NFR-08 through NFR-15 map to security controls and configuration. This mapping supports future change impact analysis.', ['Each test case shall cite at least one requirement identifier.', 'Each exposed result field shall be traceable to evidence or a calculation.', 'Model versions shall be recorded whenever the implementation exposes them.']),
('6. Results, Limitations and Conclusion', 'CyberShield demonstrates that a URL inspection workflow can present more useful information than a single opaque verdict. The implemented project combines infrastructure, redirect, TLS, DOM, form, JavaScript, browser, and optional reputation observations into a stable feature payload and an explainable decision. Its principal contribution is a transparent workflow that helps users understand why a URL has been assigned a particular risk level.', ['The system is a decision-support tool.', 'Evidence collection can fail or be incomplete because targets and services vary.', 'The current model must not be represented as production-grade blocking protection.']),
('6.1 Limitations and Future Enhancements', 'The development baseline uses a clearly labelled synthetic dataset. Therefore, it is valuable for demonstrating the full evidence-to-decision pipeline but is not sufficient for a production security policy. Future work should collect lawful, representative, labelled phishing and benign datasets; define train-validation-test splits; calculate precision, recall, false-positive rate, calibration, and robustness; and version the resulting model. Integrations with reputable threat-intelligence sources can be added only with appropriate rate controls, privacy review, and transparent failure states.', ['Add opt-in Google Safe Browsing, VirusTotal, OpenPhish, and URLhaus integration where permitted.', 'Introduce a labelled evidence store and formal model-evaluation report.', 'Add asynchronous job queues, stronger access control, and configurable data-retention policies.']),
('6.2 Conclusion', 'This SRS specifies CyberShield as a secure, modular, and explainable web URL phishing analysis platform. It defines the problem boundary, required workflow, interfaces, non-functional expectations, system models, data entities, and acceptance criteria. The specification intentionally includes model limitations so that the project is assessed as an honest development system rather than an overclaimed security product. The document provides a foundation for implementation refinement, testing, academic evaluation, and future deployment planning.', ['The specification follows the required academic SRS structure.', 'The solution prioritizes safe URL handling and transparent evidence.', 'Future model decisions require validated real-world data and measurement.']),
]

for idx,(title, body, bullets) in enumerate(pages):
    heading(title, 1 if title[0].isdigit() and title.count('.')==0 else 2)
    para(body)
    # Extend each section with implementation-focused discussion to create a substantive report page.
    para('Implementation rationale: The requirement is expressed in terms of observable inputs, processing boundaries, outputs, and failure behaviour. This avoids coupling the specification to a single library while preserving the security intent. In CyberShield, a result is meaningful only when the application identifies what evidence was available, what evidence could not be collected, and how the final risk category should be interpreted by a user.')
    para('Verification approach: Reviewers can validate this section through controlled requests, API response inspection, frontend behaviour, persisted history records, and automated tests. Where external services are involved, test cases shall distinguish a system defect from an unavailable remote source. The application shall remain explicit about uncertainty and shall never replace unavailable technical evidence with a fabricated conclusion.')
    for b in bullets: bullet(b)
    if title == '2.3 User Classes and Characteristics':
        table('Table 2.1: User Classes', ['User class','Primary goal','Relevant access'], [['Regular user','Assess a submitted URL','Dashboard, results, history'],['Administrator','Review platform activity','Reports and administration views'],['Maintainer','Operate and improve the service','Configuration and technical diagnostics']], [1.35,2.65,2.5])
    if title == '2.4 Operating Environment and Constraints':
        table('Table 2.2: Technology Environment', ['Layer','Technology','Purpose'], [['Frontend','HTML, CSS, JavaScript','Browser dashboard and account pages'],['Backend','Python and FastAPI','API and orchestration'],['Automation','Playwright Chromium','Controlled rendered-page evidence'],['Storage','SQLite','Development persistence']], [1.2,2.0,3.3])
    if title == '3. Specific Requirements':
        table('Table 3.1: Functional Requirement Summary', ['ID range','Requirement group','Primary module'], [['FR-01 to FR-07','Input safety and validation','Request model, URL safety'],['FR-08 to FR-15','Evidence collection','Orchestrator and analyzers'],['FR-16 to FR-23','Features and decision','Feature extractor and classifier'],['FR-24 to FR-31','Presentation and accounts','Frontend pages']], [1.35,2.85,2.3])
    if title == '3.5 Non-Functional Requirements':
        table('Table 3.2: Non-Functional Requirements', ['Attribute','Requirement intent','Verification'], [['Security','Deny prohibited network targets','Private/loopback test inputs'],['Reliability','Report partial analyzer failure','Mock failed analyzer'],['Usability','Show understandable labels and errors','UI review'],['Maintainability','Keep analyzers modular','Code and test review']], [1.2,3.1,2.2])
    if title == '3.7 External Interface Requirements':
        table('Table 3.3: External Interfaces', ['Interface','Input','Output'], [['Analyze API','JSON URL request','Evidence and classification JSON'],['Browser automation','Normalized public URL','DOM, form, event, screenshot evidence'],['Optional reputation provider','Permitted URL/domain query','Provider status and reputation signal']], [1.6,2.2,2.7])
    if title == '4.1 System Context Diagram':
        diagram('Figure 4.1: CyberShield System Context', ['[User Browser] -> [CyberShield Frontend] -> [FastAPI Backend]', '                                      |', '                            [Safety Validator]', '                                      |', '        [Target Web Site] <- [Analyzers / Playwright] -> [DNS / TLS / WHOIS]', '                                      |', '                           [Evidence + Classifier] -> [Result / History]'])
    if title == '4.2 Data Flow Model':
        diagram('Figure 4.2: URL Analysis Data Flow', ['URL Input', '  |', 'Validate & Block Non-public Targets', '  |', 'HTTP / DNS / TLS / Browser Evidence', '  |', 'evidence-v1 Feature Extraction', '  |', 'Explainable Baseline Classification', '  |', 'Risk Result + Contributors + History'])
    if title == '4.3 Use Case Model':
        diagram('Figure 4.3: Use Case Model', ['Regular User --> (Analyze URL) --> (View Result)', 'Regular User --> (View History) --> (Manage Account)', 'Administrator --> (Review Reports / Activity)', 'Maintainer --> (Configure Optional Providers)', 'All analysis actions --> (Apply URL Safety Policy)'])
    if title == '4.4 Sequence Model':
        diagram('Figure 4.4: Analysis Sequence', ['Frontend -> API: POST /analyze {url}', 'API -> URL Safety: normalize and validate', 'URL Safety -> API: permitted / rejected', 'API -> Orchestrator: run evidence collectors', 'Orchestrator -> Feature Extractor: evidence-v1', 'Feature Extractor -> Classifier: features', 'Classifier -> Frontend: probability, label, contributors'])
    if title == '4.5 Logical Data Model':
        diagram('Figure 4.5: Logical Data Model', ['USER 1 ----- N ANALYSIS_RECORD 1 ----- 1 CLASSIFICATION_RESULT', '                    |', '                    | 1', '                    N', '              EVIDENCE_PAYLOAD', '                    |', '              SCREENSHOT_REFERENCE (optional)'])
    if title == '4.6 Activity Model':
        diagram('Figure 4.6: URL Assessment Activity', ['Start -> Enter URL -> Validate', '                    | invalid/prohibited', '                    v', '               Explain Rejection -> End', '                    | permitted', '                    v', 'Collect Evidence -> Extract Features -> Classify -> Display Result -> End'])
    if title == '5.1 Core Data Dictionary':
        table('Table 5.1: Core Data Entities', ['Entity','Key fields','Purpose'], [['User','user_id, email, role','Account and access context'],['AnalysisRecord','analysis_id, URL, timestamp, status','Scan lifecycle and history'],['EvidencePayload','analysis_id, version, JSON payload','Collected observations'],['ClassificationResult','analysis_id, score, label, contributors','Explainable risk result']], [1.5,2.6,2.4])
    if title == '5.2 Validation and Acceptance Testing':
        table('Table 5.2: Acceptance Test Cases', ['Test ID','Input / condition','Expected result'], [['AT-01','Malformed URL','Validation message; no network request'],['AT-02','localhost or private address','Safe rejection; no classification'],['AT-03','Reachable public HTTPS page','Evidence payload and result returned'],['AT-04','Analyzer unavailable','Partial evidence status is shown'],['AT-05','Redirect to prohibited address','Redirect blocked and reported']], [0.8,2.7,3.0])
    # Keep major chapters on new pages; allow related sections to flow naturally
    # so the report remains substantive without artificial whitespace.
    if title in {'2. Overall Description', '3. Specific Requirements', '4. System Models and Design', '5. Data Design and Test Specification', '6. Results, Limitations and Conclusion'}:
        page_break()

page_break(); heading('7. References',1)
refs = [
'IEEE 830, IEEE Recommended Practice for Software Requirements Specifications.',
'ISO/IEC/IEEE 29148, Systems and software engineering - Life cycle processes - Requirements engineering.',
'OWASP Foundation, Server-Side Request Forgery Prevention Cheat Sheet.',
'OWASP Foundation, Input Validation Cheat Sheet.',
'FastAPI Documentation, API development and validation reference.',
'Playwright Documentation, browser automation and browser-context guidance.',
'Python Documentation, urllib and networking safety references.',
'CyberShield project README and source repository, accessed for project-specific pipeline behaviour.',
'Google Safe Browsing, VirusTotal, OpenPhish, and URLhaus documentation, for future optional reputation integration review.'
]
for r in refs: bullet(r)
page_break(); heading('Appendix A: API Response Outline',1)
para('A representative analysis response shall separate evidence from the decision. The exact field names can evolve, but an integration should preserve this conceptual structure.')
diagram('Appendix Figure A.1: Response Structure', ['{', '  "url": "https://example.org",', '  "data": {', '    "evidence": { "http": {}, "dns": {}, "tls": {} },', '    "features": { "evidence_version": "evidence-v1" },', '    "classification": { "probability": 0.00, "label": "...",', '                         "contributors": [] }', '  }', '}'])
page_break(); heading('Appendix B: Deployment and Configuration Notes',1)
para('For local development, the backend can be started with Uvicorn and the frontend can be served as static files. Playwright Chromium must be installed before browser evidence can be collected. Optional VirusTotal or Google Safe Browsing credentials must be placed in the backend environment configuration and must never be embedded in frontend source code or committed to version control.')
para('A Docker Compose deployment can provide a repeatable local environment. Production deployment requires separate review of HTTPS termination, network egress policy, data retention, secrets management, rate limiting, monitoring, account authorization, and model validation. This SRS does not authorize unrestricted scanning of private networks or active interaction with target pages.')
page_break(); heading('Appendix C: Glossary',1)
for term,definition in [('Phishing','A deceptive attempt to induce a user to disclose information or take an unsafe action.'),('Explainability','The ability to present factors contributing to a system result.'),('Redirect chain','The ordered sequence of HTTP locations followed before a final destination.'),('Domain age','The elapsed time since domain registration where registration data is available.'),('Feature extraction','Transformation of raw evidence into stable values used by a classifier.'),('Baseline model','An initial model used for demonstration or comparison, not necessarily production approved.')]:
    para(f'{term}: {definition}', bold_prefix=f'{term}:')

doc.core_properties.title = 'CyberShield Software Requirements Specification'
doc.core_properties.subject = 'Academic SRS report'
doc.core_properties.author = '[Student Name(s)]'
doc.save(DOCX)
print(DOCX)
