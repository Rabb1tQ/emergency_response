#!/usr/bin/env python3
import yaml
import re
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class RuleEngine:
    def __init__(self):
        self.rules = self.load_rules()
    
    def load_rules(self):
        rules_dir = Path(__file__).parent / 'rules'
        rules = {}
        loaded_files = 0
        for rule_file in rules_dir.rglob('*.yml'):
            try:
                relative_path = rule_file.relative_to(rules_dir)
                print(f"Loading rules from: {relative_path}")
                with open(rule_file, 'r', encoding='utf-8') as f:
                    try:
                        rule_data = yaml.safe_load(f)
                        if isinstance(rule_data, dict) and 'id' in rule_data:
                            rules[rule_data['id']] = rule_data
                            loaded_files += 1
                        elif isinstance(rule_data, list):
                            for rule in rule_data:
                                if isinstance(rule, dict) and 'id' in rule:
                                    rules[rule['id']] = rule
                                    loaded_files += 1
                    except yaml.YAMLError as ye:
                        print(f"YAML parsing error in {relative_path}: {str(ye)}")
                    except Exception as e:
                        print(f"Error processing rules in {relative_path}: {str(e)}")
            except Exception as e:
                print(f"Error reading file {rule_file}: {str(e)}")
        print(f"Successfully loaded {loaded_files} rules from {len(list(rules_dir.rglob('*.yml')))} files")
        return rules

    def evaluate_rule(self, rule, data):
        try:
            return self._evaluate_legacy_rule(rule, data)
        except Exception as e:
            print(f"Rule evaluation error: {str(e)}")
        return False

    def _evaluate_legacy_rule(self, rule, data):
        if 'pattern' not in rule:
            return False
        try:
            pattern = re.compile(rule['pattern'], re.I if rule.get('case_insensitive', True) else 0)
            content = data.get(rule.get('target_field', 'content'), '')
            if not content:
                return False
            matches = pattern.finditer(content)
            findings = []
            for match in matches:
                findings.append({
                    'start': match.start(),
                    'end': match.end(),
                    'matched_text': match.group(0)
                })
            if findings:
                return {
                    'rule_id': rule['id'],
                    'level': rule.get('level', 'medium'),
                    'description': rule.get('description', ''),
                    'findings': findings
                }
        except Exception as e:
            print(f"Rule evaluation error: {str(e)}")
        return False

    def analyze_report(self, report_data):
        results = {
            'high': [],
            'medium': [],
            'low': []
        }
        print("\nStarting report analysis...")
        for section, content in report_data.items():
            print(f"\nAnalyzing section: {section}")
            if isinstance(content, dict):
                for subsection, subcontent in content.items():
                    print(f"  Analyzing subsection: {subsection}")
                    data = {
                        'section': section,
                        'subsection': subsection,
                        'content': str(subcontent)
                    }
                    for rule in self.rules.values():
                        if rule.get('target_section') == section or not rule.get('target_section'):
                            print(f"    [Legacy] Matching rule: {rule.get('id')} | {rule.get('description', '')}")
                            result = self.evaluate_rule(rule, data)
                            if result:
                                print(f"Legacy rule {rule.get('id')} matched!")
                                results[result['level']].append({
                                    **result,
                                    'section': section,
                                    'subsection': subsection
                                })
        print("\nAnalysis complete!")
        print(f"Results: High: {len(results['high'])}, Medium: {len(results['medium'])}, Low: {len(results['low'])}")
        return results

engine = RuleEngine()

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        report_data = request.json
        if not report_data:
            return jsonify({'error': 'No data provided'}), 400
        results = engine.analyze_report(report_data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 