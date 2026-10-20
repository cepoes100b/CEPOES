"""Contrato de permisos de ingesta; sin red, dependencias ni credenciales."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('legislativa.sql', 'expediente_analyses', 'legislative-analysis-ingest-v2', {'select', 'insert', 'update'}),
    ('008_prensa_editorial.sql', 'press_notes', 'press-draft-ingest', {'select', 'insert'}),
)


def grants(sql, table):
    sql = re.sub(r'--[^\n]*', '', sql.lower())
    result = set()
    for privileges, roles in re.findall(r'grant\s+([\w\s,]+)\s+on\s+(?:table\s+)?public\.' + table + r'\s+to\s+([\w\s,]+);', sql):
        if 'service_role' in roles.replace(' ', '').split(','):
            result.update(p.strip() for p in privileges.split(','))
    return result


class IngestGrants(unittest.TestCase):
    def test_explicit_minimum_and_rls(self):
        for file, table, _, expected in CASES:
            with self.subTest(table=table):
                sql = (ROOT / 'infra/supabase' / file).read_text()
                self.assertEqual(grants(sql, table), expected)
                self.assertIn(f'alter table public.{table} enable row level security;', sql)
                self.assertNotRegex(sql.lower(), r'alter\s+default\s+privileges')

    def test_function_operations_match_contract(self):
        for _, table, function, expected in CASES:
            with self.subTest(function=function):
                code = (ROOT / 'supabase/functions' / function / 'index.ts').read_text()
                # Current handlers terminate every query with a semicolon.
                chains = re.findall(r'\.from\("' + table + r'"\)([^;]+);', code)
                operations = set(re.findall(r'\.(select|insert|update|delete|upsert)\(', '\n'.join(chains)))
                self.assertEqual(operations, expected)
                self.assertIn('SUPABASE_SERVICE_ROLE_KEY', code)

    def test_missing_or_excess_grant_is_detected(self):
        for file, table, _, expected in CASES:
            sql = (ROOT / 'infra/supabase' / file).read_text()
            missing = re.sub(r'grant [^;]+ on public\.' + table + r' to service_role;', '', sql)
            self.assertNotEqual(grants(missing, table), expected)
            excess = sql + f'\ngrant delete on public.{table} to service_role;'
            self.assertNotEqual(grants(excess, table), expected)


if __name__ == '__main__':
    unittest.main()
