from __future__ import annotations
import csv
import io
import math
import numbers
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from operia_crm.config.settings import settings
from operia_crm.database.db import get_conn
from operia_crm.services.emporio_mode import (
    calculate_emporio_priority,
    normalize_emporio_status,
    normalize_opportunity_type,
    parse_emporio_date,
    parse_emporio_import_fields,
)

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.png', '.jpg', '.jpeg'}


def _is_blank(value) -> bool:
    if value is None:
        return True
    try:
        if value != value:  # NaN (float('nan'), numpy.nan, pandas NA-like comparisons)
            return True
    except Exception:
        pass
    normalized = str(value).strip().lower()
    return normalized in {'', 'nan', 'none', '<na>'}


def _is_integer_float(value) -> bool:
    return (
        isinstance(value, numbers.Real)
        and not isinstance(value, bool)
        and not isinstance(value, numbers.Integral)
        and math.isfinite(float(value))
        and float(value).is_integer()
    )


def _first_non_blank(*values):
    for value in values:
        if not _is_blank(value):
            return value
    return None


def _clean_import_value(value):
    if _is_blank(value):
        return None
    if _is_integer_float(value):
        return str(int(value))
    return str(value).strip()


def normalize_phone(v) -> str:
    if _is_blank(v):
        return ''
    if _is_integer_float(v):
        v = int(v)
    return re.sub(r'\D', '', str(v).strip())


def normalize_text(v) -> str:
    if _is_blank(v):
        return ''
    return str(v).strip().lower()


def calculate_score(lead: dict) -> int:
    score = 20
    if normalize_phone(lead.get('phone') or lead.get('whatsapp')):
        score += 15
    if normalize_text(lead.get('email')):
        score += 15
    if lead.get('status') in {'Proposta enviada', 'Negociação'}:
        score += 30
    if lead.get('status') == 'Qualificar':
        score += 10
    if lead.get('next_followup'):
        score += 10
    emporio = calculate_emporio_priority(lead)
    if emporio["priority"] == "Alta":
        score += 20
    elif emporio["priority"] == "Média":
        score += 10
    return max(0, min(100, score))


