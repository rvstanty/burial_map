import csv
from app import app, db
from models import Grave, DaftarKematian

def import_csv_to_db(csv_path):
    with app.app_context():
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                lot_number = row['NO.LIANG'].strip()
                deceased_name = row['NAMA'].strip()
                alamat = row['ALAMAT'].strip() if row['ALAMAT'] else ''
                heir_name = row['NAMA WARIS'].strip() if row['NAMA WARIS'] else ''
                heir_contact = row['NO TELEFON'].strip() if row['NO TELEFON'] else ''
                date_of_death = row['TARIKH KEMATIAN'].strip() if row['TARIKH KEMATIAN'] else ''
                
                # Check if grave exists
                grave = Grave.query.filter_by(lot_number=lot_number).first()
                if not grave:
                    grave = Grave(
                        name=deceased_name,
                        date_of_birth='',  # unknown from CSV
                        date_of_death=date_of_death,
                        lot_number=lot_number,
                        section=alamat,
                        picture_url='',
                        family_details='',
                        notes=''
                    )
                    db.session.add(grave)
                    db.session.flush()  # to get grave.id
                
                # Check if DaftarKematian record exists for this grave_id
                existing_record = DaftarKematian.query.filter_by(grave_id=grave.id).first()
                if not existing_record:
                    new_record = DaftarKematian(
                        grave_id=grave.id,
                        deceased_name=deceased_name,
                        stone_number=lot_number,
                        date_of_birth='',  # unknown
                        age_at_death=0,    # unknown
                        heir_name=heir_name,
                        heir_contact=heir_contact
                    )
                    db.session.add(new_record)
            db.session.commit()
        print("CSV data imported successfully.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python import_csv.py path_to_csv_file")
    else:
        import_csv_to_db(sys.argv[1])
