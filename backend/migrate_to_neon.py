import os
from sqlalchemy import create_engine, MetaData, Table, select, text, update

# URLs
LOCAL_DB = "postgresql://postgres:postgres@localhost:5432/mess_waste_db"
REMOTE_DB = "postgresql://neondb_owner:npg_YwEkp4t7ijCy@ep-noisy-darkness-amcimztp-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    print(f"Connecting to local: {LOCAL_DB}")
    local_engine = create_engine(LOCAL_DB)
    local_meta = MetaData()
    local_meta.reflect(bind=local_engine)

    print(f"Connecting to remote: {REMOTE_DB}")
    remote_engine = create_engine(REMOTE_DB)
    
    # Tables in order
    table_order = [
        'organizations',
        'users',
        'meal_timings',
        'menus',
        'attendance',
        'food_cooked',
        'food_feedback',
        'inventory',
        'notifications',
        'predictions',
        'student_attendance',
        'waste'
    ]

    # Store original organizations created_by for later update
    org_creators = {}

    for table_name in table_order:
        if table_name not in local_meta.tables:
            print(f"Skipping {table_name} (not found)")
            continue
            
        print(f"Migrating table: {table_name}...")
        table = local_meta.tables[table_name]
        
        # Read local data
        with local_engine.connect() as conn:
            data = conn.execute(table.select()).fetchall()
            
        if not data:
            print(f"  No data in {table_name}")
            continue

        records = [dict(row._mapping) for row in data]
        
        if table_name == 'organizations':
            # Temporary strip created_by to avoid circular dependency
            for r in records:
                org_creators[r['id']] = r['created_by']
                r['created_by'] = None
        
        # Write to remote
        with remote_engine.connect() as conn:
            try:
                conn.execute(table.insert(), records)
                conn.commit()
                print(f"  Successfully copied {len(records)} records to {table_name}")
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")

    # Final step: Update organizations with their true creators
    print("Patching organizations with original created_by values...")
    org_table = local_meta.tables['organizations']
    with remote_engine.connect() as conn:
        for org_id, creator_id in org_creators.items():
            if creator_id:
                try:
                    conn.execute(
                        update(org_table).where(org_table.c.id == org_id).values(created_by=creator_id)
                    )
                except Exception as e:
                    print(f"  Failed to patch org {org_id}: {e}")
        conn.commit()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
