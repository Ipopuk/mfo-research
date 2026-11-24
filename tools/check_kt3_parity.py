"""Compare the KT2 and KT3 command-line results after building the Java JAR."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
source = ROOT / 'src/sample_data.json'
assert source.read_bytes() == (ROOT / 'src/java/sample_data.json').read_bytes()
base = json.loads(source.read_text(encoding='utf-8'))

def changed(*edits):
    case = deepcopy(base)
    for path, value in edits:
        item = case
        for key in path[:-1]:
            item = item[key]
        item[path[-1]] = value
    return case

cases = {
    'approved': base,
    'missing contact': changed((('applicant', 'contact'), '')),
    'blank name': changed((('applicant', 'full_name'), ' \t ')),
    'Unicode blank name': changed((('applicant', 'full_name'), '\u00a0\u2007\u202f\u0085')),
    'zero amount': changed((('application', 'amount'), 0)),
    'invalid document': changed((('documents', 1, 'valid'), False)),
    'foreign application link': changed((('application_documents', 1, 'application_id'), 'another')),
    'unknown linked document': changed((('application_documents', 1, 'document_id'), 'unknown')),
    'no income': changed((('incomes',), [])),
    'unverified income': changed((('incomes', 0, 'verified'), False)),
    'inactive obligation': changed((('obligations', 0, 'active'), False)),
    'retry notification': changed((('notification', 'sent'), False)),
    'refused': changed((('employee_decision', 'outcome'), 'refused')),
    'rounding non-tie': changed((('incomes', 0, 'monthly_amount'), 800),
        (('incomes', 1, 'verified'), False), (('obligations',), []), (('proposed_monthly_payment',), 81)),
    'decimal tie rounds up': changed((('incomes', 0, 'monthly_amount'), 22508.60),
        (('incomes', 1, 'monthly_amount'), 9411.40), (('obligations', 0, 'monthly_payment'), 1411.12),
        (('proposed_monthly_payment',), 8659.64)),
    'decimal tie rounds down': changed((('proposed_monthly_payment',), 17960)),
    'negative payment': changed((('proposed_monthly_payment',), -1)),
    'already final': changed((('application', 'status'), 'approved')),
    'wrong applicant': changed((('application', 'applicant_id'), 'other')),
    'missing refusal reason': changed((('employee_decision', 'outcome'), 'refused'),
        (('employee_decision', 'reason'), '')),
    'approval with zero term': changed((('employee_decision', 'approved_term_months'), 0)),
    'missing notification channel': changed((('notification', 'channel'), '')),
}

expected_shares = {'rounding non-tie': 10.1, 'decimal tie rounds up': 31.6, 'decimal tie rounds down': 37.4}
java_command = ['java', '-Dfile.encoding=UTF-8', '-jar',
                str(ROOT / 'src/java/target/mfo-kt3.jar'), '--data']

with TemporaryDirectory() as directory:
    for index, (name, data) in enumerate(cases.items()):
        path = Path(directory) / f'case-{index}.json'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        python = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'src/main.py'), '--data', str(path)],
                                capture_output=True, encoding='utf-8')
        java = subprocess.run([*java_command, str(path)], capture_output=True, encoding='utf-8')
        assert bool(python.returncode) == bool(java.returncode), (name, python, java)
        if not python.returncode:
            result = json.loads(java.stdout)
            assert json.loads(python.stdout) == result, (name, python.stdout, java.stdout)
            if name in {'blank name', 'Unicode blank name'}:
                assert result['completeness']['missing_fields'] == ['applicant.full_name']
                assert result['next_step'] == 'request_information'
            if name in expected_shares:
                assert result['payment_load']['payment_share_percent'] == expected_shares[name]
        else:
            assert java.stderr.strip() in python.stderr.splitlines()[-1], (name, python.stderr, java.stderr)
        print(f'{name}: OK')

    missing_amounts = [
        ('incomes', 'monthly_amount', 'Поле monthly_amount записи дохода income-1 должно быть числом'),
        ('obligations', 'monthly_payment', 'Поле monthly_payment записи обязательства obligation-1 должно быть числом'),
    ]
    for collection, field, expected_error in missing_amounts:
        data = deepcopy(base)
        del data[collection][0][field]
        path = Path(directory) / f'missing-{field}.json'
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        java = subprocess.run([*java_command, str(path)], capture_output=True, encoding='utf-8')
        assert java.returncode == 1 and not java.stdout.strip(), (field, java)
        assert java.stderr.strip() == expected_error, (field, java.stderr)
        print(f'{field} diagnostic: OK')
print(f'{len(cases)} shared cases and {len(missing_amounts)} Java diagnostics: OK')
