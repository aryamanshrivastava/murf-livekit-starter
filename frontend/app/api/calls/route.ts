import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const possiblePaths = [
      path.resolve(process.cwd(), '../backend/data/database.db'),
      path.resolve(process.cwd(), 'backend/data/database.db'),
      path.resolve(process.cwd(), 'data/database.db'),
    ];

    const targetDbPath = possiblePaths.find((p) => fs.existsSync(p));

    if (!targetDbPath) {
      console.warn('Database file database.db not found at expected paths.');
      return NextResponse.json({
        success: true,
        metrics: {
          total_calls: 0,
          successful_calls: 0,
          failed_calls: 0,
          recent_calls: [],
        },
      });
    }

    let total = 0;
    let successful = 0;
    let failed = 0;
    let recentCalls: any[] = [];

    try {
      const { DatabaseSync } = await import('node:sqlite');
      const db = new DatabaseSync(targetDbPath);

      // Ensure table exists
      db.exec(`
        CREATE TABLE IF NOT EXISTS call_outcomes (
            call_id TEXT PRIMARY KEY,
            room_name TEXT NOT NULL,
            seller_id TEXT,
            outbound INTEGER DEFAULT 0,
            outcome TEXT NOT NULL,
            reason TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT NOT NULL,
            duration_seconds REAL DEFAULT 0.0
        )
      `);

      const totalRow: any = db.prepare('SELECT COUNT(*) as count FROM call_outcomes').get();
      total = totalRow?.count || 0;

      const successRow: any = db
        .prepare("SELECT COUNT(*) as count FROM call_outcomes WHERE outcome = 'SUCCESS'")
        .get();
      successful = successRow?.count || 0;

      const failedRow: any = db
        .prepare("SELECT COUNT(*) as count FROM call_outcomes WHERE outcome = 'FAILED'")
        .get();
      failed = failedRow?.count || 0;

      recentCalls = db
        .prepare('SELECT * FROM call_outcomes ORDER BY started_at DESC LIMIT 50')
        .all();
    } catch (sqliteErr) {
      console.warn('node:sqlite failed, trying python fallback:', sqliteErr);
      const { execSync } = await import('child_process');
      const pyScript = `import sqlite3, json
conn = sqlite3.connect('${targetDbPath.replace(/\\/g, '/')}')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS call_outcomes (call_id TEXT PRIMARY KEY, room_name TEXT NOT NULL, seller_id TEXT, outbound INTEGER DEFAULT 0, outcome TEXT NOT NULL, reason TEXT, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, duration_seconds REAL DEFAULT 0.0)")
total = cursor.execute("SELECT COUNT(*) FROM call_outcomes").fetchone()[0]
succ = cursor.execute("SELECT COUNT(*) FROM call_outcomes WHERE outcome = 'SUCCESS'").fetchone()[0]
fail = cursor.execute("SELECT COUNT(*) FROM call_outcomes WHERE outcome = 'FAILED'").fetchone()[0]
rows = [dict(r) for r in cursor.execute("SELECT * FROM call_outcomes ORDER BY started_at DESC LIMIT 50").fetchall()]
print(json.dumps({"total": total, "successful": succ, "failed": fail, "recent": rows}))
`;
      const output = execSync(`python3 -c "${pyScript.replace(/\n/g, ' ')}"`, {
        encoding: 'utf-8',
        timeout: 5000,
      });
      const parsed = JSON.parse(output.trim() || '{}');
      total = parsed.total || 0;
      successful = parsed.successful || 0;
      failed = parsed.failed || 0;
      recentCalls = parsed.recent || [];
    }

    return NextResponse.json({
      success: true,
      metrics: {
        total_calls: total,
        successful_calls: successful,
        failed_calls: failed,
        recent_calls: recentCalls,
      },
    });
  } catch (error) {
    console.error('Failed to fetch call metrics:', error);
    return NextResponse.json(
      {
        success: false,
        metrics: {
          total_calls: 0,
          successful_calls: 0,
          failed_calls: 0,
          recent_calls: [],
        },
        error: String(error),
      },
      { status: 500 }
    );
  }
}
