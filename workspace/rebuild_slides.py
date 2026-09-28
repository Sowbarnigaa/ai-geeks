"""Rebuild image-heavy slides with editable OOXML text/shape elements."""

import os

SLIDES_DIR = "workspace/unpacked/ppt/slides"

# ─── helpers ────────────────────────────────────────────────────────────────

def sp_bg(fill_color_hex=None, scheme_fill=None, w=12192000, h=6858000):
    """Full-slide background rectangle (no text)."""
    if fill_color_hex:
        fill = f'<a:solidFill><a:srgbClr val="{fill_color_hex}"/></a:solidFill>'
    elif scheme_fill:
        fill = f'<a:solidFill><a:schemeClr val="{scheme_fill}"/></a:solidFill>'
    else:
        fill = '<a:noFill/>'
    return f'''
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="100" name="Background"/>
          <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          {fill}
          <a:ln><a:noFill/></a:ln>
        </p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody>
      </p:sp>'''

def pic(rid, x, y, cx, cy, elem_id=10):
    return f'''
      <p:pic>
        <p:nvPicPr>
          <p:cNvPr id="{elem_id}" name="Image{elem_id}"/>
          <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>
          <p:nvPr/>
        </p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="{rid}"/>
          <a:stretch><a:fillRect/></a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        </p:spPr>
      </p:pic>'''

def rect(x, y, cx, cy, fill_hex, border_hex=None, border_w=19050, radius=False, elem_id=20):
    geom = 'roundRect' if radius else 'rect'
    if border_hex:
        ln = f'<a:ln w="{border_w}"><a:solidFill><a:srgbClr val="{border_hex}"/></a:solidFill></a:ln>'
    else:
        ln = '<a:ln><a:noFill/></a:ln>'
    return f'''
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{elem_id}" name="Rect{elem_id}"/>
          <p:cNvSpPr/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
          <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill>
          {ln}
        </p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="en-US"/></a:p></p:txBody>
      </p:sp>'''

def left_bar(x, y, cy, color_hex, elem_id=30):
    """Thin vertical color bar on left of a card."""
    return rect(x, y, 19050, cy, color_hex, elem_id=elem_id)

def hline(x, y, cx, color_hex, w=9525, elem_id=40):
    """Horizontal line."""
    return f'''
      <p:cxnSp>
        <p:nvCxnSpPr>
          <p:cNvPr id="{elem_id}" name="Line{elem_id}"/>
          <p:cNvCxnSpPr/>
          <p:nvPr/>
        </p:nvCxnSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="0"/></a:xfrm>
          <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
          <a:ln w="{w}"><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill></a:ln>
        </p:spPr>
      </p:cxnSp>'''

def txbox(x, y, cx, cy, runs, wrap="square", anchor="t", elem_id=50):
    """Text box with multiple runs. Each run: (text, sz, bold, color_hex, italic)."""
    paragraphs = []
    for run in runs:
        if run is None:
            paragraphs.append('<a:p><a:endParaRPr lang="en-US"/></a:p>')
            continue
        text, sz, bold, color_hex, *rest = run
        italic = rest[0] if rest else False
        b = '1' if bold else '0'
        i = '1' if italic else '0'
        clr = f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>' if color_hex else \
              '<a:solidFill><a:schemeClr val="bg1"/></a:solidFill>'
        paragraphs.append(f'''<a:p>
              <a:r>
                <a:rPr lang="en-US" sz="{sz}" b="{b}" i="{i}" dirty="0">
                  {clr}
                  <a:latin typeface="Calibri"/>
                </a:rPr>
                <a:t>{text}</a:t>
              </a:r>
            </a:p>''')
    paras = '\n'.join(paragraphs)
    return f'''
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{elem_id}" name="TB{elem_id}"/>
          <p:cNvSpPr txBox="1"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:noFill/>
          <a:ln><a:noFill/></a:ln>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="{wrap}" rtlCol="0" anchor="{anchor}"><a:normAutofit/></a:bodyPr>
          <a:lstStyle/>
          {paras}
        </p:txBody>
      </p:sp>'''

