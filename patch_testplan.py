import zipfile, sys
sys.stdout.reconfigure(encoding='utf-8')

src = 'cloudwan_multiregion_test_plan_DRAFT(1).docx'
dst = 'cloudwan_multiregion_test_plan_DRAFT(2).docx'

# -------------------------------------------------------
# Helper: paraId counter — always produces valid 8-char hex
# -------------------------------------------------------
_para_counter = [0xAA000000]
def next_pid():
    _para_counter[0] += 1
    return f'{_para_counter[0]:08X}'

def make_cell(w, text, alt=False):
    fill = 'F2F2F2' if alt else 'FFFFFF'
    shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if alt else ''
    pid = next_pid()
    if text:
        para = (f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
                f'<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
                f'<w:t>{text}</w:t></w:r></w:p>')
    else:
        para = f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="00C01C17"/>'
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
        f'<w:tcBorders>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'</w:tcBorders>'
        f'{shd}'
        f'<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        f'<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar></w:tcPr>'
        f'{para}</w:tc>'
    )

def make_hdr_cell(w, text):
    pid = next_pid()
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
        f'<w:tcBorders>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'</w:tcBorders>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="1F4E79"/>'
        f'<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        f'<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar></w:tcPr>'
        f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
        f'<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="FFFFFF"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
        f'<w:t>{text}</w:t></w:r></w:p></w:tc>'
    )

def make_row(tc, check, expected, alt=False):
    tr_pid = next_pid()
    return (
        f'<w:tr w:rsidR="00C01C17" w14:paraId="{tr_pid}" w14:textId="77777777">'
        f'<w:tblPrEx><w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPrEx>'
        + make_cell('1200', tc, alt)
        + make_cell('3500', check, alt)
        + make_cell('3660', expected, alt)
        + make_cell('1000', '', alt)
        + '</w:tr>'
    )

# -------------------------------------------------------
# Read source
# -------------------------------------------------------
z = zipfile.ZipFile(src, 'r')
xml = z.read('word/document.xml').decode('utf-8')

# -------------------------------------------------------
# 1. Fill probe table VPC CIDR and Private IP placeholders
# -------------------------------------------------------
probe_data = {
    'probe-prod-use1':    ('10.0.0.0/24',  '10.0.0.10',  '47263382', '1F92D0E7'),
    'probe-prod-use2':    ('10.1.0.0/24',  '10.1.0.10',  '51BF3EA2', '30D2A80A'),
    'probe-prod-usw2':    ('10.2.0.0/24',  '10.2.0.10',  '653FA24F', '5542A18A'),
    'probe-nonprod-use1': ('10.10.0.0/24', '10.10.0.10', '1B771F38', '43F55FFD'),
    'probe-nonprod-use2': ('10.11.0.0/24', '10.11.0.10', '4A8E9B2C', '5BE3C46B'),
    'probe-nonprod-usw2': ('10.12.0.0/24', '10.12.0.10', '173F5FBB', '7548543C'),
    'probe-shared-use1':  ('10.20.0.0/24', '10.20.0.10', '46963FD2', '0D1B2DF0'),
    'probe-shared-use2':  ('10.21.0.0/24', '10.21.0.10', '4D05D983', '74764962'),
    'probe-shared-usw2':  ('10.22.0.0/24', '10.22.0.10', '6F8E04BE', '3658F0E6'),
    'probe-hybrid-use1':  ('10.30.0.0/24', '10.30.0.10', '415C1A7A', '0570A266'),
}

empty_cell = '<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="00C01C17"/>'
filled_cell = ('<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
               '<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
               '<w:t>{val}</w:t></w:r></w:p>')

for probe, (cidr, ip, cidr_pid, ip_pid) in probe_data.items():
    xml = xml.replace(empty_cell.format(pid=cidr_pid), filled_cell.format(pid=cidr_pid, val=cidr))
    xml = xml.replace(empty_cell.format(pid=ip_pid),   filled_cell.format(pid=ip_pid,   val=ip))

# -------------------------------------------------------
# 2. Add probe-ma-use1 row (insert before probe-onprem-dc1 row paraId 56FA30EA)
# -------------------------------------------------------
def probe_cell(w, text, pid, alt=False):
    shd = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if alt else ''
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>'
        f'<w:tcBorders>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
        f'</w:tcBorders>{shd}'
        f'<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        f'<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar></w:tcPr>'
        f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
        f'<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t>{text}</w:t></w:r></w:p></w:tc>'
    )

