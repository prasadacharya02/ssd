# victim_server/create_fake_files.py
# ============================================================
# Creates realistic-looking user files for the victim machine
# ============================================================
import os
import random
import io
import struct
import zlib
import zipfile
from datetime import datetime, timedelta
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_files")
DEFAULT_SEED = 1337
FIXTURE_DATE = datetime(2024, 10, 1)
# ═══════════════════════════════════════════════════
# FILE CONTENT GENERATORS
# ═══════════════════════════════════════════════════
def make_financial_report():
    return f"""FINANCIAL REPORT - Q3 2024
Company: Acme Corporation
Prepared by: Finance Department
Date: {FIXTURE_DATE.strftime('%Y-%m-%d')}
EXECUTIVE SUMMARY
=================
Q3 revenue increased by 12.4% compared to Q2.
Operating expenses remained stable at $2.4M.
Net profit margin improved to 18.7%.
QUARTERLY BREAKDOWN
===================
Revenue:              $8,450,000
Cost of Goods:        $3,200,000
Operating Expenses:   $2,400,000
Net Profit:           $1,580,000
DEPARTMENT PERFORMANCE
======================
Sales:        Exceeded target by 15%
Marketing:    Campaign ROI 3.2x
Engineering:  4 major releases delivered
Support:      98.2% CSAT score
RISK FACTORS
============
- Supply chain disruptions in Asia
- Rising material costs
- Currency fluctuations
""" * 20
def make_client_notes():
    return f"""CLIENT MEETING NOTES
Date: {FIXTURE_DATE.strftime('%Y-%m-%d')}
Attendees: John Smith, Sarah Johnson, Mike Chen
AGENDA
======
1. Q4 project timeline review
2. Budget approval for new features
3. Resource allocation discussion
4. Contract renewal terms
DISCUSSION POINTS
=================
The client requested additional features for Phase 2.
Timeline needs to be extended by 3 weeks.
Budget increase of $45,000 approved.
New team member to join next month.
ACTION ITEMS
============
- Send updated proposal by Friday
- Schedule follow-up call for next Tuesday
- Prepare technical specifications
- Review contract amendments
NEXT STEPS
==========
Follow up on all action items within 48 hours.
""" * 15
def make_tax_returns():
    return f"""INDIVIDUAL TAX RETURN - 2024
Taxpayer: John Doe
SSN: XXX-XX-1234
Filing Status: Married Filing Jointly
INCOME
======
Wages (W-2):              $125,000
Interest Income:            $2,450
Dividend Income:            $3,200
Capital Gains:              $8,500
Total Income:             $139,150
DEDUCTIONS
==========
Standard Deduction:        $27,700
Charitable Contributions:   $3,500
Mortgage Interest:          $8,200
State/Local Taxes:         $10,000
TAX CALCULATION
===============
Taxable Income:           $89,750
Federal Tax:              $12,450
State Tax:                 $4,200
Total Tax:                $16,650
REFUND STATUS
=============
Withholdings:             $18,200
Refund Due:                $1,550
""" * 12
def make_employee_records():
    lines = ["EMPLOYEE RECORDS - HR DEPARTMENT\n"]
    lines.append("=" * 60 + "\n")
    for i in range(50):
        lines.append(f"""
Employee ID: EMP-{1000 + i}
Name: Employee_{i}
Department: {random.choice(['Engineering', 'Sales', 'Marketing', 'HR', 'Finance'])}
Position: {random.choice(['Manager', 'Senior', 'Junior', 'Lead', 'Director'])}
Salary: ${random.randint(50, 180)},000
Hire Date: {(FIXTURE_DATE - timedelta(days=random.randint(30, 3000))).strftime('%Y-%m-%d')}
Status: Active
""")
    return "".join(lines)
