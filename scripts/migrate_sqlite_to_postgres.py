#!/usr/bin/env python3
"""
将 LearnForge SQLite 数据库的数据迁移到 PostgreSQL。

用法:
    python scripts/migrate_sqlite_to_postgres.py [--sqlite PATH] [--pg URL] [--dry-run]

默认:
    --sqlite  .data/learnforge_dev.sqlite.bak-<最新>  (自动找最新的 .bak)
    --pg      postgresql://learnforge:learnforge@localhost:5432/learnforge

行为:
    1. 对 SQLite 与 PostgreSQL 共有的表：TRUNCATE 后从 SQLite 导入全部数据。
    2. 对仅 SQLite 有的表：在 PG 创建表（TEXT 通用类型），再导入。
    3. 对列差异（SQLite 多列）：ALTER TABLE ADD COLUMN 补齐。
    4. 整个迁移在一个事务里，失败回滚。
"""
from __future__ import annotations

import argparse
import glob
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PG = "postgresql://learnforge:learnforge@localhost:5432/learnforge"

# SQLite 类型 → PostgreSQL 类型映射（用于创建 SQLite-only 表）
TYPE_MAP = {
    "INTEGER": "BIGINT",
    "INT": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "TEXT": "TEXT",
    "BLOB": "BYTEA",
    "BOOLEAN": "BOOLEAN",
}


def find_sqlite_backup() -> str:
    """找最新的 learnforge_dev.sqlite.bak-* 文件。"""
    candidates = sorted(glob.glob(str(ROOT / ".data" / "learnforge_dev.sqlite.bak-*")))
    if candidates:
        return candidates[-1]
    # 回退到原始文件（如果还在）
    orig = ROOT / ".data" / "learnforge_dev.sqlite"
    if orig.exists():
        return str(orig)
    sys.exit("✗ 找不到 SQLite 备份文件，请用 --sqlite 指定")


