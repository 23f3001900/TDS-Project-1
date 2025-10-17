from app.llm_generator import generate_app_code

files = generate_app_code("Simple calculator with buttons 0-9 and + - * / operations", [])
print(files.get("index.html", "")[:500])
print(files.get("README.md", ""))
