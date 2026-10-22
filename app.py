from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_FILE = "monitor.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (date TEXT PRIMARY KEY, download INTEGER DEFAULT 0, upload INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS last_read (id INTEGER PRIMARY KEY, rx INTEGER, tx INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# واجهة الموقع الاحترافية
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مراقب الشبكة | Netis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-orange: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body {
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.15), transparent 25%), 
                              radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.15), transparent 25%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 1.8rem; font-weight: 900; letter-spacing: 1px; }
        .header p { color: var(--text-muted); font-size: 0.9rem; margin-top: 5px; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; width: 100%; max-width: 500px; margin-bottom: 20px; }
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        .card-title { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .card-value { font-size: 1.8rem; font-weight: 700; }
        .value-download { color: var(--accent-blue); }
        .value-upload { color: var(--accent-orange); }
        
        .chart-container {
            width: 100%;
            max-width: 500px;
            background: var(--card-bg);
            border-radius: 20px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
        }
        .chart-title { font-size: 1rem; font-weight: 700; margin-bottom: 15px; text-align: center; color: var(--text-muted); }
        
        .status-bar {
            margin-top: 20px;
            padding: 10px 20px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--accent-green);
            border-radius: 50px;
            font-size: 0.8rem;
            color: var(--accent-green);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; box-shadow: 0 0 10px var(--accent-green); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>📡 لوحة تحكم الشبكة</h1>
        <p>مراقبة استهلاك البيانات بدقة</p>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">📥 التحميل اليوم</div>
            <div class="card-value value-download" id="today-dl">0.00 GB</div>
        </div>
        <div class="card">
            <div class="card-title">📤 الرفع اليوم</div>
            <div class="card-value value-upload" id="today-ul">0.00 GB</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-title">استهلاك آخر 7 أيام</div>
        <canvas id="usageChart"></canvas>
    </div>

    <div class="status-bar">
        <div class="dot"></div>
        <span id="sync-time">آخر مزامنة: ...</span>
    </div>

    <script>
        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                
                // تحديث البطاقات
                document.getElementById('today-dl').innerText = (data.today.download / 1073741824).toFixed(2) + ' GB';
                document.getElementById('today-ul').innerText = (data.today.upload / 1073741824).toFixed(2) + ' GB';
                document.getElementById('sync-time').innerText = 'آخر مزامنة: ' + new Date().toLocaleTimeString('ar-EG');

                // تحديث الرسم البياني
                updateChart(data.history);
            } catch (error) {
                document.getElementById('sync-time').innerText = 'بانتظار الاتصال بالراوتر...';
            }
        }

        let myChart = null;
        function updateChart(history) {
            const labels = history.map(item => item.date);
            const dlData = history.map(item => (item.download / 1073741824).toFixed(2));
            const ulData = history.map(item => (item.upload / 1073741824).toFixed(2));

            if (myChart) {
                myChart.data.labels = labels;
                myChart.data.datasets[0].data = dlData;
                myChart.data.datasets[1].data = ulData;
                myChart.update();
                return;
            }

            const ctx = document.getElementById('usageChart').getContext('2d');
            myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'تحميل (GB)', data: dlData, backgroundColor: '#3b82f6', borderRadius: 6 },
                        { label: 'رفع (GB)', data: ulData, backgroundColor: '#f59e0b', borderRadius: 6 }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { labels: { color: '#94a3b8', font: { family: 'Cairo' } } } },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', font: { family: 'Cairo' } } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'Cairo' } } }
                    }
                }
            });
        }

        fetchData();
        setInterval(fetchData, 10000); // تحديث الواجهة كل 10 ثواني
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_data = c.execute("SELECT download, upload FROM daily_usage WHERE date=?", (today_str,)).fetchone()
    if not today_data: today_data = (0, 0)
    
    history = c.execute("SELECT date, download, upload FROM daily_usage ORDER BY date DESC LIMIT 7").fetchall()
    history = [{"date": r[0], "download": r[1], "upload": r[2]} for r in reversed(history)]
    conn.close()
    
    return jsonify({"today": {"download": today_data[0], "upload": today_data[1]}, "history": history})

@app.route('/api/update', methods=['POST'])
def update():
    data = request.json
    rx, tx = data.get('rx'), data.get('tx')
    if rx is None or tx is None: return jsonify({"status": "error"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    last = c.execute("SELECT rx, tx FROM last_read WHERE id=1").fetchone()
    
    if last:
        # حساب الفرق (يجب أن يكون موجباً لتجنب مشكلة إعادة تشغيل الراوتر)
        if rx >= last[0] and tx >= last[1]:
            delta_rx = rx - last[0]
            delta_tx = tx - last[1]
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute('''INSERT INTO daily_usage (date, download, upload) VALUES (?, ?, ?)
                         ON CONFLICT(date) DO UPDATE SET download=download+?, upload=upload+?''',
                      (today, delta_rx, delta_tx, delta_rx, delta_tx))
    
    c.execute("INSERT OR REPLACE INTO last_read (id, rx, tx) VALUES (1, ?, ?)", (rx, tx))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