def make_invoice():
    inv_num = f"INV-2024-{random.randint(1000, 9999)}"
    return f"""INVOICE
=============================================
Invoice Number: {inv_num}
Date: {FIXTURE_DATE.strftime('%Y-%m-%d')}
Due Date: {(FIXTURE_DATE + timedelta(days=30)).strftime('%Y-%m-%d')}
BILL TO:
Client Company Ltd.
123 Business Street
New York, NY 10001
ITEMS:
=============================================
Consulting Services      40 hrs   $6,000
Software License              1   $2,500
Support Package               1   $1,200
=============================================
Subtotal:                        $9,700
Tax (10%):                         $970
Total Due:                      $10,670
Payment Terms: Net 30
Bank Details: XXXX-XXXX-XXXX-1234
""" * 8
def make_passwords():
    return """PASSWORDS - DO NOT SHARE
========================
Email:      john.doe@company.com    |  ******
Bank:       Chase Bank              |  ******
Amazon:     personal account        |  ******
Netflix:    family plan             |  ******
Router:     home WiFi               |  ******
Facebook:   personal                |  ******
Instagram:  @johndoe                |  ******
LinkedIn:   professional            |  ******
GitHub:     work account            |  ******
Dropbox:    backup                  |  ******
VPN Credentials:
Server: vpn.company.com
Username: john.doe
Certificate: ~/certs/vpn.pem
Cloud Storage:
AWS Access Key: AKIAXXXXXXXXXXXXX
Google Cloud:   proj-123456
Azure:          Sub-abcdef
Two-Factor Backup Codes:
1234-5678, 9012-3456, 7890-1234
""" * 5
def make_contacts():
    contacts = ["IMPORTANT CONTACTS\n" + "=" * 60 + "\n\n"]
    names = ["Alice Smith", "Bob Johnson", "Charlie Brown", "Diana White",
             "Edward Davis", "Fiona Martinez", "George Wilson", "Hannah Lee"]
    for name in names * 8:
        contacts.append(f"""
Name: {name}
Company: {random.choice(['Acme', 'Globex', 'Initech', 'Umbrella', 'Wayne Ent'])}
Phone: +1-555-{random.randint(100,999)}-{random.randint(1000,9999)}
Email: {name.lower().replace(' ', '.')}@example.com
Notes: {random.choice(['Client', 'Vendor', 'Partner', 'Prospect'])}
""")
    return "".join(contacts)
# Zip members default to the wall clock, which made two runs of this
# generator produce different bytes for the same seed (and made the
# determinism test fail whenever the two calls straddled a second
# boundary). Fixture archives are stamped with the fixture date instead.
ZIP_FIXTURE_DATE = (2024, 10, 1, 0, 0, 0)


def _write_zip_member(archive, name, content):
    """Add a byte-stable member to *archive*."""
    info = zipfile.ZipInfo(name, date_time=ZIP_FIXTURE_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, content)


def make_xlsx_content():
    """Create a small valid Excel workbook using only the standard library."""
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/worksheets/sheet1.xml": """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>ENTROPY Demo Financial Report</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>Quarter</t></is></c><c r="B2" t="inlineStr"><is><t>Revenue</t></is></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>Q3 2024</t></is></c><c r="B3"><v>8450000</v></c></row>
<row r="4"><c r="A4" t="inlineStr"><is><t>Status</t></is></c><c r="B4" t="inlineStr"><is><t>Healthy before simulation</t></is></c></row>
</sheetData></worksheet>""",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            _write_zip_member(archive, name, content)
    return output.getvalue()
def make_docx_content():
    """Create a valid minimal Word document."""
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>""",
        "word/document.xml": """<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>ENTROPY Demo Document - readable before the attack.</w:t></w:r></w:p><w:p><w:r><w:t>This file is a safe generated fixture.</w:t></w:r></w:p><w:sectPr/></w:body></w:document>""",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            _write_zip_member(archive, name, content)
    return output.getvalue()
def make_pdf_content():
    """Create a valid one-page PDF without third-party libraries."""
    stream = b"BT /F1 18 Tf 72 720 Td (ENTROPY Demo PDF - readable before attack) Tj ET\n"
    objects = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj",
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj",
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj",
        b"5 0 obj<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"endstream\nendobj",
    ]
    output = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(output))
        output += obj + b"\n"
    xref = len(output)
    output += b"xref\n0 6\n0000000000 65535 f \n"
    output += b"".join(
        f"{offset:010d} 00000 n ".encode() + b"\n"
        for offset in offsets[1:]
    )
    output += (
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
        + str(xref).encode()
        + b"\n%%EOF\n"
    )
    return output
def make_binary_content(size_kb, magic=b"\xff\xd8\xff\xe0"):
    """Create fake media/archive content with a VALID magic header.

    The magic must match the file's extension: the defender's analyzer
    validates magic bytes against the declared type (magic_ok). A PNG
    header inside a ".jpg" is exactly the disguise signal ransomware
    produces — fixtures stamped like that are flagged as ciphertext
    during every reset, flooding the SOC feed with false quarantines.
    The body stays a structured (non-uniform) pattern so chi2 remains
    far from the ciphertext range.
    """
    header = bytes(magic) + b"\x00" * 8
    body = bytes([i % 128 for i in range(size_kb * 1024)])
    return header + body