def mixed_para_txbox(x, y, cx, cy, paragraphs_xml, elem_id=50):
    """Text box with raw paragraph XML (for mixed-color runs in one paragraph)."""
    return f'''
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{elem_id}" name="TB{elem_id}"/>
          <p:cNvSpPr txBox="1"/>
          <p:nvPr/>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:noFill/>
          <a:ln><a:noFill/></a:ln>
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square" rtlCol="0" anchor="t"><a:normAutofit/></a:bodyPr>
          <a:lstStyle/>
          {paragraphs_xml}
        </p:txBody>
      </p:sp>'''

def slide_wrap(content, clr_map="master"):
    clr = '<a:masterClrMapping/>' if clr_map == "master" else \
          '<a:overrideClrMapping bg1="dk1" tx1="lt1" bg2="dk2" tx2="lt2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {content}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>{clr}</p:clrMapOvr>
</p:sld>'''

# ─── SLIDE 1: Cover ─────────────────────────────────────────────────────────
# Keep the full-slide dark background (image1.png = rId2). Replace the small
# footer strip (image2.png = rId3) with an editable text strip.
# Add all text as editable shapes layered on top.

s1_content = ''
# Full-slide cover image (keep as visual background)
s1_content += pic('rId2', 0, 0, 12192000, 6858000, elem_id=5)
# Overlay dark left panel for text readability (semi-transparent)
s1_content += rect(0, 0, 5800000, 6858000, '0D1B2A', elem_id=6)
# Badge: AI GEEKS TECH TALK · 2026
s1_content += rect(457200, 686055, 2286000, 266700, '0D1B2A', border_hex='00B0F0', border_w=12700, elem_id=7)
s1_content += txbox(457200, 686055, 2286000, 266700,
    [('AI GEEKS TECH TALK · 2026', 900, True, 'FFFFFF')], elem_id=8)
# Main title
s1_content += txbox(457200, 1143000, 5100000, 1371600,
    [('Guardrails for', 4800, True, '00B0F0'),
     ('Agentic AI', 4800, True, '00B0F0')], elem_id=9)
# Subtitle
s1_content += txbox(457200, 2590800, 5100000, 457200,
    [('How to Safely Let AI Take Action?', 1800, False, 'FFFFFF')], elem_id=11)
# Tagline
s1_content += txbox(457200, 3124800, 5100000, 457200,
    [('Safe and Responsible AI', 1800, True, '00B0F0')], elem_id=12)
# Divider line
s1_content += hline(457200, 3657600, 914400, 'FFFFFF', w=12700, elem_id=13)
# Author
s1_content += txbox(457200, 3810000, 5100000, 609600,
    [('Sowbarnigaa Shanmugavadivel', 1200, True, 'FFFFFF'),
     ('Software Developer @ IBM', 1200, False, 'CCCCCC')], elem_id=14)

slide1 = slide_wrap(s1_content, clr_map="override")
with open(os.path.join(SLIDES_DIR, 'slide1.xml'), 'w', encoding='utf-8') as f:
    f.write(slide1)
print("Slide 1 done.")

# ─── SLIDE 2: The Problem — Without vs. With Guardrails ─────────────────────
# Replace full image3.png with editable shapes

BG = '0D1B2A'      # dark navy
CARD_BG = '111E30' # slightly lighter card
RED_H = 'E53935'
GREEN_H = '2E7D32'
CYAN = '00B0F0'
WHITE = 'FFFFFF'
GREY = 'B0BEC5'
ORANGE = 'FFA726'
YELLOW = 'FFD600'

s2_content = ''
s2_content += sp_bg(fill_color_hex=BG)
# Blue separator line under title
s2_content += hline(228600, 685800, 11734800, CYAN, w=19050, elem_id=41)

# Title: "The Problem — Without vs. With Guardrails"
s2_content += mixed_para_txbox(228600, 228600, 9000000, 457200, f'''
  <a:p>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>The Problem &#8212; </a:t></a:r>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{CYAN}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Without vs. With Guardrails</a:t></a:r>
  </a:p>''', elem_id=50)

# ── Column 1: WITHOUT GUARDRAILS ──
col1_x = 228600
# Header bar
s2_content += rect(col1_x, 762000, 3657600, 304800, '4A0000', border_hex=RED_H, border_w=19050, radius=True, elem_id=60)
s2_content += txbox(col1_x, 762000, 3657600, 304800,
    [('✗  WITHOUT GUARDRAILS', 1200, True, RED_H)], wrap="square", anchor="ctr", elem_id=61)

# Cards col 1
cards1 = [
    ('User Prompt', 'Pay this vendor invoice immediately!', RED_H),
    ('Agent Reasoning', 'Assumes invoice is valid', RED_H),
    ('Agent Action', 'Triggers payment API directly', RED_H),
]
for i, (title, body, bar_color) in enumerate(cards1):
    cy_off = 1143000 + i * 990600
    s2_content += rect(col1_x, cy_off, 3657600, 876300, CARD_BG, radius=True, elem_id=70+i*3)
    s2_content += left_bar(col1_x, cy_off, 876300, bar_color, elem_id=71+i*3)
    s2_content += txbox(col1_x+57150, cy_off+57150, 3543450, 762000,
        [(title, 1200, True, WHITE), (body, 1100, False, GREY)], elem_id=72+i*3)

# Outcome card col1
cy_off = 1143000 + 3 * 990600
s2_content += rect(col1_x, cy_off, 3657600, 990600, CARD_BG, radius=True, elem_id=80)
s2_content += left_bar(col1_x, cy_off, 990600, ORANGE, elem_id=81)
s2_content += txbox(col1_x+57150, cy_off+57150, 3543450, 876300,
    [('Outcome ⚠', 1200, True, ORANGE),
     ('Wrong vendor paid · Duplicate invoice · Payment fraud', 1100, False, GREY)], elem_id=82)

# ── VS circle ──
s2_content += rect(4343400, 3124800, 685800, 685800, '0A3A5C', border_hex=CYAN, border_w=28575, radius=True, elem_id=90)
s2_content += txbox(4343400, 3124800, 685800, 685800,
    [('VS', 1800, True, CYAN)], wrap="square", anchor="ctr", elem_id=91)

# ── Column 2: WITH GUARDRAILS ──
col2_x = 5257200
s2_content += rect(col2_x, 762000, 3657600, 304800, '1A3A1A', border_hex='4CAF50', border_w=19050, radius=True, elem_id=100)
s2_content += txbox(col2_x, 762000, 3657600, 304800,
    [('✓  WITH GUARDRAILS', 1200, True, '4CAF50')], wrap="square", anchor="ctr", elem_id=101)

cards2 = [
    ('User Prompt', 'Pay this vendor invoice immediately!', '4CAF50'),
    ('Guardrail Checks', 'Classifies HIGH RISK → vendor validation → amount threshold → duplicate check', '4CAF50'),
    ('Agent Action', 'Executes only after approval', '4CAF50'),
    ('Outcome ✓', 'Secure, auditable transaction · Zero financial leakage', '4CAF50'),
]
for i, (title, body, bar_color) in enumerate(cards2):
    cy_off = 1143000 + i * 990600
    s2_content += rect(col2_x, cy_off, 3657600, 876300, CARD_BG, radius=True, elem_id=110+i*3)
    s2_content += left_bar(col2_x, cy_off, 876300, bar_color, elem_id=111+i*3)
    clr = '4CAF50' if title.startswith('Outcome') else WHITE
    s2_content += txbox(col2_x+57150, cy_off+57150, 3543450, 762000,
        [(title, 1200, True, clr), (body, 1000, False, GREY)], elem_id=112+i*3)

# ── Column 3: The Core Shift ──
col3_x = 9143400
s2_content += rect(col3_x, 762000, 2819400, 5371800, '0A1929', border_hex='334D6E', border_w=12700, radius=True, elem_id=130)
s2_content += txbox(col3_x+114300, 838200, 2590800, 380999,
    [('⚡ The Core Shift', 1400, True, YELLOW)], elem_id=131)
s2_content += txbox(col3_x+114300, 1219200, 2590800, 4800000, [
    ('Agentic AI can take irreversible real-world actions — pay money, send emails, delete files, call APIs.', 1000, False, GREY),
    None,
    ('Old question:', 1000, False, GREY),
    ('"Can AI do this task?"', 1000, False, WHITE, True),
    None,
    ('New question:', 1000, False, CYAN),
    ('"Should AI be allowed to do this?"', 1000, False, WHITE, True),
    None,
    ('When is human-in-the-loop essential? We must evaluate these systems for production.', 1000, False, GREY),
], elem_id=132)

slide2 = slide_wrap(s2_content)
with open(os.path.join(SLIDES_DIR, 'slide2.xml'), 'w', encoding='utf-8') as f:
    f.write(slide2)
print("Slide 2 done.")

# ─── SLIDE 3: Six Layers of Agentic AI Guardrails ────────────────────────────
# image4 = dark background (keep). image5 = diagram (replace with editable shapes).
# The slide already has editable title text. Keep that + background image.
# We rebuild the layer cards as editable shapes.

LAYER_COLORS = ['00B0F0','9C27B0','FFC107','E53935','4CAF50','76FF03']
LAYER_TITLES = ['Input Guardrail','Behavioural Guardrail','Reasoning Guardrail',
                'Tool Guardrail','Data & Security\nGuardrail','Output Guardrail']
LAYER_NUMS   = ['1','2','3','4','5','6']
LAYER_BULLETS= [
    'Prompt injection detection\nPII redaction\nTopic/content moderation\nAuthN / Rate limiting',
    'Domain scoping\ne.g. Medical domain: no food topics\nPersona boundaries',
    'Chain-of-thought validation\nFact checker\nTime/cost reality check',
    'Permission / least privilege\nSchema validation\nSandboxed execution',
    'Block harmful/illegal content\nData masking\nCompliance (legal/medical)',
    'Hallucination check\nFormat/schema validation\nPII scrub on output\nOutput length cap',
]

BOTTOM_CARDS = [
    ('🛡 Prompt Protection', 'Mask data before AI processes it. Protect prompts from user and user from AI.', 'E53935'),
    ('🖥 Code Analyser', 'Even hallucinating AI must not generate risky code. Analyse & mitigate.', 'FFC107'),
    ('🔒 Data Masker', 'Alias & mask data. Only those with permission can see real values.', '9C27B0'),
    ('✅ Fact Checker', 'Verify everything AI creates. Counterpoint missing facts. Reality-check timelines.', '00B4D8'),
    ('⏱ Cost & Latency', 'Cap token spend, execution time, and agent loop iterations.', '4CAF50'),
]

s3_content = ''
# Background image (dark template)
s3_content += pic('rId2', 0, 0, 12192000, 6858000, elem_id=5)

# Title
s3_content += mixed_para_txbox(418642, 114300, 6000000, 457200, f'''
  <a:p>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Six layers of </a:t></a:r>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{CYAN}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Agentic AI guardrails</a:t></a:r>
  </a:p>''', elem_id=50)

# 6 layer cards (top row)
card_w = 1905000
card_h = 1600200
gap = 38100
row1_y = 647700
for i in range(6):
    cx = gap + i * (card_w + gap)
    col = LAYER_COLORS[i]
    # Card background
    s3_content += rect(cx, row1_y, card_w, card_h, CARD_BG, border_hex=col, border_w=9525, radius=True, elem_id=60+i*4)
    # Colored top strip
    s3_content += rect(cx, row1_y, card_w, 57150, col, elem_id=61+i*4)
    # Number circle (simulate with colored text)
    s3_content += txbox(cx, row1_y+57150, card_w, 228600,
        [(LAYER_NUMS[i], 1600, True, col)], wrap="square", anchor="ctr", elem_id=62+i*4)
    # Title + bullets
    bullets = [(LAYER_TITLES[i], 1000, True, WHITE)] + \
              [(line, 900, False, GREY) for line in LAYER_BULLETS[i].split('\n')]
    s3_content += txbox(cx+57150, row1_y+342900, card_w-114300, card_h-400050,
        bullets, elem_id=63+i*4)

# Bottom 5 feature cards
bcard_w = 2285160
bcard_h = 1143000
row2_y = 5410800 - bcard_h - 152400
for i, (title, body, col) in enumerate(BOTTOM_CARDS):
    cx = gap + i * (bcard_w + gap)
    s3_content += rect(cx, row2_y, bcard_w, bcard_h, CARD_BG, border_hex=col, border_w=9525, radius=True, elem_id=100+i*3)
    s3_content += left_bar(cx, row2_y, bcard_h, col, elem_id=101+i*3)
    s3_content += txbox(cx+76200, row2_y+57150, bcard_w-114300, bcard_h-76200,
        [(title, 1000, True, col), (body, 900, False, GREY)], elem_id=102+i*3)

slide3 = slide_wrap(s3_content)
with open(os.path.join(SLIDES_DIR, 'slide3.xml'), 'w', encoding='utf-8') as f:
    f.write(slide3)
# Update rels: remove rId3 (old diagram image), keep rId2 (background)
rels3 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image4.png"/>
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>'''
with open(os.path.join(SLIDES_DIR, '_rels', 'slide3.xml.rels'), 'w', encoding='utf-8') as f:
    f.write(rels3)
