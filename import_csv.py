import csv
from app import app, db
from models import Grave, DaftarKematian

def import_csv_to_db(csv_path):
    with app.app_context():
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Kira jumlah rekod untuk laporan
                count = 0
                
                for row in reader:
                    # Ambil data dan bersihkan (strip whitespace)
                    lot_number = row.get('NO.LIANG', '').strip()
                    deceased_name = row.get('NAMA', '').strip()
                    alamat = row.get('ALAMAT', '').strip()
                    heir_name = row.get('NAMA WARIS', '').strip()
                    heir_contact = row.get('NO TELEFON', '').strip()
                    date_of_death = row.get('TARIKH KEMATIAN', '').strip()
                    
                    if not lot_number or not deceased_name:
                        continue  # Skip baris kosong

                    # 1. Semak jika rekod Grave sedia ada
                    grave = Grave.query.filter_by(lot_number=lot_number).first()
                    if not grave:
                        grave = Grave(
                            name=deceased_name,
                            date_of_birth='-', 
                            date_of_death=date_of_death,
                            lot_number=lot_number,
                            section=alamat if alamat else 'TIADA REKOD',
                            picture_url='',
                            family_details=heir_name,
                            notes=heir_contact
                        )
                        db.session.add(grave)
                        db.session.flush() # Dapatkan ID untuk rujukan foreign key
                    
                    # 2. Semak jika rekod DaftarKematian wujud
                    existing_record = DaftarKematian.query.filter_by(grave_id=grave.id).first()
                    if not existing_record:
                        new_record = DaftarKematian(
                            grave_id=grave.id,
                            deceased_name=deceased_name,
                            stone_number=lot_number,
                            date_of_birth='-',
                            age_at_death=0,
                            heir_name=heir_name if heir_name else 'TIADA MAKLUMAT',
                            heir_contact=heir_contact if heir_contact else 'TIADA MAKLUMAT',
                            
                            # --- DATA PENTING UNTUK PETA ---
                            # Kita setkan nilai default supaya sistem paparan tidak error
                            selected_plot='fleft', # Default ke plot hadapan kiri
                            coord_x=0.0,           # Pin akan berada di bucu atas kiri (0,0)
                            coord_y=0.0            # Admin boleh update koordinat ini kemudian
                        )
                        db.session.add(new_record)
                        count += 1
                
                db.session.commit()
                print(f"Berjaya! {count} rekod telah diimport ke dalam pangkalan data.")

        except FileNotFoundError:
            print(f"Ralat: Fail '{csv_path}' tidak dijumpai.")
        except Exception as e:
            db.session.rollback()
            print(f"Ralat berlaku semasa import: {str(e)}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Penggunaan: python import_csv.py nama_fail.csv")
    else:
        import_csv_to_db(sys.argv[1])