def create_lead(payload: dict) -> int:
    payload = dict(payload)
    if payload.get("opportunity_type"):
        payload["opportunity_type"] = normalize_opportunity_type(payload.get("opportunity_type"))
    if payload.get("emporio_status"):
        payload["emporio_status"] = normalize_emporio_status(payload.get("emporio_status"))
    if payload.get("event_or_delivery_date"):
        event_date = parse_emporio_date(payload.get("event_or_delivery_date"))
        payload["event_or_delivery_date"] = event_date.isoformat() if event_date else None
    payload['score'] = calculate_score(payload)
    with get_conn() as conn:
        cur = conn.execute(
            '''INSERT INTO leads (
                   name,company,phone,whatsapp,email,city,segment,origin,status,score,next_followup,notes,
                   opportunity_type,event_or_delivery_date,estimated_value,people_count,source_channel,
                   emporio_status,next_action,operational_notes
               )
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                payload['name'], payload.get('company'), payload.get('phone'), payload.get('whatsapp'), payload.get('email'),
                payload.get('city'), payload.get('segment'), payload['origin'], payload['status'], payload['score'],
                payload.get('next_followup'), payload.get('notes'),
                payload.get('opportunity_type'), payload.get('event_or_delivery_date'), payload.get('estimated_value'),
                payload.get('people_count'), payload.get('source_channel'), payload.get('emporio_status'),
                payload.get('next_action'), payload.get('operational_notes'),
            ),
        )
        lead_id = cur.lastrowid
        audit(conn, 'lead_created', 'lead', str(lead_id), f"lead {payload['name']}")
        return lead_id


def audit(conn, event_type, entity_type, entity_id, details=''):
    conn.execute('INSERT INTO audit_events (event_type,entity_type,entity_id,details) VALUES (?,?,?,?)',
                 (event_type, entity_type, entity_id, details))


def list_leads():
    with get_conn() as conn:
        return conn.execute('SELECT * FROM leads ORDER BY created_at DESC').fetchall()


def import_table(file_name: str, content: bytes):
    import pandas as pd

    ext = Path(file_name).suffix.lower()

    def _read_csv_bytes(raw: bytes):
        last_error = None
        fallback_df = None
        for encoding in ('utf-8-sig', 'cp1252'):
            for sep in (',', ';'):
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding=encoding, sep=sep)
                    columns = {str(c).strip().lower() for c in df.columns}
                    if 'name' in columns or 'nome' in columns:
                        return df
                    if fallback_df is None:
                        fallback_df = df
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
        if fallback_df is not None:
            return fallback_df
        raise ValueError(f'Não foi possível ler CSV ({last_error})')

    if ext == '.csv':
        df = _read_csv_bytes(content)
    else:
        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        except Exception:
            df = _read_csv_bytes(content)

    if len(df.columns) == 1:
        sample = df.iloc[:, 0].astype(str).head(20)
        if sample.str.contains(r'[;,]').any():
            raw_csv = '\n'.join(df.iloc[:, 0].astype(str).tolist()).encode('utf-8', errors='ignore')
            try:
                df = _read_csv_bytes(raw_csv)
            except Exception:
                pass

    columns = {str(c).strip().lower() for c in df.columns}
    if 'name' not in columns and 'nome' not in columns:
        raise ValueError('Arquivo sem coluna name/nome')
    return df


def dedupe_row(row: dict, existing: list[dict]) -> str:
    p = normalize_phone(_first_non_blank(row.get('phone'), row.get('whatsapp')))
    e = normalize_text(row.get('email'))
    n = normalize_text(_first_non_blank(row.get('name'), row.get('nome')))
    row_city = normalize_text(row.get('city') or row.get('cidade'))
    for lead in existing:
        existing_phones = {normalize_phone(lead.get('phone')), normalize_phone(lead.get('whatsapp'))}
        if p and p in existing_phones:
            return 'duplicado forte'
        if e and e == normalize_text(lead.get('email')):
            return 'duplicado forte'
        if n and n == normalize_text(lead.get('name')) and row_city == normalize_text(lead.get('city')):
            return 'duplicado provável'
    return 'não duplicado'


def import_deduped_leads(df, existing: list[dict]) -> dict:
    alias = {
        'name': 'name', 'nome': 'name',
        'company': 'company', 'empresa': 'company',
        'phone': 'phone', 'telefone': 'phone',
        'whatsapp': 'whatsapp',
        'email': 'email', 'e-mail': 'email',
        'city': 'city', 'cidade': 'city',
        'segment': 'segment', 'segmento': 'segment',
        'origin': 'origin', 'origem': 'origin',
        'status': 'status',
        'notes': 'notes', 'observacoes': 'notes', 'observações': 'notes',
    }
    alias.update({
        'tipo_oportunidade': 'opportunity_type',
        'opportunity_type': 'opportunity_type',
        'data_evento_ou_entrega': 'event_or_delivery_date',
        'event_or_delivery_date': 'event_or_delivery_date',
        'valor_estimado': 'estimated_value',
        'estimated_value': 'estimated_value',
        'quantidade_pessoas': 'people_count',
        'people_count': 'people_count',
        'canal_origem': 'source_channel',
        'source_channel': 'source_channel',
        'status_emporio': 'emporio_status',
        'emporio_status': 'emporio_status',
        'proxima_acao': 'next_action',
        'next_action': 'next_action',
        'observacao_operacional': 'operational_notes',
        'operational_notes': 'operational_notes',
    })
    summary = {'total_linhas': len(df), 'importados': 0, 'ignorados_duplicidade': 0, 'ignorados_sem_nome': 0, 'ignorados_sem_contato': 0, 'erros': 0}

    for _, row in df.iterrows():
        row_dict = {str(k).strip().lower(): v for k, v in row.to_dict().items()}
        dedupe = dedupe_row(row_dict, existing)
        if dedupe == 'duplicado forte':
            summary['ignorados_duplicidade'] += 1
            continue

        payload = {}
        for k, v in row_dict.items():
            mapped = alias.get(k)
            if mapped:
                payload[mapped] = _clean_import_value(v)
        payload.update(parse_emporio_import_fields(row_dict))

        if not payload.get('name'):
            summary['ignorados_sem_nome'] += 1
            continue

        has_contact = bool(
            normalize_phone(payload.get('phone'))
            or normalize_phone(payload.get('whatsapp'))
            or normalize_text(payload.get('email'))
        )
        if not has_contact:
            summary['ignorados_sem_contato'] += 1
            continue

        payload['status'] = payload.get('status') or 'Novo lead'
        payload['origin'] = payload.get('origin') or 'Prospecção ativa'

        try:
            create_lead(payload)
            existing.append(payload)
            summary['importados'] += 1
        except Exception:
            summary['erros'] += 1
    return summary


def create_proposal(lead_id: int, total_value: float, content: str, validity_date: str | None) -> str:
    with get_conn() as conn:
        last = conn.execute("SELECT number FROM proposals ORDER BY id DESC LIMIT 1").fetchone()
        seq = int(last['number'].split('-')[1]) + 1 if last else 1
        number = f'PROP-{seq:04d}'
        conn.execute('INSERT INTO proposals (lead_id,number,status,total_value,content,validity_date) VALUES (?,?,?,?,?,?)',
                     (lead_id, number, 'Aberta', total_value, content, validity_date))
        audit(conn, 'proposal_created', 'proposal', number, '')
        return number


def generate_proposal_pdf(number: str, lead_name: str, total_value: float, content: str | None = None) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    out = Path('data') / f'{number}.pdf'
    c = canvas.Canvas(str(out), pagesize=A4)

    page_width, page_height = A4
    left_margin = 20 * mm
    y = page_height - (25 * mm)

    c.setTitle(f'OperIA CRM Emporio - {number}')
    c.setFont('Helvetica-Bold', 18)
    c.drawString(left_margin, y, 'OperIA CRM - Emporio')
    y -= 10 * mm

    c.setFont('Helvetica-Bold', 13)
    c.drawString(left_margin, y, f'Proposta {number}')
    y -= 9 * mm

    c.setFont('Helvetica', 11)
    c.drawString(left_margin, y, f'Lead/Cliente: {lead_name}')
    y -= 7 * mm
    c.drawString(left_margin, y, f'Data: {date.today().isoformat()}')
    y -= 7 * mm
    c.drawString(left_margin, y, f'Valor total: R$ {total_value:,.2f}')

    if content and content.strip():
        y -= 11 * mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(left_margin, y, 'Resumo da proposta')
        y -= 6 * mm
        c.setFont('Helvetica', 10)
        for line in str(content).splitlines():
            safe_line = line.strip()
            if not safe_line:
                y -= 5 * mm
                continue
            c.drawString(left_margin, y, safe_line[:100])
            y -= 5 * mm
            if y < 25 * mm:
                c.showPage()
                y = page_height - (25 * mm)
                c.setFont('Helvetica', 10)

    c.save()
    return out


def save_attachment(lead_id: int, filename: str, data: bytes, note: str = '') -> Path:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Formato de arquivo não permitido')
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"lead{lead_id}_{int(datetime.now().timestamp())}{ext}"
    path = settings.attachments_dir / safe_name
    path.write_bytes(data)
    with get_conn() as conn:
        conn.execute('INSERT INTO attachments (lead_id,original_name,saved_name,extension,size_bytes,note) VALUES (?,?,?,?,?,?)',
                     (lead_id, filename, safe_name, ext, len(data), note))
        audit(conn, 'attachment_added', 'lead', str(lead_id), filename)
    return path


def export_leads_csv() -> str:
    rows = list_leads()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['id', 'name', 'company', 'phone', 'email', 'status', 'score'])
    for r in rows:
        w.writerow([r['id'], r['name'], r['company'], r['phone'], r['email'], r['status'], r['score']])
    return output.getvalue()


def backup_now() -> Path:
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_backup = settings.backups_dir / f'operia_{stamp}.db'
    shutil.copy2(settings.db_path, db_backup)
    att_backup = settings.backups_dir / f'attachments_{stamp}'
    if settings.attachments_dir.exists():
        shutil.copytree(settings.attachments_dir, att_backup)
    return db_backup


def register_interaction(lead_id: int, kind: str, summary: str, channel: str, followup_date: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            'INSERT INTO interactions (lead_id,kind,summary,channel,pending,followup_date) VALUES (?,?,?,?,?,?)',
            (lead_id, kind, summary, channel, 1, followup_date),
        )
        interaction_id = cur.lastrowid
        audit(conn, 'interaction_registered', 'interaction', str(interaction_id), f'{kind} pendente')
        return interaction_id


def confirm_interaction(interaction_id: int) -> None:
    with get_conn() as conn:
        conn.execute('UPDATE interactions SET pending = 0 WHERE id = ?', (interaction_id,))
        audit(conn, 'interaction_confirmed', 'interaction', str(interaction_id), 'confirmação manual')


def list_interactions(lead_id: int):
    with get_conn() as conn:
        return conn.execute('SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at DESC', (lead_id,)).fetchall()
