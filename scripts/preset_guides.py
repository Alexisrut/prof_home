import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from models import Guide

def preset_guides():
    """
    Presets guides in the database by reading markdown files from public/md.
    Equivalent to the TypeScript presetGuides implementation.
    """
    # Equivalent to path.resolve(process.cwd(), "public", "md")
    md_dir = os.path.join(os.getcwd(), "./", "md")
    
    names = ["гайды", "информация", "КМБ"]
    
    for name in names:
        file_path = os.path.join(md_dir, f"{name}.md")
        
        try:
            if not os.path.exists(file_path):
                print(f"Ошибка: файл не найден: {file_path}")
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            guide = Guide(
                guide_id=0,  # SQLite auto-increment will handle the actual ID
                title=name,
                owner_block="none",
                text=text,
                original_link=None
            )
            
            db.create_guide(guide)
            print(f"Успешно сохранен гайд: {name}")
            
        except Exception as err:
            print(f"Ошибка при обработке файла {name}.md: {err}")

if __name__ == "__main__":
    preset_guides()
