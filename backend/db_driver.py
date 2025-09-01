import sqlite3
import logging
from typing import Optional, List
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class Car:
    vin: str
    make: str
    model: str
    year: int
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} (VIN: {self.vin})"

class DatabaseDriver:
    def __init__(self, db_path: str = "auto_db.sqlite"):
        self.db_path = db_path
        logger.info(f"Initializing database at: {db_path}")
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _init_db(self):
        """Initialize the database with required tables"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create cars table with additional constraints
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cars (
                        vin TEXT PRIMARY KEY CHECK(length(vin) = 17),
                        make TEXT NOT NULL CHECK(length(make) > 0),
                        model TEXT NOT NULL CHECK(length(model) > 0),
                        year INTEGER NOT NULL CHECK(year >= 1900 AND year <= 2030),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create an index for faster lookups
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_make_model_year 
                    ON cars(make, model, year)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_car(self, vin: str, make: str, model: str, year: int) -> Optional[Car]:
        """Create a new car entry"""
        try:
            vin = vin.strip().upper()
            make = make.strip().title()
            model = model.strip().title()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO cars (vin, make, model, year) 
                       VALUES (?, ?, ?, ?)""",
                    (vin, make, model, year)
                )
                conn.commit()
                
                logger.info(f"Created car: {year} {make} {model} (VIN: {vin})")
                return Car(vin=vin, make=make, model=model, year=year)
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Car with VIN {vin} already exists")
                return None
            logger.error(f"Integrity error creating car: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating car: {e}")
            return None

    def get_car_by_vin(self, vin: str) -> Optional[Car]:
        """Get car by VIN"""
        try:
            vin = vin.strip().upper()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT vin, make, model, year FROM cars WHERE vin = ?", (vin,))
                row = cursor.fetchone()
                
                if not row:
                    logger.info(f"No car found with VIN: {vin}")
                    return None
                
                car = Car(
                    vin=row[0],
                    make=row[1],
                    model=row[2],
                    year=row[3]
                )
                
                logger.info(f"Found car: {car}")
                return car
                
        except Exception as e:
            logger.error(f"Error getting car by VIN {vin}: {e}")
            return None

    def get_cars_by_make_model(self, make: str, model: str) -> List[Car]:
        """Get cars by make and model"""
        try:
            make = make.strip().title()
            model = model.strip().title()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT vin, make, model, year FROM cars WHERE make = ? AND model = ?",
                    (make, model)
                )
                rows = cursor.fetchall()
                
                cars = [
                    Car(vin=row[0], make=row[1], model=row[2], year=row[3])
                    for row in rows
                ]
                
                logger.info(f"Found {len(cars)} cars for {make} {model}")
                return cars
                
        except Exception as e:
            logger.error(f"Error getting cars by make/model: {e}")
            return []

    def update_car(self, vin: str, make: str = None, model: str = None, year: int = None) -> Optional[Car]:
        """Update car details"""
        try:
            vin = vin.strip().upper()
            
            # Build dynamic query
            updates = []
            params = []
            
            if make:
                updates.append("make = ?")
                params.append(make.strip().title())
            if model:
                updates.append("model = ?")
                params.append(model.strip().title())
            if year:
                updates.append("year = ?")
                params.append(year)
                
            if not updates:
                logger.warning("No updates provided for car")
                return self.get_car_by_vin(vin)
                
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(vin)  # For WHERE clause
            
            query = f"UPDATE cars SET {', '.join(updates)} WHERE vin = ?"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount == 0:
                    logger.warning(f"No car found with VIN {vin} to update")
                    return None
                
                logger.info(f"Updated car with VIN: {vin}")
                return self.get_car_by_vin(vin)
                
        except Exception as e:
            logger.error(f"Error updating car: {e}")
            return None

    def delete_car(self, vin: str) -> bool:
        """Delete a car by VIN"""
        try:
            vin = vin.strip().upper()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cars WHERE vin = ?", (vin,))
                conn.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted car with VIN: {vin}")
                else:
                    logger.warning(f"No car found with VIN {vin} to delete")
                    
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting car: {e}")
            return False

    def get_all_cars(self) -> List[Car]:
        """Get all cars in the database"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT vin, make, model, year FROM cars ORDER BY make, model, year")
                rows = cursor.fetchall()
                
                cars = [
                    Car(vin=row[0], make=row[1], model=row[2], year=row[3])
                    for row in rows
                ]
                
                logger.info(f"Retrieved {len(cars)} cars from database")
                return cars
                
        except Exception as e:
            logger.error(f"Error getting all cars: {e}")
            return []

    def get_database_stats(self) -> dict:
        """Get database statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM cars")
                total_cars = cursor.fetchone()[0]
                
                # Get cars by make
                cursor.execute("""
                    SELECT make, COUNT(*) 
                    FROM cars 
                    GROUP BY make 
                    ORDER BY COUNT(*) DESC
                """)
                cars_by_make = dict(cursor.fetchall())
                
                stats = {
                    "total_cars": total_cars,
                    "cars_by_make": cars_by_make
                }
                
                logger.info(f"Database stats: {total_cars} total cars")
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"total_cars": 0, "cars_by_make": {}}