print("Slide 3 done.")

# ─── SLIDE 4: Centralized Guardrails — Agentic AI Control Plane ─────────────
# Fully image-based (image6.png rId2). Replace with editable shapes.

s4_content = ''
s4_content += sp_bg(fill_color_hex=BG)
s4_content += hline(228600, 685800, 11734800, CYAN, w=19050, elem_id=41)

# Title
s4_content += mixed_para_txbox(228600, 190500, 11734800, 457200, f'''
  <a:p>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Centralized Guardrails &#8212; </a:t></a:r>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{CYAN}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Agentic AI Control Plane</a:t></a:r>
  </a:p>''', elem_id=50)

# Left column: User/Client, Multiple Agents, External Tools/APIs
left_items = [
    ('User / Client', 'Web · Mobile · PC\nSends user query with identity context', CYAN, 762000),
    ('Multiple Agents', 'Orchestrator → Sub-agents → Tool agents\nEach hop must be guarded independently', '9C27B0', 2514600),
    ('External Tools / APIs', 'DB · Payment API · Email · Code runner\nReal-world irreversible side-effects', YELLOW, 4267200),
]
for title, body, col, y in left_items:
    s4_content += rect(114300, y, 2743200, 990600, CARD_BG, border_hex=col, border_w=9525, elem_id=60)
    s4_content += left_bar(114300, y, 990600, col, elem_id=61)
    s4_content += txbox(190500, y+76200, 2590800, 838200,
        [(title, 1100, True, col), (body, 950, False, GREY)], elem_id=62)

