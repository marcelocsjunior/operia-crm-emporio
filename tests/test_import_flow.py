import pytest

pd = pytest.importorskip("pandas")

from operia_crm.services.core import create_lead, import_deduped_leads, import_table


def test_import_csv_normal():
    df = import_table('leads.csv', b'name,email\nAlice,alice@example.com\n')
    assert len(df) == 1
    assert df.iloc[0]['name'] == 'Alice'


def test_import_csv_cp1252_encoding():
    content = 'nome;email\nJo\xe3o;joao@x.com\n'.encode('cp1252')
    df = import_table('leads.csv', content)
    assert len(df) == 1
    assert df.iloc[0]['nome'] == 'João'


def test_import_xlsx_extension_with_csv_content():
    df = import_table('leads.xlsx', b'name,phone\nMaria,11999990000\n')
    assert len(df) == 1
    assert df.iloc[0]['name'] == 'Maria'


def test_import_deduped_leads_summary(isolated_env):
    create_lead({'name': 'Existente', 'phone': '11911112222', 'origin': 'Site', 'status': 'Novo lead'})
    # carrega existentes reais
    from operia_crm.services.core import list_leads
    existing = [dict(x) for x in list_leads()]

    df = pd.DataFrame([
        {'name': 'Novo 1', 'email': 'novo1@x.com'},
        {'name': '', 'email': 'semnome@x.com'},
        {'name': 'Sem Contato'},
        {'name': 'Dup Forte', 'phone': '11911112222'},
    ])
    df['dedupe'] = ['não duplicado', 'não duplicado', 'não duplicado', 'duplicado forte']

    summary = import_deduped_leads(df, existing)
    assert summary == {
        'total_linhas': 4,
        'importados': 1,
        'ignorados_duplicidade': 1,
        'ignorados_sem_nome': 1,
        'ignorados_sem_contato': 1,
        'erros': 0,
    }


def test_import_defaults_status_origin(isolated_env):
    from operia_crm.services.core import list_leads

    df = pd.DataFrame([{'name': 'Com Default', 'email': 'd@x.com'}])
    summary = import_deduped_leads(df, [])
    assert summary['importados'] == 1
    lead = dict(list_leads()[0])
    assert lead['status'] == 'Novo lead'
    assert lead['origin'] == 'Prospecção ativa'
