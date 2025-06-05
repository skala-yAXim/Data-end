import json
import re


def clean_html(raw_html):
    return re.sub(r'<[^>]+>', '', raw_html)
  
def extract_text_values(json_str):
    def recursive_extract(obj, results):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "text":
                    results.append(value)
                else:
                    recursive_extract(value, results)
        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item, results)

    try:
        parsed = json.loads(json_str)
        texts = []
        recursive_extract(parsed, texts)
        return texts
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)
        return []