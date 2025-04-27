from flask import Flask, request, jsonify
from dateutil import parser as date_parser  # for parsing ISO 8601 datetimes
from data.repository import *
from db.database import create_tables

app = Flask(__name__)

@app.route('/new_register', methods=['POST'])
def new_register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    required_fields = [
        "traffic_cam_id",
        "start_datetime",
        "end_datetime",
        "vehicle_count",
        "average_speed"
    ]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    print(f"Received new register: {data}")

    try:
        start_time = date_parser.isoparse(data['start_datetime'])
        end_time = date_parser.isoparse(data['end_datetime'])

        # Use the repository method to insert the record
        add_traffic_record(
            device_id=data['traffic_cam_id'],
            start_time=start_time,
            end_time=end_time,
            vehicle_count=data['vehicle_count'],
            average_speed=data['average_speed']
        )

        return jsonify({"message": "Register received successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cities', methods=['GET'])
def list_cities():
    try:
        cities = get_available_cities()
        return jsonify({"cities": cities}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/cams/<string:city>', methods=['GET'])
def cams_by_city(city):
    try:
        cams = get_cams_by_city(city)
        cams_list = [
            {
                "id": cam.id,
                "alias": cam.alias,
                "city": cam.city,
                "latitude": float(cam.location_lat),
                "longitude": float(cam.location_lng)
            }
            for cam in cams
        ]
        return jsonify({"cams": cams_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/traffic/<int:traffic_cam_id>', methods=['GET'])
def traffic_state(traffic_cam_id):
    try:
        state = get_traffic_state(traffic_cam_id)
        return jsonify({"traffic_state": state.name}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/traffic/stats', methods=['GET'])
def get_traffic_stats():
    try:
        start_datetime_str = request.args.get('start_datetime')
        end_datetime_str = request.args.get('end_datetime')

        if not start_datetime_str or not end_datetime_str:
            return jsonify({"error": "Both 'start_datetime' and 'end_datetime' are required"}), 400

        start_datetime = date_parser.isoparse(start_datetime_str)
        end_datetime = date_parser.isoparse(end_datetime_str)

        result = get_traffic_stats_in_range(start_datetime, end_datetime)

        if result:
            return jsonify({
                "average_speed": result.average_speed,
                "total_vehicle_count": result.total_vehicle_count
            }), 200
        else:
            return jsonify({"error": "No records found for the given date range"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/traffic/peak_hours', methods=['GET'])
def peak_hours():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if not start_str or not end_str:
        return jsonify({"error": "Missing 'start' or 'end' parameters"}), 400

    try:
        start_time = date_parser.isoparse(start_str)
        end_time = date_parser.isoparse(end_str)

        peak = get_peak_hours(start_time, end_time)

        return jsonify({"peak_hours": peak}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/congestion', methods=['GET'])
def get_congestion():
    traffic_cam_id = request.args.get('traffic_cam_id')
    start_datetime = request.args.get('start_datetime')  
    end_datetime = request.args.get('end_datetime')      
    speed_threshold = request.args.get('speed_threshold', 20, type=int)  # Umbral de velocidad (20 por defecto)

    if not traffic_cam_id:
        return jsonify({"error": "traffic_cam_id is required"}), 400

    # Llamar a la función del repositorio para obtener el porcentaje de congestión
    result = get_speed_based_congestion(
        traffic_cam_id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        speed_threshold=speed_threshold
    )

    return jsonify(result)


@app.route('/traffic_records', methods=['GET'])
def get_traffic_records():
    start_datetime = request.args.get('start_datetime')
    end_datetime = request.args.get('end_datetime')

    if not start_datetime or not end_datetime:
        return jsonify({"error": "Both start_datetime and end_datetime are required"}), 400

    try:
        start_datetime = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
        end_datetime = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({"error": "Invalid date format, please use YYYY-MM-DD HH:MM:SS"}), 400

    traffic_records = get_traffic_records_in_range(start_datetime, end_datetime)

    if not traffic_records:
        return jsonify({"message": "No traffic records found in the given range"}), 200

    return jsonify({"traffic_records": traffic_records}), 200


@app.route('/traffic_jams', methods=['GET'])
def traffic_jams_in_range():
    try:
        start_datetime_str = request.args.get('start_datetime')
        end_datetime_str = request.args.get('end_datetime')
        speed_threshold = request.args.get('speed_threshold', default=20, type=int)  

        if not start_datetime_str or not end_datetime_str:
            return jsonify({"error": "Both start_datetime and end_datetime are required"}), 400

        start_datetime = date_parser.isoparse(start_datetime_str)
        end_datetime = date_parser.isoparse(end_datetime_str)

        traffic_jams = get_traffic_jams_in_range(start_datetime, end_datetime, speed_threshold)

        if not traffic_jams:
            return jsonify({"message": "No traffic jams found in the specified date range"}), 200

        return jsonify({"traffic_jams": traffic_jams}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    create_tables()
    app.run(host="localhost", port=6000, debug=True)
