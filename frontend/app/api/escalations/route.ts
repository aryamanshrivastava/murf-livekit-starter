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
      return NextResponse.json({ success: true, escalations: [] });
    }

    let rows: any[] = [];
    try {
      const { DatabaseSync } = await import('node:sqlite');
      const db = new DatabaseSync(targetDbPath);
      rows = db.prepare('SELECT * FROM escalation_requests ORDER BY created_at DESC').all();
    } catch (sqliteErr) {
      console.warn('node:sqlite failed, trying fallback:', sqliteErr);
      const { execSync } = await import('child_process');
      const pyScript = `import sqlite3, json
conn = sqlite3.connect('${targetDbPath.replace(/\\/g, '/')}')
conn.row_factory = sqlite3.Row
print(json.dumps([dict(r) for r in conn.execute("SELECT * FROM escalation_requests ORDER BY created_at DESC").fetchall()]))
`;
      const output = execSync(`python3 -c "${pyScript.replace(/\n/g, ' ')}"`, {
        encoding: 'utf-8',
        timeout: 5000,
      });
      rows = JSON.parse(output.trim() || '[]');
    }

    const mappedRows = rows.map((r: any) => {
      const text = `${r.category || ''} ${r.issue_summary || ''}`.toLowerCase();
      let computedUrgency = (r.urgency_level || '').toUpperCase();
      if (/payment|payout|refund|billing|dispute|money/.test(text)) {
        computedUrgency = 'CRITICAL';
      } else if (/delivery|shipping|courier|delayed|delay|logistics|package|dispatch/.test(text)) {
        computedUrgency = 'HIGH';
      } else if (!['CRITICAL', 'HIGH', 'LOW'].includes(computedUrgency)) {
        computedUrgency = 'MEDIUM';
      }
      return { ...r, urgency_level: computedUrgency };
    });

    return NextResponse.json({ success: true, escalations: mappedRows });
  } catch (error) {
    console.error('Failed to fetch escalations:', error);
    return NextResponse.json(
      { success: false, escalations: [], error: String(error) },
      { status: 500 }
    );
  }
}
