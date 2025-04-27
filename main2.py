from data.repository import get_traffic_state


if __name__ == '__main__':
    print(get_traffic_state(2))


@app.route('/congestion_by_speed/<int:traffic_cam_id>', methods=['GET'])
def congestion_by_speed(traffic_cam_id):
    try:
        start_datetime = request.args.get('start_datetime')
        end_datetime = request.args.get('end_datetime')

        start = date_parser.isoparse(start_datetime) if start_datetime else None
        end = date_parser.isoparse(end_datetime) if end_datetime else None

        result = get_speed_based_congestion(traffic_cam_id, start, end)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
