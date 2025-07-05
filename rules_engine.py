#!/usr/bin/env python3
import yaml
import re
import json
import subprocess
import os
from pathlib import Path
from flask import Flask, request, jsonify, render_template
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


def parse_text_report(text):
    """
    将原始文本格式的应急响应报告解析为结构化的 dict，
    结构与前端 parseTextReport() 相同。
    """
    sections = text.split("##########################################")
    result = {}

    for section in sections:
        if not section.strip():
            continue

        module_match = re.search(r'模块:\s*(.*?)\n', section)
        if not module_match:
            continue

        module_title = module_match.group(1).strip()
        module_key = next((k for k, v in TAB_TITLES.items() if v == module_title), None)
        if not module_key:
            continue

        subsections = re.split(r'------------------------------------------\s*', section)
        result[module_key] = {}

        i = 1  # 第一个可能是标题
        while i < len(subsections):
            title_match = re.search(r'子项:\s*(.*?)\n', subsections[i])
            if not title_match:
                i += 1
                continue

            title = title_match.group(1).strip()
            content = subsections[i + 1].strip() if i + 1 < len(subsections) else ""
            result[module_key][title] = content
            i += 2  # 跳过标题和内容

    return result


# 前端定义的 TAB_TITLES 映射表
TAB_TITLES = {
    "backdoor": "系统后门排查",
    "user": "用户与登录检查",
    "log": "日志分析",
    "network": "网络检查",
    "process": "进程检查",
    "filesystem": "文件系统检查",
    "package": "软件包检查",
    "persistence": "持久化检查",
    "integrity": "系统完整性",
    "malware": "恶意进程与提权点"
}


@app.route('/list_reports', methods=['GET'])
def list_reports():
    try:
        reports_dir = Path(__file__).parent / 'report'
        if not reports_dir.exists():
            return jsonify({'error': 'Report directory not found'}), 404

        # 获取 report 目录下的所有文件名
        files = [f.name for f in reports_dir.iterdir() if f.is_file()]
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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

@app.route('/analyze_file', methods=['POST'])
def analyze_file():
    try:
        # 获取请求中的文件名
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({'error': 'Filename is required'}), 400

        reports_dir = Path(__file__).parent / 'report'
        file_path = reports_dir / filename

        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

        # 读取原始文本报告文件
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        # 解析文本报告为结构化数据
        report_data = parse_text_report(raw_text)

        # 使用 RuleEngine 分析报告
        results = engine.analyze_report(report_data)
        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/check', methods=['GET'])
def run_shell():
    try:
        result = subprocess.run(
            ['./emergency_response.sh'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return jsonify({
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stdout': e.stdout,
            'stderr': e.stderr
        }), 500
@app.route('/report/<path:filename>', methods=['GET'])
def get_report(filename):
    reports_dir = Path(__file__).parent / 'report'
    file_path = reports_dir / filename

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return content, 200, {'Content-Type': 'text/plain'}

@app.route('/')
def index():
    return render_template('emergency_report_viewer.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=35000)