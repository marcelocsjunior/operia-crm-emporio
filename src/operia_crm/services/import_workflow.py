from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from operia_crm.services.core import dedupe_row, import_table, normalize_phone, normalize_text

DEFAULT_IMPORT_INBOX_DIR = Path(os.getenv('OPERIA_IMPORT_INBOX_DIR', 'imports/inbox'))
SERVER_INBOX_SOURCE = 'server_inbox'
UPLOAD_BROWSER_SOURCE = 'upload_browser'

COLUMN_ALIASES = {
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

DISPLAY_COLUMNS = {
    'name': 'Nome',
    'company': 'Empresa',
    'phone': 'Telefone',
    'whatsapp': 'WhatsApp',
    'email': 'E-mail',
    'city': 'Cidade',
    'segment': 'Segmento',
    'origin': 'Origem',
    'status': 'Status',
    'notes': 'Observações',
}


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _detect_file_type(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    if ext == '.csv':
        return 'CSV'
    if ext in {'.xlsx', '.xls'}:
        return 'XLSX'
    return ext.replace('.', '').upper() or 'desconhecido'


def build_import_file_info(file_name: str, content: bytes) -> dict[str, Any]:
    return {
        'file_name': file_name,
        'size': len(content),
        'sha256': file_sha256(content),
        'file_type': _detect_file_type(file_name),
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


def build_import_package(file_name: str, content: bytes, source: str) -> dict[str, Any]:
    return {
        **build_import_file_info(file_name, content),
        'source': source,
        'bytes': content,
        'df': None,
        'diagnostics': None,
        'applied': False,
        'final_summary': None,
    }


def ensure_import_inbox_dir(inbox_dir: Path = DEFAULT_IMPORT_INBOX_DIR) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    return inbox_dir


def _is_allowed_inbox_file(path: Path) -> bool:
    name = path.name
    lower_name = name.lower()
    if not path.is_file():
        return False
    if name.startswith('.') or name.startswith('~') or name.startswith('~$'):
        return False
    if lower_name.endswith('~') or lower_name.endswith('.tmp') or lower_name.endswith('.temp') or lower_name.endswith('.part'):
        return False
    return path.suffix.lower() in {'.csv', '.xlsx'}


def list_import_inbox_files(inbox_dir: Path = DEFAULT_IMPORT_INBOX_DIR) -> list[str]:
    inbox_dir = ensure_import_inbox_dir(inbox_dir)
    return sorted(path.name for path in inbox_dir.iterdir() if _is_allowed_inbox_file(path))


def load_import_inbox_file(file_name: str, inbox_dir: Path = DEFAULT_IMPORT_INBOX_DIR) -> tuple[str, bytes]:
    inbox_dir = ensure_import_inbox_dir(inbox_dir).resolve()
    requested = Path(file_name)
    if requested.name != file_name or requested.is_absolute():
        raise ValueError('Arquivo inválido para importação.')
    path = (inbox_dir / file_name).resolve()
    if path.parent != inbox_dir or not _is_allowed_inbox_file(path):
        raise ValueError('Arquivo inválido para importação.')
    return path.name, path.read_bytes()


def _clean_cell(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _recognized_columns(columns) -> list[dict[str, str]]:
    recognized = []
    seen = set()
    for column in columns:
        raw = str(column).strip()
        canonical = COLUMN_ALIASES.get(raw.lower())
        if canonical and raw.lower() not in seen:
            recognized.append({
                'column': raw,
                'field': canonical,
                'label': DISPLAY_COLUMNS.get(canonical, canonical),
            })
            seen.add(raw.lower())
    return recognized


def _ignored_columns(columns) -> list[str]:
    ignored = []
    for column in columns:
        raw = str(column).strip()
        if raw.lower() not in COLUMN_ALIASES:
            ignored.append(raw)
    return ignored


def _canonical_row(row: dict[str, Any]) -> dict[str, Any]:
    canonical = {}
    for key, value in row.items():
        mapped = COLUMN_ALIASES.get(str(key).strip().lower())
        if mapped and mapped not in canonical:
            canonical[mapped] = value
    return canonical


def summarize_import_analysis(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        'total_linhas': len(rows),
        'prontas_para_importar': 0,
        'duplicadas_fortes': 0,
        'duplicadas_provaveis': 0,
        'ignoradas_sem_nome': 0,
        'ignoradas_sem_contato': 0,
        'com_alerta': 0,
        'erros': 0,
    }
    for row in rows:
        action = row.get('acao_prevista')
        status = row.get('status_analise')
        dedupe = row.get('dedupe')
        reason_key = row.get('reason_key')
        if action == 'Importar':
            summary['prontas_para_importar'] += 1
        if dedupe == 'duplicado forte':
            summary['duplicadas_fortes'] += 1
        if dedupe == 'duplicado provável':
            summary['duplicadas_provaveis'] += 1
        if reason_key == 'sem_nome':
            summary['ignoradas_sem_nome'] += 1
        if reason_key == 'sem_contato':
            summary['ignoradas_sem_contato'] += 1
        if status == 'OK com alerta':
            summary['com_alerta'] += 1
        if status == 'Erro':
            summary['erros'] += 1
    return summary


def analyze_import_dataframe(df, existing: list[dict]) -> dict[str, Any]:
    columns = [str(column).strip() for column in df.columns]
    recognized_columns = _recognized_columns(columns)
    ignored_columns = _ignored_columns(columns)
    rows: list[dict[str, Any]] = []

    for index, row in df.iterrows():
        try:
            raw_row = {str(k).strip(): v for k, v in row.to_dict().items()}
            canonical = _canonical_row(raw_row)
            name = _clean_cell(canonical.get('name'))
            company = _clean_cell(canonical.get('company'))
            phone = _clean_cell(canonical.get('phone'))
            whatsapp = _clean_cell(canonical.get('whatsapp'))
            email = _clean_cell(canonical.get('email'))

            if not name:
                dedupe = 'não avaliado'
                status = 'Ignorada'
                reason = 'Sem nome.'
                reason_key = 'sem_nome'
                action = 'Ignorar'
            else:
                dedupe = dedupe_row(canonical, existing)
                has_phone = bool(normalize_phone(phone))
                has_whatsapp = bool(normalize_phone(whatsapp))
                has_email = bool(normalize_text(email))
                has_contact = has_phone or has_whatsapp or has_email

                if dedupe == 'duplicado forte':
                    status = 'Ignorada'
                    reason = 'Duplicidade forte detectada.'
                    reason_key = 'duplicado_forte'
                    action = 'Ignorar'
                elif not has_contact:
                    status = 'Ignorada'
                    reason = 'Sem telefone, WhatsApp ou e-mail.'
                    reason_key = 'sem_contato'
                    action = 'Ignorar'
                elif dedupe == 'duplicado provável':
                    status = 'OK com alerta'
                    reason = 'Duplicidade provável detectada.'
                    reason_key = 'duplicado_provavel'
                    action = 'Importar'
                elif not (has_phone and has_whatsapp and has_email):
                    status = 'OK com alerta'
                    missing = []
                    if not has_phone:
                        missing.append('telefone')
                    if not has_whatsapp:
                        missing.append('WhatsApp')
                    if not has_email:
                        missing.append('e-mail')
                    reason = f"Contato incompleto: {', '.join(missing)} vazio(s), mas existe contato válido."
                    reason_key = 'contato_incompleto'
                    action = 'Importar'
                else:
                    status = 'OK'
                    reason = 'Linha pronta para importação.'
                    reason_key = 'ok'
                    action = 'Importar'

            rows.append({
                'linha': int(index) + 2,
                'nome': name,
                'empresa': company,
                'telefone': phone,
                'whatsapp': whatsapp,
                'email': email,
                'dedupe': dedupe,
                'status_analise': status,
                'motivo': reason,
                'acao_prevista': action,
                'reason_key': reason_key,
            })
        except Exception as exc:  # noqa: BLE001
            rows.append({
                'linha': int(index) + 2,
                'nome': '',
                'empresa': '',
                'telefone': '',
                'whatsapp': '',
                'email': '',
                'dedupe': 'não avaliado',
                'status_analise': 'Erro',
                'motivo': f'Erro de processamento da linha: {exc}',
                'acao_prevista': 'Ignorar',
                'reason_key': 'erro',
            })

    return {
        'columns': columns,
        'recognized_columns': recognized_columns,
        'ignored_columns': ignored_columns,
        'rows': rows,
        'summary': summarize_import_analysis(rows),
    }


def _failure_reason(exc: Exception, content: bytes) -> tuple[str, str]:
    message = str(exc).lower()
    if not content:
        return 'arquivo vazio.', 'Envie um CSV UTF-8 ou XLSX com dados e cabeçalho.'
    if 'sem coluna name/nome' in message or 'name/nome' in message:
        return 'coluna nome/name não encontrada.', 'Ajuste o cabeçalho da planilha para conter nome ou name e selecione o arquivo novamente.'
    if 'emptydataerror' in message or 'no columns to parse' in message:
        return 'arquivo vazio ou planilha sem dados.', 'Confira se a planilha possui cabeçalho e pelo menos uma linha de dados.'
    if 'excel' in message or 'workbook' in message or 'file is not a zip file' in message:
        return 'formato inválido para planilha.', 'Salve o arquivo como CSV UTF-8 ou XLSX e tente novamente.'
    if 'csv' in message or 'separator' in message or 'separador' in message:
        return 'separador não reconhecido ou CSV inválido.', 'Salve como CSV UTF-8 usando vírgula ou ponto e vírgula e tente novamente.'
    return 'formato inválido ou dados incompatíveis.', 'Confira se existe coluna nome/name e se há telefone, WhatsApp ou e-mail.'


def build_import_diagnostics(file_name: str, content: bytes, existing: list[dict]) -> dict[str, Any]:
    file_info = build_import_file_info(file_name, content)
    base = {
        **file_info,
        'success': False,
        'message': 'Não foi possível analisar o arquivo.',
        'reason': '',
        'recommendation': '',
        'df': None,
        'columns': [],
        'recognized_columns': [],
        'ignored_columns': [],
        'summary': summarize_import_analysis([]),
        'rows': [],
        'row_count': 0,
    }
    try:
        df = import_table(file_name, content)
        analysis = analyze_import_dataframe(df, existing)
        return {
            **base,
            'success': True,
            'message': 'Arquivo analisado com sucesso. Revise o diagnóstico antes de confirmar a importação.',
            'reason': 'Leitura concluída.',
            'recommendation': 'Revise as colunas reconhecidas, as linhas analisadas e confirme somente se estiver tudo correto.',
            'df': df,
            'columns': analysis['columns'],
            'recognized_columns': analysis['recognized_columns'],
            'ignored_columns': analysis['ignored_columns'],
            'summary': analysis['summary'],
            'rows': analysis['rows'],
            'row_count': len(df),
        }
    except Exception as exc:  # noqa: BLE001
        reason, recommendation = _failure_reason(exc, content)
        return {
            **base,
            'message': 'Não foi possível ler o arquivo.',
            'reason': f'Motivo provável: {reason}',
            'recommendation': f'Ação recomendada: {recommendation}',
        }