# Center column: flow boxes
center_items = [
    ('🔑 Gateway Layer', 'AuthN · AuthZ · Rate Limiting\n→ 401 / 429 on fail', CYAN, 762000),
    ('🛡 Input Guardrail Layer', 'Prompt injection · PII redaction · Content mod\n→ Fallback "Sorry, I can\'t help"', '9C27B0', 1905000),
    ('🤖 Agent Core (LLM + Tools)', 'Reasoning · Planning · Tool calls\n↔ Sandboxed execution', CYAN, 3048000),
    ('✅ Output Guardrail Layer', 'Hallucination · Schema · PII scrub\n→ Retry loop max 2 · then safe fallback', '4CAF50', 4191000),
    ('📋 Audit Log & Traces', 'Every decision recorded for compliance & debugging', '334D6E', 5334000),
]
for i, (title, body, col, y) in enumerate(center_items):
    s4_content += rect(3200400, y, 5600000, 800100, CARD_BG, border_hex=col, border_w=19050, radius=True, elem_id=70+i*2)
    s4_content += txbox(3314700, y+76200, 5371600, 647700,
        [(title, 1100, True, col), (body, 950, False, GREY)], elem_id=71+i*2)
    # Down arrow between boxes (except last)
    if i < 4:
        arr_y = y + 800100
        s4_content += txbox(4800000, arr_y, 400000, 104900,
            [('↓', 1400, False, GREY)], wrap="square", anchor="ctr", elem_id=80+i)

