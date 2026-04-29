from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Attendance
from schemas import AttendanceCreate, AttendanceResponse
from auth import get_current_user
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


from ml import train_model


@router.post("/", response_model=AttendanceResponse)
def create_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user.role not in ("admin", "mess_manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    record = Attendance(
        date=data.date,
        meal=data.meal,
        students=data.students,
        organization_code=current_user.organization_code,
        created_by=current_user.id
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Automatically re-train model with new data
    try:
        train_model(db, record.meal, current_user.organization_code)
    except Exception as e:
        print(f"Auto-train failed: {e}")

    # Firestore sync (production no-op in local dev)
    try:
        from utils.firestore_sync import sync_to_firestore
        sync_to_firestore("attendance", str(record.id), {
            "date": str(record.date),
            "meal": record.meal,
            "students": record.students,
            "organization_code": record.organization_code,
            "created_by": record.created_by
        }, record.organization_code)
    except Exception as e:
        print(f"Firestore sync skipped: {e}")

    return record


@router.get("/", response_model=List[AttendanceResponse])
def get_attendance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    meal: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    query = db.query(Attendance)
    if current_user.role in ["mess_manager", "admin"] and current_user.organization_code:
        query = query.filter(Attendance.organization_code == current_user.organization_code)
    
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)
    if meal:
        query = query.filter(Attendance.meal == meal)
    return query.order_by(Attendance.date.desc()).limit(limit).all()


@router.get("/today")
def get_today_attendance(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    today = date.today()
    query = db.query(Attendance).filter(Attendance.date == today)
    if current_user.role in ["mess_manager", "admin"] and current_user.organization_code:
        query = query.filter(Attendance.organization_code == current_user.organization_code)
    
    records = query.all()
    total = sum(r.students for r in records)
    return {
        "date": today.isoformat(),
        "total_students": total,
        "meals": [{"meal": r.meal, "students": r.students} for r in records]
    }


@router.put("/{record_id}", response_model=AttendanceResponse)
def update_attendance(
    record_id: int,
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role in ["mess_manager", "admin"] and record.organization_code != current_user.organization_code:
        raise HTTPException(status_code=403, detail="Not authorized to modify this record")
    record.date = data.date
    record.meal = data.meal
    record.students = data.students
    db.commit()
    db.refresh(record)

    # Re-train model with updated data
    try:
        train_model(db, record.meal, current_user.organization_code)
    except Exception as e:
        print(f"Update-train failed: {e}")

    return record


@router.delete("/{record_id}")
def delete_attendance(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    record = db.query(Attendance).filter(Attendance.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current_user.role in ["mess_manager", "admin"] and record.organization_code != current_user.organization_code:
        raise HTTPException(status_code=403, detail="Not authorized to delete this record")
    db.delete(record)
    db.commit()
    return {"message": "Record deleted successfully"}


from typing import List as TypingList


@router.post("/bulk")
def bulk_create_attendance(
    records: TypingList[AttendanceCreate],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Bulk insert attendance records. Used by SetupWizard to bootstrap 31 days of data."""
    if current_user.role not in ["mess_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only managers or admins can bulk-insert attendance.")
    org_code = current_user.organization_code or ""
    created_count = 0
    for record in records:
        existing = db.query(Attendance).filter(
            Attendance.date == record.date,
            Attendance.meal == record.meal,
            Attendance.organization_code == org_code
        ).first()
        if existing:
            existing.students = record.students
        else:
            entry = Attendance(
                date=record.date,
                meal=record.meal,
                students=record.students,
                organization_code=org_code,
                created_by=current_user.id
            )
            db.add(entry)
            created_count += 1
    db.commit()
    return {"message": f"{created_count} records created, duplicates updated.", "total": len(records)}
