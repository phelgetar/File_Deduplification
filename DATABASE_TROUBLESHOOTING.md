# Database Troubleshooting Guide

## Issue: MySQL User Resource Limit Exceeded

### Error Message
```
(pymysql.err.OperationalError) (1226, "User 'jarheads_0231' has exceeded the 'max_questions' resource (current value: 999999)")
```

### What This Means
MySQL has a per-user resource limit on the number of queries that can be executed per hour. Your user `jarheads_0231` has reached the limit of 999,999 queries.

---

## 🔧 Solutions

### Option 1: Wait for Reset (Easiest)
MySQL resource limits reset **every hour** from when they were first set. If you hit the limit, you can:
- Wait for the next hour boundary
- The counter will automatically reset to 0

### Option 2: Flush User Resources (Requires Admin)
If you have MySQL admin privileges:

```sql
-- Connect as root or admin
mysql -u root -p

-- Flush the user's resource limits
FLUSH USER_RESOURCES;

-- Or specifically for your user
FLUSH PRIVILEGES;
```

### Option 3: Increase User Limits (Permanent Fix)
Increase the query limit for your user:

```sql
-- Connect as root or admin
mysql -u root -p

-- Check current limits
SELECT * FROM mysql.user WHERE User='jarheads_0231'\G

-- Increase max_questions (or set to 0 for unlimited)
ALTER USER 'jarheads_0231'@'localhost'
  WITH MAX_QUERIES_PER_HOUR 0;

-- Or set a higher limit (e.g., 10 million)
ALTER USER 'jarheads_0231'@'localhost'
  WITH MAX_QUERIES_PER_HOUR 10000000;

-- Apply changes
FLUSH PRIVILEGES;
```

### Option 4: Disable Database Logging Temporarily
If you don't need database logging for this scan:

```bash
# Run without --use-db flag
python main.py /your/source --base-dir /output --metadata-only-size 75MB

# Files will still be processed, but not saved to database
```

### Option 5: Use Batch Processing
Process files in smaller batches:

```bash
# Process with max file limit
python main.py /your/source --base-dir /output --use-db --max-files 1000

# Then continue with next batch
python main.py /your/source --base-dir /output --use-db --max-files 1000 --filter next_folder
```

---

## 🔍 Understanding the Issue

### Why Did This Happen?
Processing **76,562 files** generates a LOT of database queries:
- Minimum: 76,562 queries (1 per file)
- With classification: ~150,000 queries (2 per file)
- With caching checks: ~230,000 queries (3 per file)

This easily exceeds the 999,999 query limit.

### Query Breakdown Per File
For each file, the system makes:
1. **Hasher**: Check cache (1 query)
2. **Hasher**: Insert/update file entry (1 query)
3. **Classifier**: Save classification (1 query)

**Total**: ~3 queries per file × 76,562 files = **~230,000 queries**

---

## 🚀 Performance Optimizations

### 1. Batch Database Operations
Currently, each file is saved individually. To reduce queries, we could implement batch inserts:

```python
# Instead of:
for file in files:
    cache_file_entry(file)  # 1 query per file

# Use batch insert:
batch_cache_file_entries(files)  # 1 query for all files
```

### 2. Use Connection Pooling
Ensure you're reusing database connections:

```python
# In db.py
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,          # Connection pool
    max_overflow=20,       # Extra connections
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### 3. Increase Batch Size
Process files in larger batches before committing:

```python
# Commit every 100 files instead of every file
session.add(file_entry)
if index % 100 == 0:
    session.commit()
```

---

## 📊 Checking Your Limits

### View Current Resource Usage
```sql
SHOW PROCESSLIST;

SELECT * FROM information_schema.USER_STATISTICS
WHERE USER='jarheads_0231';
```

### View Current Limits
```sql
SELECT
    User,
    Host,
    max_questions,
    max_updates,
    max_connections,
    max_user_connections
FROM mysql.user
WHERE User='jarheads_0231';
```

---

## 🎯 Recommended Settings for Large Scans

For processing large file collections (50,000+ files), set these limits:

```sql
-- As MySQL root/admin
ALTER USER 'jarheads_0231'@'localhost'
  WITH
    MAX_QUERIES_PER_HOUR 0              -- Unlimited queries
    MAX_UPDATES_PER_HOUR 0              -- Unlimited updates
    MAX_CONNECTIONS_PER_HOUR 0          -- Unlimited connections
    MAX_USER_CONNECTIONS 10;            -- Max simultaneous connections

FLUSH PRIVILEGES;
```

---

## 🛡️ Alternative: Use Local SQLite

If MySQL limits are an issue, you can use SQLite for large scans:

### Option A: Modify .env Temporarily
```env
# Comment out MySQL
# DATABASE_URL=mysql+pymysql://...

# Use SQLite instead
DATABASE_URL=sqlite:///file_dedup.db
```

### Option B: Hybrid Approach
1. Use SQLite for initial large scan
2. Export results to CSV
3. Import into MySQL when needed

---

## 📝 Best Practices

### For Regular Use
1. **Use `--max-files`** to limit file count
2. **Process in batches** by directory
3. **Disable DB** for exploratory scans
4. **Enable DB** only for final organized scans

### For Large Collections
1. **Increase MySQL limits** before starting
2. **Use `--metadata-only-size`** to reduce processing
3. **Monitor resource usage** during scan
4. **Consider SQLite** for one-time scans

---

## 🔧 Quick Fix Commands

### Reset Limits Immediately
```bash
# As MySQL admin
mysql -u root -p -e "FLUSH USER_RESOURCES;"
```

### Check Time Until Reset
```sql
-- Check when user resources were last reset
SELECT USER, HOST,
       TIME_FORMAT(SEC_TO_TIME(MAX_QUERIES_PER_HOUR -
       VARIABLE_VALUE), '%H:%i:%s') AS time_until_reset
FROM mysql.user
JOIN information_schema.USER_STATISTICS USING (USER, HOST)
WHERE USER='jarheads_0231';
```

### Verify Limits Are Removed
```bash
mysql -u jarheads_0231 -p -e "
SELECT User,
       max_questions as 'Max Queries',
       IF(max_questions = 0, 'UNLIMITED', max_questions) as 'Status'
FROM mysql.user
WHERE User='jarheads_0231'\G
"
```

---

## 🆘 Emergency Workaround

If you MUST complete the scan RIGHT NOW and can't modify limits:

1. **Kill the current process** (Ctrl+C)
2. **Run without database**:
   ```bash
   python main.py /your/source --base-dir /output --metadata-only-size 75MB
   ```
3. **Save the dry-run log**:
   ```bash
   python main.py /your/source --base-dir /output --dry-run-log
   ```
4. **Import to database later** using the JSON log

---

## 📖 Related Documentation

- [MySQL Resource Limit Documentation](https://dev.mysql.com/doc/refman/8.0/en/user-resources.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html)

---

## ✅ Verification Checklist

After applying fixes:

- [ ] User resource limits increased or removed
- [ ] FLUSH PRIVILEGES executed
- [ ] Test query executes successfully
- [ ] Re-run file scan
- [ ] Monitor query count during scan
- [ ] Verify data in database

---

**Last Updated**: 2025-11-13
**Version**: 0.7.0
