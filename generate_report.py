# generate_report.py
import json
import pandas as pd
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

INPUT  = "outputs/all_findings_reviewed.json"
OUTPUT = "outputs/ai_audit_report.pdf"

SEVERITY_COLORS = {
    "high":    colors.HexColor("#FAECE7"),
    "medium":  colors.HexColor("#FAEEDA"),
    "low":     colors.HexColor("#EAF3DE"),
    "none":    colors.HexColor("#E1F5EE"),
}
SEVERITY_TEXT = {
    "high":   colors.HexColor("#712B13"),
    "medium": colors.HexColor("#633806"),
    "low":    colors.HexColor("#27500A"),
    "none":   colors.HexColor("#085041"),
}
STATUS_COLORS = {
    "gap":          colors.HexColor("#FAECE7"),
    "partial":      colors.HexColor("#FAEEDA"),
    "compliant":    colors.HexColor("#E1F5EE"),
    "not_assessed": colors.HexColor("#F1EFE8"),
}

def styles():
    s = getSampleStyleSheet()
    base = s["Normal"]
    return {
        "title":    ParagraphStyle("title",    parent=base, fontSize=20, leading=26, spaceAfter=4,  textColor=colors.HexColor("#0C0C0B")),
        "subtitle": ParagraphStyle("subtitle", parent=base, fontSize=11, leading=16, spaceAfter=16, textColor=colors.HexColor("#5F5E5A")),
        "h2":       ParagraphStyle("h2",       parent=base, fontSize=13, leading=18, spaceBefore=18, spaceAfter=6, textColor=colors.HexColor("#0C0C0B")),
        "h3":       ParagraphStyle("h3",       parent=base, fontSize=11, leading=15, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#3C3489")),
        "body":     ParagraphStyle("body",     parent=base, fontSize=9,  leading=14, spaceAfter=4,  textColor=colors.HexColor("#2C2C2A")),
        "small":    ParagraphStyle("small",    parent=base, fontSize=8,  leading=12, spaceAfter=2,  textColor=colors.HexColor("#5F5E5A")),
        "label":    ParagraphStyle("label",    parent=base, fontSize=7,  leading=10, textColor=colors.HexColor("#888780")),
        "caveat":   ParagraphStyle("caveat",   parent=base, fontSize=8,  leading=12, spaceAfter=4,  textColor=colors.HexColor("#888780")),
    }

def badge(text, bg, fg):
    return Table(
        [[Paragraph(f"<b>{text.upper()}</b>",
                    ParagraphStyle("b", fontSize=7, leading=9, textColor=fg))]],
        colWidths=[1.6*cm],
        style=TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("ROUNDEDCORNERS", [3]),
            ("TOPPADDING",    (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
            ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ])
    )

def summary_table(df, st):
    docs = df["document"].unique()
    controls = df["control_id"].unique()

    header = [""] + [Paragraph(f"<b>{d.replace('_system_card','').replace('_card','')}</b>",
                                ParagraphStyle("th", fontSize=8, leading=10,
                                               textColor=colors.HexColor("#0C447C")))
                     for d in docs]
    rows = [header]

    for ctrl in controls:
        row = [Paragraph(f"<b>{ctrl}</b>",
                         ParagraphStyle("rc", fontSize=8, leading=10,
                                        textColor=colors.HexColor("#2C2C2A")))]
        for doc in docs:
            match = df[(df["document"]==doc) & (df["control_id"]==ctrl)]
            if match.empty:
                row.append("")
            else:
                status = match.iloc[0]["status"]
                sev    = match.iloc[0]["severity"]
                cell_text = f"{status}\n{sev}"
                row.append(Paragraph(cell_text,
                    ParagraphStyle("cell", fontSize=7, leading=10,
                                   textColor=SEVERITY_TEXT.get(sev, colors.black))))
        rows.append(row)

    col_w = [2*cm] + [3.8*cm] * len(docs)
    tbl = Table(rows, colWidths=col_w, repeatRows=1)

    style_cmds = [
        ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#E6F1FB")),
        ("BACKGROUND",   (0,0), (0,-1),  colors.HexColor("#F1EFE8")),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#D3D1C7")),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ]
    for i, row in enumerate(rows[1:], 1):
        for j, doc in enumerate(docs, 1):
            match = df[(df["document"]==doc) & (df["control_id"]==controls[i-1])]
            if not match.empty:
                sev = match.iloc[0]["severity"]
                bg  = SEVERITY_COLORS.get(sev, colors.white)
                style_cmds.append(("BACKGROUND", (j,i), (j,i), bg))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl

def finding_block(f, st):
    sev_bg = SEVERITY_COLORS.get(f["severity"], colors.white)
    sev_fg = SEVERITY_TEXT.get(f["severity"], colors.black)
    status_bg = STATUS_COLORS.get(f["status"], colors.white)

    header_row = Table([[
        Paragraph(f"<b>{f['control_id']} — {f['control_name']}</b>",
                  ParagraphStyle("fh", fontSize=9, leading=12,
                                 textColor=colors.HexColor("#0C0C0B"))),
        badge(f["status"],   status_bg, sev_fg),
        badge(f["severity"], sev_bg,    sev_fg),
    ]], colWidths=[10*cm, 2*cm, 2*cm],
    style=TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    rows = [
        [Paragraph("<b>Finding</b>",        st["label"]),
         Paragraph(f["finding"],             st["small"])],
        [Paragraph("<b>Evidence</b>",        st["label"]),
         Paragraph(f'<i>"{f["evidence"]}"</i>', st["small"])],
        [Paragraph("<b>LLM suggestion</b>",  st["label"]),
         Paragraph(f["llm_recommendation"],  st["small"])],
        [Paragraph("<b>Auditor rec.</b>",    st["label"]),
         Paragraph(f"<b>{f['auditor_recommendation']}</b>", st["small"])],
        [Paragraph("<b>Reviewed</b>",        st["label"]),
         Paragraph("Yes" if f["auditor_reviewed"] else "Pending", st["small"])],
    ]

    detail = Table(rows, colWidths=[2.8*cm, 11.2*cm],
        style=TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("LINEBELOW",     (0,0), (-1,-2), 0.5, colors.HexColor("#D3D1C7")),
        ]))

    outer = Table([
        [header_row],
        [detail]
    ], colWidths=[14.2*cm],
    style=TableStyle([
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#D3D1C7")),
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#FAFAF9")),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))

    return KeepTogether([outer, Spacer(1, 0.3*cm)])

def systemic_recommendations(df, st):
    elems = []
    elems.append(Paragraph("Systemic recommendations", st["h2"]))
    elems.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#D3D1C7"), spaceAfter=8))

    gap_counts = (df[df["status"]=="gap"]
                  .groupby("control_id")["document"]
                  .count()
                  .sort_values(ascending=False))

    recs = {
        "RC-05": "Human oversight is the most systemic gap — absent in 3 of 4 documents. All providers should publish operator-level override and intervention procedures as a minimum baseline for EU AI Act Article 14 compliance.",
        "RC-03": "Technical documentation is redirected to external sources across all 4 documents. Regulators cannot rely on documents that defer compliance evidence elsewhere. Providers should produce self-contained compliance annexes.",
        "RC-01": "Risk management lifecycle documentation is absent in 3 documents. Providers must distinguish between policy commitments and operational risk management processes — the former does not satisfy Article 9.",
    }

    for ctrl_id, rec in recs.items():
        count = gap_counts.get(ctrl_id, 0)
        elems.append(Paragraph(
            f"<b>{ctrl_id}</b> — gap in {count}/4 documents",
            st["h3"]))
        elems.append(Paragraph(rec, st["body"]))

    return elems

def build_report():
    with open(INPUT) as f:
        findings = json.load(f)

    df = pd.DataFrame(findings)
    st = styles()

    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm
    )

    elems = []

    # --- cover ---
    elems.append(Spacer(1, 1*cm))
    elems.append(Paragraph("AI System Audit Report", st["title"]))
    elems.append(Paragraph(
        f"EU AI Act compliance assessment — Claude, Gemini, GPT-5, Llama 3.1 &nbsp;·&nbsp; {date.today().strftime('%d %b %Y')}",
        st["subtitle"]))
    elems.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#D3D1C7"), spaceAfter=12))

    # --- summary stats ---
    total   = len(findings)
    gaps    = sum(1 for f in findings if f["status"]=="gap")
    highs   = sum(1 for f in findings if f["severity"]=="high")
    reviewed= sum(1 for f in findings if f["auditor_reviewed"])

    stats = Table([[
        Paragraph(f"<b>{total}</b><br/>Total findings", st["small"]),
        Paragraph(f"<b>{gaps}</b><br/>Gaps identified", st["small"]),
        Paragraph(f"<b>{highs}</b><br/>High severity",  st["small"]),
        Paragraph(f"<b>{reviewed}</b><br/>Auditor reviewed", st["small"]),
    ]], colWidths=[3.5*cm]*4,
    style=TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#E6F1FB")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#85B7EB")),
        ("LINEAFTER",     (0,0), (-2,-1), 0.5, colors.HexColor("#85B7EB")),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    elems.append(stats)
    elems.append(Spacer(1, 0.5*cm))

    # --- heatmap ---
    elems.append(Paragraph("Compliance heatmap", st["h2"]))
    elems.append(summary_table(df, st))
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(
        "Color indicates severity: red = high, amber = medium, green = low/compliant.",
        st["caveat"]))
    elems.append(Spacer(1, 0.5*cm))

    # --- per-document findings ---
    elems.append(Paragraph("Detailed findings", st["h2"]))
    elems.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#D3D1C7"), spaceAfter=8))

    for doc_name in df["document"].unique():
        label = doc_name.replace("_system_card","").replace("_card","").replace("_"," ").title()
        elems.append(Paragraph(label, st["h3"]))
        doc_findings = [f for f in findings if f["document"]==doc_name]
        for f in doc_findings:
            elems.append(finding_block(f, st))
        elems.append(Spacer(1, 0.4*cm))

    # --- systemic recommendations ---
    elems += systemic_recommendations(df, st)

    # --- limitations ---
    elems.append(Spacer(1, 0.5*cm))
    elems.append(Paragraph("Limitations", st["h2"]))
    elems.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#D3D1C7"), spaceAfter=8))
    elems.append(Paragraph(
        "This assessment is based solely on publicly available model cards and system cards. "
        "Findings reflect documentation quality, not necessarily the underlying system's actual compliance posture. "
        "LLM-generated findings were reviewed and overridden where necessary by a human auditor. "
        "A full EU AI Act compliance assessment would require access to internal technical documentation, "
        "audit logs, and direct engagement with the provider.",
        st["body"]))

    doc.build(elems)
    print(f"Report saved: {OUTPUT}")

if __name__ == "__main__":
    build_report()