import time
import pandas as pd
from database import engine, SessionLocal
from models import Base, Material, TariffCode
import os
from sqlalchemy.exc import OperationalError

def seed_db():
    print("Waiting for database connection...")
    retries = 5
    while retries > 0:
        try:
            Base.metadata.create_all(bind=engine)
            break
        except OperationalError:
            print("Database not ready yet. Retrying in 2 seconds...")
            time.sleep(2)
            retries -= 1
            
    if retries == 0:
        print("Failed to connect to database after multiple attempts.")
        return

    print("Tables created. Proceeding with seeding...")
    
    db = SessionLocal()
    
    # Check if we already have data
    if db.query(TariffCode).first() is None:
        print("Seeding Tariff Codes...")
        tariff_path = "/app/data/CostumsData.csv"
        if os.path.exists(tariff_path):
            df_tariffs = pd.read_csv(tariff_path, dtype=str)
            df_tariffs = df_tariffs.fillna("")
            
            tariffs_to_insert = []
            for _, row in df_tariffs.iterrows():
                tariffs_to_insert.append(TariffCode(
                    goods_code=row.get('Goods code', ''),
                    description=row.get('Description', ''),
                    language=row.get('Language', ''),
                    start_date=row.get('Start date', ''),
                    end_date=row.get('End date', '')
                ))
            db.bulk_save_objects(tariffs_to_insert)
            db.commit()
            print(f"Inserted {len(tariffs_to_insert)} tariff codes.")
        else:
            print(f"Warning: {tariff_path} not found.")

    if db.query(Material).first() is None:
        print("Seeding Materials...")
        materials_path = "/app/data/Export_SAP_200MM.csv"
        if os.path.exists(materials_path):
            df_materials = pd.read_csv(materials_path, dtype=str)
            df_materials = df_materials.fillna("")
            
            materials_to_insert = []
            for _, row in df_materials.iterrows():
                materials_to_insert.append(Material(
                    material_number=row.get('Materialnummer', ''),
                    short_text=row.get('Kurztext', ''),
                    purchase_order_text=row.get('Einkaufsbestelltext', '')
                ))
            db.bulk_save_objects(materials_to_insert)
            db.commit()
            print(f"Inserted {len(materials_to_insert)} materials.")
        else:
            print(f"Warning: {materials_path} not found.")
            
    db.close()
    print("Database seeding completed.")

if __name__ == "__main__":
    seed_db()