# Right column: outcomes
right_items = [
    ('🚫 Rejected at Gateway', '401 Unauthorized\n429 Rate Limited', RED_H, 762000),
    ('⚠ Fallback Response', '"Sorry, I can\'t help with that"\nUnsafe input blocked pre-LLM', ORANGE, 1905000),
    ('🔒 Action Blocked', 'Unauthorized tool / data access denied', '9C27B0', 3048000),
    ('👤 Human Review Queue', 'High-risk / irreversible actions\nApprove / Deny before execution', '00B4D8', 4191000),
    ('✅ Validated Response', 'Safe, grounded, PII-free output delivered', '4CAF50', 5334000),
]
right_colors = [RED_H, ORANGE, '9C27B0', '00B4D8', '4CAF50']
for i, (title, body, col, y) in enumerate(right_items):
    s4_content += rect(9029400, y, 2857500, 800100, CARD_BG, border_hex=col, border_w=9525, radius=True, elem_id=90+i*2)
    s4_content += left_bar(9029400, y, 800100, col, elem_id=91+i*2)
    s4_content += txbox(9105600, y+57150, 2743200, 685800,
        [(title, 1000, True, col), (body, 900, False, GREY)], elem_id=92+i*2)

slide4 = slide_wrap(s4_content)
with open(os.path.join(SLIDES_DIR, 'slide4.xml'), 'w', encoding='utf-8') as f:
    f.write(slide4)
