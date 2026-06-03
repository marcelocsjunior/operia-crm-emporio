import pickle

from operia_crm.services.core import create_lead, list_leads


def test_list_leads_rows_convert_to_dict_and_widget_options_are_pickleable(isolated_env):
    create_lead({"name": "Lead Teste", "origin": "Site", "status": "Novo lead"})

    lead_rows = list_leads()
    leads = [dict(row) for row in lead_rows]

    assert leads
    assert isinstance(leads[0], dict)

    lead_options = {int(lead["id"]): f"{lead['id']} - {lead['name']}" for lead in leads}

    assert all(isinstance(lead_id, int) for lead_id in lead_options)
    assert all(isinstance(label, str) for label in lead_options.values())

    pickle.dumps(list(lead_options.keys()))
    pickle.dumps(lead_options)
