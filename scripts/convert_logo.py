import base64
import os

logo_path = "src/ui/assets/logo.png"
output_path = "src/ui/assets/logo_data.py"

if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    content = f'LOGO_BASE64 = "{encoded_string}"\n'
    
    with open(output_path, "w") as f:
        f.write(content)
    print(f"Successfully created {output_path}")
else:
    print(f"Error: {logo_path} not found")