# Remove image rels for slide4 (was using image6.png)
rels4 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>'''
with open(os.path.join(SLIDES_DIR, '_rels', 'slide4.xml.rels'), 'w', encoding='utf-8') as f:
    f.write(rels4)
print("Slide 4 done.")

# ─── SLIDE 5: Are Guardrails just Filters? ───────────────────────────────────
# Already has editable title text (sz=4800). Keep image4 (bg) + image7 (AI shield photo).
# Just ensure the title shape is clean — original XML is fine, no changes needed.
print("Slide 5 unchanged (already editable).")

# ─── SLIDE 6: Evaluation ─────────────────────────────────────────────────────
# image4=bg (rId2), image8=content (rId3). Replace image8 with editable shapes.

s6_content = ''
s6_content += pic('rId2', 0, 3482, 12192000, 6854518, elem_id=4)
s6_content += hline(228600, 685800, 11734800, CYAN, w=19050, elem_id=41)

# Title
s6_content += txbox(228600, 190500, 4000000, 457200,
    [('Evaluation', 2000, True, WHITE)], elem_id=50)

# LEFT column
# 1) Traditional Evaluation
s6_content += rect(114300, 762000, 5257200, 952500, CARD_BG, border_hex=YELLOW, border_w=9525, radius=True, elem_id=60)
s6_content += left_bar(114300, 762000, 952500, YELLOW, elem_id=61)
s6_content += txbox(190500, 800100, 5066700, 876300, [
    ('🔍 Traditional Evaluation', 1200, True, YELLOW),
    ('Accuracy metrics, benchmarks, unit tests — evaluate model quality offline', 950, False, GREY),
    ('But agentic AI needs runtime evaluation at every step', 950, False, GREY),
], elem_id=62)

# 2) LLM-as-Judge
s6_content += rect(114300, 1790700, 5257200, 1076100, CARD_BG, border_hex=CYAN, border_w=9525, radius=True, elem_id=63)
s6_content += left_bar(114300, 1790700, 1076100, CYAN, elem_id=64)
s6_content += txbox(190500, 1828800, 5066700, 1000000, [
    ('🤖 LLM-as-Judge', 1200, True, CYAN),
    ('A separate LLM evaluates the primary LLM\'s output', 950, False, GREY),
    ('"Who judges the judge?"', 950, False, WHITE, True),
    ('→ Use ensemble of judges or rule-based fallback', 950, False, GREY),
], elem_id=65)

# 3+4) Code-Based | Human Feedback (side by side)
s6_content += rect(114300, 2943000, 2514600, 1028700, CARD_BG, border_hex='9C27B0', border_w=9525, radius=True, elem_id=66)
s6_content += left_bar(114300, 2943000, 1028700, '9C27B0', elem_id=67)
s6_content += txbox(190500, 2981100, 2400300, 952500, [
    ('🧩 Code-Based', 1100, True, '9C27B0'),
    ('Regex · Schema validator · Unit tests · Structured output checks', 900, False, GREY),
], elem_id=68)

s6_content += rect(2705400, 2943000, 2666100, 1028700, CARD_BG, border_hex='4CAF50', border_w=9525, radius=True, elem_id=69)
s6_content += left_bar(2705400, 2943000, 1028700, '4CAF50', elem_id=70)
s6_content += txbox(2781600, 2981100, 2514600, 952500, [
    ('👤 Human Feedback', 1100, True, '4CAF50'),
    ('Thumbs up / down · RLHF · Human-in-the-loop approval for high-risk', 900, False, GREY),
], elem_id=71)

# RIGHT column: Self-Correction Loop
s6_content += rect(5600000 + 114300, 762000, 6133500, 2514600, CARD_BG, border_hex=CYAN, border_w=19050, radius=True, elem_id=80)
s6_content += txbox(5790400, 800100, 5943300, 380999, [
    ('🔄 The Self-Correction Loop — Guardrails as Feedback', 1200, True, CYAN),
], elem_id=81)
s6_content += txbox(5790400, 1143000, 5943300, 304800, [
    ('Don\'t treat guardrails as a filter. Treat them as a feedback mechanism.', 950, False, GREY),
], elem_id=82)

# Flow diagram (text-based)
flow_items = [
    ('LLM generates response', WHITE, 5790400, 1524000),
    ('→', GREY, 7162800, 1524000),
    ('Guardrail checks output', WHITE, 7543800, 1524000),
    ('→', GREY, 8991600, 1524000),
    ('Issue detected', RED_H, 9372600, 1524000),
    ('↓', GREY, 9753600, 1790700),
    ('Pass - deliver', '4CAF50', 5790400, 2057400),
    ('←', GREY, 7162800, 2057400),
    ('Retry LLM with correction prompt', WHITE, 7543800, 2057400),
    ('←', GREY, 9144000, 2057400),
    ('Here is what was wrong, revise', YELLOW, 9372600, 2057400),
]
for txt, col, fx, fy in flow_items:
    s6_content += txbox(fx, fy, 1371600, 228600, [(txt, 850, True if txt in ('Pass - deliver','Issue detected','Guardrail checks output') else False, col)], wrap="square", anchor="ctr", elem_id=83)

s6_content += txbox(5790400, 2400300, 5943300, 762000, [
    ('When a guardrail detects a problem, instead of surfacing failure to the user, the system feeds flagged issues back to the LLM with a targeted correction prompt. The agent retries until the response passes — or a retry limit is hit.', 900, False, GREY),
], elem_id=90)

# Bottom hierarchy bar
s6_content += rect(114300, 4114800, 11963400, 304800, CARD_BG, border_hex='334D6E', border_w=9525, elem_id=91)
s6_content += txbox(190500, 4114800, 11810700, 304800, [
    ('Guardrails work at every level of the agent hierarchy:', 1000, True, WHITE),
], wrap="square", anchor="ctr", elem_id=92)
hierarchy = [('Orchestrator Agent','00B0F0'),('→',GREY),('Sub-Agent','9C27B0'),('→',GREY),('Tool Agent',RED_H),('→',GREY),('External Action',YELLOW)]
hx = 190500
for txt, col in hierarchy:
    s6_content += rect(hx, 4495800, 1371600 if txt != '→' else 304800, 304800,
                       '0A1929' if txt != '→' else CARD_BG,
                       border_hex=col if txt != '→' else None, border_w=9525, elem_id=93)
    s6_content += txbox(hx, 4495800, 1371600 if txt != '→' else 304800, 304800,
        [(txt, 900, False, col)], wrap="square", anchor="ctr", elem_id=94)
    hx += (1371600 if txt != '→' else 304800) + 38100

slide6 = slide_wrap(s6_content)
with open(os.path.join(SLIDES_DIR, 'slide6.xml'), 'w', encoding='utf-8') as f:
    f.write(slide6)
# rels: keep only bg image4 (rId2), remove image8 (rId3)
rels6 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image4.png"/>
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>'''
with open(os.path.join(SLIDES_DIR, '_rels', 'slide6.xml.rels'), 'w', encoding='utf-8') as f:
    f.write(rels6)