ma_row = (
    '<w:tr w:rsidR="00C01C17" w14:paraId="6874BD4B" w14:textId="77777777">'
    '<w:tblPrEx><w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
    '<w:bottom w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPrEx>'
    + probe_cell('1800', 'probe-ma-use1',       '6874BD4C')
    + probe_cell('1400', 'M&amp;A',             '6874BD4D')
    + probe_cell('1400', 'us-east-1',           '6874BD4E')
    + probe_cell('1400', '172.16.100.0/24',     '6874BD4F')
    + probe_cell('1200', '172.16.100.10',       '6874BD50')
    + probe_cell('2160', 'M&amp;A acquisition network test host', '6874BD51')
    + '</w:tr>'
)

xml = xml.replace(
    '<w:tr w:rsidR="00C01C17" w14:paraId="56FA30EA"',
    ma_row + '<w:tr w:rsidR="00C01C17" w14:paraId="56FA30EA"'
)

# -------------------------------------------------------
# 3. Renumber TC-15: 004->003, 005->004, 006->005, 007->006
#    Use a temp token to avoid cascading
# -------------------------------------------------------
xml = xml.replace('>TC-15-007<', '>TC-15-TEMP6<')
xml = xml.replace('>TC-15-006<', '>TC-15-TEMP5<')
xml = xml.replace('>TC-15-005<', '>TC-15-TEMP4<')
xml = xml.replace('>TC-15-004<', '>TC-15-003<')
xml = xml.replace('>TC-15-TEMP4<', '>TC-15-004<')
xml = xml.replace('>TC-15-TEMP5<', '>TC-15-005<')
xml = xml.replace('>TC-15-TEMP6<', '>TC-15-006<')

# -------------------------------------------------------
# 4. Fill failover convergence targets ([sec] placeholders)
# -------------------------------------------------------
failover_targets = {
    'TC-11-021': '&lt; 30s',
    'TC-11-022': '&lt; 60s',
    'TC-11-023': '&lt; 60s',
    'TC-11-024': '&lt; 90s',
    'TC-11-025': '&lt; 90s',
    'TC-11-026': '&lt; 120s',
    'TC-11-027': '&lt; 60s',
    'TC-11-028': '&lt; 120s',
    'TC-13-024': '&lt; 30s',
    'TC-13-025': '&lt; 120s',
    'TC-13-026': '&lt; 30s',
    'TC-14-001': '&lt; 30s',
    'TC-14-002': '&lt; 120s',
    'TC-14-003': '&lt; 60s',
    'TC-14-004': '&lt; 60s',
    'TC-14-005': 'N/A',
}

for tc_id, target in failover_targets.items():
    idx = xml.find(f'>{tc_id}<')
    if idx != -1:
        sec_idx = xml.find('>[sec]<', idx)
        if sec_idx != -1:
            xml = xml[:sec_idx] + f'>{target}<' + xml[sec_idx + len('>[sec]<'):]

# -------------------------------------------------------
# 5. Build and insert Section 16
# -------------------------------------------------------
sec16_heading = (
    f'<w:p w14:paraId="{next_pid()}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
    '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
    '<w:r><w:t>16. Service Quotas and Limits Validation</w:t></w:r></w:p>'
    f'<w:p w14:paraId="{next_pid()}" w14:textId="77777777" w:rsidR="00C01C17" w:rsidRDefault="009065E8">'
    '<w:pPr>'
    '<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="ED7D31"/></w:pBdr>'
    '<w:shd w:val="clear" w:color="auto" w:fill="FFF4E5"/>'
    '<w:spacing w:before="120" w:after="120"/>'
    '</w:pPr>'
    '<w:r><w:rPr><w:b/><w:bCs/></w:rPr><w:t xml:space="preserve">Goal: </w:t></w:r>'
    '<w:r><w:t>Confirm the environment operates within AWS service quotas and that '
    'no quota breach will block production onboarding or failover.</w:t></w:r></w:p>'
)

