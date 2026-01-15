"""Tests for database restore with automatic migration functionality.

Verifies that:
1. Migrations are applied automatically to old database schemas
2. New columns are added without losing existing data
"""
import os
import sqlite3
import tempfile
import pytest
from io import BytesIO

from app.factory import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, ComponentAdjustment


def create_old_database_without_notes():
    """Create a database file with old schema (without notes column)."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables with old schema (without 'notes' column in component_adjustments)
    cursor.executescript('''
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
        
        CREATE TABLE participants (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        );
        
        CREATE TABLE monthly_bills (
            id INTEGER PRIMARY KEY,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            electricity_amount FLOAT NOT NULL,
            water_amount FLOAT NOT NULL,
            internet_amount FLOAT NOT NULL,
            archived BOOLEAN DEFAULT 0,
            UNIQUE (year, month)
        );
        
        CREATE TABLE bill_components (
            id INTEGER PRIMARY KEY,
            month_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            amount FLOAT NOT NULL,
            split_method VARCHAR(20) NOT NULL,
            position INTEGER DEFAULT 0,
            FOREIGN KEY (month_id) REFERENCES monthly_bills(id),
            UNIQUE (month_id, name)
        );
        
        CREATE TABLE component_adjustments (
            id INTEGER PRIMARY KEY,
            month_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            zero BOOLEAN DEFAULT 0,
            redis_rule JSON,
            FOREIGN KEY (month_id) REFERENCES monthly_bills(id),
            FOREIGN KEY (component_id) REFERENCES bill_components(id),
            FOREIGN KEY (participant_id) REFERENCES participants(id),
            UNIQUE (month_id, component_id, participant_id)
        );
        
        CREATE TABLE meter_readings (
            id INTEGER PRIMARY KEY,
            month_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            reading_current FLOAT NOT NULL,
            reading_previous FLOAT NOT NULL,
            FOREIGN KEY (month_id) REFERENCES monthly_bills(id),
            FOREIGN KEY (participant_id) REFERENCES participants(id),
            UNIQUE (month_id, participant_id)
        );
        
        CREATE TABLE month_participants (
            id INTEGER PRIMARY KEY,
            month_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            FOREIGN KEY (month_id) REFERENCES monthly_bills(id),
            FOREIGN KEY (participant_id) REFERENCES participants(id),
            UNIQUE (month_id, participant_id)
        );
        
        -- Insert test data
        INSERT INTO participants (id, name) VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie');
        
        INSERT INTO monthly_bills (id, year, month, electricity_amount, water_amount, internet_amount)
        VALUES (1, 2025, 10, 500.0, 150.0, 100.0);
        
        INSERT INTO bill_components (id, month_id, name, amount, split_method, position)
        VALUES 
            (1, 1, 'Electricity', 500.0, 'usage', 0),
            (2, 1, 'Water', 150.0, 'equal', 1);
        
        INSERT INTO component_adjustments (id, month_id, component_id, participant_id, zero, redis_rule)
        VALUES (1, 1, 2, 1, 1, '{"mode": "percent", "targets": {"2": 50, "3": 50}}');
        
        INSERT INTO meter_readings (id, month_id, participant_id, reading_current, reading_previous)
        VALUES 
            (1, 1, 1, 200, 100),
            (2, 1, 2, 150, 100),
            (3, 1, 3, 180, 100);
        
        -- Set old migration version
        INSERT INTO alembic_version (version_num) VALUES ('cccccccccccc');
    ''')
    
    conn.commit()
    conn.close()
    
    return db_path


class TestMigrationAddsNotesColumn:
    """Test that migration adds notes column to old databases."""
    
    def test_old_database_has_no_notes_column(self):
        """Verify our test database truly lacks the notes column."""
        db_path = create_old_database_without_notes()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(component_adjustments)")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()
            
            assert 'notes' not in columns
            assert 'zero' in columns
            assert 'redis_rule' in columns
        finally:
            os.unlink(db_path)
    
    def test_data_preserved_after_adding_column(self):
        """Test that existing data is preserved after adding notes column."""
        db_path = create_old_database_without_notes()
        try:
            # Manually add the notes column (simulating what upload does)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("ALTER TABLE component_adjustments ADD COLUMN notes VARCHAR(255)")
            conn.commit()
            
            # Check data is preserved
            cursor.execute("SELECT name FROM participants ORDER BY id")
            names = [row[0] for row in cursor.fetchall()]
            assert names == ['Alice', 'Bob', 'Charlie']
            
            # Check monthly bill
            cursor.execute("SELECT year, month, electricity_amount FROM monthly_bills")
            bill = cursor.fetchone()
            assert bill == (2025, 10, 500.0)
            
            # Check components
            cursor.execute("SELECT name FROM bill_components ORDER BY position")
            comp_names = [row[0] for row in cursor.fetchall()]
            assert comp_names == ['Electricity', 'Water']
            
            # Check adjustment with redis_rule
            cursor.execute("SELECT zero, redis_rule FROM component_adjustments WHERE id = 1")
            adj = cursor.fetchone()
            assert adj[0] == 1  # zero = True
            assert '{"mode": "percent"' in adj[1]
            
            conn.close()
        finally:
            os.unlink(db_path)
    
    def test_notes_can_be_used_after_adding_column(self):
        """Test that notes column can be used after being added."""
        db_path = create_old_database_without_notes()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Add notes column
            cursor.execute("ALTER TABLE component_adjustments ADD COLUMN notes VARCHAR(255)")
            conn.commit()
            
            # Insert a new row with notes
            cursor.execute('''
                INSERT INTO component_adjustments 
                (month_id, component_id, participant_id, zero, redis_rule, notes)
                VALUES (1, 1, 2, 1, '{"mode": "amount", "targets": {"3": 100}}', 'Test note')
            ''')
            conn.commit()
            
            # Verify
            cursor.execute("SELECT notes FROM component_adjustments WHERE participant_id = 2")
            notes = cursor.fetchone()[0]
            assert notes == 'Test note'
            
            conn.close()
        finally:
            os.unlink(db_path)


class TestDatabaseUploadAppliesMigration:
    """Test that database upload via route applies migrations."""
    
    @pytest.fixture
    def app_with_file_db(self):
        """Create app with a file-based SQLite database for testing."""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        app = create_app()
        app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'WTF_CSRF_ENABLED': False,
        })
        
        with app.app_context():
            db.create_all()
            yield app, db_path
            db.session.remove()
        
        # Cleanup
        try:
            os.unlink(db_path)
        except OSError:
            pass
        # Also clean up any backup files
        import glob
        for f in glob.glob(db_path + '.backup_*'):
            try:
                os.unlink(f)
            except OSError:
                pass
    
    def test_upload_triggers_migration(self, app_with_file_db):
        """Test that uploading old DB file triggers migration."""
        app, current_db_path = app_with_file_db
        client = app.test_client()
        
        old_db_path = create_old_database_without_notes()
        
        try:
            with open(old_db_path, 'rb') as f:
                old_db_content = f.read()
            
            data = {"database": (BytesIO(old_db_content), "backup.db")}
            response = client.post(
                "/settings/database",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True
            )
            
            assert response.status_code == 200
            
            # Check that the database now has the notes column
            conn = sqlite3.connect(current_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(component_adjustments)")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()
            
            assert 'notes' in columns
            
            # Check success message
            assert b"Database replaced" in response.data or b"migration" in response.data.lower()
        finally:
            os.unlink(old_db_path)
    
    def test_upload_preserves_data_from_old_db(self, app_with_file_db):
        """Test that data from uploaded DB is preserved."""
        app, current_db_path = app_with_file_db
        client = app.test_client()
        
        old_db_path = create_old_database_without_notes()
        
        try:
            with open(old_db_path, 'rb') as f:
                old_db_content = f.read()
            
            data = {"database": (BytesIO(old_db_content), "backup.db")}
            client.post(
                "/settings/database",
                data=data,
                content_type="multipart/form-data",
                follow_redirects=True
            )
            
            # Check that data was preserved using raw SQL
            conn = sqlite3.connect(current_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM participants ORDER BY id")
            names = [row[0] for row in cursor.fetchall()]
            assert names == ['Alice', 'Bob', 'Charlie']
            
            cursor.execute("SELECT year, month FROM monthly_bills")
            bill = cursor.fetchone()
            assert bill == (2025, 10)
            
            conn.close()
        finally:
            os.unlink(old_db_path)