print("Slide 6 done.")

# ─── SLIDE 7: DEMO — already editable ─────────────────────────────────────
print("Slide 7 unchanged (already editable).")

# ─── SLIDE 8: References & Key Takeaways ─────────────────────────────────────
# image9.png is the full content. Replace with editable shapes.

s8_content = ''
s8_content += sp_bg(fill_color_hex=BG)
s8_content += hline(228600, 685800, 11734800, CYAN, w=19050, elem_id=41)

# Title
s8_content += mixed_para_txbox(228600, 190500, 8000000, 457200, f'''
  <a:p>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{WHITE}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>References &amp; </a:t></a:r>
    <a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{CYAN}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>Key Takeaways</a:t></a:r>
  </a:p>''', elem_id=50)

# Left: References list
refs = [
    ('GuardrailsAI — Why Use Guardrails?', 'Official docs · validators hub · DetectJailbreak', 'guardrailsai.com/docs & guardrailsai.com/hub', '00B0F0'),
    ('LangChain + Guardrails Crash Course', 'Building Safe AI Agents with LangChain guardrails', 'youtube.com/watch?v=ruiLq0OzjkI', '9C27B0'),
    ('Agentic AI 102 — Guardrails & Evaluation', 'Working demo walkthrough · Towards Data Science', 'towardsdatascience.com/agentic-ai-102', YELLOW),
    ('Production Guardrails — Redis', 'Agentic AI guardrails at production scale', 'redis.io/blog/agentic-ai-guardrails', 'E53935'),
    ('LangChain Guardrails Docs', 'Integration guide for LangChain OSS Python', 'docs.langchain.com/guardrails', '4CAF50'),
]
for i, (title, desc, url, col) in enumerate(refs):
    ry = 762000 + i * 1009800
    s8_content += rect(114300, ry, 8610000, 914400, CARD_BG, radius=True, elem_id=60+i*3)
    s8_content += left_bar(114300, ry, 914400, col, elem_id=61+i*3)
    s8_content += txbox(266700, ry+76200, 8381400, 762000, [
        (title, 1100, True, col),
        (desc, 950, False, GREY),
        (url, 900, False, CYAN),
    ], elem_id=62+i*3)

