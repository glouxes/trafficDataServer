
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy import func

from db.database import SessionLocal
from db.entities import (
    TrafficRecord,
    TrafficCam,
    TrafficJamAlert
)
from utils import TrafficStates


def add_traffic_record(device_id: int, start_time: datetime, end_time: datetime, vehicle_count: int,
                       average_speed: float):
    """
    Inserts a new traffic record into the database.
    """
    db = SessionLocal()
    try:
        new_record = TrafficRecord(
            traffic_cam_id=device_id,
            start_time=start_time,
            end_time=end_time,
            vehicle_count=vehicle_count,
            average_speed=average_speed
        )
        db.add(new_record)
        db.commit()
        print("Traffic record added successfully.")

        if get_traffic_state(device_id) == TrafficStates.Jam:
            new_alert = TrafficJamAlert(traffic_cam_id=device_id, event_time=datetime.now())
            db.add(new_alert)
            db.commit()
            pass
        return new_record
    except Exception as e:
        db.rollback()
        print(f"Error adding traffic record: {e}")
        raise e
    finally:
        db.close()


def get_traffic_history(device_id: int = None, start_date: datetime = None, end_date: datetime = None):
    """
    Retrieves traffic history.
    - If device_id is provided, returns records for that specific device.
    - Otherwise, returns all traffic records.
    Optionally filters by a date range if both start_date and end_date are provided.
    """
    db = SessionLocal()
    try:
        query = db.query(TrafficRecord)
        if device_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == device_id)
        if start_date and end_date:
            query = query.filter(TrafficRecord.start_time.between(start_date, end_date))
        records = query.all()
        return records
    except Exception as e:
        print(f"Error retrieving traffic history: {e}")
        raise e
    finally:
        db.close()


def get_device_list():
    """
    Retrieves a list of traffic cam devices with their IDs, locations, and aliases.
    """
    db = SessionLocal()
    try:
        devices = db.query(TrafficCam.id, TrafficCam.location, TrafficCam.alias).all()
        return devices
    except Exception as e:
        print(f"Error retrieving device list: {e}")
        raise e
    finally:
        db.close()


def get_critical_events(device_id: int):
    """
    Retrieves critical events for a specific device.
    """
    db = SessionLocal()
    try:
        events = db.query(TrafficJamAlert).filter(TrafficJamAlert.traffic_cam_id == device_id).all()
        return events
    except Exception as e:
        print(f"Error retrieving critical events: {e}")
        raise e
    finally:
        db.close()


def get_critical_events_since(since_datetime: datetime):
    """
    Retrieves critical events that occurred on or after the specified datetime.
    """
    db = SessionLocal()
    try:
        events = db.query(TrafficJamAlert).filter(TrafficJamAlert.event_time >= since_datetime).all()
        return events
    except Exception as e:
        print(f"Error retrieving critical events since {since_datetime}: {e}")
        raise e
    finally:
        db.close()


def update_traffic_record(record_id: int, vehicle_count: int, average_speed: float):
    """
    Updates an existing traffic record with a new vehicle count and average speed.
    """
    db = SessionLocal()
    try:
        record = db.query(TrafficRecord).filter(TrafficRecord.id == record_id).first()
        if record:
            record.vehicle_count = vehicle_count
            record.average_speed = average_speed
            db.commit()
            print("Traffic record updated successfully.")
            return record
        else:
            raise Exception("Traffic record not found.")
    except Exception as e:
        db.rollback()
        print(f"Error updating traffic record: {e}")
        raise e
    finally:
        db.close()


def delete_traffic_record(record_id: int):
    """
    Deletes a traffic record from the database.
    """
    db = SessionLocal()
    try:
        record = db.query(TrafficRecord).filter(TrafficRecord.id == record_id).first()
        if record:
            db.delete(record)
            db.commit()
            print("Traffic record deleted successfully.")
        else:
            raise Exception("Traffic record not found.")
    except Exception as e:
        db.rollback()
        print(f"Error deleting traffic record: {e}")
        raise e
    finally:
        db.close()


def get_total_traffic_volume(device_id: int = None, start_date: datetime = None, end_date: datetime = None):
    """
    Retrieves the total traffic volume (sum of vehicle_count).
    Optionally filters by device_id and by a date range (start_date and end_date).
    """
    db = SessionLocal()
    try:
        query = db.query(func.sum(TrafficRecord.vehicle_count))
        if device_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == device_id)
        if start_date and end_date:
            query = query.filter(TrafficRecord.start_time.between(start_date, end_date))
        total_volume = query.scalar()
        return total_volume or 0  # Return 0 if total_volume is None
    except Exception as e:
        print(f"Error retrieving total traffic volume: {e}")
        raise e
    finally:
        db.close()


# List of available cities
def get_available_cities():
    db = SessionLocal()
    try:
        result = db.query(TrafficCam.city).all()
        cities = [value[0] for value in result]
        print(cities)
        return cities
    except Exception as e:
        print(f"Error retrieving total traffic volume: {e}")
        raise e
    finally:
        db.close()


def get_cams_by_city(city):
    db = SessionLocal()
    try:
        result = db.query(TrafficCam).filter(TrafficCam.city == city).all()
        return result
    except Exception as e:
        print(f"Error retrieving total traffic volume: {e}")
        raise e
    finally:
        db.close()