# ═══════════════════════════════════════════════════
# FILE CREATION
# ═══════════════════════════════════════════════════
FILES = {
    "Documents": [
        ("Financial_Report_2024.xlsx",  "binary", make_xlsx_content),
        ("Client_Meeting_Notes.docx",    "binary", make_docx_content),
        ("Tax_Returns.pdf",              "binary", make_pdf_content),
        ("Employee_Records.xlsx",        "binary", make_xlsx_content),
        ("Project_Roadmap.docx",         "binary", make_docx_content),
        ("Budget_2024.xlsx",             "binary", make_xlsx_content),
    ],
    "Downloads": [
        ("Invoice_INV-2024-1042.pdf",   "binary", make_pdf_content),
        ("Invoice_INV-2024-1043.pdf",   "binary", make_pdf_content),
        ("Software_Update.zip",         "binary", lambda: make_binary_content(150, magic=b"PK\x03\x04")),
        ("Report_Draft.docx",           "binary", make_docx_content),
    ],
    "Pictures": [
        ("Family_Vacation_2023.jpg",    "binary", lambda: make_binary_content(200)),
        ("Wedding_Photos.jpg",          "binary", lambda: make_binary_content(300)),
        ("Birthday_Party.jpg",          "binary", lambda: make_binary_content(180)),
        ("Beach_Trip.jpg",              "binary", lambda: make_binary_content(220)),
    ],
    "Desktop": [
        ("Passwords.txt",               "text", make_passwords),
        ("Important_Contacts.txt",      "text", make_contacts),
        ("Todo_List.txt",               "text", lambda: "TODO:\n- Meeting @ 3pm\n- Send email\n- Review PR\n" * 30),
        ("Notes.txt",                   "text", lambda: "Random notes\n" * 50),
    ],
}
def create_all_files(base_dir=None, *, seed=DEFAULT_SEED, clean=False, quiet=False):
    """Generate a clean, deterministic set of fake victim files.
    Args:
        base_dir: Destination directory. Defaults to ``victim_server/user_files``.
        seed: Seed used for all generated names and values.
        clean: Remove an existing destination before generation.
        quiet: Suppress progress output (useful for automated tests).
    Returns:
        A summary containing the destination, file count, and total size.
    """
    import shutil
    destination = os.path.abspath(base_dir or BASE)
    if clean and os.path.exists(destination):
        shutil.rmtree(destination)
    if not quiet:
        print("=" * 50)
        print("  CREATING VICTIM MACHINE FILES")
        print("=" * 50)
    total_created = 0
    total_size = 0
    random_state = random.getstate()
    random.seed(seed)
    try:
        for folder, files in FILES.items():
            folder_path = os.path.join(destination, folder)
            os.makedirs(folder_path, exist_ok=True)
            for filename, ftype, generator in files:
                filepath = os.path.join(folder_path, filename)
                content = generator()
                if ftype == "text":
                    with open(filepath, "w", encoding="utf-8") as file_handle:
                        file_handle.write(content)
                else:
                    with open(filepath, "wb") as file_handle:
                        file_handle.write(content)
                size = os.path.getsize(filepath)
                total_size += size
                total_created += 1
                if not quiet:
                    print(f"  [OK] {folder}/{filename:35} {size/1024:.1f} KB")
    finally:
        random.setstate(random_state)
    summary = {
        "destination": destination,
        "files_created": total_created,
        "total_size": total_size,
        "seed": seed,
    }
    if not quiet:
        print()
        print("=" * 50)
        print(f"  Created: {total_created} files")
        print(f"  Total size: {total_size/1024:.1f} KB")
        print(f"  Location: {destination}")
        print("=" * 50)
    return summary
def restore_all_files(base_dir=None, *, seed=DEFAULT_SEED, quiet=False):
    """Delete and deterministically regenerate the controlled fixture tree."""
    return create_all_files(
        base_dir=base_dir,
        seed=seed,
        clean=True,
        quiet=quiet,
    )
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate safe ENTROPY victim fixtures")
    parser.add_argument("--output", help="destination directory (default: user_files)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--clean", action="store_true", help="replace existing fixtures")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    create_all_files(
        base_dir=args.output,
        seed=args.seed,
        clean=args.clean,
        quiet=args.quiet,
    )
if __name__ == "__main__":
    main()