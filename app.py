import os
import gpxpy
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from datetime import timedelta
from geopy.distance import geodesic

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def parse_gpx(file_path):
    with open(file_path, 'r') as f:
        gpx = gpxpy.parse(f)
    points = []
    total_distance = 0
    prev_coords = None
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords = (point.latitude, point.longitude)
                if prev_coords:
                    dist = geodesic(prev_coords, coords).meters
                    total_distance += dist
                points.append({
                    'time': point.time,
                    'coords': coords,
                    'distance': total_distance
                })
                prev_coords = coords
    return points

def calculate_pace(points):
    if len(points) < 2:
        return None, 0, 0
    dist = points[-1]['distance'] - points[0]['distance']
    time = (points[-1]['time'] - points[0]['time']).total_seconds()
    if dist == 0:
        return None, dist, time
    pace_sec_per_km = time / (dist / 1000)
    pace = f"{int(pace_sec_per_km // 60)}:{int(pace_sec_per_km % 60):02d} min/km"
    return pace, dist, time

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None

    if request.method == 'POST':
        file = request.files['gpx_file']
        if not file or not file.filename.endswith('.gpx'):
            error = "Please upload a valid GPX file."
        else:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            points = parse_gpx(path)

            method = request.form['method']
            selected = []

            try:
                if method == 'distance':
                    start_km = float(request.form['start_km']) * 1000
                    end_km = float(request.form['end_km']) * 1000
                    selected = [p for p in points if start_km <= p['distance'] <= end_km]

                elif method == 'time':
                    def parse_offset(hms):
                        parts = [int(p) for p in hms.strip().split(':')]
                        while len(parts) < 3:
                            parts.insert(0, 0)
                        return timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
                    base_time = points[0]['time']
                    start_time = base_time + parse_offset(request.form['start_offset'])
                    end_time = base_time + parse_offset(request.form['end_offset'])
                    selected = [p for p in points if start_time <= p['time'] <= end_time]

                pace, dist, duration = calculate_pace(selected)
                result = {
                    'pace': pace,
                    'distance': f"{dist/1000:.2f} km",
                    'duration': f"{int(duration//60)}m {int(duration%60)}s"
                }

            except Exception as e:
                error = str(e)

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