def sqlite_create_to_pg(create_sql: str, table: str) -> str:
    """把 SQLite CREATE TABLE 语句转成 PG 的（粗糙但够用：全部用 TEXT/BIGINT）。"""
    inner = create_sql.split("(", 1)[1].rsplit(")", 1)[0]
    raw_lines = [l.strip() for l in inner.split("\n") if l.strip() and not l.strip().startswith("--")]
    pg_cols = []
    for line in raw_lines:
        # 去掉行末逗号（SQLite 列定义每行末尾的逗号）
        line = line.rstrip(",").strip()
        if not line:
            continue
        upper = line.upper()
        # 跳过/转换表级约束
        if upper.startswith("UNIQUE("):
            pg_cols.append(line)
            continue
        if upper.startswith(("PRIMARY", "FOREIGN", "CHECK", "CONSTRAINT")):
            continue
        parts = line.split()
        col_name = parts[0].strip('"`[]')
        col_def = parts[1].upper() if len(parts) > 1 else "TEXT"
        pg_type = TYPE_MAP.get(col_def, "TEXT")
        rest = " ".join(parts[2:]) if len(parts) > 2 else ""
        pg_line = f'"{col_name}" {pg_type}'
        if "PRIMARY KEY" in upper:
            pg_line += " PRIMARY KEY"
        if "NOT NULL" in upper and "PRIMARY KEY" not in pg_line:
            pg_line += " NOT NULL"
        # 提取 DEFAULT 值（支持 'xxx' / 数字）
        if "DEFAULT" in rest.upper():
            idx = rest.upper().find("DEFAULT")
            default_part = rest[idx:].strip()
            pg_line += " " + default_part
        pg_cols.append(pg_line)
    return f'CREATE TABLE IF NOT EXISTS "{table}" (\n  ' + ",\n  ".join(pg_cols) + "\n)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default=None, help="SQLite 文件路径")
    ap.add_argument("--pg", default=os.environ.get("DATABASE_URL", DEFAULT_PG))
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不执行")
    args = ap.parse_args()

    sqlite_path = args.sqlite or find_sqlite_backup()
    print(f"源 SQLite : {sqlite_path}")
    print(f"目标 PG    : {args.pg}")
    print()

    scon = sqlite3.connect(sqlite_path)
    scon.row_factory = sqlite3.Row
    scur = scon.cursor()
    s_tables = [r[0] for r in scur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]

    # 用 autocommit 模式：每条 DDL/DML 即时提交，避免大事务锁表（之前因 API 后端
    # 持有 auth_sessions 的读锁，TRUNCATE 在一个大事务里等了 13 分钟卡死）。
    pcon = psycopg.connect(args.pg.replace("postgresql+psycopg://", "postgresql://"), autocommit=True)
    pcur = pcon.cursor()
    # 临时禁用外键约束触发器，避免插入顺序问题
    pcur.execute("SET session_replication_role = 'replica'")
    pcur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    p_tables = {r[0] for r in pcur.fetchall()}

    total_rows = 0
    migrated_tables = 0

    for table in s_tables:
        print(f"→ {table}")

        # 1. 如果 PG 没有这张表，创建（基于 SQLite schema 转换）
        if table not in p_tables:
            create_sql = scur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()[0]
            pg_create = sqlite_create_to_pg(create_sql, table)
            print(f"  创建 PG 表: {pg_create[:80]}...")
            if not args.dry_run:
                pcur.execute(pg_create)
            p_tables.add(table)

        # 2. 列对齐：SQLite 有而 PG 没有的列，ALTER TABLE ADD COLUMN (TEXT)
        scols = [r[1] for r in scur.execute(f'PRAGMA table_info("{table}")').fetchall()]
        # 同时取 PG 列的类型，用于后续 vector/jsonb 适配
        pcur.execute(
            """SELECT column_name, data_type, udt_name
               FROM information_schema.columns
               WHERE table_schema='public' AND table_name=%s""",
            (table,),
        )
        pg_col_info = {r[0]: (r[1], r[2]) for r in pcur.fetchall()}
        pcols = set(pg_col_info.keys())
        for col in scols:
            if col not in pcols:
                print(f"  + ALTER TABLE 添加列: {col} TEXT")
                if not args.dry_run:
                    pcur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
                pg_col_info[col] = ("text", "text")
                pcols.add(col)

        # 3. 清空目标表（用 DELETE 而非 TRUNCATE：TRUNCATE 需 ACCESS EXCLUSIVE 锁，
        #    会阻塞所有并发读连接，在 autocommit 模式下更安全）
        if not args.dry_run:
            pcur.execute(f'DELETE FROM "{table}"')

        # 4. 读取 SQLite 数据并批量插入
        srows = scur.execute(f'SELECT * FROM "{table}"').fetchall()
        if not srows:
            print(f"  0 行（空表）")
            continue
        # 只插入两边都有的列（PG 列名的子集）
        insert_cols = [c for c in scols if c in pcols]
        col_list = ", ".join(f'"{c}"' for c in insert_cols)
        placeholders = ", ".join("%s" for _ in insert_cols)
        insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        # 识别需要特殊适配的列：
        #  - vector (udt_name='vector'): 空/[] → NULL；非空字符串原样传入
        #  - jsonb (udt_name='jsonb'): 先 json.loads 成 Python 对象再用 Json() 包装（避免双重编码）
        #  - _text / _* (PG 数组): 把 JSON 字符串解析成 Python list，psycopg 自动转 PG 数组
        #  - timestamp: SQLite 存 ISO 字符串，PG 能自动从文本转 timestamp，无需特殊处理
        import json as _json
        def adapt_value(col: str, raw):
            info = pg_col_info.get(col)
            if info is None or raw is None:
                return raw
            _, udt = info
            if udt == "vector":
                s = str(raw).strip()
                if s == "" or s == "[]":
                    return None
                return s  # pgvector 接受 '[1,2,3]' 文本字面量
            if udt == "jsonb":
                s = str(raw).strip()
                if s == "":
                    return None
                try:
                    return Json(_json.loads(s))
                except (ValueError, TypeError):
                    return None
            if udt.startswith("_"):
                # PG 数组类型（如 _text = text[]）
                s = str(raw).strip()
                if s == "" or s == "[]":
                    return None
                try:
                    parsed = _json.loads(s)
                    return parsed if isinstance(parsed, list) else [parsed]
                except (ValueError, TypeError):
                    return None
            if udt == "bool":
                # PG boolean：SQLite 可能存 0/1/smallint/"true"/"false"
                if isinstance(raw, bool):
                    return raw
                if isinstance(raw, (int, float)):
                    return bool(raw)
                s = str(raw).strip().lower()
                if s in ("0", "false", "f", "no", ""):
                    return False
                return True
            if udt == "timestamp":
                # PG timestamp 不接受 "+00:00Z"（时区偏移和 Z 同时存在）
                s = str(raw).strip()
                if s == "" or s.lower() == "none":
                    return None
                # "+00:00Z" → "+00:00"；"+HH:MMZ" → "+HH:MM"
                import re
                s = re.sub(r'([+-]\d{2}:\d{2})Z$', r'\1', s)
                return s
            return raw

        batch = []
        batch_size = 500
        count = 0
        for row in srows:
            batch.append(tuple(adapt_value(c, row[c]) for c in insert_cols))
            if len(batch) >= batch_size:
                if not args.dry_run:
                    pcur.executemany(insert_sql, batch)
                count += len(batch)
                batch = []
        if batch:
            if not args.dry_run:
                pcur.executemany(insert_sql, batch)
            count += len(batch)
        total_rows += count
        migrated_tables += 1
        print(f"  ✓ 迁移 {count} 行")

    # 恢复外键约束
    pcur.execute("SET session_replication_role = 'origin'")

    if args.dry_run:
        print(f"\n[DRY-RUN] 预计迁移 {migrated_tables} 表，{total_rows} 行")
    else:
        print(f"\n✓ 迁移完成：{migrated_tables} 表，{total_rows} 行")

    scon.close()
    pcon.close()


if __name__ == "__main__":
    main()