def get_traffic_state(traffic_cam_id):
    db = SessionLocal()
    try:
        # 4 estados: Trafico bajo, regular, alto, atascamiento

        # Obtain the latest traffic record
        latest_record = (db.query(TrafficRecord)
                         .filter(TrafficRecord.traffic_cam_id == traffic_cam_id)
                         .order_by(desc(TrafficRecord.end_time))
                         .first())
        print(latest_record.average_speed)
        # Obtain average speed from location
        avg_speed = (
            db.query(func.avg(TrafficRecord.average_speed))
            .filter(TrafficRecord.traffic_cam_id == traffic_cam_id)
            .scalar()
        )

        # Compare average speeds
        if avg_speed * 0.8 <= latest_record.average_speed <= avg_speed * 1.2:
            return TrafficStates.Regular
        if latest_record.average_speed >= avg_speed * 1.2:
            return TrafficStates.Low
        if avg_speed * 0.2 < latest_record.average_speed < avg_speed * 0.8:
            return TrafficStates.High
        return TrafficStates.Jam


    except Exception as e:
        print(f"Error retrieving total traffic volume: {e}")
        raise e
    finally:
        db.close()


def get_traffic_stats_in_range(start_datetime: datetime, end_datetime: datetime, cam_id: int = None, city: str = None):
    """
    Retrieves the average speed and vehicle count within a given date and time range, with optional filters for cam_id and city.
    """
    db = SessionLocal()
    try:
        query = db.query(
            func.avg(TrafficRecord.average_speed).label('average_speed'),
            func.sum(TrafficRecord.vehicle_count).label('total_vehicle_count')
        ).filter(
            TrafficRecord.start_time >= start_datetime,
            TrafficRecord.end_time <= end_datetime
        )
        
        if cam_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == cam_id)
        if city is not None:
            query = query.join(TrafficCam).filter(TrafficCam.city == city)

        result = query.first()
        return result
    except Exception as e:
        print(f"Error retrieving traffic stats in range: {e}")
        raise e
    finally:
        db.close()


def get_peak_hours(start_datetime, end_datetime, cam_id: int = None, city: str = None):
    db = SessionLocal()
    try:
        query = db.query(
            func.hour(TrafficRecord.start_time).label("hour"),
            func.sum(TrafficRecord.vehicle_count).label("total_vehicles")
        ).filter(
            TrafficRecord.start_time >= start_datetime,
            TrafficRecord.end_time <= end_datetime
        )
        
        if cam_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == cam_id)
        if city is not None:
            query = query.join(TrafficCam).filter(TrafficCam.city == city)

        results = query.group_by(func.hour(TrafficRecord.start_time)).order_by(
            func.sum(TrafficRecord.vehicle_count).desc()
        ).all()

        return [
            {
                "hour": f"{row.hour:02d}:00",
                "total_vehicles": row.total_vehicles
            } for row in results
        ]
    finally:
        db.close()


def get_speed_based_congestion(traffic_cam_id, start_datetime=None, end_datetime=None, speed_threshold=20, city: str = None):
    db = SessionLocal()
    try:
        query = db.query(TrafficRecord).filter(TrafficRecord.traffic_cam_id == traffic_cam_id)
        
        if start_datetime and end_datetime:
            query = query.filter(
                TrafficRecord.start_time >= start_datetime,
                TrafficRecord.end_time <= end_datetime
            )
        if city is not None:
            query = query.join(TrafficCam).filter(TrafficCam.city == city)

        total_records = query.count()

        if total_records == 0:
            return {"congestion_percentage": 0, "status": "sin datos"}

        low_speed_records = query.filter(TrafficRecord.average_speed <= speed_threshold).count()

        congestion_percentage = (low_speed_records / total_records) * 100

        status = "congestionado" if congestion_percentage > 50 else "fluido"

        return {
            "congestion_percentage": round(congestion_percentage, 2),
            "status": status
        }
    finally:
        db.close()


def get_traffic_records_in_range(start_datetime, end_datetime, cam_id: int = None, city: str = None):
    db = SessionLocal()
    try:
        query = db.query(TrafficRecord).filter(
            TrafficRecord.start_time >= start_datetime,
            TrafficRecord.end_time <= end_datetime
        )
        
        if cam_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == cam_id)
        if city is not None:
            query = query.join(TrafficCam).filter(TrafficCam.city == city)

        results = query.all()

        # Convertimos los resultados a un formato de diccionario
        traffic_records = [
            {
                "traffic_cam_id": record.traffic_cam_id,
                "start_datetime": record.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_datetime": record.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "vehicle_count": record.vehicle_count,
                "average_speed": record.average_speed
            }
            for record in results
        ]

        return traffic_records
    finally:
        db.close()


def get_traffic_jams_in_range(start_datetime, end_datetime, speed_threshold=20, cam_id: int = None, city: str = None):
    db = SessionLocal()
    try:
        query = db.query(TrafficRecord).filter(
            TrafficRecord.start_time >= start_datetime,
            TrafficRecord.end_time <= end_datetime,
            TrafficRecord.average_speed <= speed_threshold
        )
        
        if cam_id is not None:
            query = query.filter(TrafficRecord.traffic_cam_id == cam_id)
        if city is not None:
            query = query.join(TrafficCam).filter(TrafficCam.city == city)

        results = query.all()

        traffic_jams = [
            {
                "traffic_cam_id": record.traffic_cam_id,
                "start_datetime": record.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "end_datetime": record.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "vehicle_count": record.vehicle_count,
                "average_speed": record.average_speed
            }
            for record in results
        ]

        return traffic_jams
    finally:
        db.close()