header_row = (
    f'<w:tr w:rsidR="00C01C17" w14:paraId="{next_pid()}" w14:textId="77777777">'
    '<w:tblPrEx><w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
    '<w:bottom w:w="0" w:type="dxa"/></w:tblCellMar></w:tblPrEx>'
    '<w:trPr><w:tblHeader/></w:trPr>'
    + make_hdr_cell('1200', 'Test ID')
    + make_hdr_cell('3500', 'Check')
    + make_hdr_cell('3660', 'Expected Result')
    + make_hdr_cell('1000', 'Status')
    + '</w:tr>'
)

checks = [
    ('TC-16-001', 'CNE attachment count per Region vs quota (default 5,000 per core network)', 'Within quota; headroom documented'),
    ('TC-16-002', 'DXGW prefix advertisement limit (100 prefixes per DXGW association)', 'Prefix count &lt; 100 per DXGW'),
    ('TC-16-003', 'VPC attachment limit per core network edge', 'Within quota; raise SR if &gt; 80% utilised'),
    ('TC-16-004', 'Segment count vs quota (max 20 segments per core network)', 'Current 5 segments; well within limit'),
    ('TC-16-005', 'Core Network Policy document size (&lt; 10 MB)', 'Policy JSON &lt; 10 MB'),
    ('TC-16-006', 'Network Manager global network limit per account', 'Within quota'),
    ('TC-16-007', 'AWS Network Firewall rules per firewall policy', 'Within quota; headroom documented'),
    ('TC-16-008', 'VPC Flow Log delivery latency under load', 'Logs arrive within 10 min of traffic event'),
    ('TC-16-009', 'CloudWatch Logs retention and storage quota', 'Retention policy set; no quota breach'),
]

rows = header_row
for i, (tc, check, expected) in enumerate(checks):
    rows += make_row(tc, check, expected, alt=(i % 2 == 1))

sec16_table = (
    '<w:tbl>'
    '<w:tblPr><w:tblW w:w="9360" w:type="dxa"/>'
    '<w:tblBorders>'
    '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '</w:tblBorders>'
    '<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
    '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" '
    'w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
    '</w:tblPr>'
    '<w:tblGrid>'
    '<w:gridCol w:w="1200"/><w:gridCol w:w="3500"/>'
    '<w:gridCol w:w="3660"/><w:gridCol w:w="1000"/>'
    '</w:tblGrid>'
    + rows +
    '</w:tbl>'
)

sec16 = sec16_heading + sec16_table

xml = xml.replace(
    '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>17. Logging',
    sec16 + '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>17. Logging'
)

# -------------------------------------------------------
# Validate XML before writing
# -------------------------------------------------------
from xml.etree import ElementTree as ET
try:
    ET.fromstring(xml)
    print('XML validation: PASS')
except ET.ParseError as e:
    print('XML validation: FAIL -', e)
    line, col = e.position
    lines = xml.splitlines()
    for i, l in enumerate(lines[max(0,line-3):line+2], start=max(0,line-3)+1):
        print(f'  {i}: {l[:150]}')
    sys.exit(1)

# -------------------------------------------------------
# Write clean output docx
# -------------------------------------------------------
with zipfile.ZipFile(src, 'r') as zin, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.filename == 'word/document.xml':
            zout.writestr(item, xml.encode('utf-8'))
        else:
            zout.writestr(item, zin.read(item.filename))

# Verify
z2 = zipfile.ZipFile(dst, 'r')
xml2 = z2.read('word/document.xml').decode('utf-8')
results = [
    ('probe-ma-use1' in xml2,          'probe-ma-use1 row added'),
    ('10.0.0.0/24' in xml2,            'VPC CIDR filled'),
    ('10.0.0.10' in xml2,              'Private IP filled'),
    ('TC-15-003' in xml2,              'TC-15-003 present'),
    ('TC-15-004' in xml2,              'TC-15-004 present'),
    ('TC-15-005' in xml2,              'TC-15-005 present'),
    ('TC-15-006' in xml2,              'TC-15-006 present'),
    ('TC-15-007' not in xml2,          'TC-15-007 removed'),
    ('16. Service Quotas' in xml2,     'Section 16 added'),
    ('TC-16-001' in xml2,              'TC-16-001 present'),
    ('&lt; 30s' in xml2,               'Failover targets added'),
    (xml2.count('word/document.xml') == 0, 'No duplicate zip entries'),
]
for ok, msg in results:
    print(f'{"OK" if ok else "FAIL"}: {msg}')

print(f'\nOutput: {dst}')