# Right: Key Takeaways
s8_content += rect(9000000, 762000, 2962800, 4191000, CARD_BG, border_hex='334D6E', border_w=9525, radius=True, elem_id=90)
s8_content += txbox(9076200, 800100, 2819400, 380999,
    [('🎯 Key Takeaways', 1200, True, WHITE)], elem_id=91)
takeaways = [
    'Guardrails ≠ prompts. They are enforceable system controls independent of the LLM.',
    'Six layers: Input → Behavioural → Reasoning → Tool → Data/Security → Output',
    'Centralized control plane: every agent hop must be individually guarded.',
    'Guardrails ≠ Governance ≠ Security — complementary, not interchangeable.',
    'Treat failures as feedback: self-correction loops beat simple filters.',
    'Human-in-the-loop is essential for high-risk, irreversible actions.',
]
ty = 1143000
for t in takeaways:
    s8_content += txbox(9076200, ty, 2819400, 457200, [('✓  ' + t, 900, False, GREY)], elem_id=92)
    ty += 533400

# CTA box
s8_content += rect(9000000, 5029200, 2962800, 952500, '0A1929', border_hex=CYAN, border_w=28575, radius=True, elem_id=100)
s8_content += txbox(9076200, 5067300, 2819400, 876300, [
    ('Build Fast.', 1600, True, CYAN),
    ('But Build Safe.', 1400, False, WHITE),
    ('AI Geeks Tech Talk · 2025', 1000, False, GREY),
], wrap="square", anchor="ctr", elem_id=101)

slide8 = slide_wrap(s8_content)
with open(os.path.join(SLIDES_DIR, 'slide8.xml'), 'w', encoding='utf-8') as f:
    f.write(slide8)
# Remove image9 from rels
rels8 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
</Relationships>'''
with open(os.path.join(SLIDES_DIR, '_rels', 'slide8.xml.rels'), 'w', encoding='utf-8') as f:
    f.write(rels8)
print("Slide 8 done.")

print("\nAll slides rebuilt successfully.")
