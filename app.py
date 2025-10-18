from flask import Flask, request, jsonify, g
import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parents[1] / 'tasks.db'

app = Flask(__name__)
app.config['DATABASE'] = str(DATABASE)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            done INTEGER DEFAULT 0
        );
    ''')
    db.commit()

@app.before_request
def initialize():
    if not hasattr (app, 'db_initialized'):
        init_db()
        app.db_initialized = True

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/tasks', methods=['GET'])
def list_tasks():
    db = get_db()
    cur = db.execute('SELECT id, title, description, done FROM tasks')
    rows = cur.fetchall()
    tasks = [dict(r) for r in rows]
    return jsonify(tasks)

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    db = get_db()
    cur = db.execute('SELECT id, title, description, done FROM tasks WHERE id=?', (task_id,))
    row = cur.fetchone()
    if row is None:
        return jsonify({'error':'Not found'}), 404
    return jsonify(dict(row))

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json() or {}
    title = data.get('title')
    if not title:
        return jsonify({'error':'title is required'}), 400
    description = data.get('description','')
    db = get_db()
    cur = db.execute('INSERT INTO tasks (title, description) VALUES (?,?)', (title, description))
    db.commit()
    task_id = cur.lastrowid
    return jsonify({'id': task_id, 'title': title, 'description': description, 'done': 0}), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description')
    done = data.get('done')
    db = get_db()
    cur = db.execute('SELECT id FROM tasks WHERE id=?', (task_id,))
    if cur.fetchone() is None:
        return jsonify({'error':'Not found'}), 404
    # build update dynamically
    fields = []
    params = []
    if title is not None:
        fields.append('title=?'); params.append(title)
    if description is not None:
        fields.append('description=?'); params.append(description)
    if done is not None:
        fields.append('done=?'); params.append(1 if bool(done) else 0)
    if not fields:
        return jsonify({'error':'no fields to update'}), 400
    params.append(task_id)
    db.execute('UPDATE tasks SET ' + ','.join(fields) + ' WHERE id=?', tuple(params))
    db.commit()
    return jsonify({'id': task_id}), 200

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    db = get_db()
    cur = db.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    db.commit()
    if cur.rowcount==0:
        return jsonify({'error':'Not found'}), 404
    return jsonify({'result':'deleted'}), 200

@app.route('/')
def home():
 return "flask rodando com sucesso"

if __name__ == '__main__':
    app.run()
