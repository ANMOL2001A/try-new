import enum
from typing import Annotated
import logging
from db_driver import DatabaseDriver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("user-data")

DB = DatabaseDriver()

class CarDetails(enum.Enum):
    VIN = "vin"
    MAKE = "make"
    MODEL = "model"
    YEAR = "year"

class AssistantFnc:
    def __init__(self):
        super().__init__()
        
        self._car_details = {
            CarDetails.VIN: "",
            CarDetails.MAKE: "",
            CarDetails.MODEL: "",
            CarDetails.YEAR: ""
        }
        logger.info("AssistantFnc initialized")
    
    def get_car_str(self) -> str:
        """Format car details as a readable string"""
        if not self.has_car():
            return "No car profile found"
            
        car_info = []
        for key, value in self._car_details.items():
            if value:  # Only include non-empty values
                car_info.append(f"{key.value.title()}: {value}")
                
        return "\n".join(car_info) if car_info else "No car details available"
    
    def lookup_car(self, vin: str):
        """Look up car details by VIN"""
        logger.info(f"Looking up car with VIN: {vin}")
        
        try:
            # Clean and validate VIN
            vin = vin.strip().upper()
            if len(vin) != 17:
                return f"Invalid VIN format. VIN should be 17 characters long. You provided: {len(vin)} characters."
            
            result = DB.get_car_by_vin(vin)
            if result is None:
                logger.info(f"Car not found for VIN: {vin}")
                return f"No car found with VIN: {vin}. Would you like me to help you create a new profile?"
            
            # Update internal car details
            self._car_details = {
                CarDetails.VIN: result.vin,
                CarDetails.MAKE: result.make,
                CarDetails.MODEL: result.model,
                CarDetails.YEAR: str(result.year)
            }
            
            logger.info(f"Car found: {result.make} {result.model} {result.year}")
            return f"Great! I found your vehicle:\n{self.get_car_str()}\n\nHow can I help you with your {result.year} {result.make} {result.model} today?"
            
        except Exception as e:
            logger.error(f"Error looking up car: {e}")
            return "I encountered an error looking up your vehicle. Please try again or contact support."
    
    def get_car_details(self):
        """Get current car details"""
        logger.info("Getting current car details")
        
        if not self.has_car():
            return "No car profile is currently loaded. Please provide your VIN or create a new profile."
            
        return f"Current vehicle details:\n{self.get_car_str()}"
    
    def create_car(
        self, 
        vin: str,
        make: str,
        model: str,
        year: int
    ):
        """Create a new car profile"""
        logger.info(f"Creating car - VIN: {vin}, Make: {make}, Model: {model}, Year: {year}")
        
        try:
            # Validate inputs
            vin = vin.strip().upper()
            make = make.strip().title()
            model = model.strip().title()
            
            if len(vin) != 17:
                return f"Invalid VIN format. VIN must be exactly 17 characters. You provided: {len(vin)} characters."
                
            if year < 1900 or year > 2030:
                return f"Invalid year: {year}. Please provide a valid year between 1900 and 2030."
            
            # Check if car already exists
            existing_car = DB.get_car_by_vin(vin)
            if existing_car:
                return f"A car with VIN {vin} already exists in our system. It's a {existing_car.year} {existing_car.make} {existing_car.model}."
            
            # Create new car
            result = DB.create_car(vin, make, model, year)
            if result is None:
                return "Failed to create car profile. Please try again or contact support."
            
            # Update internal car details
            self._car_details = {
                CarDetails.VIN: result.vin,
                CarDetails.MAKE: result.make,
                CarDetails.MODEL: result.model,
                CarDetails.YEAR: str(result.year)
            }
            
            logger.info(f"Car profile created successfully: {make} {model} {year}")
            return f"Perfect! I've created your car profile:\n{self.get_car_str()}\n\nYour profile is now set up. How can I assist you with your {year} {make} {model} today?"
            
        except Exception as e:
            logger.error(f"Error creating car: {e}")
            return "I encountered an error creating your car profile. Please try again or contact support."
    
    def transfer_to_department(
        self, 
        department: str
    ):
        """Transfer customer to appropriate department"""
        logger.info(f"Transferring customer to {department} department")
        
        department_info = {
            "service": "Service Department - for maintenance, repairs, and appointments",
            "parts": "Parts Department - for ordering replacement parts and accessories",
            "billing": "Billing Department - for payment questions and account issues", 
            "warranty": "Warranty Department - for warranty claims and coverage questions",
            "sales": "Sales Department - for new vehicle purchases and trade-ins"
        }
        
        dept_lower = department.lower()
        if dept_lower in department_info:
            return f"I'm transferring you to our {department_info[dept_lower]}. Please hold while I connect you. A specialist will be with you shortly."
        else:
            return f"I'm transferring you to our {department} department. Please hold while I connect you."
    
    def has_car(self) -> bool:
        """Check if a car profile is currently loaded"""
        return self._car_details[CarDetails.VIN] != ""
    
    def get_car_vin(self) -> str:
        """Get the VIN of the current car"""
        return self._car_details[CarDetails.VIN]
    
    def reset_car_profile():
        """Reset the current car profile"""
        logger.info("Resetting car profile")
        self._car_details = {
            CarDetails.VIN: "",
            CarDetails.MAKE: "",
            CarDetails.MODEL: "",
            CarDetails.YEAR: ""
        }

    def get_tools(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "lookup_car",
                    "description": "Look up a car by its VIN number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vin": {"type": "string", "description": "The VIN (Vehicle Identification Number) of the car to lookup"}
                        },
                        "required": ["vin"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_car_details",
                    "description": "Get the details of the currently loaded car profile",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_car",
                    "description": "Create a new car profile in the database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vin": {"type": "string", "description": "The VIN (Vehicle Identification Number) of the car - must be 17 characters"},
                            "make": {"type": "string", "description": "The manufacturer/make of the car (e.g., Toyota, Ford, BMW)"},
                            "model": {"type": "string", "description": "The model of the car (e.g., Camry, F-150, X3)"},
                            "year": {"type": "integer", "description": "The year the car was manufactured"},
                        },
                        "required": ["vin", "make", "model", "year"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "transfer_to_department",
                    "description": "Transfer customer to a specific department",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "department": {"type": "string", "description": "Department name (e.g., 'service', 'parts', 'billing', 'warranty')"}
                        },
                        "required": ["department"],
                    },
                },
            },
        ]